"""
迅雷网盘API - 使用Playwright获取token创建分享链接
"""
import requests
import logging
import json
import time
import os
from typing import Tuple, Optional, List, Dict
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

# 是否使用无头模式，默认根据环境变量判断，服务器部署时设为True
HEADLESS_MODE = os.getenv('XUNLEI_HEADLESS', 'true').lower() == 'true'

# 全局浏览器管理器
class BrowserManager:
    """全局浏览器实例管理器，确保所有操作在独立线程中"""
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None  # 全局context，复用
        self.page = None     # 全局page，复用
        self.auth_info = {'authorization': None, 'x-captcha-token': None}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def _init_browser(self):
        """初始化Playwright浏览器（在当前线程中）"""
        with self.lock:
            if self.browser:
                return
            
            mode = "无头" if HEADLESS_MODE else "有头"
            logger.info(f"🌐 启动全局Playwright浏览器（{mode}模式）...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=HEADLESS_MODE)
            logger.info(f"✅ 全局浏览器初始化成功（{mode}模式）")
    
    def _init_context(self, cookies):
        """初始化浏览器上下文和页面（在当前线程中）"""
        with self.lock:
            if self.context and self.page:
                return
            
            logger.info("📱 初始化全局浏览器上下文...")
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            self.context.add_cookies(cookies)
            self.page = self.context.new_page()
            
            # 设置请求监听，捕获token
            def capture_token(request):
                headers = request.headers
                if 'api-pan.xunlei.com' in request.url or 'api-gateway-pan.xunlei.com' in request.url:
                    if 'authorization' in headers:
                        self.auth_info['authorization'] = headers['authorization']
                    if 'x-captcha-token' in headers:
                        self.auth_info['x-captcha-token'] = headers['x-captcha-token']
            
            self.page.on('request', capture_token)
            logger.info("✅ 全局浏览器上下文初始化成功")
    
    def get_browser(self):
        """获取浏览器实例（在当前线程中调用，不额外提交任务）"""
        if not self.browser:
            self._init_browser()
        return self.browser
    
    def get_page(self, cookies):
        """获取页面实例，复用全局page"""
        if not self.browser:
            self._init_browser()
        if not self.context or not self.page:
            self._init_context(cookies)
        return self.page, self.auth_info
    
    def run_in_thread(self, func):
        """在浏览器线程中运行函数"""
        return self.executor.submit(func).result()

# 全局单例
_browser_manager = BrowserManager()


class XunleiAPIError(Exception):
    """迅雷网盘API异常"""
    pass


class XunleiAPI:
    """迅雷网盘API封装 - 使用Playwright方案"""
    
    def __init__(self, cookie: str, user_id: str = None):
        """
        初始化迅雷网盘API
        
        Args:
            cookie: 迅雷Cookie（JSON格式或简单键值对格式）
            user_id: 用户ID（可选，会从cookie中提取）
        """
        self.cookie_str = cookie
        self.cookies = self._parse_cookie(cookie)
        self.user_id = user_id or self._extract_user_id()
        
    def _parse_cookie(self, cookie_str: str) -> List[Dict]:
        """解析Cookie为Playwright格式"""
        cookies = []
        
        # 尝试解析JSON格式
        try:
            parsed = json.loads(cookie_str)
            if isinstance(parsed, list):
                # 已经是列表格式
                for item in parsed:
                    if 'name' in item and 'value' in item:
                        cookies.append({
                            'name': item['name'],
                            'value': item['value'],
                            'domain': item.get('domain', '.xunlei.com'),
                            'path': item.get('path', '/')
                        })
                return cookies
        except:
            pass
        
        # 解析键值对格式：key1=value1; key2=value2
        for item in cookie_str.strip().split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies.append({
                    'name': key.strip(),
                    'value': value.strip(),
                    'domain': '.xunlei.com',
                    'path': '/'
                })
        
        return cookies
    
    def _extract_user_id(self) -> Optional[str]:
        """从Cookie中提取user_id"""
        for cookie in self.cookies:
            if cookie.get('name') == 'userid':
                return cookie.get('value')
        return None
    
    def _refresh_token_sync(self, page, auth_info) -> bool:
        """刷新页面获取新token（同步版本，在线程中运行）"""
        try:
            logger.info("🔄 刷新页面获取token...")
            
            # 重置token
            auth_info['authorization'] = None
            auth_info['x-captcha-token'] = None
            
            # 检查当前URL，如果不是迅雷网盘，就导航过去
            current_url = page.url
            if 'pan.xunlei.com' not in current_url:
                logger.info(f"   当前页面: {current_url}，导航到迅雷网盘...")
                page.goto('https://pan.xunlei.com', wait_until='networkidle', timeout=30000)
                logger.info("   页面加载完成")
            else:
                logger.info("   刷新现有页面...")
                page.reload(wait_until='networkidle', timeout=30000)
                logger.info("   页面刷新完成")
            
            # 等待token捕获（最多10秒）
            logger.info("   等待捕获token...")
            max_wait = 10
            waited = 0
            while waited < max_wait:
                if auth_info['authorization'] and auth_info['x-captcha-token']:
                    logger.info(f"✅ Token获取成功 (耗时{waited}秒)")
                    return True
                time.sleep(0.5)
                waited += 0.5
                if waited % 2 == 0:
                    logger.info(f"   等待中... ({waited}s) auth:{bool(auth_info['authorization'])} token:{bool(auth_info['x-captcha-token'])}")
            
            logger.error(f"❌ Token获取超时 - auth:{bool(auth_info['authorization'])} token:{bool(auth_info['x-captcha-token'])}")
            return False
            
        except Exception as e:
            logger.error(f"刷新token失败: {str(e)}")
            return False
    
    def search_file(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        搜索文件获取file_id
        
        Args:
            filename: 文件夹名称
            
        Returns:
            (file_id, error_msg): 成功返回(file_id, None)，失败返回(None, 错误信息)
        """
        try:
            # 获取全局page和auth_info
            page, auth_info = _browser_manager.run_in_thread(lambda: _browser_manager.get_page(self.cookies))
            
            # 获取新token
            result = _browser_manager.run_in_thread(lambda: self._refresh_token_sync(page, auth_info))
            if not result:
                return None, "无法获取认证token"
            
            # 搜索文件
            logger.info(f"🔍 搜索文件: {filename}")
            
            headers = {
                'accept': '*/*',
                'authorization': auth_info['authorization'],
                'x-captcha-token': auth_info['x-captcha-token'],
                'x-client-id': 'Xqp0kJBXWhwaTpB6',
                'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            params = {
                "keyword": filename,
                "limit": "20",
                "space": "*",
                "user_id": self.user_id,
                "parent_id": "",
                "page_token": ""
            }
            
            response = requests.get(
                "https://api-gateway-pan.xunlei.com/xlppc.searcher.api/drive_file_search",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"搜索请求失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return None, error_msg
            
            data = response.json()
            
            # 检查响应
            if data.get('code') != 0:
                error_msg = f"搜索失败: {data.get('message', '未知错误')}"
                logger.error(error_msg)
                return None, error_msg
            
            # 获取文件列表
            files = data.get('data', {}).get('files', [])
            if not files:
                error_msg = f"未找到文件: {filename}"
                logger.warning(error_msg)
                return None, error_msg
            
            # 精确匹配文件名
            for item in files:
                if item.get('name') == filename:
                    file_id = item.get('id')
                    logger.info(f"✅ 找到文件: {filename}")
                    logger.info(f"   file_id: {file_id}")
                    return file_id, None
            
            # 如果没有精确匹配，返回第一个
            file_id = files[0].get('id')
            file_name = files[0].get('name')
            logger.warning(f"未找到精确匹配，使用第一个结果: {file_name}")
            return file_id, None
            
        except requests.RequestException as e:
            error_msg = f"搜索请求异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"搜索文件时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def create_share_link(self, file_id: str, auth_info: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        创建分享链接
        
        Args:
            file_id: 文件ID
            auth_info: 认证信息字典
            
        Returns:
            (share_link, error_msg): 成功返回(完整链接, None)，失败返回(None, 错误信息)
        """
        try:
            logger.info(f"📤 创建分享链接: file_id={file_id}")
            
            headers = {
                'accept': 'application/json, text/plain, */*',
                'authorization': auth_info['authorization'],
                'x-captcha-token': auth_info['x-captcha-token'],
                'x-client-id': 'Xqp0kJBXWhwaTpB6',
                'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            data = {
                "file_ids": [file_id],
                "share_to": "copy",
                "params": {
                    "subscribe_push": "false",
                    "WithPassCodeInLink": "true"
                },
                "title": "云盘资源分享",
                "restore_limit": "-1",
                "expiration_days": "-1"
            }
            
            response = requests.post(
                "https://api-pan.xunlei.com/drive/v1/share",
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"创建分享链接请求失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return None, error_msg
            
            result = response.json()
            
            # 提取链接
            share_url = result.get('share_url')
            pass_code = result.get('pass_code', '')
            
            if not share_url:
                error_msg = f"创建分享链接失败: {result.get('error_description', result.get('message', '未知错误'))}"
                logger.error(error_msg)
                return None, error_msg
            
            # 格式化完整链接
            share_link = f"{share_url}?pwd={pass_code} 提取码: {pass_code}"
            logger.info(f"✅ 分享链接创建成功: {share_url}")
            
            return share_link, None
            
        except requests.RequestException as e:
            error_msg = f"创建分享链接时网络异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"创建分享链接时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def generate_share_link(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        一键生成分享链接（完整流程）
        
        Args:
            filename: 文件夹名称
            
        Returns:
            (share_link, error_msg): 成功返回(完整分享链接, None)，失败返回(None, 错误信息)
        """
        logger.info(f"开始生成迅雷分享链接: {filename}")
        
        # 1. 搜索文件获取file_id（内部会刷新token）
        file_id, error = self.search_file(filename)
        if error:
            return None, error
        
        # 2. 创建分享链接（使用同一个token）
        # 获取全局auth_info
        _, auth_info = _browser_manager.run_in_thread(lambda: _browser_manager.get_page(self.cookies))
        share_link, error = self.create_share_link(file_id, auth_info)
        if error:
            return None, error
        
        logger.info(f"✅ 完整流程成功: {filename} -> {share_link}")
        return share_link, None
        
        # 注意：全局浏览器和页面保持打开，复用以提高性能


def test():
    """测试函数"""
    # 测试Cookie（JSON格式）
    cookies = [
        {"name": "XLA_CI", "value": "5ae70956cf5eb5acc2644c1ded0e22fd", "domain": ".xunlei.com", "path": "/"},
        {"name": "deviceid", "value": "wdi10.d765a49124d0b4c8d593d73daa738f51134146e64398f5f02515b17ad857699e", "domain": ".xunlei.com", "path": "/"},
        {"name": "sessionid", "value": "cs001.3480B930C7A49B0671DC7FAB26763D02", "domain": ".xunlei.com", "path": "/"},
        {"name": "userid", "value": "683676213", "domain": ".xunlei.com", "path": "/"},
    ]
    
    cookie_str = json.dumps(cookies)
    
    api = XunleiAPI(cookie_str)
    link, error = api.generate_share_link("A-闲鱼影视（自动更新）")
    
    if error:
        print(f"❌ 失败: {error}")
    else:
        print(f"✅ 成功: {link}")


if __name__ == '__main__':
    test()
