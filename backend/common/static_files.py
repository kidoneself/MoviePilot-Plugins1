"""
静态文件服务 - 带缓存头优化
"""
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope, Receive, Send
import logging

logger = logging.getLogger(__name__)


class CachedStaticFiles(StaticFiles):
    """
    带缓存头的静态文件服务
    
    优化:
    - 为静态资源添加 Cache-Control 头
    - 提升浏览器缓存命中率
    - 减少服务器负载
    """
    
    def __init__(self, *args, max_age: int = 86400, **kwargs):
        """
        Args:
            max_age: 缓存时间（秒），默认24小时
        """
        super().__init__(*args, **kwargs)
        self.max_age = max_age
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """添加缓存头"""
        if scope["type"] == "http":
            # 创建原始响应
            async def send_with_cache_headers(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    
                    # 添加缓存头
                    cache_control = f"public, max-age={self.max_age}, immutable"
                    headers[b"cache-control"] = cache_control.encode()
                    
                    # 转回列表格式
                    message["headers"] = list(headers.items())
                
                await send(message)
            
            await super().__call__(scope, receive, send_with_cache_headers)
        else:
            await super().__call__(scope, receive, send)

