"""
统一HTTP客户端
提供超时、日志、异常处理
"""
import requests
import logging
from typing import Optional, Dict, Any
from backend.common.constants import DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


class HTTPClient:
    """统一HTTP客户端"""
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.session = requests.Session()
        self.timeout = timeout
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET请求"""
        kwargs.setdefault('timeout', self.timeout)
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"HTTP GET失败: {url}, 错误: {e}")
            raise
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST请求"""
        kwargs.setdefault('timeout', self.timeout)
        try:
            response = self.session.post(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"HTTP POST失败: {url}, 错误: {e}")
            raise
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT请求"""
        kwargs.setdefault('timeout', self.timeout)
        try:
            response = self.session.put(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"HTTP PUT失败: {url}, 错误: {e}")
            raise
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE请求"""
        kwargs.setdefault('timeout', self.timeout)
        try:
            response = self.session.delete(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"HTTP DELETE失败: {url}, 错误: {e}")
            raise
    
    def close(self):
        """关闭会话"""
        self.session.close()


# 全局HTTP客户端实例
http_client = HTTPClient()

