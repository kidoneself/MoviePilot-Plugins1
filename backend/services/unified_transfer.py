#!/usr/bin/env python3
"""
统一转存服务
整合 OpenList路径管理 + 三网盘转存API

核心功能：
1. 自动检测网盘类型（通过分享链接）
2. 通过OpenList检查和创建目录（一层一层）
3. 获取转存参数（百度用路径，夸克/迅雷用文件夹ID）
4. 调用网盘API执行转存

技术要点：
- OpenList API：列出目录、创建目录
- 目录自动创建：从根目录开始逐层检查，不存在则创建
- 参数转换：用户输入路径 → 百度路径/夸克ID/迅雷ID
"""
import re
import requests
import logging
from typing import Dict, Optional
from .pan_transfer_api import PanTransferAPI

logger = logging.getLogger(__name__)


class UnifiedTransfer:
    """
    统一转存接口
    
    使用示例：
        credentials = {
            'baidu': {'cookie': 'xxx'},
            'quark': {'cookie': 'yyy'},
            'xunlei': {'token': 'zzz'}
        }
        transfer = UnifiedTransfer(pan_credentials=credentials)
        result = transfer.transfer(
            share_url='https://pan.baidu.com/s/xxx',
            pass_code='1234',
            target_path='/A-闲鱼影视/剧集/日韩剧集/模范出租车',
            pan_type='baidu'
        )
    """
    
    # OpenList配置（文件管理服务）
    OPENLIST_URL = "http://10.10.10.17:5255"
    OPENLIST_TOKEN = "openlist-1e33e197-915f-4894-adfb-514387a5054dLjiXDkXmIe21Yub5F9g9b6REyJLNVuB2DxV9vc4fnDcKiZwLMbivLsN7y8K7oum4"
    
    # 网盘在OpenList中的挂载点名称（注意：kuake不是quark）
    PAN_MOUNT_MAP = {
        'baidu': 'baidu',      # 百度网盘挂载点
        'quark': 'kuake',      # 夸克网盘挂载点（OpenList中的实际名称）
        'xunlei': 'xunlei'     # 迅雷网盘挂载点
    }
    
    def __init__(self, pan_credentials: Dict[str, Dict]):
        """
        初始化
        
        Args:
            pan_credentials: 各网盘的认证信息
            {
                'baidu': {'cookie': 'xxx'},
                'quark': {'cookie': 'xxx'},
                'xunlei': {'authorization': 'xxx', 'x_captcha_token': 'xxx', ...}
            }
        """
        self.pan_credentials = pan_credentials
    
    def _get_openlist_headers(self):
        """获取OpenList请求头"""
        return {
            'Authorization': self.OPENLIST_TOKEN,
            'Content-Type': 'application/json'
        }
    
    def _list_directory(self, path: str) -> Dict:
        """列出OpenList目录内容"""
        url = f"{self.OPENLIST_URL}/api/fs/list"
        data = {
            "path": path,
            "page": 1,
            "per_page": 100,
            "refresh": False
        }
        
        response = requests.post(url, json=data, headers=self._get_openlist_headers())
        result = response.json()
        
        if result.get('code') != 200:
            raise Exception(f"列出目录失败: {result.get('message')}")
        
        return result.get('data', {})
    
    def get_transfer_param(self, user_path: str, pan_type: str) -> str:
        """
        根据用户路径获取转存参数，自动创建不存在的目录
        
        核心逻辑：
        1. 构建完整路径：/{挂载点}{用户路径}
           例如：/baidu/A-闲鱼影视/剧集/日韩剧集/模范出租车
        
        2. 逐层检查目录：
           - /baidu 存在吗？
           - /baidu/A-闲鱼影视 存在吗？不存在则创建
           - /baidu/A-闲鱼影视/剧集 存在吗？不存在则创建
           - ...以此类推
        
        3. 返回转存参数：
           - 百度：返回完整路径字符串
           - 夸克/迅雷：返回最终目录的文件夹ID
        
        Args:
            user_path: 用户输入的路径（如：/A-闲鱼影视（自动更新）/电影）
            pan_type: 网盘类型（baidu, quark, xunlei）
        
        Returns:
            百度：完整路径字符串
            夸克/迅雷：文件夹ID
            
        Raises:
            Exception: 网盘类型不支持、创建目录失败等
        """
        mount_point = self.PAN_MOUNT_MAP.get(pan_type)
        if not mount_point:
            raise Exception(f"不支持的网盘类型: {pan_type}")
        
        # 构建完整路径
        full_path = f"/{mount_point}{user_path}"
        
        # 检查并创建目录（所有网盘类型）
        parts = [p for p in full_path.split('/') if p]
        current_path = ""
        
        for idx, part in enumerate(parts, 1):
            current_path = f"{current_path}/{part}"
            parent_path = "/".join(current_path.split('/')[:-1]) or "/"
            
            data = self._list_directory(parent_path)
            content = data.get('content', [])
            
            # 记录父目录下所有文件夹（调试用）
            existing_folders = [(item.get('name'), item.get('is_dir'), item.get('mount_details') is not None) for item in content]
            logger.info(f"第{idx}层检查: 目标='{part}', 父目录={parent_path}")
            logger.info(f"  现有内容: {existing_folders}")
            
            found = False
            folder_id = None
            
            for item in content:
                # 挂载点有mount_details字段，普通文件夹有is_dir=True
                is_mount = item.get('mount_details') is not None
                is_directory = item.get('is_dir') == True
                item_name = item.get('name', '')
                
                # 标准化比对：去除首尾空格
                item_name_clean = item_name.strip() if item_name else ''
                part_clean = part.strip()
                
                # 详细日志
                if item_name_clean:
                    logger.info(f"  对比: '{item_name_clean}' == '{part_clean}' ? {item_name_clean == part_clean}, is_dir={is_directory}, is_mount={is_mount}")
                
                # 匹配条件：名称相同 且 （是目录 或 是挂载点）
                if item_name_clean == part_clean and (is_directory or is_mount):
                    folder_id = item.get('id', '')
                    found = True
                    logger.info(f"✅ 第{idx}层找到目录: '{part}', id={folder_id}, path={current_path}")
                    break
            
            if not found:
                logger.warning(f"❌ 第{idx}层未找到目录: {part}, 将创建新目录")
            
            # 如果不存在，创建目录
            if not found:
                logger.info(f"📁 创建第{idx}层目录: {current_path}")
                folder_id = self._create_directory(parent_path, part)
                logger.info(f"✅ 创建成功")
            
            # 如果是最后一级，返回结果
            if idx == len(parts):
                # 百度返回路径
                if pan_type == 'baidu':
                    return full_path
                # 夸克/迅雷返回ID
                else:
                    if not folder_id:
                        raise Exception(f"文件夹ID为空: {current_path}")
                    return folder_id
        
        return full_path if pan_type == 'baidu' else None
    
    def _create_directory(self, parent_path: str, name: str) -> str:
        """
        通过OpenList API创建目录
        
        步骤：
        1. 调用OpenList的 /api/fs/mkdir 接口创建目录
        2. 重新列出父目录获取新建目录的ID
        3. 返回目录ID（夸克/迅雷转存需要）
        
        Args:
            parent_path: 父目录路径（如：/baidu/A-闲鱼影视）
            name: 目录名称（如：剧集）
        
        Returns:
            创建的目录ID（用于夸克/迅雷转存）
            
        Raises:
            Exception: 创建失败或无法获取ID
        """
        url = f"{self.OPENLIST_URL}/api/fs/mkdir"
        headers = {
            "Authorization": self.OPENLIST_TOKEN,
            "Content-Type": "application/json"
        }
        data = {
            "path": f"{parent_path}/{name}" if parent_path != "/" else f"/{name}"
        }
        
        response = requests.post(url, json=data, headers=headers)
        result = response.json()
        
        if result.get('code') != 200:
            error_msg = f"创建目录失败: {result.get('message')}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"✅ 创建API调用成功，重新获取ID")
        
        # 重新列出父目录，获取新建目录的ID
        list_data = self._list_directory(parent_path)
        content = list_data.get('content', [])
        
        for item in content:
            # 标准化比对
            item_name = item.get('name', '').strip()
            name_clean = name.strip()
            
            # 新建的目录肯定有is_dir=True，但为了一致性也检查mount_details
            is_directory = item.get('is_dir') == True
            is_mount = item.get('mount_details') is not None
            
            if item_name == name_clean and (is_directory or is_mount):
                folder_id = item.get('id', '')
                logger.info(f"✅ 创建后找到目录: {name}, id={folder_id}")
                return folder_id
        
        error_msg = f"创建目录后无法获取ID，父目录={parent_path}，目标={name}，现有内容: {[i.get('name') for i in content]}"
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg)
    
    def detect_pan_type(self, share_url: str) -> str:
        """自动检测网盘类型"""
        if 'pan.baidu.com' in share_url:
            return 'baidu'
        elif 'pan.quark.cn' in share_url:
            return 'quark'
        elif 'pan.xunlei.com' in share_url:
            return 'xunlei'
        else:
            raise ValueError(f"无法识别的分享链接: {share_url}")
    
    def transfer(self, share_url: str, pass_code: Optional[str],
                target_path: str, pan_type: Optional[str] = None) -> Dict:
        """
        统一转存接口
        
        Args:
            share_url: 分享链接
            pass_code: 提取码（可选）
            target_path: 目标路径（统一格式，如：/A-闲鱼影视（自动更新）/电影）
            pan_type: 网盘类型（可选，不提供则自动检测）
        
        Returns:
            {
                'success': bool,
                'pan_type': str,
                'file_count': int,
                'file_ids': List[str],
                'message': str,
                'target_path': str,        # 用户输入的路径
                'actual_param': str,       # 实际使用的参数（路径或ID）
                'details': Dict
            }
        """
        try:
            # 1. 检测网盘类型
            if not pan_type:
                pan_type = self.detect_pan_type(share_url)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"统一转存 - {pan_type.upper()}")
            logger.info(f"{'='*60}")
            logger.info(f"分享链接: {share_url}")
            logger.info(f"目标路径: {target_path}")
            
            # 2. 获取转存参数
            logger.info(f"🔍 通过OpenList获取转存参数...")
            transfer_param = self.get_transfer_param(target_path, pan_type)
            logger.info(f"✅ 获取成功")
            
            if pan_type == 'baidu':
                logger.info(f"参数类型: 路径")
            else:
                logger.info(f"参数类型: 文件夹ID")
            logger.info(f"参数值: {transfer_param}")
            
            # 3. 检查认证信息
            credentials = self.pan_credentials.get(pan_type)
            if not credentials:
                raise Exception(f"未配置{pan_type}网盘的认证信息")
            
            # 3.5. 迅雷网盘自动刷新token
            if pan_type == 'xunlei':
                logger.info(f"🔄 刷新迅雷token...")
                try:
                    from backend.utils.xunlei_api import XunleiAPI, _browser_manager
                    import json
                    
                    # 尝试从credentials中获取浏览器cookie（JSON数组格式）
                    # 兼容两种情况：
                    # 1. credentials本身就是数组（用户直接存了浏览器cookie）
                    # 2. credentials是字典，包含browser_cookie字段
                    cookie_data = None
                    
                    if isinstance(credentials, list):
                        # 情况1：整个credentials就是cookie数组
                        cookie_data = json.dumps(credentials)
                        logger.info("   检测到浏览器cookie数组格式")
                    elif isinstance(credentials, dict) and credentials.get('browser_cookie'):
                        # 情况2：字典中有browser_cookie字段
                        cookie_data = credentials.get('browser_cookie')
                        logger.info("   使用browser_cookie字段")
                    
                    if cookie_data:
                        logger.info("   启动浏览器自动获取token...")
                        xunlei_api = XunleiAPI(cookie=cookie_data)
                        
                        # 在浏览器线程中执行刷新操作
                        def refresh_in_thread():
                            page, auth_info = _browser_manager.get_page(xunlei_api.cookies)
                            logger.info("   刷新页面捕获token...")
                            return xunlei_api._refresh_token_sync(page, auth_info), auth_info
                        
                        success, auth_info = _browser_manager.run_in_thread(refresh_in_thread)
                        
                        if success and auth_info.get('authorization') and auth_info.get('x-captcha-token'):
                            # 如果credentials是数组，转为字典
                            if isinstance(credentials, list):
                                credentials = {}
                            credentials['authorization'] = auth_info['authorization']
                            credentials['x_captcha_token'] = auth_info['x-captcha-token']
                            credentials['x_client_id'] = 'Xqp0kJBXWhwaTpB6'
                            credentials['x_device_id'] = 'd765a49124d0b4c8d593d73daa738f51'
                            logger.info(f"   ✅ Token刷新成功")
                            logger.info(f"   authorization: {auth_info['authorization'][:50]}...")
                            logger.info(f"   x_captcha_token: {auth_info['x-captcha-token'][:50]}...")
                        else:
                            logger.warning("   ⚠️  Token未捕获")
                            raise Exception("无法获取迅雷token，请检查浏览器cookie是否有效")
                    else:
                        logger.warning("   ⚠️  未找到浏览器cookie")
                        raise Exception("需要浏览器cookie才能自动获取token")
                        
                except Exception as e:
                    logger.error(f"   ❌ Token刷新失败: {str(e)}")
                    raise Exception(f"迅雷token获取失败: {str(e)}")
            
            # 4. 创建转存API实例
            logger.info(f"📤 开始转存...")
            api = PanTransferAPI(pan_type=pan_type, credentials=credentials)
            
            # 5. 执行转存
            result = api.transfer(
                share_url=share_url,
                pass_code=pass_code,
                target_path=transfer_param
            )
            
            # 6. 补充统一字段
            result['target_path'] = target_path
            result['actual_param'] = transfer_param
            
            if result['success']:
                logger.info(f"✅ 转存成功！")
                logger.info(f"   文件数量: {result['file_count']}")
            else:
                logger.error(f"❌ 转存失败: {result['message']}")
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'pan_type': pan_type if pan_type else 'unknown',
                'file_count': 0,
                'file_ids': [],
                'message': f'统一转存失败: {str(e)}',
                'target_path': target_path,
                'actual_param': None,
                'details': {}
            }


# 便捷函数
def easy_transfer(share_url: str, pass_code: str, target_path: str,
                 pan_credentials: Dict[str, Dict]) -> Dict:
    """
    简化的转存函数
    
    Args:
        share_url: 分享链接
        pass_code: 提取码
        target_path: 目标路径（如：/A-闲鱼影视（自动更新）/电影）
        pan_credentials: 认证信息字典
    
    Returns:
        转存结果
    """
    transfer = UnifiedTransfer(pan_credentials)
    return transfer.transfer(share_url, pass_code, target_path)
