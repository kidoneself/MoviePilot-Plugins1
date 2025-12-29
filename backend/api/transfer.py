"""
转存API路由
提供网盘文件转存功能

核心功能：
1. 单个转存 - 从分享链接转存到指定路径
2. 转存状态查询 - 查看转存功能状态和支持的网盘

技术架构：
- OpenList集成：自动检查和创建目录
- 统一转存接口：支持百度/夸克/迅雷三网盘
- 超时保护：60秒超时避免长时间阻塞
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.models import get_db, PanCookie, CustomNameMapping
from backend.services.unified_transfer import UnifiedTransfer
from backend.common.constants import OPENLIST_URL, OPENLIST_TOKEN, OPENLIST_PATH_PREFIX, PAN_MOUNT_MAP, DEFAULT_TIMEOUT, TRANSFER_TIMEOUT

router = APIRouter()


# ==================== 请求/响应模型 ====================

class TransferRequest(BaseModel):
    """转存请求"""
    share_url: str = Field(..., description="分享链接")
    pass_code: Optional[str] = Field(None, description="提取码")
    target_path: str = Field(..., description="目标路径（如：/电影/动作片/钢铁侠3）")
    pan_type: str = Field(..., description="网盘类型：baidu/quark/xunlei")
    use_openlist: bool = Field(True, description="是否使用OpenList管理路径")

    class Config:
        json_schema_extra = {
            "example": {
                "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
                "pass_code": "1234",
                "target_path": "/电影/动作片/钢铁侠3",
                "pan_type": "baidu",
                "use_openlist": True
            }
        }




class TransferResponse(BaseModel):
    """转存响应"""
    success: bool = Field(..., description="是否成功")
    pan_type: str = Field(..., description="网盘类型")
    file_count: int = Field(..., description="文件数量")
    file_ids: List[str] = Field(default_factory=list, description="文件ID列表")
    message: str = Field(..., description="消息")
    details: dict = Field(default_factory=dict, description="详细信息")


# ==================== API接口 ====================

@router.post("/transfer", response_model=TransferResponse, summary="单个转存")
async def transfer_file(
    request: TransferRequest,
    db: Session = Depends(get_db)
):
    """
    转存单个分享链接到指定网盘
    
    工作流程：
    1. 验证网盘类型和认证信息
    2. 使用OpenList检查目录是否存在
    3. 不存在则自动创建目录（一层一层）
    4. 获取转存参数（百度用路径，夸克/迅雷用ID）
    5. 调用网盘API执行转存
    6. 返回转存结果
    
    参数说明：
    - share_url: 分享链接（如：https://pan.baidu.com/s/xxx）
    - pass_code: 提取码（前端会自动从URL解析）
    - target_path: 目标路径（如：/A-闲鱼影视/剧集/日韩剧集/模范出租车）
    - pan_type: 网盘类型（baidu/quark/xunlei）
    - use_openlist: 是否使用OpenList管理（推荐true）
    
    返回示例：
    {
        "success": true,
        "pan_type": "baidu",
        "file_count": 16,
        "message": "转存成功"
    }
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 收到转存请求: {request.pan_type} - {request.share_url} -> {request.target_path}")
    
    try:
        # 验证网盘类型
        if request.pan_type not in ['baidu', 'quark', 'xunlei']:
            raise HTTPException(status_code=400, detail=f"不支持的网盘类型: {request.pan_type}")
        
        # 从数据库获取认证信息
        pan_record = db.query(PanCookie).filter_by(
            pan_type=request.pan_type,
            is_active=True
        ).first()
        
        if not pan_record:
            raise HTTPException(
                status_code=404,
                detail=f"未找到{request.pan_type}的认证信息，请先配置Cookie"
            )
        
        # ========== OpenList模式（推荐） ==========
        if request.use_openlist:
            import json
            import concurrent.futures
            
            # 1. 准备所有网盘的认证信息（UnifiedTransfer需要）
            pan_credentials = {}
            for pan_type in ['baidu', 'quark', 'xunlei']:
                record = db.query(PanCookie).filter_by(
                    pan_type=pan_type,
                    is_active=True
                ).first()
                
                if record:
                    # 迅雷需要JSON格式，其他网盘只需Cookie
                    if pan_type == 'xunlei':
                        try:
                            parsed = json.loads(record.cookie)
                            # 兼容两种格式：
                            # 1. 字典格式：{"authorization": "...", "x_captcha_token": "..."}
                            # 2. 数组格式：[{"name": "userid", "value": "..."}]
                            if isinstance(parsed, list):
                                # 数组格式 -> 转为browser_cookie字段
                                pan_credentials[pan_type] = {'browser_cookie': record.cookie}
                            else:
                                # 字典格式 -> 直接使用
                                pan_credentials[pan_type] = parsed
                        except:
                            pan_credentials[pan_type] = {'cookie': record.cookie}
                    else:
                        pan_credentials[pan_type] = {'cookie': record.cookie}
            
            # 2. 创建统一转存实例
            logger.info(f"📦 准备调用UnifiedTransfer.transfer")
            transfer = UnifiedTransfer(pan_credentials=pan_credentials)
            logger.info(f"📦 UnifiedTransfer实例化完成，开始转存...")
            
            # 3. 使用全局线程池执行，避免阻塞FastAPI主线程
            # ✅ 复用线程池，提升性能
            from backend.common.thread_pool import get_executor
            executor = get_executor()
            future = executor.submit(
                transfer.transfer,
                share_url=request.share_url,
                pass_code=request.pass_code,
                target_path=request.target_path,
                pan_type=request.pan_type
            )
            try:
                result = future.result(timeout=TRANSFER_TIMEOUT)
                logger.info(f"✅ UnifiedTransfer.transfer完成，结果: {result}")
            except concurrent.futures.TimeoutError:
                logger.error(f"❌ 转存超时（{TRANSFER_TIMEOUT}秒）")
                raise HTTPException(status_code=504, detail="转存超时，请稍后重试")
        else:
            # 方式2：直接使用网盘API（不使用OpenList）
            from backend.utils.pan_factory import PanFactory
            import json
            
            # 准备认证信息
            if request.pan_type == 'xunlei':
                credentials = json.loads(pan_record.cookie)
            else:
                credentials = {'cookie': pan_record.cookie}
            
            # 创建API实例
            api = PanFactory.create_api(request.pan_type, credentials)
            
            # 添加网盘前缀
            target_path = f"/{PAN_MOUNT_MAP[request.pan_type]}{request.target_path}"
            
            # 转存
            result = api.transfer(
                share_url=request.share_url,
                pass_code=request.pass_code,
                target_path=target_path
            )
        
        return TransferResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转存失败: {str(e)}")




@router.post("/transfer/from_mapping/{mapping_id}", summary="从映射转存")
async def transfer_from_mapping(
    mapping_id: int,
    pan_type: str,
    db: Session = Depends(get_db)
):
    """
    从映射记录转存（自动使用category构建路径）
    
    Args:
        mapping_id: 映射ID
        pan_type: 网盘类型 baidu/quark/xunlei
    """
    try:
        import requests
        
        # 1. 获取映射记录
        mapping = db.query(CustomNameMapping).filter_by(id=mapping_id).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="映射不存在")
        
        # 2. 获取分享链接
        share_url = getattr(mapping, f"{pan_type}_link")
        if not share_url:
            raise HTTPException(status_code=400, detail=f"未配置{pan_type}分享链接")
        
        # 3. 构建目标路径（使用各网盘对应的映射名）
        base_path = OPENLIST_PATH_PREFIX
        
        # 获取对应网盘的显示名，如果没有则用原名
        if pan_type == 'quark':
            folder_name = mapping.quark_name or mapping.original_name
        elif pan_type == 'baidu':
            folder_name = mapping.baidu_name or mapping.original_name
        elif pan_type == 'xunlei':
            folder_name = mapping.xunlei_name or mapping.original_name
        else:
            folder_name = mapping.original_name
        
        if mapping.category:
            # 有分类：/A-闲鱼影视（自动更新）/剧集/国产剧集/映射名
            target_path = f"{base_path}/{mapping.category}/{folder_name}"
        else:
            # 无分类：/A-闲鱼影视（自动更新）/未分类/映射名
            target_path = f"{base_path}/未分类/{folder_name}"
        
        logger.info(f"转存到{pan_type}: 原名={mapping.original_name}, 映射名={folder_name}, 路径={target_path}")
        
        # 4. 检查目录是否存在（OpenList）
        openlist_path = f"/{PAN_MOUNT_MAP[pan_type]}{target_path}"
        
        headers = {
            'Authorization': OPENLIST_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # 检查剧名文件夹是否存在
        try:
            check_resp = requests.post(
                f"{OPENLIST_URL}/api/fs/get",
                json={"path": openlist_path},
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
        except requests.RequestException as e:
            logger.error(f"检查OpenList目录失败: {e}")
            raise HTTPException(status_code=503, detail=f"OpenList服务异常: {str(e)}")
        
        folder_exists = check_resp.json().get('code') == 200
        
        if not folder_exists:
            # 文件夹不存在，创建
            try:
                create_resp = requests.post(
                    f"{OPENLIST_URL}/api/fs/mkdir",
                    json={"path": openlist_path},
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT
                )
            except requests.RequestException as e:
                logger.error(f"创建OpenList目录失败: {e}")
                raise HTTPException(status_code=503, detail=f"OpenList服务异常: {str(e)}")
            
            if create_resp.json().get('code') != 200:
                raise HTTPException(status_code=500, detail="创建文件夹失败")
            
            # 等待同步
            import time
            time.sleep(2)
        
        # 5. 获取认证信息
        pan_record = db.query(PanCookie).filter_by(
            pan_type=pan_type,
            is_active=True
        ).first()
        
        if not pan_record:
            raise HTTPException(status_code=404, detail=f"未找到{pan_type}认证信息")
        
        # 6. 转存
        from backend.utils.pan_factory import PanFactory
        import json
        if pan_type == 'xunlei':
            credentials = json.loads(pan_record.cookie)
        else:
            credentials = {'cookie': pan_record.cookie}
        
        api = PanFactory.create_api(pan_type, credentials)
        
        # 获取文件夹ID（夸克和迅雷需要）
        if pan_type in ['quark', 'xunlei']:
            try:
                folder_resp = requests.post(
                    f"{OPENLIST_URL}/api/fs/get",
                    json={"path": openlist_path},
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT
                )
                folder_id = folder_resp.json()['data'].get('id')
            except requests.RequestException as e:
                logger.error(f"获取OpenList文件夹ID失败: {e}")
                raise HTTPException(status_code=503, detail=f"OpenList服务异常: {str(e)}")
            result = api.transfer(share_url=share_url, pass_code=None, target_path=folder_id)
        else:
            # 百度直接用路径
            result = api.transfer(share_url=share_url, pass_code=None, target_path=openlist_path)
        
        return TransferResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转存失败: {str(e)}")


@router.get("/transfer/status", summary="支持的网盘")
async def get_transfer_status(db: Session = Depends(get_db)):
    """
    获取转存功能状态和支持的网盘列表
    """
    try:
        # 检查各网盘的认证状态
        pan_status = {}
        
        for pan_type in ['baidu', 'quark', 'xunlei']:
            pan_record = db.query(PanCookie).filter_by(
                pan_type=pan_type,
                is_active=True
            ).first()
            
            pan_status[pan_type] = {
                'available': pan_record is not None,
                'name': {
                    'baidu': '百度网盘',
                    'quark': '夸克网盘',
                    'xunlei': '迅雷网盘'
                }[pan_type]
            }
        
        return {
            'success': True,
            'supported_platforms': pan_status,
            'features': {
                'openlist_integration': True,
                'direct_api': True,
                'batch_transfer': True,
                'mapping_transfer': True
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")
