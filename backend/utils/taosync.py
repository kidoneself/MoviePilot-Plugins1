import logging
import requests
import threading
import time
from typing import Optional, Tuple, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class TaoSyncStatus(Enum):
    """TaoSync任务状态"""
    RUNNING = 1  # 执行中
    COMPLETED = 2  # 已完成


class TaoSyncClient:
    """TaoSync客户端，用于触发云盘同步任务"""
    # 注意：为了向后兼容，保留原有的trigger_sync()方法返回bool的调用方式
    # 新代码应使用返回Tuple[bool, str]的方式
    
    def __init__(self, url: str, username: str, password: str, job_ids: list[int] = None, job_id: int = None):
        """
        初始化TaoSync客户端
        
        Args:
            url: TaoSync服务地址
            username: 用户名
            password: 密码
            job_ids: 要触发的任务ID列表（支持多个）
            job_id: 单个任务ID（向后兼容，不推荐使用）
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        
        # 支持多个任务ID
        if job_ids:
            self.job_ids = job_ids if isinstance(job_ids, list) else [job_ids]
        elif job_id:
            self.job_ids = [job_id]
        else:
            self.job_ids = []
            
        self.session: Optional[requests.Session] = None
        logger.info(f"TaoSync初始化，任务ID: {self.job_ids}")
    
    def login(self) -> bool:
        """
        登录TaoSync
        
        Returns:
            bool: 登录是否成功
        """
        try:
            login_url = f"{self.url}/svr/noAuth/login"
            login_data = {
                'userName': self.username,
                'passwd': self.password
            }
            
            self.session = requests.Session()
            response = self.session.post(login_url, json=login_data, timeout=10)
            
            if response.status_code == 200 and response.json().get('code') == 200:
                logger.info("TaoSync登录成功")
                return True
            else:
                logger.error(f"TaoSync登录失败: {response.text}")
                return False
        except Exception as e:
            logger.error(f"TaoSync登录异常: {e}")
            return False
    
    def check_job_status(self) -> Optional[dict]:
        """
        查询任务状态列表，返回最新的任务记录
        
        Returns:
            Optional[dict]: 最新的任务记录，如果查询失败返回None
        """
        if not self.session:
            if not self.login():
                return None
        
        try:
            status_url = f"{self.url}/svr/job"
            params = {
                'id': self.job_id,
                'current': 1
            }
            
            response = self.session.get(status_url, params=params, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    data_list = result.get('data', {}).get('dataList', [])
                    if data_list:
                        # 返回第一个（最新的）任务记录
                        latest_job = data_list[0]
                        logger.debug(f"最新任务状态: id={latest_job.get('id')}, status={latest_job.get('status')}")
                        return latest_job
            
            logger.error(f"查询任务状态失败: {response.text}")
            return None
        except Exception as e:
            logger.error(f"查询任务状态异常: {e}")
            return None
    
    def is_job_running(self) -> bool:
        """
        检查是否有任务正在执行
        
        Returns:
            bool: True表示有任务执行中，False表示空闲
        """
        job_status = self.check_job_status()
        if job_status:
            status = job_status.get('status')
            return status == TaoSyncStatus.RUNNING.value
        # 如果查询失败，保守起见认为有任务在执行
        return True
    
    def trigger_sync(self, check_status: bool = True, notifier: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        触发同步任务（支持多个任务ID）
        
        Args:
            check_status: 是否在触发前检查任务状态
            notifier: 通知回调函数
        
        Returns:
            Tuple[bool, str]: (是否全部成功, 详细消息)
        """
        if not self.session:
            if not self.login():
                return False, "login_failed"
        
        if not self.job_ids:
            return False, "no_job_ids"
        
        # 触发所有任务
        success_count = 0
        failed_count = 0
        running_count = 0
        results = []
        
        for job_id in self.job_ids:
            try:
                exec_url = f"{self.url}/svr/job"
                exec_data = {
                    'id': job_id,
                    'pause': None
                }
                
                response = self.session.put(exec_url, json=exec_data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 200:
                        logger.info(f"✅ TaoSync任务 {job_id} 触发成功")
                        results.append(f"任务{job_id}: 成功")
                        success_count += 1
                        if notifier:
                            notifier(f"TaoSync任务 {job_id} 触发成功")
                    elif result.get('code') == 500 and '执行中' in result.get('msg', ''):
                        logger.warning(f"⚠️ TaoSync任务 {job_id} 正在执行中")
                        results.append(f"任务{job_id}: 执行中")
                        running_count += 1
                    else:
                        logger.error(f"❌ TaoSync任务 {job_id} 触发失败: {result.get('msg')}")
                        results.append(f"任务{job_id}: 失败")
                        failed_count += 1
                else:
                    logger.error(f"❌ TaoSync任务 {job_id} 触发失败: {response.text}")
                    results.append(f"任务{job_id}: 失败")
                    failed_count += 1
            except Exception as e:
                logger.error(f"❌ TaoSync任务 {job_id} 触发异常: {e}")
                results.append(f"任务{job_id}: 异常")
                failed_count += 1
        
        # 汇总结果
        summary = f"成功{success_count}个, 执行中{running_count}个, 失败{failed_count}个"
        detail = ", ".join(results)
        message = f"{summary} | {detail}"
        
        # 发送汇总通知
        if notifier:
            notifier(f"TaoSync触发完成: {summary}")
        
        # 只要有一个成功就算成功
        return success_count > 0, message


class TaoSyncQueue:
    """TaoSync任务队列管理器，处理任务执行中的延迟触发"""
    
    def __init__(self, client: TaoSyncClient, check_interval: int = 60, notifier: Optional[Callable] = None):
        """
        初始化任务队列管理器
        
        Args:
            client: TaoSync客户端
            check_interval: 检查间隔（秒），默认60秒
            notifier: 通知回调函数
        """
        self.client = client
        self.check_interval = check_interval
        self.notifier = notifier
        
        self.pending_trigger = False  # 是否有待触发的任务
        self.pending_count = 0  # 待触发的批次数
        self.pending_files = 0  # 待触发的文件数
        self.last_trigger_time = None  # 最后一次触发时间
        
        self.lock = threading.Lock()
        self.check_thread = None
        self.stop_event = threading.Event()
        self.running = False
    
    def start(self):
        """启动队列检查线程"""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        logger.info(f"TaoSync队列管理器已启动，检查间隔: {self.check_interval}秒")
    
    def stop(self):
        """停止队列检查线程"""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("TaoSync队列管理器已停止")
    
    def add_pending_trigger(self, file_count: int = 1):
        """添加待触发的任务请求"""
        with self.lock:
            self.pending_trigger = True
            self.pending_count += 1
            self.pending_files += file_count
            logger.info(f"添加待触发任务：批次 {self.pending_count}，共 {self.pending_files} 个文件")
    
    def trigger_now(self, file_count: int = 0, force: bool = False) -> Tuple[bool, str]:
        """
        立即尝试触发任务
        
        Args:
            file_count: 本次批次的文件数
            force: 是否强制触发（不检查状态）
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        success, reason = self.client.trigger_sync(check_status=not force, notifier=self.notifier)
        
        if success:
            with self.lock:
                self.last_trigger_time = datetime.now()
                # 清空待触发标记
                if self.pending_trigger:
                    logger.info(f"✅ 触发成功，清空待触发队列（批次: {self.pending_count}, 文件: {self.pending_files}）")
                self.pending_trigger = False
                self.pending_count = 0
                self.pending_files = 0
            return True, "success"
        elif reason == "running":
            # 任务执行中，添加到待触发队列
            self.add_pending_trigger(file_count)
            if self.notifier:
                self.notifier(f"TaoSync任务执行中，已加入队列等待（批次: {self.pending_count}, 文件: {self.pending_files}）")
            return False, "queued"
        else:
            logger.error(f"触发失败: {reason}")
            return False, reason
    
    def _check_loop(self):
        """后台检查循环"""
        while not self.stop_event.wait(self.check_interval):
            self._check_and_trigger()
    
    def _check_and_trigger(self):
        """检查是否有待触发的任务，如果任务空闲则触发"""
        with self.lock:
            if not self.pending_trigger:
                return
            
            pending_count = self.pending_count
            pending_files = self.pending_files
        
        logger.info(f"检查待触发任务：批次 {pending_count}，文件 {pending_files}")
        
        # 检查任务是否空闲
        if not self.client.is_job_running():
            logger.info("任务空闲，尝试触发待处理的同步任务...")
            success, reason = self.client.trigger_sync(check_status=False, notifier=self.notifier)
            
            if success:
                with self.lock:
                    self.last_trigger_time = datetime.now()
                    self.pending_trigger = False
                    self.pending_count = 0
                    self.pending_files = 0
                
                logger.info(f"✅ 队列任务触发成功（批次: {pending_count}, 文件: {pending_files}）")
                if self.notifier:
                    self.notifier(f"队列任务触发成功（批次: {pending_count}, 文件: {pending_files}）")
            else:
                logger.warning(f"队列任务触发失败: {reason}")
        else:
            logger.info("任务仍在执行中，继续等待...")
    
    def get_status(self) -> dict:
        """获取队列状态"""
        with self.lock:
            return {
                'pending': self.pending_trigger,
                'pending_count': self.pending_count,
                'pending_files': self.pending_files,
                'last_trigger_time': self.last_trigger_time.isoformat() if self.last_trigger_time else None
            }
