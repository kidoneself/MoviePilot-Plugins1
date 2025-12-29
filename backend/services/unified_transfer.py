#!/usr/bin/env python3
"""
统一转存服务
整合 OpenList路径管理 + 三网盘转存API
"""
import logging
from typing import Dict, Optional

from backend.common.constants import OPENLIST_PATH_PREFIX, PAN_MOUNT_MAP
from backend.utils.openlist_client import OpenListClient
from backend.utils.pan_factory import PanFactory

logger = logging.getLogger(__name__)


class UnifiedTransfer:
    """统一转存接口"""
    
    def __init__(self, pan_credentials: Dict[str, Dict]):
        """
        初始化
        
        Args:
            pan_credentials: 各网盘的认证信息
        """
        self.pan_credentials = pan_credentials
        self.openlist_client = OpenListClient()
    
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
            target_path: 目标路径（如：/A-闲鱼影视（自动更新）/电影）
            pan_type: 网盘类型（可选，不提供则自动检测）
        
        Returns:
            转存结果
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
            
            # 2. 获取转存参数（通过OpenList）
            logger.info(f"🔍 通过OpenList获取转存参数...")
            transfer_param = self.openlist_client.get_transfer_param(target_path, pan_type)
            logger.info(f"✅ 获取成功")
            logger.info(f"参数值: {transfer_param}")
            
            # 3. 检查认证信息
            credentials = self.pan_credentials.get(pan_type)
            if not credentials:
                raise Exception(f"未配置{pan_type}网盘的认证信息")
            
            # 4. 迅雷网盘自动刷新token
            if pan_type == 'xunlei':
                credentials = self._refresh_xunlei_token(credentials)
            
            # 5. 创建API实例并执行转存
            logger.info(f"📤 开始转存...")
            api = PanFactory.create_api(pan_type, credentials)
            result = api.transfer(share_url, pass_code, transfer_param)
            
            # 6. 补充统一字段
            result['target_path'] = target_path
            result['actual_param'] = transfer_param
            
            if result['success']:
                logger.info(f"✅ 转存成功！文件数量: {result['file_count']}")
            else:
                logger.error(f"❌ 转存失败: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"统一转存失败: {e}")
            return {
                'success': False,
                'pan_type': pan_type if pan_type else 'unknown',
                'file_count': 0,
                'file_ids': [],
                'message': f'统一转存失败: {str(e)}',
                'target_path': target_path,
                'actual_param': None
            }
    
    def _refresh_xunlei_token(self, credentials: Dict) -> Dict:
        """刷新迅雷token"""
        import json
        from backend.utils.xunlei_api import XunleiAPI, _browser_manager
        
        logger.info(f"🔄 刷新迅雷token...")
        try:
            cookie_data = None
            
            if isinstance(credentials, list):
                cookie_data = json.dumps(credentials)
            elif isinstance(credentials, dict) and credentials.get('browser_cookie'):
                cookie_data = credentials.get('browser_cookie')
            
            if cookie_data:
                xunlei_api = XunleiAPI(cookie=cookie_data)
                
                def refresh_in_thread():
                    page, auth_info = _browser_manager.get_page(xunlei_api.cookies)
                    return xunlei_api._refresh_token_sync(page, auth_info), auth_info
                
                success, auth_info = _browser_manager.run_in_thread(refresh_in_thread)
                
                if success and auth_info.get('authorization'):
                    if isinstance(credentials, list):
                        credentials = {}
                    credentials['authorization'] = auth_info['authorization']
                    credentials['x_captcha_token'] = auth_info['x-captcha-token']
                    credentials['x_client_id'] = 'Xqp0kJBXWhwaTpB6'
                    credentials['x_device_id'] = 'd765a49124d0b4c8d593d73daa738f51'
                    logger.info(f"✅ Token刷新成功")
                else:
                    raise Exception("Token刷新失败")
            
            return credentials
        except Exception as e:
            logger.error(f"Token刷新失败: {e}")
            raise


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
