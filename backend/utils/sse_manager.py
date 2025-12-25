"""
SSE (Server-Sent Events) 管理器
用于实时推送进度和二维码到前端
"""
import asyncio
import json
import logging
from typing import Dict, Optional
from fastapi import Request
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


class SSEManager:
    """SSE连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, asyncio.Queue] = {}
    
    def create_session(self, session_id: str) -> asyncio.Queue:
        """创建新的SSE会话"""
        queue = asyncio.Queue()
        self.connections[session_id] = queue
        logger.info(f"创建SSE会话: {session_id}")
        return queue
    
    def close_session(self, session_id: str):
        """关闭SSE会话"""
        if session_id in self.connections:
            del self.connections[session_id]
            logger.info(f"关闭SSE会话: {session_id}")
    
    async def send_message(self, session_id: str, event: str, data: dict):
        """发送消息到指定会话"""
        if session_id not in self.connections:
            logger.warning(f"SSE会话不存在: {session_id}")
            return
        
        queue = self.connections[session_id]
        message = {
            'event': event,
            'data': data
        }
        await queue.put(message)
        logger.debug(f"发送SSE消息到 {session_id}: {event}")
    
    async def send_step(self, session_id: str, step: str, status: str):
        """发送步骤消息"""
        await self.send_message(session_id, 'step', {
            'step': step,
            'status': status
        })
    
    async def send_qrcode(self, session_id: str, qrcode_base64: str):
        """发送二维码"""
        await self.send_message(session_id, 'qrcode', {
            'qrcode': qrcode_base64
        })
    
    async def send_complete(self, session_id: str, success: bool, message: str):
        """发送完成消息"""
        await self.send_message(session_id, 'complete', {
            'success': success,
            'message': message
        })
    
    async def event_generator(self, session_id: str, request: Request):
        """生成SSE事件流"""
        queue = self.create_session(session_id)
        
        try:
            while True:
                # 检查客户端是否断开
                if await request.is_disconnected():
                    logger.info(f"客户端断开连接: {session_id}")
                    break
                
                try:
                    # 等待消息，超时则发送心跳
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        'event': message['event'],
                        'data': json.dumps(message['data'], ensure_ascii=False)
                    }
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield {
                        'event': 'heartbeat',
                        'data': json.dumps({'time': asyncio.get_event_loop().time()})
                    }
        
        finally:
            self.close_session(session_id)


# 全局SSE管理器实例
_sse_manager: Optional[SSEManager] = None


def get_sse_manager() -> SSEManager:
    """获取SSE管理器实例"""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager()
    return _sse_manager

