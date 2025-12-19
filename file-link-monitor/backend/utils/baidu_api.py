"""
百度网盘API - 通过接口创建分享链接
"""
import requests
import logging
import re
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class BaiduPanAPIError(Exception):
    """百度网盘API异常"""
    pass


class BaiduPanAPI:
    """百度网盘API封装"""
    
    def __init__(self, cookie: str):
        """
        初始化百度网盘API
        
        Args:
            cookie: 百度网盘Cookie字符串
        """
        self.cookie = cookie
        self.cookies = self._parse_cookie(cookie)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://pan.baidu.com/disk/main',
            'Accept': 'application/json, text/plain, */*',
        })
        
    def _parse_cookie(self, cookie_string: str) -> Dict[str, str]:
        """解析Cookie字符串为字典"""
        cookies = {}
        for item in cookie_string.strip().replace('\n', '').split(';'):
            if '=' in item:
                key, value = item.strip().split('=', 1)
                cookies[key] = value
        return cookies
    
    def search_file(self, filename: str, recursion: int = 1) -> Tuple[Optional[int], Optional[str]]:
        """
        搜索文件获取fs_id
        
        Args:
            filename: 文件夹名称
            recursion: 是否递归搜索全盘 (1=是, 0=否)
            
        Returns:
            (fs_id, error_msg): 成功返回(fs_id, None)，失败返回(None, 错误信息)
        """
        try:
            url = "https://pan.baidu.com/api/search"
            params = {
                'clienttype': 0,
                'app_id': 250528,
                'web': 1,
                'order': 'name',
                'desc': 0,
                'num': 100,
                'page': 1,
                'recursion': recursion,
                'key': filename
            }
            
            logger.info(f"🔍 搜索文件: {filename}")
            response = self.session.get(url, params=params, cookies=self.cookies, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"搜索请求失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return None, error_msg
            
            data = response.json()
            
            # 检查errno
            if data.get('errno') != 0:
                error_msg = f"搜索失败: errno={data.get('errno')}"
                logger.error(error_msg)
                return None, error_msg
            
            # 精确匹配文件夹
            file_list = data.get('list', [])
            if not file_list:
                error_msg = f"未找到文件: {filename}"
                logger.warning(error_msg)
                return None, error_msg
            
            for item in file_list:
                # 精确匹配文件名且必须是文件夹
                if item.get('server_filename') == filename and item.get('isdir') == 1:
                    fs_id = item.get('fs_id')
                    path = item.get('path', '')
                    logger.info(f"✅ 找到文件夹: {filename}")
                    logger.info(f"   fs_id: {fs_id}, path: {path}")
                    return fs_id, None
            
            error_msg = f"搜索到文件但不是文件夹或名称不完全匹配: {filename}"
            logger.warning(error_msg)
            return None, error_msg
            
        except requests.RequestException as e:
            error_msg = f"搜索请求异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"搜索文件时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def get_bdstoken(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取bdstoken
        
        Returns:
            (bdstoken, error_msg): 成功返回(bdstoken, None)，失败返回(None, 错误信息)
        """
        try:
            # 方案1: 从Cookie中获取
            if 'csrfToken' in self.cookies:
                bdstoken = self.cookies['csrfToken']
                logger.info(f"✅ 从Cookie提取bdstoken: {bdstoken}")
                return bdstoken, None
            
            if 'bdstoken' in self.cookies:
                bdstoken = self.cookies['bdstoken']
                logger.info(f"✅ 从Cookie提取bdstoken: {bdstoken}")
                return bdstoken, None
            
            # 方案2: 从网盘首页提取
            logger.info("⚠️  Cookie中未找到bdstoken，尝试从页面提取...")
            url = "https://pan.baidu.com/disk/main"
            response = self.session.get(url, cookies=self.cookies, timeout=30)
            
            if response.status_code != 200:
                error_msg = f"访问网盘首页失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return None, error_msg
            
            # 从页面HTML中查找 bdstoken
            match = re.search(r'bdstoken["\']?\s*:\s*["\']([^"\']+)', response.text)
            if match:
                bdstoken = match.group(1)
                logger.info(f"✅ 从页面提取到bdstoken: {bdstoken}")
                return bdstoken, None
            
            error_msg = "无法获取bdstoken，Cookie可能已失效"
            logger.error(error_msg)
            return None, error_msg
            
        except requests.RequestException as e:
            error_msg = f"获取bdstoken时网络异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"获取bdstoken时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def create_share_link(
        self, 
        fs_id: int, 
        bdstoken: str,
        pwd: str = 'yyds', 
        period: int = 0
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        创建分享链接
        
        Args:
            fs_id: 文件ID
            bdstoken: CSRF Token
            pwd: 提取码，默认yyds
            period: 有效期，0=永久，7=7天
            
        Returns:
            (share_link, error_msg): 成功返回(完整分享链接, None)，失败返回(None, 错误信息)
        """
        try:
            url = "https://pan.baidu.com/share/pset"
            params = {
                'channel': 'chunlei',
                'bdstoken': bdstoken,
                'clienttype': 0,
                'app_id': 250528,
                'web': 1,
            }
            
            data = {
                'is_knowledge': 0,
                'public': 0,
                'period': period,
                'pwd': pwd,
                'eflag_disable': 'true',
                'linkOrQrcode': 'link',
                'channel_list': '[]',
                'schannel': 4,
                'fid_list': f'[{fs_id}]'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            logger.info(f"📤 创建分享链接: fs_id={fs_id}, pwd={pwd}")
            response = self.session.post(
                url, 
                params=params, 
                data=data, 
                cookies=self.cookies, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"创建分享链接请求失败，状态码: {response.status_code}"
                logger.error(error_msg)
                return None, error_msg
            
            result = response.json()
            
            # 检查errno
            errno = result.get('errno', -1)
            if errno != 0:
                error_msg = f"创建分享链接失败: errno={errno}"
                # 特殊错误码处理
                if errno == -6:
                    error_msg += " (文件不存在或已删除)"
                elif errno == -9:
                    error_msg += " (权限不足)"
                elif errno == 112:
                    error_msg += " (页面过期，请重新获取bdstoken)"
                logger.error(error_msg)
                return None, error_msg
            
            # 提取链接
            link = result.get('link') or result.get('shorturl')
            if not link:
                error_msg = "响应中未包含分享链接"
                logger.error(error_msg)
                return None, error_msg
            
            # 格式化完整链接
            share_link = f"{link}?pwd={pwd} 提取码: {pwd}"
            logger.info(f"✅ 分享链接创建成功: {link}")
            
            return share_link, None
            
        except requests.RequestException as e:
            error_msg = f"创建分享链接时网络异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"创建分享链接时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def generate_share_link(self, filename: str, pwd: str = 'yyds', period: int = 0) -> Tuple[Optional[str], Optional[str]]:
        """
        一键生成分享链接（完整流程）
        
        Args:
            filename: 文件夹名称
            pwd: 提取码，默认yyds
            period: 有效期，0=永久，7=7天
            
        Returns:
            (share_link, error_msg): 成功返回(完整分享链接, None)，失败返回(None, 错误信息)
        """
        logger.info(f"开始生成分享链接: {filename}")
        
        # 1. 搜索文件获取fs_id
        fs_id, error = self.search_file(filename)
        if error:
            return None, error
        
        # 2. 获取bdstoken
        bdstoken, error = self.get_bdstoken()
        if error:
            return None, error
        
        # 3. 创建分享链接
        share_link, error = self.create_share_link(fs_id, bdstoken, pwd, period)
        if error:
            return None, error
        
        logger.info(f"✅ 完整流程成功: {filename} -> {share_link}")
        return share_link, None


def test():
    """测试函数"""
    cookie = """
    BAIDUID=29F8A9F9ED335ED512B1471B22CE89E0:FG=1; 
    BDUSS=你的BDUSS; 
    csrfToken=你的csrfToken;
    """
    
    api = BaiduPanAPI(cookie)
    link, error = api.generate_share_link("测试文件夹名")
    
    if error:
        print(f"❌ 失败: {error}")
    else:
        print(f"✅ 成功: {link}")


if __name__ == '__main__':
    test()
