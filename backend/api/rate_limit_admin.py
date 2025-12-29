"""
限流管理API - 查看统计和管理白名单
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
import logging

from backend.common.rate_limiter import rate_limiter

router = APIRouter()
logger = logging.getLogger(__name__)


class ResetRequest(BaseModel):
    """重置限流请求"""
    ip: Optional[str] = None


@router.get("/rate-limit/stats")
async def get_rate_limit_stats():
    """
    获取限流统计
    
    返回：
    - enabled: 是否启用
    - max_requests: 最大请求数
    - window_seconds: 时间窗口
    - tracked_ips: 跟踪的IP数量
    - total_requests: 总请求数
    """
    try:
        stats = rate_limiter.get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取限流统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate-limit/reset")
async def reset_rate_limit(request: ResetRequest):
    """
    重置限流记录
    
    Args:
        ip: 要重置的IP（不传则重置所有）
    """
    try:
        rate_limiter.reset(request.ip)
        
        if request.ip:
            message = f"已重置IP {request.ip} 的限流记录"
        else:
            message = "已重置所有限流记录"
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"重置限流失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limit/check")
async def check_rate_limit(
    x_forwarded_for: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None)
):
    """
    检查当前IP的限流状态
    
    返回：
    - allowed: 是否允许请求
    - current: 当前请求数
    - remaining: 剩余请求数
    - limit: 最大请求数
    - window: 时间窗口
    """
    try:
        # 获取客户端IP
        client_ip = x_forwarded_for or x_real_ip or "unknown"
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        
        allowed, current, remaining = rate_limiter.is_allowed(client_ip)
        
        return {
            "success": True,
            "data": {
                "ip": client_ip,
                "allowed": allowed,
                "current": current,
                "remaining": remaining,
                "limit": rate_limiter.max_requests,
                "window": rate_limiter.window_seconds
            }
        }
    except Exception as e:
        logger.error(f"检查限流状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

