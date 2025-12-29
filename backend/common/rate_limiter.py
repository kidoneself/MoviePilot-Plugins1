"""
API 限流中间件 - 基于IP地址
防止恶意请求、爬虫攻击、暴力破解
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, Tuple
import logging
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    基于IP的滑动窗口限流器
    
    原理：
    - 记录每个IP在时间窗口内的请求次数
    - 超过阈值则拒绝请求
    - 自动清理过期记录
    
    配置（环境变量）：
        RATE_LIMIT_ENABLED: 是否启用限流（默认True）
        RATE_LIMIT_REQUESTS: 时间窗口内最大请求数（默认100）
        RATE_LIMIT_WINDOW: 时间窗口（秒，默认60）
    """
    
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        enabled: bool = True
    ):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
            enabled: 是否启用限流
        """
        self.max_requests = int(os.getenv('RATE_LIMIT_REQUESTS', max_requests))
        self.window_seconds = int(os.getenv('RATE_LIMIT_WINDOW', window_seconds))
        self.enabled = os.getenv('RATE_LIMIT_ENABLED', str(enabled)).lower() == 'true'
        
        # 存储: {ip: [(timestamp1, timestamp2, ...)]}
        self.requests: Dict[str, list] = defaultdict(list)
        
        # 最后清理时间
        self.last_cleanup = time.time()
        
        if self.enabled:
            logger.info(f"✅ API限流已启用: {self.max_requests}次/{self.window_seconds}秒")
        else:
            logger.info("⚠️ API限流已禁用")
    
    def _cleanup_old_requests(self):
        """清理过期的请求记录（每5分钟执行一次）"""
        now = time.time()
        
        # 每5分钟清理一次
        if now - self.last_cleanup < 300:
            return
        
        self.last_cleanup = now
        cutoff = now - self.window_seconds
        
        # 清理过期记录
        to_remove = []
        for ip, timestamps in self.requests.items():
            # 只保留时间窗口内的记录
            self.requests[ip] = [ts for ts in timestamps if ts > cutoff]
            # 如果该IP没有任何记录，标记删除
            if not self.requests[ip]:
                to_remove.append(ip)
        
        # 删除空记录
        for ip in to_remove:
            del self.requests[ip]
        
        if to_remove:
            logger.debug(f"🧹 限流器清理: 移除{len(to_remove)}个IP记录")
    
    def is_allowed(self, ip: str) -> Tuple[bool, int, int]:
        """
        检查IP是否允许请求
        
        Args:
            ip: 客户端IP地址
            
        Returns:
            (是否允许, 当前请求数, 剩余请求数)
        """
        if not self.enabled:
            return True, 0, self.max_requests
        
        now = time.time()
        cutoff = now - self.window_seconds
        
        # 获取该IP的请求记录
        timestamps = self.requests[ip]
        
        # 过滤出时间窗口内的请求
        recent_requests = [ts for ts in timestamps if ts > cutoff]
        
        # 更新记录
        self.requests[ip] = recent_requests
        
        # 检查是否超限
        current_count = len(recent_requests)
        remaining = self.max_requests - current_count
        
        if current_count >= self.max_requests:
            logger.warning(f"🚫 限流触发: IP={ip}, 请求数={current_count}/{self.max_requests}")
            return False, current_count, 0
        
        # 记录本次请求
        self.requests[ip].append(now)
        
        # 定期清理
        self._cleanup_old_requests()
        
        return True, current_count + 1, remaining - 1
    
    def get_stats(self) -> Dict:
        """获取限流统计"""
        total_ips = len(self.requests)
        total_requests = sum(len(ts) for ts in self.requests.values())
        
        return {
            "enabled": self.enabled,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "tracked_ips": total_ips,
            "total_requests": total_requests
        }
    
    def reset(self, ip: str = None):
        """重置限流记录"""
        if ip:
            if ip in self.requests:
                del self.requests[ip]
                logger.info(f"🔄 重置IP限流: {ip}")
        else:
            self.requests.clear()
            logger.info("🔄 重置所有限流记录")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI限流中间件
    
    功能：
    - 基于IP地址限流
    - 自动添加限流响应头
    - 白名单机制（跳过限流）
    """
    
    def __init__(self, app, limiter: RateLimiter, whitelist: list = None):
        super().__init__(app)
        self.limiter = limiter
        self.whitelist = set(whitelist or ["127.0.0.1", "::1", "localhost"])
        
        if self.whitelist:
            logger.info(f"✅ 限流白名单: {self.whitelist}")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端真实IP
        
        优先级：
        1. X-Forwarded-For (nginx/CDN代理)
        2. X-Real-IP (nginx代理)
        3. request.client.host (直连)
        """
        # 从代理头获取真实IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For 可能包含多个IP，取第一个
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 直连IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        # 跳过健康检查和静态资源
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        if request.url.path.startswith(("/assets/", "/uploads/", "/svg/")):
            return await call_next(request)
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 白名单跳过
        if client_ip in self.whitelist:
            response = await call_next(request)
            return response
        
        # 限流检查
        allowed, current, remaining = self.limiter.is_allowed(client_ip)
        
        if not allowed:
            # 超出限流
            logger.warning(f"🚫 拒绝请求: IP={client_ip}, 路径={request.url.path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"请求过于频繁，请在{self.limiter.window_seconds}秒后重试",
                    "limit": self.limiter.max_requests,
                    "window": self.limiter.window_seconds
                },
                headers={
                    "X-RateLimit-Limit": str(self.limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + self.limiter.window_seconds)),
                    "Retry-After": str(self.limiter.window_seconds)
                }
            )
        
        # 正常处理请求
        response = await call_next(request)
        
        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.limiter.window_seconds))
        
        return response


# 全局限流器实例
rate_limiter = RateLimiter()

