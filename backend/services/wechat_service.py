"""
企业微信服务层 - 封装企业微信API调用
"""
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WeChatService:
    """企业微信服务类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化企业微信服务
        
        Args:
            config: 企业微信配置字典
        """
        self.corp_id = config.get('corp_id')
        self.agent_id = config.get('agent_id')
        self.secret = config.get('secret')
        self.token = config.get('token')
        self.encoding_aes_key = config.get('encoding_aes_key')
        
        # 代理配置
        proxy_config = config.get('proxy', {})
        self.proxies = None
        if proxy_config.get('enabled'):
            self.proxies = {
                'http': proxy_config.get('http'),
                'https': proxy_config.get('https')
            }
            logger.info(f"✅ 企业微信代理已启用: {self.proxies}")
        
        # Access Token缓存
        self._access_token = None
        self._token_expires_at = None
        
        logger.info(f"企业微信服务初始化完成 (AgentId: {self.agent_id})")
    
    def get_access_token(self) -> str:
        """
        获取企业微信Access Token（带缓存）
        
        Returns:
            Access Token字符串
        """
        # 检查缓存
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        # 重新获取
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            'corpid': self.corp_id,
            'corpsecret': self.secret
        }
        
        try:
            response = requests.get(url, params=params, proxies=self.proxies, timeout=10)
            data = response.json()
            
            if data.get('errcode') == 0:
                self._access_token = data['access_token']
                # 提前5分钟过期
                expires_in = data.get('expires_in', 7200) - 300
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                logger.info("✅ 获取Access Token成功")
                return self._access_token
            else:
                error_msg = f"获取Access Token失败: {data.get('errmsg')}"
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f"获取Access Token异常: {e}")
            raise
    
    def send_text(self, user_id: str, content: str) -> bool:
        """
        发送文本消息
        
        Args:
            user_id: 用户ID
            content: 消息内容
            
        Returns:
            是否发送成功
        """
        access_token = self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        data = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        try:
            response = requests.post(url, json=data, proxies=self.proxies, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"✅ 发送消息成功 -> {user_id}")
                return True
            else:
                logger.error(f"❌ 发送消息失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False
    
    def send_markdown(self, user_id: str, content: str) -> bool:
        """
        发送Markdown消息
        
        Args:
            user_id: 用户ID
            content: Markdown内容
            
        Returns:
            是否发送成功
        """
        access_token = self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        data = {
            "touser": user_id,
            "msgtype": "markdown",
            "agentid": self.agent_id,
            "markdown": {
                "content": content
            }
        }
        
        try:
            response = requests.post(url, json=data, proxies=self.proxies, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"✅ 发送Markdown消息成功 -> {user_id}")
                return True
            else:
                logger.error(f"❌ 发送Markdown消息失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            logger.error(f"发送Markdown消息异常: {e}")
            return False
    
    def send_textcard(self, user_id: str, title: str, description: str, 
                      url: str = None, btntxt: str = "详情") -> bool:
        """
        发送文本卡片消息
        
        Args:
            user_id: 用户ID
            title: 标题
            description: 描述
            url: 点击跳转URL（可选）
            btntxt: 按钮文本
            
        Returns:
            是否发送成功
        """
        access_token = self.get_access_token()
        api_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        card_data = {
            "title": title,
            "description": description,
            "btntxt": btntxt
        }
        
        if url:
            card_data["url"] = url
        
        data = {
            "touser": user_id,
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": card_data
        }
        
        try:
            response = requests.post(api_url, json=data, proxies=self.proxies, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"✅ 发送卡片消息成功 -> {user_id}")
                return True
            else:
                logger.error(f"❌ 发送卡片消息失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            logger.error(f"发送卡片消息异常: {e}")
            return False
