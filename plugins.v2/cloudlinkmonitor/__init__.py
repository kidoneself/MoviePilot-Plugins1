from datetime import datetime, timedelta
import hashlib
import re
import requests
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
from app.core.event import eventmanager, Event
from app.core.metainfo import MetaInfoPath
from app.db.downloadhistory_oper import DownloadHistoryOper
from app.db.transferhistory_oper import TransferHistoryOper
from app.log import logger
from app.modules.filemanager import FileManagerModule
from app.plugins import _PluginBase
from app.schemas import NotificationType
from app.schemas.types import EventType, SystemConfigKey
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
    plugin_desc = "监控目录文件变化，硬链接转移，拼音混淆剧名（保留分类目录），批次汇总通知，TaoSync多网盘同步。"
    # 插件图标
    plugin_icon = "Linkease_A.png"
    # 插件版本
    plugin_version = "5.2.1"
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
    # 存储源目录与目的目录关系（一对多）
    _dirconf: Dict[str, List[Path]] = {}
    # 退出事件
    _event = threading.Event()
    # 批次汇总相关
    _batch_files = []  # 批次处理的文件列表
    _last_process_time = None  # 最后处理时间
    _summary_timer = None  # 汇总定时器
    _batch_lock = threading.Lock()  # 批次数据锁
    # TaoSync 同步相关
    _enable_taosync = False  # 是否启用 TaoSync 同步
    _taosync_url = ""  # TaoSync 地址
    _taosync_username = ""  # TaoSync 用户名
    _taosync_password = ""  # TaoSync 密码
    _taosync_job_ids = ""  # TaoSync Job IDs（要触发的任务ID，多个用逗号分隔）
    _last_taosync_trigger = None  # 最后触发 TaoSync 的时间
    # 会话统计
    _session_files = 0  # 本次会话处理的文件数
    _session_size = 0  # 本次会话处理的总大小
    _session_success = 0  # 成功数
    _session_failed = 0  # 失败数
    _session_start_time = None  # 会话开始时间
    _recent_files = []  # 最近处理的文件（最多10个）

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
        
        # 初始化会话统计
        if self._session_start_time is None:
            self._session_start_time = datetime.now()
        self._session_files = 0
        self._session_size = 0
        self._session_success = 0
        self._session_failed = 0
        self._recent_files = []

        # 读取配置
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._onlyonce = config.get("onlyonce")
            self._monitor_dirs = config.get("monitor_dirs") or ""
            self._exclude_keywords = config.get("exclude_keywords") or ""
            self._cron = config.get("cron")
            self._size = config.get("size") or 0
            
            # TaoSync 配置
            self._enable_taosync = config.get("enable_taosync") or False
            self._taosync_url = config.get("taosync_url") or ""
            self._taosync_username = config.get("taosync_username") or "admin"
            self._taosync_password = config.get("taosync_password") or ""
            self._taosync_job_ids = config.get("taosync_job_ids") or ""

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
                
                # 兼容旧版本：过滤掉 # 后面的转移方式标记（如 #link）
                if "#" in mon_path:
                    mon_path = mon_path.split("#")[0]
                    logger.debug(f"过滤旧版本配置标记，使用：{mon_path}")

                # 存储目的目录
                if SystemUtils.is_windows():
                    if mon_path.count(":") > 1:
                        paths = [mon_path.split(":")[0] + ":" + mon_path.split(":")[1],
                                 mon_path.split(":")[2] + ":" + mon_path.split(":")[3]]
                    else:
                        paths = [mon_path]
                else:
                    paths = mon_path.split(":")

                target_path = None
                if len(paths) > 1:
                    mon_path = paths[0]
                    target_path = Path(paths[1])
                    # 支持一对多：如果源目录已存在，追加目标；否则创建新列表
                    if mon_path in self._dirconf:
                        if target_path not in self._dirconf[mon_path]:
                            self._dirconf[mon_path].append(target_path)
                    else:
                        self._dirconf[mon_path] = [target_path]
                else:
                    # 没有目标目录的情况
                    if mon_path not in self._dirconf:
                        self._dirconf[mon_path] = []

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
        for mon_path, target_list in self._dirconf.items():
            if not target_list:
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
                
                # 检查所有目标目录
                all_target_info = []
                
                for target_path in target_list:
                    if not target_path.exists():
                        all_target_info.append({
                            'target_name': target_path.name,
                            'status': '❌ 目标不存在',
                            'count': 0
                        })
                        continue
                    
                    # 遍历目标目录查找可能的匹配
                    target_folders = []
                    for target_item in target_path.rglob('*'):
                        if target_item.is_dir():
                            target_files = SystemUtils.list_files(target_item, settings.RMT_MEDIAEXT)
                            if target_files:
                                target_folders.append({
                                    'name': target_item.name,
                                    'relative': str(target_item.relative_to(target_path)),
                                    'files': [f.name for f in target_files]
                                })
                    
                    # 尝试匹配目标文件夹
                    matched_target = None
                    for tf in target_folders:
                        if len(tf['files']) == source_count:
                            matched_target = tf
                            break
                    
                    if matched_target:
                        all_target_info.append({
                            'target_name': target_path.name,
                            'status': f"✅ {matched_target['relative']}",
                            'count': len(matched_target['files'])
                        })
                    else:
                        all_target_info.append({
                            'target_name': target_path.name,
                            'status': '❌ 未找到匹配',
                            'count': 0
                        })
                
                # 构建通知内容
                source_info = f"📁 源：{folder_info['path']}/\n"
                for f in source_files:
                    source_info += f"  ∙ {f}\n"
                
                # 汇总所有目标状态
                target_summary = []
                success_count = sum(1 for t in all_target_info if '✅' in t['status'])
                for t in all_target_info:
                    target_summary.append(f"  {t['target_name']}: {t['status']}")
                
                target_info = "\n".join(target_summary)
                status = f"✅ 成功 {success_count}/{len(all_target_info)} 个目标 | 源{source_count}个文件"
                
                message = (
                    f"📂 {folder_name}\n\n"
                    f"{source_info}\n"
                    f"📁 目标状态：\n{target_info}\n\n"
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
        发送批次汇总通知（优化版：区分剧集和电影）
        """
        if not self._batch_files:
            return
        
        try:
            # 去重：按源文件统计（避免一对多重复计数）
            unique_files = {}
            for f in self._batch_files:
                source_file = f.get('source_file')
                if source_file not in unique_files:
                    unique_files[source_file] = f
            
            # 统计信息
            total_files = len(unique_files)
            total_size = sum(f.get('size', 0) for f in unique_files.values())
            
            # 计算用时
            start_time = self._batch_files[0].get('time')
            end_time = self._batch_files[-1].get('time')
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒" if duration >= 60 else f"{int(duration)}秒"
            else:
                duration_str = "未知"
            
            # 格式化总大小
            if total_size >= 1024**3:
                size_str = f"{total_size / (1024**3):.2f} GB"
            elif total_size >= 1024**2:
                size_str = f"{total_size / (1024**2):.2f} MB"
            else:
                size_str = f"{total_size / 1024:.2f} KB"
            
            # 统计目标数量
            target_dirs = set()
            for f in self._batch_files:
                target_dir = f.get('target_dir', '')
                if target_dir:
                    # 提取第一级目录作为目标名
                    target_name = target_dir.split('/')[0] if '/' in target_dir else target_dir
                    target_dirs.add(target_name)
            target_count = len(target_dirs)
            
            # 按剧集/电影分组
            tv_shows = {}  # {show_name: {season: [episodes]}}
            movies = []
            
            for f in unique_files.values():
                source_file = f.get('source_file', '')
                source_dir = f.get('source_dir', '')
                file_size = f.get('size', 0)
                
                # 检查是否是剧集（包含Season或S\d+E\d+）
                import re
                episode_match = re.search(r'S(\d+)E(\d+)', source_file, re.IGNORECASE)
                
                if 'Season' in source_dir or episode_match:
                    # 剧集
                    # 从目录提取剧名
                    parts = source_dir.split('/')
                    show_name = None
                    season_num = None
                    
                    for i, part in enumerate(parts):
                        if 'Season' in part:
                            season_match = re.search(r'Season\s*(\d+)', part, re.IGNORECASE)
                            if season_match:
                                season_num = int(season_match.group(1))
                            if i > 0:
                                show_name = parts[i-1]
                            break
                    
                    if not show_name or not season_num:
                        # 尝试从文件名提取
                        if episode_match:
                            season_num = int(episode_match.group(1))
                            # 剧名为source_dir的最后一个目录
                            show_name = parts[-1] if parts else "未知剧集"
                    
                    if show_name and season_num is not None:
                        episode_num = int(episode_match.group(2)) if episode_match else 0
                        
                        if show_name not in tv_shows:
                            tv_shows[show_name] = {}
                        if season_num not in tv_shows[show_name]:
                            tv_shows[show_name][season_num] = []
                        
                        if episode_num > 0:
                            tv_shows[show_name][season_num].append(episode_num)
                else:
                    # 电影
                    # 从source_dir提取电影名（通常是最后一个目录）
                    parts = source_dir.split('/')
                    movie_name = parts[-1] if parts else source_file.rsplit('.', 1)[0]
                    movies.append({
                        'name': movie_name,
                        'size': file_size
                    })
            
            # 构建通知内容
            content_lines = []
            
            # 剧集部分
            if tv_shows:
                content_lines.append("� 剧集：")
                for show_name, seasons in sorted(tv_shows.items()):
                    for season_num in sorted(seasons.keys()):
                        episodes = sorted(seasons[season_num])
                        # 智能显示集数范围
                        episode_str = self.__format_episodes(episodes)
                        content_lines.append(f"  • {show_name} S{season_num:02d} ({episode_str})")
            
            # 电影部分
            if movies:
                if tv_shows:
                    content_lines.append("")
                content_lines.append("🎬 电影：")
                for movie in movies:
                    size_gb = movie['size'] / (1024**3)
                    content_lines.append(f"  • {movie['name']} ({size_gb:.1f}GB)")
            
            content = "\n".join(content_lines)
            
            # 发送通知
            notify_text = (
                f"� {total_files}个文件 | 💾 {size_str} | ⏱️ {duration_str}\n"
                f"🔗 硬链接 → {target_count}个目标\n\n"
                f"{content}"
            )
            
            self.post_message(
                mtype=NotificationType.Manual,
                title="✅ 批次处理完成！",
                text=notify_text
            )
            
            logger.info(f"批次汇总通知已发送：共处理 {total_files} 个文件")
            
            # 触发 TaoSync 同步
            if self._enable_taosync:
                self.__trigger_taosync_sync()
            
        except Exception as e:
            logger.error(f"发送批次汇总通知失败：{str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # 清空批次列表
            self._batch_files = []
            self._last_process_time = None
    
    def __format_episodes(self, episodes: list) -> str:
        """
        智能格式化集数范围
        :param episodes: 集数列表 [1, 2, 3, 5, 6]
        :return: "E01-E03, E05-E06" 或 "E01-E05"
        """
        if not episodes:
            return ""
        
        episodes = sorted(set(episodes))  # 去重并排序
        
        # 如果只有一集
        if len(episodes) == 1:
            return f"E{episodes[0]:02d}"
        
        # 检查是否完全连续
        if episodes[-1] - episodes[0] + 1 == len(episodes):
            return f"E{episodes[0]:02d}-E{episodes[-1]:02d}"
        
        # 不连续，分段显示
        ranges = []
        start = episodes[0]
        end = episodes[0]
        
        for i in range(1, len(episodes)):
            if episodes[i] == end + 1:
                end = episodes[i]
            else:
                # 结束当前范围
                if start == end:
                    ranges.append(f"E{start:02d}")
                else:
                    ranges.append(f"E{start:02d}-E{end:02d}")
                start = episodes[i]
                end = episodes[i]
        
        # 添加最后一个范围
        if start == end:
            ranges.append(f"E{start:02d}")
        else:
            ranges.append(f"E{start:02d}-E{end:02d}")
        
        return ", ".join(ranges)
    
    def __trigger_taosync_sync(self):
        """
        触发 TaoSync 任务执行（批次完成后）
        """
        if not self._taosync_job_ids:
            logger.debug("未配置 TaoSync Job IDs，跳过")
            return
        
        # 解析 Job IDs（支持逗号分隔）
        job_ids = [jid.strip() for jid in self._taosync_job_ids.split(',') if jid.strip()]
        if not job_ids:
            logger.debug("TaoSync Job IDs 为空，跳过")
            return
        
        try:
            logger.info(f"批次完成，触发 TaoSync {len(job_ids)} 个任务执行")
            
            # 登录 TaoSync
            login_url = f"{self._taosync_url}/svr/noAuth/login"
            login_data = {
                'userName': self._taosync_username,
                'passwd': self._taosync_password
            }
            
            session = requests.Session()
            login_resp = session.post(login_url, json=login_data, timeout=10)
            if login_resp.status_code != 200 or login_resp.json().get('code') != 200:
                logger.error(f"TaoSync 登录失败：{login_resp.text}")
                return
            
            # 遍历所有 Job ID 并触发执行
            success_count = 0
            for job_id in job_ids:
                try:
                    # 转换为整数
                    job_id_int = int(job_id)
                    
                    # 触发任务执行
                    exec_url = f"{self._taosync_url}/svr/job"
                    exec_data = {
                        'id': job_id_int,
                        'pause': None
                    }
                    
                    exec_resp = session.put(exec_url, json=exec_data, timeout=10)
                    if exec_resp.status_code == 200:
                        logger.info(f"TaoSync Job {job_id} 触发成功")
                        success_count += 1
                    else:
                        logger.error(f"TaoSync Job {job_id} 触发失败：{exec_resp.text}")
                
                except ValueError:
                    logger.error(f"TaoSync Job ID 格式错误：{job_id}")
                except Exception as e:
                    logger.error(f"TaoSync Job {job_id} 触发异常：{str(e)}")
            
            logger.info(f"TaoSync 任务触发完成：成功 {success_count}/{len(job_ids)}")
            
            # 记录触发时间
            if success_count > 0:
                self._last_taosync_trigger = datetime.now()
        
        except Exception as e:
            logger.error(f"触发 TaoSync 同步失败：{str(e)}")
            logger.error(traceback.format_exc())
    
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
                # 检查历史记录
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

                # 查询转移目的目录列表（支持一对多）
                target_list: List[Path] = self._dirconf.get(mon_path, [])

                # 硬链接转移
                logger.info(f"开始处理 {file_path.name}，共 {len(target_list)} 个目标")
                if not target_list:
                    logger.error(f"未配置监控目录 {mon_path} 的目的目录")
                    return
                
                # 计算相对路径（所有目标共用）
                mon_path_obj = Path(mon_path)
                relative_path = file_path.relative_to(mon_path_obj)
                logger.info(f"相对路径 {relative_path}")
                
                # 遍历所有目标目录
                success_count = 0
                for idx, target in enumerate(target_list, 1):
                    try:
                        logger.info(f"[{idx}/{len(target_list)}] 处理目标 {target}")
                        
                        # 生成新的目录和文件名
                        target_dir, new_file_name = self.__generate_new_paths(relative_path, target, file_path.name)
                        target_file = target_dir / new_file_name
                        logger.info(f"目标路径 {target_file}")
                        
                        # 如果文件已存在且内容相同，跳过
                        if target_file.exists():
                            if target_file.samefile(file_path):
                                logger.info(f"目标文件已存在且为同一文件，跳过")
                                success_count += 1
                                continue
                            else:
                                logger.warn(f"目标文件已存在但不是同一文件，跳过")
                                continue
                        
                        # 确保目标目录存在
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 尝试硬链接，失败则复制
                        try:
                            logger.info(f"尝试创建硬链接 {file_path} -> {target_file}")
                            import os
                            os.link(str(file_path), str(target_file))
                            transfer_method = "硬链接"
                            logger.info(f"硬链接创建成功")
                        except OSError as link_err:
                            logger.warn(f"硬链接失败（可能跨文件系统），尝试复制：{str(link_err)}")
                            shutil.copy2(file_path, target_file)
                            transfer_method = "复制"
                            logger.info(f"文件复制完成")
                        
                        # 添加到批次汇总
                        original_dir = relative_path.parent if relative_path.parent != Path('.') else "根目录"
                        target_relative = target_file.relative_to(target)
                        target_dir_display = target_relative.parent if target_relative.parent != Path('.') else "根目录"
                        
                        file_size = target_file.stat().st_size
                        
                        self.__add_to_batch({
                            'time': datetime.now(),
                            'source_dir': str(original_dir),
                            'target_dir': f"{target.name}/{target_dir_display}",
                            'source_file': file_path.name,
                            'target_file': new_file_name,
                            'size': file_size,
                            'method': transfer_method
                        })
                        
                        logger.info(f"[{idx}/{len(target_list)}] 处理成功（{transfer_method}）")
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"[{idx}/{len(target_list)}] 处理失败：{str(e)}")
                        logger.error(f"错误详情 {traceback.format_exc()}")
                        continue
                
                # 写入转移历史（所有目标都成功后才写入，避免重复处理）
                if success_count == len(target_list):
                    try:
                        logger.info(f"准备写入转移历史：{file_path.name}")
                        # 获取文件项
                        file_item = self.storagechain.get_file_item(storage="local", path=file_path)
                        if not file_item:
                            logger.warn(f"无法获取文件项，跳过写入历史：{file_path}")
                        else:
                            logger.info(f"获取文件项成功，开始写入历史")
                            # 简化的元数据
                            file_meta = MetaInfoPath(file_path)
                            # 写入历史记录（简化版，不需要完整的 mediainfo）
                            self.transferhis.add_success(
                                fileitem=file_item,
                                mode="link",  # 硬链接模式
                                meta=file_meta,
                                mediainfo=None,  # 不识别媒体信息
                                transferinfo=None  # 简化版，不需要完整信息
                            )
                            logger.info(f"✅ 已写入转移历史：{file_path.name}")
                    except Exception as e:
                        logger.error(f"❌ 写入转移历史失败：{str(e)}")
                        logger.error(f"错误详情：{traceback.format_exc()}")
                
                logger.info(f"{file_path.name} 处理完成，成功 {success_count}/{len(target_list)} 个目标")
                
                # 更新会话统计
                self._session_files += 1
                self._session_size += file_size
                if success_count == len(target_list):
                    self._session_success += 1
                elif success_count > 0:
                    self._session_success += 1  # 部分成功也算成功
                else:
                    self._session_failed += 1
                
                # 添加到最近处理记录
                self._recent_files.insert(0, {
                    'name': new_file_name,
                    'size': file_size,
                    'time': datetime.now(),
                    'success': success_count,
                    'total': len(target_list)
                })
                # 只保留最近10个
                if len(self._recent_files) > 10:
                    self._recent_files = self._recent_files[:10]
                
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
        return [
            {
                "path": "/cloud_link_sync",
                "endpoint": self.sync,
                "methods": ["GET"],
                "summary": "云盘实时监控同步",
                "description": "云盘实时监控同步",
            },
            {
                "path": "/test_webdav",
                "endpoint": self.test_webdav_api,
                "methods": ["GET"],
                "summary": "测试 WebDAV 连接",
                "description": "测试 WebDAV 连接配置是否正确",
            }
        ]

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
                                    'md': 6
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
                                            'text': '硬链接转移（同文件系统）或复制（跨文件系统），混淆剧名（保留1-2个字+繁体字+年份）和文件名（S01E01-1080p.mkv或1080p.mkv），Season目录不改。'
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
                                            'text': 'TaoSync 同步配置：批次完成后自动触发指定任务执行（需先在 TaoSync 中手动创建任务）'
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
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enable_taosync',
                                            'label': '启用 TaoSync 同步',
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
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'taosync_url',
                                            'label': 'TaoSync 地址',
                                            'placeholder': 'http://10.10.10.17:8024'
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
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'taosync_username',
                                            'label': 'TaoSync 用户名',
                                            'placeholder': 'admin'
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
                                            'model': 'taosync_password',
                                            'label': 'TaoSync 密码',
                                            'type': 'password',
                                            'placeholder': '******'
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
                                            'model': 'taosync_job_ids',
                                            'label': 'TaoSync Job IDs',
                                            'placeholder': '任务ID，多个用逗号分隔（如：3,5,7）'
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
            "notify": False,  # 默认关闭实时通知，只保留批次汇总
            "onlyonce": False,
            "monitor_dirs": "",
            "exclude_keywords": "",
            "cron": "0 0 * * *",
            "size": 0,
            "enable_taosync": False,
            "taosync_url": "",
            "taosync_username": "admin",
            "taosync_password": "",
            "taosync_job_ids": ""
        }

    def get_page(self) -> List[dict]:
        """
        插件详情页面 - 混合仪表盘
        """
        # 计算运行时长
        if self._session_start_time:
            runtime = datetime.now() - self._session_start_time
            runtime_str = f"{int(runtime.total_seconds() // 3600)}时{int((runtime.total_seconds() % 3600) // 60)}分"
        else:
            runtime_str = "未知"
        
        # 格式化总大小
        if self._session_size >= 1024**3:
            size_str = f"{self._session_size / (1024**3):.2f}GB"
        elif self._session_size >= 1024**2:
            size_str = f"{self._session_size / (1024**2):.2f}MB"
        else:
            size_str = f"{self._session_size / 1024:.2f}KB"
        
        # 统计目标数量
        target_count = 0
        for targets in self._dirconf.values():
            target_count = max(target_count, len(targets) if targets else 0)
        
        # 监控目录数量
        monitor_count = len(self._dirconf)
        
        # 运行状态
        status_text = "🟢 运行中" if self._enabled else "⭕ 已停止"
        
        # TaoSync 状态
        if self._enable_taosync:
            taosync_status = f"✅ 已启用  |  Job: {self._taosync_job_ids or '未配置'}"
            if self._last_taosync_trigger:
                time_diff = (datetime.now() - self._last_taosync_trigger).total_seconds()
                if time_diff < 60:
                    trigger_str = f"{int(time_diff)}秒前"
                elif time_diff < 3600:
                    trigger_str = f"{int(time_diff // 60)}分钟前"
                else:
                    trigger_str = f"{int(time_diff // 3600)}小时前"
                taosync_trigger = f"📡 最后触发：{trigger_str}"
            else:
                taosync_trigger = "📡 尚未触发"
        else:
            taosync_status = "⭕ 未启用"
            taosync_trigger = ""
        
        # 构建最近处理记录
        recent_items = []
        for f in self._recent_files[:5]:  # 只显示最近5个
            time_diff = (datetime.now() - f['time']).total_seconds()
            if time_diff < 60:
                time_str = f"{int(time_diff)}秒前"
            elif time_diff < 3600:
                time_str = f"{int(time_diff // 60)}分钟前"
            else:
                time_str = f"{int(time_diff // 3600)}小时前"
            
            size_gb = f['size'] / (1024**3)
            status_icon = "✅" if f['success'] == f['total'] else "⚠️"
            recent_items.append(
                f"  • {f['name']} ({size_gb:.1f}GB) - {time_str} {status_icon}"
            )
        
        recent_text = "\n".join(recent_items) if recent_items else "  暂无处理记录"
        
        return [
            {
                'component': 'VRow',
                'content': [
                    {
                        'component': 'VCol',
                        'props': {'cols': 12},
                        'content': [
                            {
                                'component': 'VCard',
                                'props': {'variant': 'tonal'},
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'text': '📊 CloudLink Monitor 状态'
                                    },
                                    {
                                        'component': 'VCardText',
                                        'text': f"{status_text}  |  监控 {monitor_count} 个目录\n🔗 硬链接模式  |  一对多（{target_count}目标）\n⏰ 运行时长：{runtime_str}"
                                    }
                                ]
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
                        'props': {'cols': 12, 'md': 6},
                        'content': [
                            {
                                'component': 'VCard',
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'text': '📈 本次会话统计'
                                    },
                                    {
                                        'component': 'VCardText',
                                        'text': f"📦 {self._session_files}个文件  |  💾 {size_str}  |  ⏱️ {runtime_str}\n✅ 成功：{self._session_success}  |  ❌ 失败：{self._session_failed}"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VCol',
                        'props': {'cols': 12, 'md': 6},
                        'content': [
                            {
                                'component': 'VCard',
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'text': '🎯 TaoSync 状态'
                                    },
                                    {
                                        'component': 'VCardText',
                                        'text': f"{taosync_status}\n{taosync_trigger}"
                                    }
                                ]
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
                        'props': {'cols': 12},
                        'content': [
                            {
                                'component': 'VCard',
                                'content': [
                                    {
                                        'component': 'VCardTitle',
                                        'text': '📺 最近处理'
                                    },
                                    {
                                        'component': 'VCardText',
                                        'text': recent_text
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

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
