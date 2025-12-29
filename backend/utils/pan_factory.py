"""
网盘工厂类
统一创建三网盘API实例
"""
import logging
from typing import Dict, Union

from backend.common.constants import PanType
from backend.common.exceptions import PanAPIError, ValidationError
from backend.utils.baidu_api import BaiduPanAPI
from backend.utils.quark_api import QuarkAPI
from backend.utils.xunlei_api import XunleiAPI

logger = logging.getLogger(__name__)


class PanFactory:
    """
    网盘工厂类 - 统一创建网盘API实例
    
    使用示例:
        >>> credentials = {'cookie': 'xxx'}
        >>> api = PanFactory.create_api('baidu', credentials)
        >>> api.transfer(share_url, pass_code, target_path)
    """
    
    @staticmethod
    def create_api(pan_type: str, credentials: Dict) -> Union[BaiduPanAPI, QuarkAPI, XunleiAPI]:
        """
        根据网盘类型创建对应的API实例
        
        Args:
            pan_type: 网盘类型 ('baidu', 'quark', 'xunlei')
            credentials: 认证信息
                - baidu: {'cookie': str}
                - quark: {'cookie': str}
                - xunlei: {'cookie': str} (JSON格式的浏览器cookie)
        
        Returns:
            对应的网盘API实例
        
        Raises:
            ValidationError: 网盘类型不合法
            PanAPIError: API初始化失败
        
        Examples:
            >>> # 百度网盘
            >>> api = PanFactory.create_api('baidu', {'cookie': 'BDUSS=xxx'})
            
            >>> # 夸克网盘
            >>> api = PanFactory.create_api('quark', {'cookie': 'xxx'})
            
            >>> # 迅雷网盘
            >>> api = PanFactory.create_api('xunlei', {'cookie': '[{...}]'})
        """
        # 验证网盘类型
        if not PanType.validate(pan_type):
            raise ValidationError(f"不支持的网盘类型: {pan_type}")
        
        # 验证credentials
        if not credentials or not isinstance(credentials, dict):
            raise ValidationError("credentials必须是字典类型")
        
        try:
            if pan_type == PanType.BAIDU:
                cookie = credentials.get('cookie')
                if not cookie:
                    raise PanAPIError("百度网盘需要提供cookie")
                logger.debug(f"创建百度网盘API实例")
                return BaiduPanAPI(cookie=cookie)
            
            elif pan_type == PanType.QUARK:
                cookie = credentials.get('cookie')
                if not cookie:
                    raise PanAPIError("夸克网盘需要提供cookie")
                logger.debug(f"创建夸克网盘API实例")
                return QuarkAPI(cookie=cookie)
            
            elif pan_type == PanType.XUNLEI:
                cookie = credentials.get('cookie')
                if not cookie:
                    raise PanAPIError("迅雷网盘需要提供cookie")
                logger.debug(f"创建迅雷网盘API实例")
                return XunleiAPI(cookie=cookie)
            
        except (PanAPIError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"创建{pan_type}网盘API失败: {e}")
            raise PanAPIError(f"创建API实例失败: {str(e)}")
    
    @staticmethod
    def get_supported_types():
        """获取所有支持的网盘类型"""
        return PanType.all()
    
    @staticmethod
    def get_pan_name(pan_type: str) -> str:
        """获取网盘中文名称"""
        return PanType.get_name(pan_type)

