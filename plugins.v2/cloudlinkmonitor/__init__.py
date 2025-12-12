import datetime
import hashlib
import random
import re
import shutil
import threading
import traceback
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

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
    plugin_desc = "监控目录文件变化，纯复制模式转移文件，保持目录结构并修改hash。"
    # 插件图标
    plugin_icon = "Linkease_A.png"
    # 插件版本
    plugin_version = "3.1.0"
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
    _transfer_type = "copyhash"
    # 存储源目录与目的目录关系
    _dirconf: Dict[str, Optional[Path]] = {}
    # 存储源目录转移方式
    _transferconf: Dict[str, Optional[str]] = {}
    # 退出事件
    _event = threading.Event()

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
            self._transfer_type = config.get("transfer_type") or "copyhash"
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

                # 自定义转移方式（支持copy和copyhash）
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
                        if self._mode == "compatibility":
                            # 兼容模式，目录同步性能降低且NAS不能休眠，但可以兼容挂载的远程共享目录如SMB
                            observer = PollingObserver(timeout=10)
                        else:
                            # 内部处理系统操作类型选择最优解
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
                                        run_date=datetime.datetime.now(
                                            tz=pytz.timezone(settings.TZ)) + datetime.timedelta(seconds=3)
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
        远程全量同步
        """
        if event:
            event_data = event.event_data
            if not event_data or event_data.get("action") != "cloud_link_sync":
                return
            self.post_message(channel=event.event_data.get("channel"),
                              title="开始同步云盘实时监控目录 ...",
                              userid=event.event_data.get("user"))
        self.sync_all()
        if event:
            self.post_message(channel=event.event_data.get("channel"),
                              title="云盘实时监控目录同步完成！", userid=event.event_data.get("user"))

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

                # copy模式：纯复制模式，保持目录结构和文件名不变
                if transfer_type == "copy":
                    logger.info(f"copy模式：开始纯复制处理 {file_path.name}")
                    try:
                        if not target:
                            logger.error(f"copy模式：未配置监控目录 {mon_path} 的目的目录")
                            return
                        
                        # 计算相对路径，保持目录结构
                        mon_path_obj = Path(mon_path)
                        relative_path = file_path.relative_to(mon_path_obj)
                        logger.info(f"copy模式：相对路径 {relative_path}")
                        
                        # 构建目标路径（保持完整的目录结构和文件名）
                        target_file = target / relative_path
                        logger.info(f"copy模式：目标路径 {target_file}")
                        
                        # 确保目标目录存在
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 复制文件
                        logger.info(f"copy模式：开始复制文件 {file_path} -> {target_file}")
                        shutil.copy2(file_path, target_file)
                        logger.info(f"copy模式：文件复制完成")
                        
                        # 发送通知
                        if self._notify:
                            file_size = target_file.stat().st_size
                            original_dir = relative_path.parent if relative_path.parent != Path('.') else "根目录"
                            
                            notify_text = (
                                f"📁 目录：{original_dir}\n"
                                f"📄 文件名：{file_path.name}\n"
                                f"💾 文件大小：{file_size} 字节"
                            )
                            
                            self.post_message(
                                mtype=NotificationType.Manual,
                                title=f"✅ copy处理完成：{file_path.name}",
                                text=notify_text
                            )
                            logger.info(f"copy模式：已发送通知")
                        
                        logger.info(f"copy模式：{file_path.name} 处理成功")
                        return
                    except Exception as e:
                        logger.error(f"copy模式处理失败：{str(e)}")
                        logger.error(f"copy模式：错误详情 {traceback.format_exc()}")
                        return

                # copyhash模式：纯复制模式，跳过识别和整理流程
                elif transfer_type == "copyhash":
                    logger.info(f"copyhash模式：开始纯复制处理 {file_path.name}")
                    try:
                        if not target:
                            logger.error(f"copyhash模式：未配置监控目录 {mon_path} 的目的目录")
                            return
                        
                        # 计算相对路径，保持目录结构
                        mon_path_obj = Path(mon_path)
                        relative_path = file_path.relative_to(mon_path_obj)
                        logger.info(f"copyhash模式：相对路径 {relative_path}")
                        
                        # 处理目录名：对最后一级父目录名使用固定算法添加繁体字
                        if relative_path.parent != Path('.'):
                            # 有父目录
                            parent_parts = list(relative_path.parent.parts)
                            if parent_parts:
                                # 对最后一级目录名进行固定算法改变
                                last_dir = parent_parts[-1]
                                # 使用MD5 hash确保同名文件夹每次结果相同
                                hash_obj = hashlib.md5(last_dir.encode('utf-8'))
                                hash_int = int(hash_obj.hexdigest(), 16)
                                
                                traditional_chars = ['繁', '體', '字', '隨', '機', '變', '換', '檔', '案', '雜', '湊', '測', '試', '電', '影', '視', '頻', '劇', '集', '節', '檔']
                                # 使用hash值作为随机种子，确保每次结果相同
                                char_count = (hash_int % 3) + 2  # 2-4个字符
                                selected_chars = []
                                for i in range(char_count):
                                    idx = (hash_int >> (i * 5)) % len(traditional_chars)
                                    selected_chars.append(traditional_chars[idx])
                                random_chars = ''.join(selected_chars)
                                
                                # 在目录名中间插入
                                if len(last_dir) > 3:
                                    insert_pos = (hash_int % (len(last_dir) - 2)) + 1
                                    new_last_dir = last_dir[:insert_pos] + random_chars + last_dir[insert_pos:]
                                else:
                                    new_last_dir = last_dir + random_chars
                                
                                logger.info(f"copyhash模式：目录名固定算法改变 {last_dir} -> {new_last_dir}")
                                parent_parts[-1] = new_last_dir
                                target_dir = target / Path(*parent_parts)
                            else:
                                target_dir = target
                        else:
                            # 没有父目录，直接放在目标目录
                            target_dir = target
                        
                        # 构建目标文件路径
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
                            file_stem = target_file.stem
                            file_suffix = target_file.suffix
                            logger.info(f"copyhash模式：原始文件名={file_stem}, 扩展名={file_suffix}")
                            
                            # 查找文件名中的数字（优先提取集数E后的数字）
                            episode_pattern = re.search(r'[Ee](\d+)', file_stem)
                            
                            if episode_pattern:
                                new_stem = episode_pattern.group(1)
                                logger.info(f"copyhash模式：检测到集数标识E，提取集数={new_stem}")
                            else:
                                number_pattern = re.search(r'(\d+)', file_stem)
                                if number_pattern:
                                    new_stem = number_pattern.group(1)
                                    logger.info(f"copyhash模式：未检测到集数标识，提取第一个数字={new_stem}")
                                else:
                                    logger.info(f"copyhash模式：文件名不包含数字，将插入繁体字")
                                    traditional_chars = ['繁', '體', '字', '隨', '機', '變', '換', '檔', '案', '雜', '湊', '測', '試', '電', '影', '視', '頻', '劇', '集', '節', '檔']
                                    char_count = random.randint(2, 4)
                                    random_chars = ''.join(random.sample(traditional_chars, char_count))
                                    logger.info(f"copyhash模式：随机选择{char_count}个繁体字={random_chars}")
                                    if len(file_stem) > 3:
                                        insert_pos = random.randint(1, len(file_stem) - 1)
                                        new_stem = file_stem[:insert_pos] + random_chars + file_stem[insert_pos:]
                                        logger.info(f"copyhash模式：在位置{insert_pos}插入繁体字")
                                    else:
                                        new_stem = file_stem + random_chars
                                        logger.info(f"copyhash模式：文件名较短，在末尾追加繁体字")
                            
                            logger.info(f"copyhash模式：新文件名={new_stem}{file_suffix}")
                            new_file_path = target_file.parent / f"{new_stem}{file_suffix}"
                            
                            # 计算原始文件hash
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
                            
                            # 重命名文件
                            target_file.rename(new_file_path)
                            logger.info(f"copyhash模式：文件重命名成功 {target_file.name} -> {new_file_path.name}")
                            logger.info(f"copyhash模式：处理完成 {new_file_path}")
                        
                        # 发送通知
                        if self._notify:
                            # 构建通知内容
                            original_dir = relative_path.parent if relative_path.parent != Path('.') else "根目录"
                            target_relative = new_file_path.relative_to(target)
                            target_dir_display = target_relative.parent if target_relative.parent != Path('.') else "根目录"
                            
                            notify_text = (
                                f"📁 原目录：{original_dir}\n"
                                f"📁 新目录：{target_dir_display}\n"
                                f"📄 原文件名：{file_path.name}\n"
                                f"📄 新文件名：{new_file_path.name}\n"
                                f"🔐 原Hash：{original_hash[:16]}...\n"
                                f"🔐 新Hash：{new_hash[:16]}...\n"
                                f"💾 文件大小：{original_size} → {new_size} 字节"
                            )
                            
                            self.post_message(
                                mtype=NotificationType.Manual,
                                title=f"✅ copyhash处理完成：{file_path.name}",
                                text=notify_text
                            )
                            logger.info(f"copyhash模式：已发送通知")
                        
                        logger.info(f"copyhash模式：{file_path.name} 处理成功")
                        return
                    except Exception as e:
                        logger.error(f"copyhash模式处理失败：{str(e)}")
                        logger.error(f"copyhash模式：错误详情 {traceback.format_exc()}")
                        return
                
                else:
                    # 不支持的转移方式
                    logger.error(f"不支持的转移方式：{transfer_type}，仅支持copy和copyhash")
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
        return [{
            "cmd": "/cloud_link_sync",
            "event": EventType.PluginAction,
            "desc": "云盘实时监控同步",
            "category": "",
            "data": {
                "action": "cloud_link_sync"
            }
        }]

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
                                                {'title': '纯复制', 'value': 'copy'},
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
                                                           '监控目录:转移目的目录#copy\n'
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
                                            'text': 'copy模式：纯复制，保持目录结构和文件名不变。\ncopyhash模式：纯复制，保持目录结构，对最后一级目录名和文件名进行固定算法改变，修改文件hash。'
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
            "transfer_type": "copyhash",
            "monitor_dirs": "",
            "exclude_keywords": "",
            "cron": "",
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
