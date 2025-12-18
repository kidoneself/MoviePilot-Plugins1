"""
网盘自动化模块
"""
from .base import CloudPanBase
from .baidu import BaiduPan
from .quark import QuarkPan
from .manager import CloudPanManager

__all__ = ['CloudPanBase', 'BaiduPan', 'QuarkPan', 'CloudPanManager']
