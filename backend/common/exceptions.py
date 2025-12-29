"""
自定义异常类
"""


class BaseAPIError(Exception):
    """API异常基类"""
    
    def __init__(self, message: str, code: int = -1):
        self.message = message
        self.code = code
        super().__init__(self.message)


class PanAPIError(BaseAPIError):
    """网盘API异常"""
    pass


class BaiduPanError(PanAPIError):
    """百度网盘异常"""
    pass


class QuarkError(PanAPIError):
    """夸克网盘异常"""
    pass


class XunleiError(PanAPIError):
    """迅雷网盘异常"""
    pass


class OpenListError(BaseAPIError):
    """OpenList API异常"""
    pass


class ConfigError(BaseAPIError):
    """配置错误"""
    pass


class DatabaseError(BaseAPIError):
    """数据库错误"""
    pass


class ValidationError(BaseAPIError):
    """参数验证错误"""
    
    def __init__(self, message: str):
        super().__init__(message, code=400)

