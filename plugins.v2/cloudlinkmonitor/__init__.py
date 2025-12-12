from datetime import datetime, timedelta
import hashlib
import random
import re
import shutil
import threading
import traceback
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

try:
    from .pinyin_map import PINYIN_MAP
except ImportError:
    PINYIN_MAP = {}

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from app import schemas
from app.chain.media import MediaChain
from app.chain.storage import StorageChain
from app.chain.tmdb import TmdbChain
from app.chain.transfer import TransferChain
from app.core.config import settings
from app.core.context import MediaInfo
from app.core.event import eventmanager, Event
from app.core.metainfo import MetaInfoPath
from app.db.downloadhistory_oper import DownloadHistoryOper
from app.db.transferhistory_oper import TransferHistoryOper
from app.helper.directory import DirectoryHelper
from app.log import logger
from app.modules.filemanager import FileManagerModule
from app.plugins import _PluginBase
from app.schemas import NotificationType, TransferInfo, TransferDirectoryConf
from app.schemas.types import EventType, MediaType, SystemConfigKey
from app.utils.string import StringUtils
from app.utils.system import SystemUtils

lock = threading.Lock()


class FileMonitorHandler(FileSystemEventHandler):
    """
    目录监控响应类
    """

    def __init__(self, monpath: str, sync: Any, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        self._watch_path = monpath
        self.sync = sync

    def on_created(self, event):
        self.sync.event_handler(event=event, text="创建",
                                mon_path=self._watch_path, event_path=event.src_path)

    def on_moved(self, event):
        self.sync.event_handler(event=event, text="移动",
                                mon_path=self._watch_path, event_path=event.dest_path)


class CloudLinkMonitor(_PluginBase):
    # 插件名称
    plugin_name = "监控转移文件"
    # 插件描述
    plugin_desc = "监控目录文件变化，支持硬链接和复制改Hash，拼音混淆剧名（保留分类目录），批次汇总通知。"
    # 插件图标
    plugin_icon = "Linkease_A.png"
    # 插件版本
    plugin_version = "3.5.1"
    # 插件作者
    plugin_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    plugin_config_prefix = "cloudlinkmonitor_"
    # 加载顺序
    plugin_order = 4
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _scheduler = None
    transferhis = None
    downloadhis = None
    transferchian = None
    tmdbchain = None
    storagechain = None
    _observer = []
    _enabled = False
    _notify = False
    _onlyonce = False
    _cron = None
    filetransfer = None
    mediaChain = None
    _size = 0
    _monitor_dirs = ""
    _exclude_keywords = ""
    _transfer_type = "link"
    # 存储源目录与目的目录关系
    _dirconf: Dict[str, Optional[Path]] = {}
    # 存储源目录转移方式
    _transferconf: Dict[str, Optional[str]] = {}
    # 退出事件
    _event = threading.Event()
    # 批次汇总相关
    _batch_files = []  # 批次处理的文件列表
    _last_process_time = None  # 最后处理时间
    _summary_timer = None  # 汇总定时器
    _batch_lock = threading.Lock()  # 批次数据锁

    def init_plugin(self, config: dict = None):
        self.transferhis = TransferHistoryOper()
        self.downloadhis = DownloadHistoryOper()
        self.transferchian = TransferChain()
        self.tmdbchain = TmdbChain()
        self.mediaChain = MediaChain()
        self.storagechain = StorageChain()
        self.filetransfer = FileManagerModule()
        # 清空配置
        self._dirconf = {}
        self._transferconf = {}

        # 读取配置
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._onlyonce = config.get("onlyonce")
            self._transfer_type = config.get("transfer_type") or "link"
            self._monitor_dirs = config.get("monitor_dirs") or ""
            self._exclude_keywords = config.get("exclude_keywords") or ""
            self._cron = config.get("cron")
            self._size = config.get("size") or 0

        # 停止现有任务
        self.stop_service()

        if self._enabled or self._onlyonce:
            # 定时服务管理器
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)

            # 读取目录配置
            monitor_dirs = self._monitor_dirs.split("\n")
            if not monitor_dirs:
                return
            for mon_path in monitor_dirs:
                # 格式源目录:目的目录
                if not mon_path:
                    continue

                # 自定义转移方式（支持link和copyhash）
                _transfer_type = self._transfer_type
                if mon_path.count("#") == 1:
                    _transfer_type = mon_path.split("#")[1]
                    mon_path = mon_path.split("#")[0]

                # 存储目的目录
                if SystemUtils.is_windows():
                    if mon_path.count(":") > 1:
                        paths = [mon_path.split(":")[0] + ":" + mon_path.split(":")[1],
                                 mon_path.split(":")[2] + ":" + mon_path.split(":")[3]]
                    else:
                        paths = [mon_path]
                else:
                    paths = mon_path.split(":")

                # 目的目录
                target_path = None
                if len(paths) > 1:
                    mon_path = paths[0]
                    target_path = Path(paths[1])
                    self._dirconf[mon_path] = target_path
                else:
                    self._dirconf[mon_path] = None

                # 转移方式
                self._transferconf[mon_path] = _transfer_type

                # 启用目录监控
                if self._enabled:
                    # 检查媒体库目录是不是下载目录的子目录
                    try:
                        if target_path and target_path.is_relative_to(Path(mon_path)):
                            logger.warn(f"{target_path} 是监控目录 {mon_path} 的子目录，无法监控")
                            self.systemmessage.put(f"{target_path} 是下载目录 {mon_path} 的子目录，无法监控")
                            continue
                    except Exception as e:
                        logger.debug(str(e))
                        pass

                    try:
                        # 使用默认Observer
                        observer = Observer(timeout=10)
                        self._observer.append(observer)
                        observer.schedule(FileMonitorHandler(mon_path, self), path=mon_path, recursive=True)
                        observer.daemon = True
                        observer.start()
                        logger.info(f"{mon_path} 的云盘实时监控服务启动")
                    except Exception as e:
                        err_msg = str(e)
                        if "inotify" in err_msg and "reached" in err_msg:
                            logger.warn(
                                f"云盘实时监控服务启动出现异常：{err_msg}，请在宿主机上（不是docker容器内）执行以下命令并重启："
                                + """
                                     echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
                                     echo fs.inotify.max_user_instances=524288 | sudo tee -a /etc/sysctl.conf
                                     sudo sysctl -p
                                     """)
                        else:
                            logger.error(f"{mon_path} 启动目云盘实时监控失败：{err_msg}")
                        self.systemmessage.put(f"{mon_path} 启动云盘实时监控失败：{err_msg}")

            # 运行一次定时服务
            if self._onlyonce:
                logger.info("云盘实时监控服务启动，立即运行一次")
                self._scheduler.add_job(name="云盘实时监控",
                                        func=self.sync_all, trigger='date',
                                        run_date=datetime.now(
                                            tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3)
                                        )
                # 关闭一次性开关
                self._onlyonce = False
                # 保存配置
                self.__update_config()

            # 启动定时服务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __update_config(self):
        """
        更新配置
        """
        self.update_config({
            "enabled": self._enabled,
            "notify": self._notify,
            "onlyonce": self._onlyonce,
            "transfer_type": self._transfer_type,
            "monitor_dirs": self._monitor_dirs,
            "exclude_keywords": self._exclude_keywords,
            "cron": self._cron,
            "size": self._size,
        })

    @eventmanager.register(EventType.PluginAction)
    def remote_sync(self, event: Event):
        """
        远程命令处理
        """
        if event:
            event_data = event.event_data
            if not event_data:
                return
            
            action = event_data.get("action")
            channel = event_data.get("channel")
            user = event_data.get("user")
            
            # 全量同步命令
            if action == "cloud_link_sync":
                self.post_message(channel=channel, title="开始同步云盘实时监控目录 ...", userid=user)
                self.sync_all()
                self.post_message(channel=channel, title="云盘实时监控目录同步完成！", userid=user)
            
            # 同步检查命令
            elif action == "sync_check":
                self.post_message(channel=channel, title="开始检查同步状态 ...", userid=user)
                self.sync_check(channel=channel, user=user)
                self.post_message(channel=channel, title="同步状态检查完成！", userid=user)

    def sync_all(self):
        """
        立即运行一次，全量同步目录中所有文件
        """
        logger.info("开始全量同步云盘实时监控目录 ...")
        # 遍历所有监控目录
        for mon_path in self._dirconf.keys():
            logger.info(f"开始处理监控目录 {mon_path} ...")
            list_files = SystemUtils.list_files(Path(mon_path), settings.RMT_MEDIAEXT)
            logger.info(f"监控目录 {mon_path} 共发现 {len(list_files)} 个文件")
            # 遍历目录下所有文件
            for file_path in list_files:
                logger.info(f"开始处理文件 {file_path} ...")
                self.__handle_file(event_path=str(file_path), mon_path=mon_path)
    
    def sync_check(self, channel=None, user=None):
        """
        检查同步状态，对比源目录和目标目录
        """
        logger.info("开始检查同步状态 ...")
        
        # 遍历所有监控目录
        for mon_path, target_path in self._dirconf.items():
            if not target_path:
                continue
            
            mon_path_obj = Path(mon_path)
            if not mon_path_obj.exists():
                continue
            
            # 扫描源目录，按一级子目录分组（媒体文件夹）
            media_folders = {}
            for item in mon_path_obj.iterdir():
                if item.is_dir():
                    # 统计该文件夹下的媒体文件
                    files = SystemUtils.list_files(item, settings.RMT_MEDIAEXT)
                    if files:
                        media_folders[item.name] = {
                            'path': str(item),
                            'files': [f.name for f in files]
                        }
            
            # 对每个媒体文件夹发送通知
            for folder_name, folder_info in media_folders.items():
                source_files = folder_info['files']
                source_count = len(source_files)
                
                # 检查目标目录是否存在对应文件夹
                target_folders = []
                target_count = 0
                target_files_list = []
                
                # 遍历目标目录查找可能的匹配
                if target_path.exists():
                    for target_item in target_path.rglob('*'):
                        if target_item.is_dir():
                            target_files = SystemUtils.list_files(target_item, settings.RMT_MEDIAEXT)
                            if target_files:
                                target_folders.append({
                                    'name': target_item.name,
                                    'relative': str(target_item.relative_to(target_path)),
                                    'files': [f.name for f in target_files]
                                })
                
                # 尝试匹配目标文件夹（通过文件数量或模糊匹配）
                matched_target = None
                for tf in target_folders:
                    # 简单匹配：文件数量相同
                    if len(tf['files']) == source_count:
                        matched_target = tf
                        break
                
                if matched_target:
                    target_count = len(matched_target['files'])
                    target_info = f"📁 目标：{matched_target['relative']}/\n"
                    for f in matched_target['files']:
                        target_info += f"  ∙ {f}\n"
                    status = f"✅ 源{source_count}个 = 目标{target_count}个"
                else:
                    target_info = "❌ 未找到或不存在\n"
                    status = f"⚠️ 源{source_count}个 ≠ 目标0个"
                
                # 构建通知内容
                source_info = f"📁 源：{folder_info['path']}/\n"
                for f in source_files:
                    source_info += f"  ∙ {f}\n"
                
                message = (
                    f"📂 {folder_name}\n\n"
                    f"{source_info}\n"
                    f"{target_info}\n"
                    f"{status}"
                )
                
                # 发送通知
                self.post_message(
                    channel=channel,
                    title=f"📊 {folder_name}",
                    text=message,
                    userid=user
                )
                
        logger.info("同步状态检查完成")
        logger.info("全量同步云盘实时监控目录完成！")

    def event_handler(self, event, mon_path: str, text: str, event_path: str):
        """
        处理文件变化
        :param event: 事件
        :param mon_path: 监控目录
        :param text: 事件描述
        :param event_path: 事件文件路径
        """
        if not event.is_directory:
            # 文件发生变化
            logger.debug("文件%s：%s" % (text, event_path))
            self.__handle_file(event_path=event_path, mon_path=mon_path)
    
    def __add_to_batch(self, file_info: dict):
        """
        添加文件到批次汇总
        :param file_info: 文件处理信息
        """
        with self._batch_lock:
            self._batch_files.append(file_info)
            self._last_process_time = datetime.now()
            
            # 重置汇总定时器
            if self._summary_timer:
                self._summary_timer.cancel()
            
            # 30秒后检查是否发送汇总
            self._summary_timer = threading.Timer(30.0, self.__check_and_send_summary)
            self._summary_timer.daemon = True
            self._summary_timer.start()
    
    def __check_and_send_summary(self):
        """
        检查并发送批次汇总通知
        """
        with self._batch_lock:
            if not self._batch_files:
                return
            
            # 检查是否30秒内无新文件
            if self._last_process_time and (datetime.now() - self._last_process_time).total_seconds() >= 30:
                self.__send_batch_summary()
    
    def __send_batch_summary(self):
        """
        发送批次汇总通知
        """
        if not self._batch_files:
            return
        
        try:
            # 统计信息
            total_files = len(self._batch_files)
            total_size = sum(f.get('size', 0) for f in self._batch_files)
            
            # 计算用时
            start_time = self._batch_files[0].get('time')
            end_time = self._batch_files[-1].get('time')
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒" if duration >= 60 else f"{int(duration)}秒"
            else:
                duration_str = "未知"
            
            # 按目录分组统计
            dir_stats = {}
            for f in self._batch_files:
                source_dir = f.get('source_dir', '未知')
                target_dir = f.get('target_dir', '未知')
                key = f"{source_dir}→{target_dir}"
                
                if key not in dir_stats:
                    dir_stats[key] = {
                        'source': source_dir,
                        'target': target_dir,
                        'count': 0,
                        'size': 0
                    }
                dir_stats[key]['count'] += 1
                dir_stats[key]['size'] += f.get('size', 0)
            
            # 构建目录汇总文本
            dir_summary_lines = []
            for i, stats in enumerate(dir_stats.values(), 1):
                size_gb = stats['size'] / (1024**3)
                dir_summary_lines.append(
                    f"  {i}. � {stats['source']} ({stats['count']}个 | {size_gb:.1f}GB)\n"
                    f"     ⬇️  \n"
                    f"     � {stats['target']}"
                )
            dir_summary = "\n\n".join(dir_summary_lines)
            
            # 格式化总大小
            if total_size >= 1024**3:
                size_str = f"{total_size / (1024**3):.2f} GB"
            elif total_size >= 1024**2:
                size_str = f"{total_size / (1024**2):.2f} MB"
            else:
                size_str = f"{total_size / 1024:.2f} KB"
            
            # 发送通知
            notify_text = (
                f"📊 本批次统计\n"
                f"━━━━━━━━━━━━━━\n"
                f"📦 文件数量：{total_files} 个\n"
                f"💾 总大小：{size_str}\n"
                f"⏱️ 耗时：{duration_str}\n"
                f"🔗 方式：{self._batch_files[0].get('method', '未知')}\n\n"
                f"📂 目录详情\n"
                f"━━━━━━━━━━━━━━\n"
                f"{dir_summary}"
            )
            
            self.post_message(
                mtype=NotificationType.Manual,
                title="✅ 批次处理完成！",
                text=notify_text
            )
            
            logger.info(f"批次汇总通知已发送：共处理 {total_files} 个文件")
            
        except Exception as e:
            logger.error(f"发送批次汇总通知失败：{str(e)}")
        finally:
            # 清空批次列表
            self._batch_files = []
            self._last_process_time = None
    
    def __obfuscate_name(self, name: str) -> str:
        """
        混淆剧名：中文+拼音+特殊字符
        :param name: 原始名称
        :return: 混淆后的名称
        """
        # 特殊字符库（只使用最保守的绝对安全字符）
        special_chars = ['_', '-']
        
        # 使用MD5确保确定性
        hash_obj = hashlib.md5(name.encode('utf-8'))
        hash_int = int(hash_obj.hexdigest(), 16)
        
        result = []
        for i, char in enumerate(name):
            # 根据hash决定处理方式
            choice = (hash_int >> (i * 3)) % 2
            
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                if choice == 0:
                    # 保留中文
                    result.append(char)
                else:
                    # 转拼音
                    pinyin = PINYIN_MAP.get(char, char)
                    result.append(pinyin)
                
                # 添加特殊字符（概率30%）
                if (hash_int >> (i * 5)) % 10 < 3:
                    special_idx = (hash_int >> (i * 7)) % len(special_chars)
                    result.append(special_chars[special_idx])
            else:
                # 非中文字符保持不变
                result.append(char)
        
        return ''.join(result)
    
    def __generate_new_paths(self, relative_path: Path, target: Path, file_name: str):
        """
        生成混淆后的目录和文件名
        :param relative_path: 相对路径
        :param target: 目标根目录
        :param file_name: 原始文件名
        :return: (目标目录, 新文件名)
        """
        # 处理目录名：只混淆剧名文件夹，保留分类目录和Season目录
        if relative_path.parent != Path('.'):
            parent_parts = list(relative_path.parent.parts)
            new_parent_parts = []
            
            for i, dir_name in enumerate(parent_parts):
                # 保留Season目录不变
                if re.match(r'^Season\s+\d+$', dir_name, re.IGNORECASE):
                    new_parent_parts.append(dir_name)
                    logger.info(f"保留Season目录: {dir_name}")
                    continue
                
                # 保留第一层分类目录不变（电视剧、电影等）
                if i == 0:
                    new_parent_parts.append(dir_name)
                    logger.info(f"保留分类目录: {dir_name}")
                    continue
                
                # 提取年份（如果有）
                year_match = re.search(r'\((\d{4})\)$', dir_name)
                year_suffix = f" ({year_match.group(1)})" if year_match else ""
                
                # 去掉年份后的目录名
                dir_name_without_year = re.sub(r'\s*\(\d{4}\)$', '', dir_name)
                
                # 混淆剧名
                obfuscated_name = self.__obfuscate_name(dir_name_without_year)
                
                # 构建新目录名：混淆名 + 年份
                new_dir = obfuscated_name + year_suffix
                new_parent_parts.append(new_dir)
                logger.info(f"目录名混淆: {dir_name} -> {new_dir}")
            
            target_dir = target / Path(*new_parent_parts) if new_parent_parts else target
        else:
            target_dir = target
        
        # 处理文件名：提取S01E01和视频格式
        file_stem = Path(file_name).stem
        file_suffix = Path(file_name).suffix
        
        # 提取季集号（S01E01格式）
        season_episode = re.search(r'[Ss](\d+)[Ee](\d+)', file_stem)
        
        # 提取视频格式信息（1080p, 4K, 2160p等）
        video_format = re.search(r'(\d{3,4}[pP]|[248][kK]|[hH][dD]|[uU][hH][dD])', file_stem)
        
        if season_episode:
            # 电视剧：S01E01-1080p.mkv
            new_stem = f"S{season_episode.group(1)}E{season_episode.group(2)}"
            if video_format:
                new_stem += f"-{video_format.group(1)}"
            logger.info(f"电视剧文件名: {new_stem}")
        elif video_format:
            # 电影：1080p.mkv
            new_stem = video_format.group(1)
            logger.info(f"电影文件名: {new_stem}")
        else:
            # 没有识别到格式，使用movie作为前缀
            new_stem = "movie"
            logger.info(f"未识别到格式，使用默认文件名: {new_stem}")
        
        new_file_name = f"{new_stem}{file_suffix}"
        
        return target_dir, new_file_name

    def __handle_file(self, event_path: str, mon_path: str):
        """
        同步一个文件
        :param event_path: 事件文件路径
        :param mon_path: 监控目录
        """
        file_path = Path(event_path)
        try:
            if not file_path.exists():
                return
            # 全程加锁
            with lock:
                # 查询转移方式（提前获取，用于判断是否跳过历史检查）
                transfer_type = self._transferconf.get(mon_path)
                
                # copyhash模式不检查历史记录，允许重复处理
                if transfer_type != "copyhash":
                    transfer_history = self.transferhis.get_by_src(event_path)
                    if transfer_history:
                        logger.info("文件已处理过：%s" % event_path)
                        return

                # 回收站及隐藏的文件不处理
                if event_path.find('/@Recycle/') != -1 \
                        or event_path.find('/#recycle/') != -1 \
                        or event_path.find('/.') != -1 \
                        or event_path.find('/@eaDir') != -1:
                    logger.debug(f"{event_path} 是回收站或隐藏的文件")
                    return

                # 命中过滤关键字不处理
                if self._exclude_keywords:
                    for keyword in self._exclude_keywords.split("\n"):
                        if keyword and re.findall(keyword, event_path):
                            logger.info(f"{event_path} 命中过滤关键字 {keyword}，不处理")
                            return

                # 整理屏蔽词不处理
                transfer_exclude_words = self.systemconfig.get(SystemConfigKey.TransferExcludeWords)
                if transfer_exclude_words:
                    for keyword in transfer_exclude_words:
                        if not keyword:
                            continue
                        if keyword and re.search(r"%s" % keyword, event_path, re.IGNORECASE):
                            logger.info(f"{event_path} 命中整理屏蔽词 {keyword}，不处理")
                            return

                # 不是媒体文件不处理
                if file_path.suffix not in settings.RMT_MEDIAEXT:
                    logger.debug(f"{event_path} 不是媒体文件")
                    return

                # 判断是不是蓝光目录
                if re.search(r"BDMV[/\\]STREAM", event_path, re.IGNORECASE):
                    # 截取BDMV前面的路径
                    blurray_dir = event_path[:event_path.find("BDMV")]
                    file_path = Path(blurray_dir)
                    logger.info(f"{event_path} 是蓝光目录，更正文件路径为：{str(file_path)}")
                    # 查询历史记录，已转移的不处理
                    if self.transferhis.get_by_src(str(file_path)):
                        logger.info(f"{file_path} 已整理过")
                        return

                # 元数据
                file_meta = MetaInfoPath(file_path)
                if not file_meta.name:
                    logger.error(f"{file_path.name} 无法识别有效信息")
                    return

                # 判断文件大小
                if self._size and float(self._size) > 0 and file_path.stat().st_size < float(self._size) * 1024 ** 3:
                    logger.info(f"{file_path} 文件大小小于监控文件大小，不处理")
                    return

                # 查询转移目的目录
                target: Path = self._dirconf.get(mon_path)

                # link模式：硬链接+改名（不改hash）
                if transfer_type == "link":
                    logger.info(f"link模式：开始处理 {file_path.name}")
                    try:
                        if not target:
                            logger.error(f"link模式：未配置监控目录 {mon_path} 的目的目录")
                            return
                        
                        # 计算相对路径
                        mon_path_obj = Path(mon_path)
                        relative_path = file_path.relative_to(mon_path_obj)
                        logger.info(f"link模式：相对路径 {relative_path}")
                        
                        # 生成新的目录和文件名
                        target_dir, new_file_name = self.__generate_new_paths(relative_path, target, file_path.name)
                        target_file = target_dir / new_file_name
                        logger.info(f"link模式：目标路径 {target_file}")
                        
                        # 确保目标目录存在
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 尝试硬链接，失败则复制
                        try:
                            logger.info(f"link模式：尝试创建硬链接 {file_path} -> {target_file}")
                            import os
                            os.link(str(file_path), str(target_file))
                            transfer_method = "硬链接"
                            logger.info(f"link模式：硬链接创建成功")
                        except OSError as link_err:
                            logger.warn(f"link模式：硬链接失败（可能跨文件系统），尝试复制：{str(link_err)}")
                            shutil.copy2(file_path, target_file)
                            transfer_method = "复制"
                            logger.info(f"link模式：文件复制完成")
                        
                        # 发送简化通知
                        if self._notify:
                            file_size = target_file.stat().st_size
                            
                            # 格式化文件大小
                            if file_size >= 1024**3:
                                size_str = f"{file_size / (1024**3):.2f}GB"
                            elif file_size >= 1024**2:
                                size_str = f"{file_size / (1024**2):.2f}MB"
                            else:
                                size_str = f"{file_size / 1024:.2f}KB"
                            
                            notify_text = f"🔗 {transfer_method} | 💾 {size_str}"
                            
                            self.post_message(
                                mtype=NotificationType.Manual,
                                title=f"✅ 转移：{new_file_name}",
                                text=notify_text
                            )
                            logger.info(f"link模式：已发送简化通知")
                        
                        # 添加到批次汇总
                        original_dir = relative_path.parent if relative_path.parent != Path('.') else "根目录"
                        target_relative = target_file.relative_to(target)
                        target_dir_display = target_relative.parent if target_relative.parent != Path('.') else "根目录"
                        
                        self.__add_to_batch({
                            'time': datetime.now(),
                            'source_dir': str(original_dir),
                            'target_dir': str(target_dir_display),
                            'source_file': file_path.name,
                            'target_file': new_file_name,
                            'size': file_size,
                            'method': 'link'
                        })
                        
                        logger.info(f"link模式：{file_path.name} 处理成功（{transfer_method}）")
                        return
                    except Exception as e:
                        logger.error(f"link模式处理失败：{str(e)}")
                        logger.error(f"link模式：错误详情 {traceback.format_exc()}")
                        return

                # copyhash模式：纯复制模式，跳过识别和整理流程
                elif transfer_type == "copyhash":
                    logger.info(f"copyhash模式：开始纯复制处理 {file_path.name}")
                    try:
                        if not target:
                            logger.error(f"copyhash模式：未配置监控目录 {mon_path} 的目的目录")
                            return
                        
                        # 计算相对路径
                        mon_path_obj = Path(mon_path)
                        relative_path = file_path.relative_to(mon_path_obj)
                        logger.info(f"copyhash模式：相对路径 {relative_path}")
                        
                        # 生成新的目录和文件名
                        target_dir, new_file_name = self.__generate_new_paths(relative_path, target, file_path.name)
                        target_file = target_dir / file_path.name
                        logger.info(f"copyhash模式：目标路径 {target_file}")
                        
                        # 确保目标目录存在
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 复制文件
                        logger.info(f"copyhash模式：开始复制文件 {file_path} -> {target_file}")
                        shutil.copy2(file_path, target_file)
                        logger.info(f"copyhash模式：文件复制完成")
                        
                        # 处理hash修改和重命名
                        if target_file.exists() and target_file.is_file():
                            # 使用公共函数生成的文件名
                            new_file_path = target_file.parent / new_file_name
                            
                            # 计算原始文件hash（重命名前）
                            original_size = target_file.stat().st_size
                            hash_md5_original = hashlib.md5()
                            with open(target_file, 'rb') as f:
                                for chunk in iter(lambda: f.read(8192), b""):
                                    hash_md5_original.update(chunk)
                            original_hash = hash_md5_original.hexdigest()
                            logger.info(f"copyhash模式：原始文件hash={original_hash}")
                            
                            # 在文件末尾追加随机空白字符改变hash
                            whitespace_chars = [' ', '\t', '\n']
                            random_count = random.randint(10, 30)
                            random_whitespaces = ''.join(random.choices(whitespace_chars, k=random_count))
                            logger.info(f"copyhash模式：准备在文件末尾添加{random_count}个随机空白字符")
                            
                            with open(target_file, 'ab') as f:
                                f.write(random_whitespaces.encode('utf-8'))
                            new_size = target_file.stat().st_size
                            logger.info(f"copyhash模式：文件大小从{original_size}字节增加到{new_size}字节")
                            
                            # 计算修改后的文件hash
                            hash_md5_new = hashlib.md5()
                            with open(target_file, 'rb') as f:
                                for chunk in iter(lambda: f.read(8192), b""):
                                    hash_md5_new.update(chunk)
                            new_hash = hash_md5_new.hexdigest()
                            logger.info(f"copyhash模式：修改后文件hash={new_hash}")
                            logger.info(f"copyhash模式：hash已改变 {original_hash} -> {new_hash}")
                            
                            # 先修改hash，再重命名（避免文件名冲突）
                            if target_file != new_file_path:
                                target_file.rename(new_file_path)
                                logger.info(f"copyhash模式：文件重命名成功 {target_file.name} -> {new_file_path.name}")
                            logger.info(f"copyhash模式：处理完成 {new_file_path}")
                        
                        # 发送简化通知
                        if self._notify:
                            # 格式化文件大小
                            if new_size >= 1024**3:
                                size_str = f"{new_size / (1024**3):.2f}GB"
                            elif new_size >= 1024**2:
                                size_str = f"{new_size / (1024**2):.2f}MB"
                            else:
                                size_str = f"{new_size / 1024:.2f}KB"
                            
                            notify_text = f"📝 复制+改Hash | 💾 {size_str}"
                            
                            self.post_message(
                                mtype=NotificationType.Manual,
                                title=f"✅ 转移：{new_file_path.name}",
                                text=notify_text
                            )
                            logger.info(f"copyhash模式：已发送简化通知")
                        
                        # 添加到批次汇总
                        original_dir = relative_path.parent if relative_path.parent != Path('.') else "根目录"
                        target_relative = new_file_path.relative_to(target)
                        target_dir_display = target_relative.parent if target_relative.parent != Path('.') else "根目录"
                        
                        self.__add_to_batch({
                            'time': datetime.now(),
                            'source_dir': str(original_dir),
                            'target_dir': str(target_dir_display),
                            'source_file': file_path.name,
                            'target_file': new_file_path.name,
                            'size': new_size,
                            'method': 'copyhash'
                        })
                        
                        logger.info(f"copyhash模式：{file_path.name} 处理成功")
                        return
                    except Exception as e:
                        logger.error(f"copyhash模式处理失败：{str(e)}")
                        logger.error(f"copyhash模式：错误详情 {traceback.format_exc()}")
                        return
                
                else:
                    # 不支持的转移方式
                    logger.error(f"不支持的转移方式：{transfer_type}，仅支持link和copyhash")
                    return
        
        except Exception as e:
            logger.error("目录监控发生错误：%s - %s" % (str(e), traceback.format_exc()))


    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        定义远程控制命令
        :return: 命令关键字、事件、描述、附带数据
        """
        return [
            {
                "cmd": "/cloud_link_sync",
                "event": EventType.PluginAction,
                "desc": "云盘实时监控同步",
                "category": "",
                "data": {
                    "action": "cloud_link_sync"
                }
            },
            {
                "cmd": "/sync_check",
                "event": EventType.PluginAction,
                "desc": "检查同步状态",
                "category": "",
                "data": {
                    "action": "sync_check"
                }
            }
        ]

    def get_api(self) -> List[Dict[str, Any]]:
        return [{
            "path": "/cloud_link_sync",
            "endpoint": self.sync,
            "methods": ["GET"],
            "summary": "云盘实时监控同步",
            "description": "云盘实时监控同步",
        }]

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        if self._enabled and self._cron:
            return [{
                "id": "CloudLinkMonitor",
                "name": "云盘实时监控全量同步服务",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.sync_all,
                "kwargs": {}
            }]
        return []

    def sync(self) -> schemas.Response:
        """
        API调用目录同步
        """
        self.sync_all()
        return schemas.Response(success=True)

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '发送通知',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'model': 'transfer_type',
                                            'label': '转移方式',
                                            'items': [
                                                {'title': '硬链接', 'value': 'link'},
                                                {'title': '复制改Hash', 'value': 'copyhash'}
                                            ]
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 4
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'cron',
                                            'label': '定时任务',
                                            'placeholder': '0 0 * * *'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'monitor_dirs',
                                            'label': '监控目录',
                                            'rows': 5,
                                            'placeholder': '每一行一个目录，支持以下几种配置方式：\n'
                                                           '监控目录:转移目的目录\n'
                                                           '监控目录:转移目的目录#link\n'
                                                           '监控目录:转移目的目录#copyhash\n'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'exclude_keywords',
                                            'label': '排除关键词',
                                            'rows': 2,
                                            'placeholder': '每一行一个关键词'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': 'link模式：硬链接（同文件系统）或复制（跨文件系统）+改名，不改hash。\ncopyhash模式：复制+改名+改hash。\n两种模式都会混淆目录名（保留1-2个字+繁体字+年份）和文件名（S01E01-1080p.mkv或1080p.mkv），Season目录不改。'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ], {
            "enabled": False,
            "notify": False,
            "onlyonce": False,
            "transfer_type": "link",
            "monitor_dirs": "",
            "exclude_keywords": "",
            "cron": "0 0 * * *",
            "size": 0
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        if self._observer:
            for observer in self._observer:
                try:
                    observer.stop()
                    observer.join()
                except Exception as e:
                    print(str(e))
        self._observer = []
        if self._scheduler:
            self._scheduler.remove_all_jobs()
            if self._scheduler.running:
                self._event.set()
                self._scheduler.shutdown()
                self._event.clear()
            self._scheduler = None
