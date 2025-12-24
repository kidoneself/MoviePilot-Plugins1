"""
夸克网盘API封装
提供搜索文件和创建分享链接功能
"""
import requests
import time
import logging
from typing import Tuple, Optional

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
