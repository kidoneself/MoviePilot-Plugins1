"""
常量定义
所有硬编码的配置项集中在这里
"""
from backend.common.config import config_manager

# ==================== OpenList 配置 ====================
# 从config.yaml读取，提供默认值作为fallback
_openlist_config = config_manager.get('openlist', {})
OPENLIST_URL = _openlist_config.get('url', 'http://10.10.10.17:5255')
OPENLIST_TOKEN = _openlist_config.get('token', '')
OPENLIST_PATH_PREFIX = _openlist_config.get('path_prefix', '/A-闲鱼影视（自动更新）')

# ==================== 网盘挂载点映射 ====================
# 注意：OpenList中夸克挂载点是 kuake 不是 quark
PAN_MOUNT_MAP = {
    'baidu': 'baidu',
    'quark': 'kuake',  # 特别注意：夸克在OpenList中叫kuake
    'xunlei': 'xunlei'
}

# ==================== 网盘类型 ====================
class PanType:
    """网盘类型常量"""
    BAIDU = 'baidu'
    QUARK = 'quark'
    XUNLEI = 'xunlei'
    
    @classmethod
    def all(cls):
        """获取所有支持的网盘类型"""
        return [cls.BAIDU, cls.QUARK, cls.XUNLEI]
    
    @classmethod
    def validate(cls, pan_type: str) -> bool:
        """验证网盘类型是否合法"""
        return pan_type in cls.all()
    
    @classmethod
    def get_name(cls, pan_type: str) -> str:
        """获取网盘中文名称"""
        names = {
            cls.BAIDU: '百度网盘',
            cls.QUARK: '夸克网盘',
            cls.XUNLEI: '迅雷网盘'
        }
        return names.get(pan_type, '未知网盘')

# ==================== HTTP 超时配置 ====================
DEFAULT_TIMEOUT = 30  # 默认HTTP请求超时时间（秒）
TRANSFER_TIMEOUT = 60  # 转存操作超时时间（秒）
TASK_POLL_INTERVAL = 0.5  # 任务轮询间隔（秒）
TASK_MAX_RETRIES = 120  # 任务最大重试次数

# ==================== 响应状态码 ====================
class ResponseCode:
    """统一响应状态码"""
    SUCCESS = 0
    ERROR = -1
    INVALID_PARAM = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    SERVER_ERROR = 500

