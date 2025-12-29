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
    
    # ============ 转存功能 ============
    
    def transfer(self, share_url: str, pass_code: Optional[str], target_path: str) -> Dict:
        """
        转存文件（从pan_transfer_api.py迁移过来）
        
        Args:
            share_url: 分享链接
            pass_code: 提取码
            target_path: 目标路径（完整路径，如：/baidu/A-闲鱼影视/剧集）
        
        Returns:
            {
                'success': bool,
                'file_count': int,
                'file_ids': List[str],
                'message': str
            }
        """
        from backend.common.response import ResponseUtil
        from urllib.parse import unquote
        import time
        
        try:
            # 1. 解析分享链接
            shorturl = self._parse_share_url(share_url)
            
            # 2. 创建Session并验证提取码
            sekey, session, bdstoken = self._verify_code_with_session(shorturl, pass_code)
            
            # 3. 获取文件列表
            share_id, uk, fs_ids = self._get_file_list(shorturl, bdstoken, session)
            
            # 4. 执行转存
            task_id = self._do_transfer(share_id, uk, fs_ids, target_path, sekey, bdstoken)
            
            # 5. 如果是异步任务，轮询
            if task_id != 0:
                self._poll_task(task_id, bdstoken)
            
            return ResponseUtil.pan_transfer_success(
                pan_type='baidu',
                file_count=len(fs_ids),
                file_ids=[str(fid) for fid in fs_ids],
                message='转存成功'
            )
        except Exception as e:
            logger.error(f"百度转存失败: {e}")
            return ResponseUtil.pan_transfer_error('baidu', f'转存失败: {str(e)}')
    
    def _parse_share_url(self, share_url: str) -> str:
        """解析分享链接"""
        match = re.search(r'/s/1([a-zA-Z0-9_-]+)', share_url)
        if not match:
            raise BaiduPanAPIError("无效的百度分享链接")
        return match.group(1)
    
    def _verify_code_with_session(self, shorturl: str, pass_code: Optional[str]):
        """验证提取码并返回sekey、session、bdstoken"""
        from urllib.parse import unquote
        
        # 创建Session
        session = requests.Session()
        session.cookies.update(self.cookies)
        
        # 清除旧BDCLND
        if 'BDCLND' in session.cookies:
            del session.cookies['BDCLND']
        
        # 1. 获取bdstoken
        response = session.get("https://pan.baidu.com/disk/main")
        
        patterns = [
            r'"bdstoken"\s*:\s*"([^"]+)"',
            r'bdstoken\s*:\s*"([^"]+)"',
            r'bdstoken=([a-f0-9]+)'
        ]
        
        bdstoken = None
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                bdstoken = match.group(1)
                break
        
        if not bdstoken:
            raise BaiduPanAPIError("无法提取bdstoken")
        
        # 2. 验证提取码
        verify_url = "https://pan.baidu.com/share/verify"
        verify_params = {
            'surl': shorturl,
            'channel': 'chunlei',
            'web': '1',
            'app_id': '250528',
            'clienttype': '0'
        }
        verify_data = {'pwd': pass_code} if pass_code else {}
        
        verify_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://pan.baidu.com',
            'Referer': f'https://pan.baidu.com/s/1{shorturl}'
        }
        
        verify_response = session.post(verify_url, params=verify_params, data=verify_data, headers=verify_headers)
        verify_result = verify_response.json()
        
        if verify_result.get('errno') != 0:
            raise BaiduPanAPIError(f"验证提取码失败: {verify_result.get('show_msg', 'Unknown error')}")
        
        # 获取BDCLND
        sekey = None
        for cookie in session.cookies:
            if cookie.name == 'BDCLND':
                sekey = unquote(cookie.value)
                break
        
        if not sekey:
            raise BaiduPanAPIError("未获取到sekey (BDCLND Cookie)")
        
        return sekey, session, bdstoken
    
    def _get_file_list(self, shorturl: str, bdstoken: str, session):
        """获取文件列表"""
        url = "https://pan.baidu.com/share/list"
        params = {
            'shorturl': shorturl,
            'root': 1,
            'page': 1,
            'num': 1000,
            'web': 1,
            'channel': 'chunlei',
            'clienttype': 0,
            'showempty': 0,
            'bdstoken': bdstoken,
            'order': 'time',
            'app_id': '250528'
        }
        
        headers = {
            'Referer': f'https://pan.baidu.com/s/1{shorturl}'
        }
        
        response = session.get(url, params=params, headers=headers)
        result = response.json()
        
        if result.get('errno') != 0:
            raise BaiduPanAPIError(f"获取文件列表失败: {result}")
        
        share_id = result.get('share_id')
        uk = result.get('uk')
        file_list = result.get('list', [])
        
        # 如果只有一个文件夹，获取文件夹内容
        if len(file_list) == 1 and str(file_list[0].get('isdir')) == '1':
            folder_path = file_list[0]['path']
            params['dir'] = folder_path
            params['root'] = 0
            response = session.get(url, params=params, headers=headers)
            result = response.json()
            file_list = result.get('list', [])
        
        fs_ids = [int(f['fs_id']) for f in file_list]
        return share_id, uk, fs_ids
    
    def _do_transfer(self, share_id: str, uk: str, fs_ids: list, target_path: str, sekey: str, bdstoken: str) -> int:
        """执行转存"""
        # 去掉OpenList路径前缀 /baidu/
        if target_path.startswith('/baidu/'):
            target_path = target_path[6:]
        
        url = "https://pan.baidu.com/share/transfer"
        params = {
            'shareid': share_id,
            'from': uk,
            'sekey': sekey,
            'ondup': 'newcopy',
            'async': 1,
            'channel': 'chunlei',
            'web': 1,
            'app_id': '250528',
            'bdstoken': bdstoken,
            'clienttype': 0
        }
        
        data = {
            'fsidlist': f'[{",".join(map(str, fs_ids))}]',
            'path': target_path
        }
        
        cookies = self.cookies.copy()
        cookies['BDCLND'] = sekey
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://pan.baidu.com/'
        }
        
        response = requests.post(url, params=params, data=data, cookies=cookies, headers=headers)
        result = response.json()
        
        # errno=0: 成功, errno=4: 文件已存在
        if result.get('errno') in [0, 4]:
            info = result.get('info', {})
            if isinstance(info, dict):
                return info.get('task_id', 0)
            return 0
        else:
            raise BaiduPanAPIError(f"转存失败: {result}")
    
    def _poll_task(self, task_id: int, bdstoken: str):
        """轮询异步任务"""
        import time
        
        url = "https://pan.baidu.com/share/taskquery"
        params = {'taskid': task_id, 'bdstoken': bdstoken}
        
        for _ in range(60):
            time.sleep(0.5)
            response = requests.get(url, params=params, cookies=self.cookies)
            result = response.json()
            
            if result.get('errno') != 0:
                raise BaiduPanAPIError(f"查询任务失败: {result}")
            
            status = result.get('status')
            if status == 'success':
                return
            elif status == 'failed':
                raise BaiduPanAPIError("转存任务失败")


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
