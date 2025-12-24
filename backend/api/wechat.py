"""
企业微信API - 处理消息回调
"""
import logging
from fastapi import APIRouter, Request, Response
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise import parse_message
from wechatpy.exceptions import InvalidSignatureException
from backend.services.wechat_service import WeChatService
from backend.handlers.wechat_handler import WeChatCommandHandler

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局变量（在启动时初始化）
wechat_service = None
wechat_handler = None
wechat_crypto = None


def init_wechat(config: dict, db_engine):
    """
    初始化企业微信相关组件
    
    Args:
        config: 配置字典
        db_engine: 数据库引擎
    """
    global wechat_service, wechat_handler, wechat_crypto
    
    wechat_config = config.get('wechat', {})
    
    if not wechat_config.get('enabled'):
        logger.info("企业微信功能未启用")
        return
    
    try:
        # 初始化服务
        wechat_service = WeChatService(wechat_config)
        wechat_handler = WeChatCommandHandler(wechat_service, db_engine)
        
        # 初始化加密工具
        wechat_crypto = WeChatCrypto(
            wechat_config['token'],
            wechat_config['encoding_aes_key'],
            wechat_config['corp_id']
        )
        
        logger.info("✅ 企业微信功能初始化成功")
    except Exception as e:
        logger.error(f"❌ 企业微信功能初始化失败: {e}")
        raise


@router.get("/wechat/callback")
async def wechat_verify(request: Request):
    """
    企业微信验证URL有效性
    GET请求用于首次配置时验证
    """
    if not wechat_crypto:
        return Response(content="企业微信功能未启用", status_code=503)
    
    # 获取参数
    msg_signature = request.query_params.get('msg_signature', '')
    timestamp = request.query_params.get('timestamp', '')
    nonce = request.query_params.get('nonce', '')
    echostr = request.query_params.get('echostr', '')
    
    logger.info(f"收到企业微信验证请求: signature={msg_signature[:10]}...")
    
    try:
        # 验证签名并解密
        echo = wechat_crypto.check_signature(
            msg_signature,
            timestamp,
            nonce,
            echostr
        )
        logger.info("✅ 企业微信URL验证成功")
        return Response(content=echo, media_type="text/plain")
    except InvalidSignatureException:
        logger.error("❌ 企业微信URL验证失败: 签名无效")
        return Response(content="Signature verification failed", status_code=403)
    except Exception as e:
        logger.error(f"❌ 企业微信URL验证异常: {e}")
        return Response(content=str(e), status_code=500)


@router.post("/wechat/callback")
async def wechat_callback(request: Request):
    """
    企业微信消息回调
    POST请求用于接收用户消息
    """
    if not wechat_crypto or not wechat_handler:
        return Response(content="企业微信功能未启用", status_code=503)
    
    # 获取参数
    msg_signature = request.query_params.get('msg_signature', '')
    timestamp = request.query_params.get('timestamp', '')
    nonce = request.query_params.get('nonce', '')
    
    # 获取加密的消息体
    body = await request.body()
    
    try:
        # 解密消息
        decrypted_xml = wechat_crypto.decrypt_message(
            body,
            msg_signature,
            timestamp,
            nonce
        )
        
        # 解析消息
        msg = parse_message(decrypted_xml)
        
        logger.info(f"📨 收到消息: type={msg.type}, from={msg.source}")
        
        # 只处理文本消息
        if msg.type == 'text':
            user_id = msg.source
            content = msg.content
            logger.info(f"💬 用户消息: {user_id} -> {content}")
            
            # 异步处理消息（不阻塞回调）
            import threading
            thread = threading.Thread(
                target=wechat_handler.handle_message,
                args=(user_id, content)
            )
            thread.start()
        else:
            logger.info(f"⏭ 忽略非文本消息: {msg.type}")
        
        # 返回空响应（企业微信要求）
        return Response(content="success", media_type="text/plain")
        
    except InvalidSignatureException:
        logger.error("❌ 消息签名验证失败")
        return Response(content="Signature verification failed", status_code=403)
    except Exception as e:
        logger.error(f"❌ 处理消息异常: {e}")
        import traceback
        traceback.print_exc()
        return Response(content="Internal Server Error", status_code=500)
