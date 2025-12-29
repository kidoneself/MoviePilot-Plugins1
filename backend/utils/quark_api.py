"""
夸克网盘API封装
提供搜索文件、创建分享链接和转存功能
"""
import requests
import time
import logging
import re
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class QuarkAPI:
    """夸克网盘API封装类"""
    
    SEARCH_URL = "https://drive-pc.quark.cn/1/clouddrive/file/search"
    CREATE_SHARE_URL = "https://drive-pc.quark.cn/1/clouddrive/share"
    TASK_URL = "https://drive-pc.quark.cn/1/clouddrive/task"
    PASSWORD_URL = "https://drive-pc.quark.cn/1/clouddrive/share/password"
    
    def __init__(self, cookie: str):
        """
        初始化夸克网盘API
        
        Args:
            cookie: 完整的Cookie字符串
        """
        self.cookie = cookie.strip()
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://pan.quark.cn',
            'referer': 'https://pan.quark.cn/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        logger.info("QuarkAPI初始化完成")
    
    def search_file(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        搜索文件获取fid
        
        Args:
            filename: 文件名
            
        Returns:
            (fid, error_message) 元组
            成功返回 (fid, None)
            失败返回 (None, error_message)
        """
        try:
            logger.info(f"搜索文件: {filename}")
            
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'uc_param_str': '',
                'q': filename,
                '_page': 1,
                '_size': 50,
                '_fetch_total': 1,
                '_sort': 'file_type:desc,updated_at:desc',
                '_is_hl': 1
            }
            
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                cookies={'Cookie': self.cookie},
                timeout=10
            )
            
            data = response.json()
            
            # 检查响应码
            if data.get('code') != 0:
                error_msg = f"搜索失败: {data.get('message', '未知错误')}"
                logger.error(error_msg)
                return None, error_msg
            
            # 获取文件列表
            files = data.get('data', {}).get('list', [])
            if not files:
                error_msg = f"未找到文件: {filename}"
                logger.warning(error_msg)
                return None, error_msg
            
            # 精确匹配文件夹
            for file in files:
                if file.get('file_name') == filename and file.get('dir', False):
                    fid = file.get('fid')
                    if fid:
                        logger.info(f"找到文件夹: {filename}, fid={fid}")
                        return fid, None
            
            error_msg = f"未找到完全匹配的文件夹: {filename}"
            logger.warning(error_msg)
            return None, error_msg
            
        except requests.RequestException as e:
            error_msg = f"搜索文件时网络异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"搜索文件时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def create_share(self, fid: str, title: str) -> Tuple[Optional[str], Optional[str]]:
        """
        创建分享任务（异步）
        
        Args:
            fid: 文件ID
            title: 分享标题
            
        Returns:
            (task_id, error_message) 元组
        """
        try:
            logger.info(f"创建分享任务: {title}")
            
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'uc_param_str': ''
            }
            
            payload = {
                'fid_list': [fid],
                'title': title,
                'url_type': 1,
                'expired_type': 1
            }
            
            response = self.session.post(
                self.CREATE_SHARE_URL,
                params=params,
                json=payload,
                cookies={'Cookie': self.cookie},
                timeout=10
            )
            
            data = response.json()
            
            # 检查响应码
            if data.get('code') != 0:
                error_msg = f"创建分享失败: {data.get('message', '未知错误')}"
                logger.error(error_msg)
                return None, error_msg
            
            # 获取task_id
            task_id = data.get('data', {}).get('task_id')
            if not task_id:
                error_msg = "响应中没有task_id"
                logger.error(error_msg)
                return None, error_msg
            
            logger.info(f"分享任务已创建, task_id={task_id}")
            return task_id, None
            
        except requests.RequestException as e:
            error_msg = f"创建分享时网络异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"创建分享时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def poll_task(self, task_id: str, max_retry: int = 20, interval: float = 0.5) -> Tuple[Optional[str], Optional[str]]:
        """
        轮询任务状态获取share_id
        
        Args:
            task_id: 任务ID
            max_retry: 最大重试次数
            interval: 轮询间隔（秒）
            
        Returns:
            (share_id, error_message) 元组
        """
        try:
            logger.info(f"开始轮询任务状态, task_id={task_id}, 最多{max_retry}次")
            
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'uc_param_str': '',
                'task_id': task_id,
                'retry_index': 0
            }
            
            for i in range(max_retry):
                try:
                    response = self.session.get(
                        self.TASK_URL,
                        params=params,
                        cookies={'Cookie': self.cookie},
                        timeout=10
                    )
                    
                    data = response.json()
                    
                    if data.get('code') != 0:
                        error_msg = f"查询任务失败: {data.get('message', '未知错误')}"
                        logger.error(error_msg)
                        return None, error_msg
                    
                    task_data = data.get('data', {})
                    status = task_data.get('status')
                    
                    # 状态2表示完成
                    if status == 2:
                        share_id = task_data.get('share_id')
                        if share_id:
                            logger.info(f"任务完成, share_id={share_id}")
                            return share_id, None
                        else:
                            error_msg = "任务完成但没有share_id"
                            logger.error(error_msg)
                            return None, error_msg
                    
                    # 等待后继续
                    if i < max_retry - 1:
                        time.sleep(interval)
                    
                except Exception as e:
                    logger.warning(f"第{i+1}次轮询异常: {e}")
                    if i < max_retry - 1:
                        time.sleep(interval)
                    continue
            
            error_msg = f"超过最大重试次数({max_retry})，任务仍未完成"
            logger.error(error_msg)
            return None, error_msg
            
        except Exception as e:
            error_msg = f"轮询任务时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def get_share_link(self, share_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        获取分享链接
        
        Args:
            share_id: 分享ID
            
        Returns:
            (share_link, error_message) 元组
        """
        try:
            logger.info(f"获取分享链接, share_id={share_id}")
            
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'uc_param_str': ''
            }
            
            payload = {
                'share_id': share_id
            }
            
            response = self.session.post(
                self.PASSWORD_URL,
                params=params,
                json=payload,
                cookies={'Cookie': self.cookie},
                timeout=10
            )
            
            data = response.json()
            
            # 检查响应码
            if data.get('code') != 0:
                error_msg = f"获取链接失败: {data.get('message', '未知错误')}"
                logger.error(error_msg)
                return None, error_msg
            
            # 提取链接信息
            share_data = data.get('data', {})
            share_url = share_data.get('share_url')
            passcode = share_data.get('passcode')
            
            if not share_url:
                error_msg = "响应中没有链接"
                logger.error(error_msg)
                return None, error_msg
            
            # 格式化链接（夸克通常没有提取码，但如果有就加上）
            if passcode:
                full_link = f"{share_url} 提取码: {passcode}"
            else:
                full_link = share_url
            
            logger.info(f"分享链接获取成功: {full_link}")
            return full_link, None
            
        except requests.RequestException as e:
            error_msg = f"获取链接时网络异常: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"获取链接时发生未知错误: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def generate_share_link(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        一键生成分享链接（完整流程）
        
        Args:
            filename: 文件名
            
        Returns:
            (share_link, error_message) 元组
            成功返回 (link, None)
            失败返回 (None, error_message)
        """
        logger.info(f"开始生成分享链接: {filename}")
        
        # 步骤1: 搜索文件
        fid, error = self.search_file(filename)
        if error:
            return None, error
        
        # 步骤2: 创建分享任务
        task_id, error = self.create_share(fid, filename)
        if error:
            return None, error
        
        # 步骤3: 轮询任务状态
        share_id, error = self.poll_task(task_id)
        if error:
            return None, error
        
        # 步骤4: 获取分享链接
        share_link, error = self.get_share_link(share_id)
        if error:
            return None, error
        
        logger.info(f"✅ 分享链接生成成功: {filename} -> {share_link}")
        return share_link, None
    
    # ============ 转存功能 ============
    
    def transfer(self, share_url: str, pass_code: Optional[str], target_fid: str) -> Dict:
        """
        转存文件（从pan_transfer_api.py迁移过来）
        
        Args:
            share_url: 分享链接
            pass_code: 提取码
            target_fid: 目标文件夹ID
        
        Returns:
            {
                'success': bool,
                'file_count': int,
                'file_ids': List[str],
                'message': str
            }
        """
        from backend.common.response import ResponseUtil
        
        try:
            # 1. 解析分享链接
            pwd_id = self._parse_transfer_url(share_url)
            
            # 2. 获取 stoken
            stoken = self._get_stoken(pwd_id, pass_code)
            
            # 3. 获取文件列表
            pdir_fid, file_count = self._get_file_list_for_transfer(pwd_id, stoken)
            
            # 4. 转存
            task_id = self._do_transfer(pwd_id, stoken, pdir_fid, target_fid)
            
            # 5. 轮询任务
            result = self._poll_transfer_task(task_id)
            
            return ResponseUtil.pan_transfer_success(
                pan_type='quark',
                file_count=file_count,
                file_ids=result.get('save_as', {}).get('save_as_top_fids', []),
                message='转存成功'
            )
        except Exception as e:
            logger.error(f"夸克转存失败: {e}")
            return ResponseUtil.pan_transfer_error('quark', f'转存失败: {str(e)}')
    
    def _parse_transfer_url(self, share_url: str) -> str:
        """解析分享链接"""
        match = re.search(r'/s/([a-zA-Z0-9]+)', share_url)
        if not match:
            raise Exception("无效的夸克分享链接")
        return match.group(1)
    
    def _get_transfer_headers(self) -> Dict:
        """获取转存请求头"""
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'cookie': self.cookie,
            'origin': 'https://pan.quark.cn',
            'referer': 'https://pan.quark.cn/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    def _get_stoken(self, pwd_id: str, pass_code: Optional[str]) -> str:
        """获取 stoken"""
        url = "https://drive-h.quark.cn/1/clouddrive/share/sharepage/token"
        data = {"pwd_id": pwd_id}
        if pass_code:
            data["passcode"] = pass_code
        
        response = requests.post(url, json=data, headers=self._get_transfer_headers())
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"获取 stoken 失败: {result}")
        
        return result['data']['stoken']
    
    def _get_file_list_for_transfer(self, pwd_id: str, stoken: str) -> Tuple[str, int]:
        """获取文件列表"""
        url = "https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail"
        params = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "_page": 1,
            "_size": 50,
            "_fetch_total": 1
        }
        
        response = requests.get(url, params=params, headers=self._get_transfer_headers())
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"获取文件列表失败: {result}")
        
        metadata = result.get('metadata', {})
        pdir_fid = metadata.get('fid', metadata.get('_pdir_fid', '0'))
        file_count = metadata.get('_total', len(result.get('data', {}).get('list', [])))
        
        return pdir_fid, file_count
    
    def _do_transfer(self, pwd_id: str, stoken: str, pdir_fid: str, to_pdir_fid: str) -> str:
        """执行转存"""
        url = "https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save"
        params = {'pr': 'ucpro', 'fr': 'pc', 'uc_param_str': ''}
        
        data = {
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": pdir_fid,
            "to_pdir_fid": to_pdir_fid,
            "pdir_save_all": True,
            "scene": "link"
        }
        
        response = requests.post(url, params=params, json=data, headers=self._get_transfer_headers())
        result = response.json()
        
        if result.get('code') != 0:
            raise Exception(f"转存失败: {result}")
        
        return result['data']['task_id']
    
    def _poll_transfer_task(self, task_id: str) -> Dict:
        """轮询任务"""
        url = "https://drive-pc.quark.cn/1/clouddrive/task"
        
        for retry in range(120):
            time.sleep(0.5)
            
            params = {
                'pr': 'ucpro',
                'fr': 'pc',
                'uc_param_str': '',
                'task_id': task_id,
                'retry_index': retry
            }
            
            response = requests.get(url, params=params, headers=self._get_transfer_headers())
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"查询任务失败: {result}")
            
            task_data = result.get('data', {})
            status = task_data.get('status')
            
            if status == 2:  # 成功
                return task_data
            elif status == 1:  # 失败
                raise Exception("转存任务失败")
        
        raise Exception("任务超时")
