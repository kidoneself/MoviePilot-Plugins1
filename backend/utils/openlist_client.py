"""
OpenList API 客户端
统一封装 OpenList 相关操作，消除代码重复
"""
import requests
import logging
from typing import Dict, List, Optional, Tuple

from backend.common.constants import OPENLIST_URL, OPENLIST_TOKEN, PAN_MOUNT_MAP
from backend.common.exceptions import OpenListError

logger = logging.getLogger(__name__)


class OpenListClient:
    """OpenList API 客户端"""
    
    def __init__(self, url: str = None, token: str = None):
        """
        初始化 OpenList 客户端
        
        Args:
            url: OpenList服务地址，默认从constants读取
            token: 认证Token，默认从constants读取
        """
        self.url = url or OPENLIST_URL
        self.token = token or OPENLIST_TOKEN
    
    def _get_headers(self) -> Dict:
        """获取请求头"""
        return {
            'Authorization': self.token,
            'Content-Type': 'application/json'
        }
    
    def list_files(self, path: str, page: int = 1, per_page: int = 1000, refresh: bool = False) -> Dict:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            page: 页码
            per_page: 每页数量
            refresh: 是否刷新缓存
        
        Returns:
            {
                'content': [...],  # 文件列表
                'total': int,
                'page': int
            }
        
        Raises:
            OpenListError: API调用失败
        """
        url = f"{self.url}/api/fs/list"
        data = {
            "path": path,
            "page": page,
            "per_page": per_page,
            "refresh": refresh
        }
        
        try:
            response = requests.post(url, json=data, headers=self._get_headers(), timeout=30)
            result = response.json()
            
            if result.get('code') != 200:
                raise OpenListError(f"列出目录失败: {result.get('message')}")
            
            return result.get('data', {})
        except requests.RequestException as e:
            raise OpenListError(f"OpenList请求失败: {str(e)}")
    
    def mkdir(self, path: str) -> bool:
        """
        创建目录
        
        Args:
            path: 目录路径
        
        Returns:
            是否成功
        
        Raises:
            OpenListError: 创建失败
        """
        url = f"{self.url}/api/fs/mkdir"
        data = {"path": path}
        
        try:
            response = requests.post(url, json=data, headers=self._get_headers(), timeout=30)
            result = response.json()
            
            if result.get('code') != 200:
                raise OpenListError(f"创建目录失败: {result.get('message')}")
            
            logger.info(f"✅ 创建目录成功: {path}")
            return True
        except requests.RequestException as e:
            raise OpenListError(f"创建目录请求失败: {str(e)}")
    
    def get_file_info(self, path: str) -> Optional[Dict]:
        """
        获取文件/目录信息
        
        Args:
            path: 文件路径
        
        Returns:
            文件信息字典，不存在返回None
        """
        url = f"{self.url}/api/fs/get"
        data = {"path": path}
        
        try:
            response = requests.post(url, json=data, headers=self._get_headers(), timeout=30)
            result = response.json()
            
            if result.get('code') == 200:
                return result.get('data', {})
            return None
        except:
            return None
    
    def ensure_path_exists(self, full_path: str) -> str:
        """
        确保路径存在，不存在则自动创建（逐层）
        
        Args:
            full_path: 完整路径（如：/xunlei/A-闲鱼影视/剧集/国产剧集）
        
        Returns:
            最终目录的文件夹ID（用于夸克/迅雷转存）
        
        Raises:
            OpenListError: 创建失败
        """
        parts = [p for p in full_path.split('/') if p]
        current_path = ""
        folder_id = None
        
        for idx, part in enumerate(parts, 1):
            current_path = f"{current_path}/{part}"
            parent_path = "/".join(current_path.split('/')[:-1]) or "/"
            
            # 列出父目录
            data = self.list_files(parent_path)
            content = data.get('content', [])
            
            # 查找当前层级的目录
            found = False
            for item in content:
                item_name = item.get('name', '').strip()
                part_clean = part.strip()
                
                # 检查是否是目录或挂载点
                is_mount = item.get('mount_details') is not None
                is_directory = item.get('is_dir') == True
                
                if item_name == part_clean and (is_directory or is_mount):
                    folder_id = item.get('id', '')
                    found = True
                    logger.debug(f"✅ 第{idx}层找到: {part}, id={folder_id}")
                    break
            
            # 如果不存在，创建目录
            if not found:
                logger.info(f"📁 第{idx}层不存在，创建: {current_path}")
                self.mkdir(current_path)
                
                # 重新列出获取ID
                data = self.list_files(parent_path)
                content = data.get('content', [])
                
                for item in content:
                    if item.get('name', '').strip() == part.strip():
                        folder_id = item.get('id', '')
                        logger.info(f"✅ 创建成功: {part}, id={folder_id}")
                        break
                
                if not folder_id:
                    raise OpenListError(f"创建目录后无法获取ID: {current_path}")
        
        return folder_id
    
    def find_file_id_by_name(self, pan_type: str, path: str, filename: str) -> Optional[str]:
        """
        通过文件名查找文件ID
        
        Args:
            pan_type: 网盘类型 (baidu/quark/xunlei)
            path: 文件所在目录路径（不含挂载点）
            filename: 文件名
        
        Returns:
            文件ID，未找到返回None
        """
        mount_point = PAN_MOUNT_MAP.get(pan_type)
        if not mount_point:
            raise OpenListError(f"不支持的网盘类型: {pan_type}")
        
        full_path = f"/{mount_point}{path}"
        
        try:
            data = self.list_files(full_path)
            files = data.get('content', [])
            
            # 精确匹配
            for file in files:
                if file.get('name') == filename:
                    file_id = file.get('id', '')
                    logger.info(f"✅ 精确匹配: {filename}, ID: {file_id}")
                    return file_id
            
            # 模糊匹配（包含关键词，跳过文件夹）
            for file in files:
                file_name = file.get('name', '')
                if filename in file_name and not file.get('is_dir'):
                    file_id = file.get('id', '')
                    logger.info(f"✅ 模糊匹配: {file_name}, ID: {file_id}")
                    return file_id
            
            logger.warning(f"❌ 未找到文件: {filename}")
            return None
        except Exception as e:
            logger.error(f"查找文件失败: {e}")
            return None
    
    def get_transfer_param(self, user_path: str, pan_type: str) -> str:
        """
        根据用户路径获取转存参数（自动创建不存在的目录）
        
        Args:
            user_path: 用户输入的路径（如：/A-闲鱼影视/剧集/国产剧集）
            pan_type: 网盘类型 (baidu/quark/xunlei)
        
        Returns:
            - 百度：完整路径字符串
            - 夸克/迅雷：文件夹ID
        
        Raises:
            OpenListError: 创建目录失败
        """
        mount_point = PAN_MOUNT_MAP.get(pan_type)
        if not mount_point:
            raise OpenListError(f"不支持的网盘类型: {pan_type}")
        
        # 构建完整路径
        full_path = f"/{mount_point}{user_path}"
        
        # 确保路径存在
        folder_id = self.ensure_path_exists(full_path)
        
        # 百度返回路径，其他返回ID
        if pan_type == 'baidu':
            return full_path
        else:
            return folder_id

