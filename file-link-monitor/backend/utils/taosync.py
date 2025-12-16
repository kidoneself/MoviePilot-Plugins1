import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TaoSyncClient:
    """TaoSync客户端，用于触发云盘同步任务"""
    
    def __init__(self, url: str, username: str, password: str, job_id: int):
        """
        初始化TaoSync客户端
        
        Args:
            url: TaoSync服务地址
            username: 用户名
            password: 密码
            job_id: 要触发的任务ID
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.job_id = job_id
        self.session: Optional[requests.Session] = None
    
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
    
    def trigger_sync(self) -> bool:
        """
        触发同步任务
        
        Returns:
            bool: 触发是否成功
        """
        if not self.session:
            if not self.login():
                return False
        
        try:
            exec_url = f"{self.url}/svr/job"
            exec_data = {
                'id': self.job_id,
                'pause': None
            }
            
            response = self.session.put(exec_url, json=exec_data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"TaoSync任务 {self.job_id} 触发成功")
                return True
            else:
                logger.error(f"TaoSync任务触发失败: {response.text}")
                return False
        except Exception as e:
            logger.error(f"TaoSync任务触发异常: {e}")
            return False
