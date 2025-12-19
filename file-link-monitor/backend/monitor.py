import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from backend.models import LinkRecord, get_session
from backend.utils.linker import FileLinker
from backend.utils.notifier import Notifier
from backend.utils.taosync import TaoSyncClient, TaoSyncQueue

logger = logging.getLogger(__name__)


class FileMonitorHandler(FileSystemEventHandler):
    """文件监控处理器"""
    
    def __init__(self, source_path: str, target_configs: List[dict], 
                 exclude_patterns: List[str], db_engine, config: dict, obfuscate_enabled: bool = False,
                 template_files_path: str = None):
        self.source_path = Path(source_path)
        self.target_configs = target_configs  # [{"path": "...", "name": "..."}, ...]
        self.target_paths = [Path(t['path'] if isinstance(t, dict) else t) for t in target_configs]
        self.exclude_patterns = exclude_patterns or []
        self.db_engine = db_engine
        self.obfuscate_enabled = obfuscate_enabled
        self.linker = FileLinker(obfuscate_enabled=obfuscate_enabled, db_engine=db_engine)
        self.notifier = Notifier(config)
        self.template_files_path = Path(template_files_path) if template_files_path else None
        self.linked_dirs = set()  # 记录已经链接过模板文件的目录
        
        # 初始化TaoSync客户端和队列
        self.taosync_queue = None
        taosync_config = config.get('taosync', {})
        if taosync_config.get('enabled'):
            # 读取任务ID配置（支持列表或单个ID）
            job_id_config = taosync_config.get('job_id')
            if isinstance(job_id_config, list):
                # 列表格式：[1, 2, 3]
                job_ids = job_id_config
            elif isinstance(job_id_config, (int, str)):
                # 单个ID或逗号分隔的字符串："1,2,3"
                if isinstance(job_id_config, str) and ',' in job_id_config:
                    job_ids = [int(x.strip()) for x in job_id_config.split(',')]
                else:
                    job_ids = [int(job_id_config)]
            else:
                job_ids = [1]  # 默认值
            
            taosync_client = TaoSyncClient(
                url=taosync_config.get('url', ''),
                username=taosync_config.get('username', 'admin'),
                password=taosync_config.get('password', ''),
                job_ids=job_ids  # 使用job_ids参数
            )
            # 创建队列管理器，设置检查间隔
            check_interval = taosync_config.get('check_interval', 60)  # 默认60秒
            self.taosync_queue = TaoSyncQueue(
                client=taosync_client,
                check_interval=check_interval,
                notifier=lambda msg: self.notifier.notify_info("TaoSync队列", msg)
            )
            self.taosync_queue.start()
            logger.info(f"TaoSync已启用，任务ID: {job_ids}，队列检查间隔: {check_interval}秒")
        
        # 批次汇总相关
        self.batch_files = []  # 批次处理的文件列表
        self.last_process_time = None  # 最后处理时间
        self.batch_timer = None  # 汇总定时器
        self.batch_lock = threading.Lock()  # 批次数据锁
        
        logger.info(f"初始化监控: {source_path} -> {self.target_paths}, 混淆: {obfuscate_enabled}")
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        logger.info(f"检测到新文件: {file_path}")
        self._process_file(file_path)
    
    def on_moved(self, event):
        """文件移动事件"""
        if event.is_directory:
            return
        
        file_path = Path(event.dest_path)
        logger.info(f"检测到文件移动: {file_path}")
        self._process_file(file_path)
    
    def _process_file(self, file_path: Path):
        """处理文件"""
        # 等待文件写入完成
        time.sleep(1)
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return
        
        # 只处理媒体文件（视频+字幕）
        from backend.utils.obfuscator import FolderObfuscator
        if not FolderObfuscator.is_media_file(file_path):
            logger.debug(f"非媒体文件，跳过: {file_path}")
            return
        
        # 检查是否应该排除
        if self.linker.should_exclude(file_path, self.exclude_patterns):
            logger.info(f"文件被排除: {file_path}")
            return
        
        # 获取相对路径
        try:
            relative_path = file_path.relative_to(self.source_path)
        except ValueError:
            logger.error(f"文件不在源目录中: {file_path}")
            return
        
        # 获取文件大小
        try:
            file_size = file_path.stat().st_size
        except Exception as e:
            logger.error(f"获取文件大小失败: {e}")
            file_size = 0
        
        # 为每个目标目录创建硬链接
        session = get_session(self.db_engine)
        success_count = 0
        failed_count = 0
        last_error = None
        success_targets = []
        
        try:
            for idx, target_path in enumerate(self.target_paths):
                target_file = target_path / relative_path
                
                logger.info(f"创建链接: {file_path} -> {target_file}")
                success, method, error, actual_target = self.linker.create_hardlink(
                    file_path, target_file, 
                    source_base=self.source_path, 
                    target_base=target_path
                )
                
                if success:
                    success_count += 1
                    # 获取目标目录的自定义名称
                    target_config = self.target_configs[idx]
                    target_name = target_config.get('name', target_config.get('path', str(target_path))) if isinstance(target_config, dict) else str(target_path)
                    success_targets.append(f"{target_name}: {file_path.name}")
                    
                    # 自动链接模板文件到剧集文件夹（只链接一次）
                    if self.template_files_path and self.template_files_path.exists() and actual_target:
                        target_show_dir = actual_target.parent  # 使用实际创建的文件路径
                        # 如果是季度文件夹，获取剧集根目录
                        if target_show_dir.name.startswith('Season'):
                            target_show_dir = target_show_dir.parent
                        
                        # 使用目录路径作为唯一标识，避免重复链接
                        dir_key = str(target_show_dir)
                        if dir_key not in self.linked_dirs:
                            linked_count = self.linker.link_template_files(target_show_dir, self.template_files_path)
                            if linked_count > 0:
                                logger.info(f"✓ 已链接 {linked_count} 个模板文件到: {target_show_dir}")
                                self.linked_dirs.add(dir_key)
                else:
                    failed_count += 1
                    last_error = error
                
                # 记录到数据库（保存实际创建的混淆后路径）
                # 查询或创建记录
                record = session.query(LinkRecord).filter(
                    LinkRecord.source_file == str(file_path)
                ).first()
                
                if not record:
                    # 创建新记录
                    from backend.utils.obfuscator import FolderObfuscator
                    original_name = FolderObfuscator.extract_show_name(file_path)
                    record = LinkRecord(
                        source_file=str(file_path),
                        original_name=original_name,
                        file_size=file_size
                    )
                    session.add(record)
                
                # 根据target_name判断是哪个网盘
                target_config = self.target_configs[idx]
                target_name = target_config.get('name', '') if isinstance(target_config, dict) else ''
                
                if success and actual_target:
                    # 根据网盘名称更新对应字段
                    if '夸克' in target_name or '测试1' in target_name or idx == 0:
                        record.quark_target_file = str(actual_target)
                        record.quark_synced_at = datetime.now()
                    else:
                        record.baidu_target_file = str(actual_target)
                        record.baidu_synced_at = datetime.now()
                    
                    record.updated_at = datetime.now()
            
            session.commit()
            logger.info(f"✅ 文件处理完成: {file_path.name}")
            
            # 添加到批次汇总
            if success_count > 0:
                self._add_to_batch({
                    'file_name': file_path.name,
                    'targets': success_targets,
                    'time': datetime.now()
                })
            if failed_count > 0:
                self.notifier.notify_sync_failed(file_path.name, last_error or "未知错误")
                
        except Exception as e:
            logger.error(f"数据库操作失败: {e}")
            session.rollback()
        finally:
            session.close()
    
    def _add_to_batch(self, file_info: dict):
        """添加文件到批次汇总"""
        with self.batch_lock:
            self.batch_files.append(file_info)
            self.last_process_time = datetime.now()
            
            # 重置汇总定时器
            if self.batch_timer:
                self.batch_timer.cancel()
            
            # 30秒后检查是否发送汇总
            self.batch_timer = threading.Timer(30.0, self._check_and_send_batch)
            self.batch_timer.daemon = True
            self.batch_timer.start()
    
    def _check_and_send_batch(self):
        """检查并发送批次汇总通知"""
        with self.batch_lock:
            if not self.batch_files:
                return
            
            # 检查是否30秒内无新文件
            if self.last_process_time and (datetime.now() - self.last_process_time).total_seconds() >= 30:
                self._send_batch_summary()
    
    def _send_batch_summary(self):
        """发送批次汇总通知"""
        if not self.batch_files:
            return
        
        try:
            file_count = len(self.batch_files)
            file_names = [f['file_name'] for f in self.batch_files]
            
            # 发送批次汇总通知
            self.notifier.notify_batch_sync_success(file_names)
            
            # 触发TaoSync同步
            if self.taosync_queue:
                logger.info(f"批次完成，触发TaoSync同步任务（共{file_count}个文件）")
                success, reason = self.taosync_queue.trigger_now(file_count=file_count)
                if success:
                    self.notifier.notify_taosync_triggered_batch(file_count)
                elif reason == "queued":
                    logger.info(f"TaoSync任务已加入队列，等待执行（文件数: {file_count}）")
                else:
                    logger.error(f"TaoSync触发失败: {reason}")
            
            logger.info(f"批次汇总通知已发送：共处理 {file_count} 个文件")
            
        except Exception as e:
            logger.error(f"发送批次汇总通知失败: {e}")
        finally:
            # 清空批次列表
            self.batch_files = []
            self.last_process_time = None


class MonitorService:
    """监控服务"""
    
    def __init__(self, config: dict, db_engine):
        self.config = config
        self.db_engine = db_engine
        self.observer = None
        self.handlers = []
        self.notifier = Notifier(config)
    
    def start(self):
        """启动监控"""
        monitors = self.config.get('monitors', [])
        
        if not monitors:
            logger.warning("未配置监控目录")
            return
        
        self.observer = Observer()
        
        for monitor in monitors:
            if not monitor.get('enabled', True):
                logger.info(f"监控已禁用: {monitor['source']}")
                continue
            
            source = monitor['source']
            targets_config = monitor['targets']
            exclude = monitor.get('exclude_patterns', [])
            obfuscate = monitor.get('obfuscate_enabled', False)
            template_path = monitor.get('template_files_path')
            
            # 检查源目录是否存在
            if not Path(source).exists():
                logger.error(f"源目录不存在: {source}")
                continue
            
            # 创建监控处理器（传递完整的target配置）
            handler = FileMonitorHandler(source, targets_config, exclude, self.db_engine, self.config, obfuscate, template_path)
            self.handlers.append(handler)
            
            # 启动监控
            self.observer.schedule(handler, source, recursive=True)
            logger.info(f"✅ 启动监控: {source}")
        
        self.observer.start()
        logger.info("监控服务已启动")
    
    def sync_all(self):
        """全量同步所有文件"""
        logger.info("开始全量同步...")
        
        if not self.config or 'monitors' not in self.config:
            logger.error("配置文件无效")
            return
        
        total_files = 0
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for monitor in self.config['monitors']:
            if not monitor.get('enabled', True):
                continue
            
            source = Path(monitor['source'])
            # 兼容新旧配置格式
            targets_config = monitor['targets']
            targets = []
            for t in targets_config:
                if isinstance(t, dict):
                    targets.append(Path(t['path']))
                else:
                    targets.append(Path(t))
            exclude = monitor.get('exclude_patterns', [])
            obfuscate = monitor.get('obfuscate_enabled', False)
            template_path = monitor.get('template_files_path')
            template_dir = Path(template_path) if template_path else None
            
            if not source.exists():
                logger.error(f"源目录不存在: {source}")
                continue
            
            logger.info(f"🔄 开始全量同步: {source}, 混淆: {obfuscate}")
            
            linker = FileLinker(obfuscate_enabled=obfuscate, db_engine=self.db_engine)
            session = get_session(self.db_engine)
            linked_dirs = set()  # 记录已链接模板文件的目录
            
            try:
                # 递归扫描所有文件
                for file_path in source.rglob('*'):
                    if file_path.is_file():
                        # 只处理媒体文件（视频+字幕）
                        from backend.utils.obfuscator import FolderObfuscator
                        if not FolderObfuscator.is_media_file(file_path):
                            continue
                        
                        # 检查是否排除
                        if linker.should_exclude(file_path, exclude):
                            continue
                        
                        total_files += 1
                        relative_path = file_path.relative_to(source)
                        file_size = file_path.stat().st_size
                        
                        # 为每个目标创建硬链接
                        for idx, target in enumerate(targets):
                            target_file = target / relative_path
                            
                            # 查询或创建记录
                            record = session.query(LinkRecord).filter(
                                LinkRecord.source_file == str(file_path)
                            ).first()
                            
                            # 判断是否已同步过（检查对应网盘字段）
                            is_first_target = idx == 0
                            already_synced = False
                            if record:
                                if is_first_target and record.quark_target_file:
                                    already_synced = True
                                elif not is_first_target and record.baidu_target_file:
                                    already_synced = True
                            
                            if already_synced:
                                logger.debug(f"数据库已有记录，跳过: {file_path} -> {target}")
                                skipped_count += 1
                                continue
                            
                            logger.info(f"同步: {file_path} -> {target_file}")
                            success, method, error, actual_target = linker.create_hardlink(
                                file_path, target_file,
                                source_base=source,
                                target_base=target
                            )
                            
                            if success:
                                success_count += 1
                                
                                # 自动链接模板文件到剧集文件夹（只链接一次）
                                if template_dir and template_dir.exists() and actual_target:
                                    target_show_dir = actual_target.parent
                                    if target_show_dir.name.startswith('Season'):
                                        target_show_dir = target_show_dir.parent
                                    
                                    dir_key = str(target_show_dir)
                                    if dir_key not in linked_dirs:
                                        linked_count = linker.link_template_files(target_show_dir, template_dir)
                                        if linked_count > 0:
                                            logger.info(f"✓ 已链接 {linked_count} 个模板文件到: {target_show_dir}")
                                            linked_dirs.add(dir_key)
                                
                                # 更新或创建记录
                                if not record:
                                    from backend.utils.obfuscator import FolderObfuscator
                                    original_name = FolderObfuscator.extract_show_name(file_path)
                                    record = LinkRecord(
                                        source_file=str(file_path),
                                        original_name=original_name,
                                        file_size=file_size
                                    )
                                    session.add(record)
                                
                                # 根据索引判断是哪个网盘
                                if is_first_target:
                                    record.quark_target_file = str(actual_target)
                                    record.quark_synced_at = datetime.now()
                                else:
                                    record.baidu_target_file = str(actual_target)
                                    record.baidu_synced_at = datetime.now()
                                
                                record.updated_at = datetime.now()
                            else:
                                failed_count += 1
                
                session.commit()
                logger.info(f"✅ 全量同步完成: 总文件 {total_files}, 新建 {success_count}, 跳过 {skipped_count}, 失败 {failed_count}")
                
            except Exception as e:
                logger.error(f"全量同步失败: {e}")
                session.rollback()
                return {"success": False, "message": str(e)}
            finally:
                session.close()
        
        # 发送全量同步完成通知
        self.notifier.notify_full_sync_complete(total_files, success_count, skipped_count, failed_count)
        
        return {
            "success": True,
            "total_files": total_files,
            "success_count": success_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count
        }
    
    def stop(self):
        """停止监控"""
        # 停止所有handler的TaoSync队列
        for handler in self.handlers:
            if hasattr(handler, 'taosync_queue') and handler.taosync_queue:
                handler.taosync_queue.stop()
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("监控服务已停止")
