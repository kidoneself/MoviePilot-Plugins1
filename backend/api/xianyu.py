"""
闲鱼管家 API 路由
包括商品管理、卡密管理、定时任务等
"""
import os
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc
from datetime import datetime

from backend.models import get_session
from backend.models.xianyu import GoofishProduct, GoofishConfig, GoofishScheduleTask

def _get_session():
    """获取数据库会话"""
    from backend.main import db_engine
    return get_session(db_engine)
from backend.utils.xianyu_api import (
    GoofishSDK, GoofishConfig as SDKConfig,
    CreateProductRequest, PublishShop, PublishProductRequest,
    DownShelfProductRequest, DeleteProductRequest, ProductListRequest
)
from backend.services.image_upload import ImageUploadService

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局 SDK 实例
_sdk_instance: Optional[GoofishSDK] = None
_image_service: Optional[ImageUploadService] = None


def get_sdk() -> GoofishSDK:
    """获取 SDK 实例"""
    global _sdk_instance
    if _sdk_instance is None:
        # 从数据库加载配置
        session = _get_session()
        try:
            app_key_cfg = session.query(GoofishConfig).filter_by(config_key='goofish.app_key').first()
            app_secret_cfg = session.query(GoofishConfig).filter_by(config_key='goofish.app_secret').first()
            
            if not app_key_cfg or not app_secret_cfg:
                raise HTTPException(status_code=500, detail="闲鱼配置未设置，请先配置 app_key 和 app_secret")
            
            config = SDKConfig(
                app_key=app_key_cfg.config_value,
                app_secret=app_secret_cfg.config_value
            )
            _sdk_instance = GoofishSDK(config)
        finally:
            session.close()
    
    return _sdk_instance


def get_image_service() -> ImageUploadService:
    """获取图片上传服务"""
    global _image_service
    if _image_service is None:
        base_url = os.getenv('BASE_URL', 'http://localhost:8080')
        _image_service = ImageUploadService(upload_type='local', base_url=base_url)
    return _image_service


def get_config_value(key: str, default: str = "") -> str:
    """从数据库获取配置值"""
    session = _get_session()
    try:
        cfg = session.query(GoofishConfig).filter_by(config_key=key).first()
        return cfg.config_value if cfg else default
    finally:
        session.close()


def set_config_value(key: str, value: str, description: str = ""):
    """设置配置值"""
    session = _get_session()
    try:
        cfg = session.query(GoofishConfig).filter_by(config_key=key).first()
        if cfg:
            cfg.config_value = value
        else:
            cfg = GoofishConfig(config_key=key, config_value=value, description=description)
            session.add(cfg)
        session.commit()
    finally:
        session.close()


# ==================== 请求模型 ====================

class CreateProductFromMediaRequest(BaseModel):
    """从媒体创建商品请求"""
    media_id: int  # 媒体ID
    title: Optional[str] = None  # 可选，覆盖默认标题
    content: Optional[str] = None  # 可选，覆盖默认内容
    price: Optional[float] = None  # 价格（元）
    express_fee: Optional[float] = None  # 运费（元）
    stock: Optional[int] = None  # 库存
    image_urls: List[str]  # 图片URL列表


class ConfigRequest(BaseModel):
    """配置请求"""
    config_key: str
    config_value: str
    description: Optional[str] = ""


class ScheduleTaskRequest(BaseModel):
    """定时任务请求"""
    task_type: str  # publish/downshelf
    product_ids: List[int]
    execute_time: str  # ISO格式时间
    repeat_daily: bool = False


class KamiKindRequest(BaseModel):
    """创建卡种请求"""
    kind_name: str
    category_id: Optional[int] = None


class AddKamiRequest(BaseModel):
    """添加卡密请求"""
    kind_name: str
    kami_data: str  # 卡密数据（每行一组）
    repeat_count: int = 1


class AutoShippingRequest(BaseModel):
    """自动发货请求"""
    kind_name: str
    product_title: str  # 商品标题（用于搜索）


# ==================== 商品管理 ====================

@router.post("/xianyu/product/create-from-media")
async def create_product_from_media(request: CreateProductFromMediaRequest):
    """从媒体库创建商品（自动生成海报）"""
    try:
        sdk = get_sdk()
        session = _get_session()
        
        try:
            # 获取媒体信息
            from backend.models import CustomNameMapping
            media = session.query(CustomNameMapping).filter_by(id=request.media_id).first()
            if not media:
                raise HTTPException(status_code=404, detail="媒体不存在")
            
            # 检查海报
            if not media.poster_url:
                raise HTTPException(status_code=400, detail="该媒体没有海报图片")
            
            # 获取配置
            username1 = get_config_value('username1', '')
            username2 = get_config_value('username2', '')
            
            if not username1:
                raise HTTPException(status_code=400, detail="请先配置闲鱼会员名1（username1）")
            
            # 优先使用前端传来的图片URL，否则使用TMDB原图
            if request.image_urls and len(request.image_urls) > 0:
                logger.info(f"使用前端上传的海报创建商品: {media.original_name}")
                image_urls = request.image_urls
            else:
                logger.info(f"使用TMDB原图创建商品: {media.original_name}")
                image_urls = [media.poster_url]
            
            # 使用传入的参数或默认配置
            title = request.title or get_config_value('product.title.template', media.original_name)
            content = request.content or get_config_value('product.content.template', media.overview or '商品内容')
            price_yuan = request.price or float(get_config_value('product.price', '0.1'))
            fee_yuan = request.express_fee or float(get_config_value('product.express.fee', '0'))
            stock = request.stock or int(get_config_value('product.stock', '100'))
            stuff_status = int(get_config_value('product.stuff.status', '100'))
            
            # 转换价格为分
            price = int(price_yuan * 100)
            express_fee = int(fee_yuan * 100)
            
            # 准备商品信息
            product_request = CreateProductRequest(
                itemBizType=2,
                spBizType=99,
                channelCatId="0625f85b2c607412a7f7e02f36b0b49a",
                price=price,
                expressFee=express_fee,
                stock=stock,
                stuffStatus=stuff_status,
                publishShop=[]
            )
            
            # 店铺1
            shop1 = PublishShop(
                userName=username1,
                province=110000,
                city=110100,
                district=110101,
                title=title,
                content=content,
                images=image_urls
            )
            product_request.publishShop = [shop1]
            
            # 创建商品
            response1 = sdk.product().create_product(product_request)
            
            if not response1.productId:
                raise HTTPException(status_code=500, detail="店铺1创建失败")
            
            # 立即上架
            publish_req = PublishProductRequest(
                productId=response1.productId,
                userName=[username1]
            )
            sdk.product().publish_product(publish_req)
            
            # 保存到数据库
            db_product = GoofishProduct(
                product_id=response1.productId,
                title=title,
                price=price,
                stock=stock,
                express_fee=express_fee,
                product_status=response1.productStatus,
                media_id=request.media_id
            )
            session.add(db_product)
            session.commit()
            
            result = {
                'success': True,
                'message': '商品创建并上架成功',
                'product_id': response1.productId,
                'product_status': response1.productStatus,
                'image_urls': image_urls,
                'image_count': len(image_urls)
            }
            
            # 如果有第二个店铺
            if username2:
                shop2 = PublishShop(
                    userName=username2,
                    province=110000,
                    city=110100,
                    district=110101,
                    title=title,
                    content=content,
                    images=image_urls
                )
                product_request.publishShop = [shop2]
                
                try:
                    response2 = sdk.product().create_product(product_request)
                    if response2.productId:
                        publish_req2 = PublishProductRequest(
                            productId=response2.productId,
                            userName=[username2]
                        )
                        sdk.product().publish_product(publish_req2)
                        
                        # 保存第二个商品
                        db_product2 = GoofishProduct(
                            product_id=response2.productId,
                            title=title,
                            price=price,
                            stock=stock,
                            express_fee=express_fee,
                            product_status=response2.productStatus,
                            media_id=request.media_id
                        )
                        session.add(db_product2)
                        session.commit()
                        
                        result['message'] = '海报已自动生成，两个店铺商品均创建并上架成功'
                        result['product_id'] = f"{response1.productId}, {response2.productId}"
                except Exception as e:
                    logger.warning(f"店铺2创建失败: {e}")
                    result['message'] += f"，店铺2创建失败: {str(e)}"
            
            return result
            
        finally:
            session.close()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.post("/xianyu/product/upload-images-only")
async def upload_images_only(
    files: List[UploadFile] = File(...),
    x_forwarded_host: Optional[str] = Header(None),
    x_forwarded_proto: Optional[str] = Header(None),
    host: Optional[str] = Header(None)
):
    """只上传图片，返回URL列表（不创建商品）"""
    try:
        # 确定base_url
        actual_host = x_forwarded_host or host or 'localhost:8080'
        actual_proto = x_forwarded_proto or 'http'
        
        if 'ngrok' in actual_host:
            actual_proto = 'https'
        
        base_url = f"{actual_proto}://{actual_host}"
        
        # 上传图片
        image_service = ImageUploadService(upload_type='local', base_url=base_url)
        image_urls = []
        
        for file in files:
            if file and file.filename:
                file_data = await file.read()
                # 使用时间戳作为文件名
                custom_name = f"{int(datetime.now().timestamp() * 1000)}_{file.filename}"
                url = image_service._upload_to_local(file_data, file.filename, custom_name)
                image_urls.append(url)
        
        if not image_urls:
            raise HTTPException(status_code=400, detail="请至少上传一张图片")
        
        return {
            'success': True,
            'message': '图片上传成功',
            'image_urls': image_urls,
            'image_count': len(image_urls)
        }
    
    except Exception as e:
        logger.error(f"上传图片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/xianyu/product/upload-images")
async def upload_images(
    files: List[UploadFile] = File(...),
    title: str = Form(...),
    content: Optional[str] = Form(None),
    x_forwarded_host: Optional[str] = Header(None),
    x_forwarded_proto: Optional[str] = Header(None),
    host: Optional[str] = Header(None)
):
    """上传图片并创建商品（原始方式，兼容Java逻辑）"""
    try:
        sdk = get_sdk()
        session = _get_session()
        
        try:
            # 确定base_url
            actual_host = x_forwarded_host or host or 'localhost:8080'
            actual_proto = x_forwarded_proto or 'http'
            
            if 'ngrok' in actual_host:
                actual_proto = 'https'
            
            base_url = f"{actual_proto}://{actual_host}"
            
            # 上传图片
            image_service = ImageUploadService(upload_type='local', base_url=base_url)
            image_urls = []
            
            for file in files:
                if file and file.filename:
                    file_data = await file.read()
                    custom_name = f"{int(datetime.now().timestamp() * 1000)}_{title}_{file.filename}"
                    url = image_service._upload_to_local(file_data, file.filename, custom_name)
                    image_urls.append(url)
            
            if not image_urls:
                raise HTTPException(status_code=400, detail="请至少上传一张图片")
            
            # 获取配置
            username1 = get_config_value('username1', '')
            username2 = get_config_value('username2', '')
            
            if not username1:
                raise HTTPException(status_code=400, detail="请先配置闲鱼会员名1")
            
            # 获取默认配置
            price_yuan = float(get_config_value('product.price', '0.1'))
            fee_yuan = float(get_config_value('product.express.fee', '0'))
            stock = int(get_config_value('product.stock', '100'))
            stuff_status = int(get_config_value('product.stuff.status', '100'))
            
            price = int(price_yuan * 100)
            express_fee = int(fee_yuan * 100)
            
            # 准备商品请求
            product_request = CreateProductRequest(
                itemBizType=2,
                spBizType=99,
                channelCatId="0625f85b2c607412a7f7e02f36b0b49a",
                price=price,
                expressFee=express_fee,
                stock=stock,
                stuffStatus=stuff_status,
                publishShop=[]
            )
            
            # 店铺1
            shop1 = PublishShop(
                userName=username1,
                province=110000,
                city=110100,
                district=110101,
                title=title,
                content=content or get_config_value('product.content.template', '商品内容'),
                images=image_urls
            )
            product_request.publishShop = [shop1]
            
            # 创建并上架
            response1 = sdk.product().create_product(product_request)
            
            if not response1.productId:
                raise HTTPException(status_code=500, detail="店铺1创建失败")
            
            publish_req = PublishProductRequest(
                productId=response1.productId,
                userName=[username1]
            )
            sdk.product().publish_product(publish_req)
            
            result = {
                'success': True,
                'message': '商品创建并上架成功',
                'product_id': response1.productId,
                'product_status': response1.productStatus,
                'image_urls': image_urls,
                'image_count': len(image_urls)
            }
            
            # 如果有第二个店铺
            if username2:
                shop2 = PublishShop(
                    userName=username2,
                    province=110000,
                    city=110100,
                    district=110101,
                    title=title,
                    content=content or get_config_value('product.content.template', '商品内容'),
                    images=image_urls
                )
                product_request.publishShop = [shop2]
                
                try:
                    response2 = sdk.product().create_product(product_request)
                    if response2.productId:
                        publish_req2 = PublishProductRequest(
                            productId=response2.productId,
                            userName=[username2]
                        )
                        sdk.product().publish_product(publish_req2)
                        result['message'] = '两个店铺商品均创建并上架成功'
                        result['product_id'] = f"{response1.productId}, {response2.productId}"
                except Exception as e:
                    logger.warning(f"店铺2创建失败: {e}")
                    result['message'] += f"，店铺2创建失败"
            
            return result
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"上传图片并创建商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/xianyu/product/sync")
async def sync_products(page_no: int = 1, page_size: int = 50, product_status: Optional[int] = None):
    """同步商品列表"""
    try:
        sdk = get_sdk()
        session = _get_session()
        
        try:
            # 构建请求
            request = ProductListRequest(
                pageNo=page_no,
                pageSize=page_size,
                productStatus=product_status
            )
            
            # 如果没有指定状态，默认查询最近6个月
            if not product_status:
                import time
                now = int(time.time())
                six_months_ago = now - (6 * 30 * 24 * 60 * 60)
                request.updateTime = [six_months_ago, now]
            
            # 查询商品列表
            response = sdk.product().list_product(request)
            
            saved_count = 0
            for item in response.list:
                product_id = item.get('productId')
                if not product_id:
                    continue
                
                # 查找或创建
                db_product = session.query(GoofishProduct).filter_by(product_id=product_id).first()
                
                if db_product:
                    # 更新
                    db_product.title = item.get('title')
                    db_product.price = item.get('price')
                    db_product.stock = item.get('stock')
                    db_product.sold = item.get('sold')
                    db_product.product_status = item.get('productStatus')
                    db_product.sync_time = datetime.now()
                else:
                    # 新建
                    db_product = GoofishProduct(
                        product_id=product_id,
                        title=item.get('title'),
                        outer_id=item.get('outerId'),
                        price=item.get('price'),
                        original_price=item.get('originalPrice'),
                        stock=item.get('stock'),
                        sold=item.get('sold'),
                        product_status=item.get('productStatus'),
                        item_biz_type=item.get('itemBizType'),
                        sp_biz_type=item.get('spBizType'),
                        channel_cat_id=item.get('channelCatId'),
                        district_id=item.get('districtId'),
                        stuff_status=item.get('stuffStatus'),
                        express_fee=item.get('expressFee'),
                        spec_type=item.get('specType'),
                        source=item.get('source'),
                        online_time=item.get('onlineTime'),
                        offline_time=item.get('offlineTime'),
                        update_time_remote=item.get('updateTime'),
                        create_time_remote=item.get('createTime')
                    )
                    session.add(db_product)
                
                saved_count += 1
            
            session.commit()
            
            return {
                'success': True,
                'message': '同步成功',
                'synced_count': saved_count,
                'total': response.total
            }
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"同步商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/xianyu/product/list")
async def list_products(status: Optional[int] = None, page: int = 1, page_size: int = 20):
    """获取商品列表"""
    try:
        session = _get_session()
        try:
            query = session.query(GoofishProduct)
            
            if status is not None:
                query = query.filter_by(product_status=status)
            
            total = query.count()
            
            products = query.order_by(desc(GoofishProduct.sync_time))\
                           .limit(page_size)\
                           .offset((page - 1) * page_size)\
                           .all()
            
            return {
                'success': True,
                'data': [p.to_dict() for p in products],
                'total': total,
                'page': page,
                'page_size': page_size
            }
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"获取商品列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/xianyu/product/{product_id}/publish")
async def publish_product(product_id: int, user_name: Optional[str] = None):
    """上架商品"""
    try:
        sdk = get_sdk()
        
        # 如果没有指定用户名，使用默认配置
        if not user_name:
            user_name = get_config_value('username1', '')
            if not user_name:
                raise HTTPException(status_code=400, detail="请指定用户名或配置默认会员名")
        
        request = PublishProductRequest(
            productId=product_id,
            userName=[user_name]
        )
        
        sdk.product().publish_product(request)
        
        return {
            'success': True,
            'message': f'上架成功到店铺: {user_name}'
        }
    
    except Exception as e:
        logger.error(f"上架商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上架失败: {str(e)}")


@router.post("/xianyu/product/{product_id}/downshelf")
async def downshelf_product(product_id: int):
    """下架商品"""
    try:
        sdk = get_sdk()
        request = DownShelfProductRequest(productId=product_id)
        sdk.product().downshelf_product(request)
        
        return {
            'success': True,
            'message': '下架成功'
        }
    
    except Exception as e:
        logger.error(f"下架商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下架失败: {str(e)}")


@router.delete("/xianyu/product/{product_id}")
async def delete_product(product_id: int):
    """删除商品（仅草稿箱/待发布状态）"""
    try:
        sdk = get_sdk()
        session = _get_session()
        
        try:
            # 远程删除
            request = DeleteProductRequest(productId=product_id)
            sdk.product().delete_product(request)
            
            # 本地删除
            db_product = session.query(GoofishProduct).filter_by(product_id=product_id).first()
            if db_product:
                session.delete(db_product)
                session.commit()
            
            return {
                'success': True,
                'message': '删除成功'
            }
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"删除商品失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ==================== 配置管理 ====================

@router.get("/xianyu/config")
async def get_configs():
    """获取所有配置"""
    try:
        session = _get_session()
        try:
            configs = session.query(GoofishConfig).all()
            return {
                'success': True,
                'data': [c.to_dict() for c in configs]
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"获取配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xianyu/config")
async def save_config(request: ConfigRequest):
    """保存配置"""
    try:
        set_config_value(request.config_key, request.config_value, request.description)
        
        # 如果是 SDK 配置，重置 SDK 实例
        if request.config_key in ['goofish.app_key', 'goofish.app_secret']:
            global _sdk_instance
            if _sdk_instance:
                _sdk_instance.close()
                _sdk_instance = None
        
        return {
            'success': True,
            'message': '配置已保存'
        }
    except Exception as e:
        logger.error(f"保存配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 定时任务 ====================

@router.post("/xianyu/schedule-task")
async def create_schedule_task(request: ScheduleTaskRequest):
    """创建定时任务"""
    try:
        session = _get_session()
        try:
            # 解析执行时间
            execute_time = datetime.fromisoformat(request.execute_time.replace('Z', '+00:00'))
            
            # 获取商品标题
            product_titles = []
            for pid in request.product_ids:
                product = session.query(GoofishProduct).filter_by(product_id=pid).first()
                if product:
                    product_titles.append(product.title or '')
            
            # 创建任务
            task = GoofishScheduleTask(
                task_type=request.task_type,
                product_ids=json.dumps(request.product_ids),
                product_titles=json.dumps(product_titles),
                execute_time=execute_time,
                repeat_daily=request.repeat_daily,
                status='PENDING'
            )
            
            session.add(task)
            session.commit()
            
            return {
                'success': True,
                'message': '定时任务创建成功',
                'task_id': task.id
            }
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/xianyu/schedule-task/list")
async def list_schedule_tasks(status: Optional[str] = None):
    """获取定时任务列表"""
    try:
        session = _get_session()
        try:
            query = session.query(GoofishScheduleTask)
            
            if status:
                query = query.filter_by(status=status)
            
            tasks = query.order_by(desc(GoofishScheduleTask.create_time)).all()
            
            return {
                'success': True,
                'data': [t.to_dict() for t in tasks]
            }
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"获取定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/xianyu/schedule-task/{task_id}")
async def delete_schedule_task(task_id: int):
    """删除定时任务"""
    try:
        session = _get_session()
        try:
            task = session.query(GoofishScheduleTask).filter_by(id=task_id).first()
            if task:
                session.delete(task)
                session.commit()
            
            return {
                'success': True,
                'message': '删除成功'
            }
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"删除定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 卡密管理（Selenium） ====================

@router.post("/xianyu/kami/create-kind")
async def create_kami_kind(request: KamiKindRequest):
    """创建卡种（异步任务）"""
    try:
        from backend.utils.task_manager import get_task_manager
        from backend.utils.xianyu_playwright import KamiAutomation
        import threading
        
        # 创建任务
        task_manager = get_task_manager()
        task_id = task_manager.create_task('create_kind')
        logger.info(f"✅ 任务已创建: {task_id}, 卡种名称: {request.kind_name}")
        logger.info(f"当前任务列表: {list(task_manager.tasks.keys())}")
        
        # 定义回调函数
        def step_callback(step: str, status: str):
            logger.info(f"任务 {task_id} 步骤回调: {step} - {status}")
            if status == "qrcode" and step.startswith("QRCODE:"):
                # 保存二维码
                qrcode_base64 = step[7:]  # 去掉 "QRCODE:" 前缀
                task_manager.set_qrcode(task_id, qrcode_base64)
                logger.info(f"任务 {task_id} 二维码已设置")
            else:
                # 添加步骤
                task_manager.add_step(task_id, step, status)
        
        # 后台线程执行
        def run_automation():
            try:
                logger.info(f"🚀 开始执行任务 {task_id}")
                task_manager.add_step(task_id, "正在启动浏览器", "loading")
                
                # 本地macOS默认使用有头模式，Docker中设置XIANYU_HEADLESS=true
                import os
                import platform
                # macOS本地默认有头，Linux/Docker默认无头
                default_headless = 'false' if platform.system() == 'Darwin' else 'true'
                headless = os.getenv('XIANYU_HEADLESS', default_headless).lower() == 'true'
                logger.info(f"浏览器模式: {'无头' if headless else '有头'}")
                automation = KamiAutomation(headless=headless)
                automation.set_step_callback(step_callback)
                
                task_manager.add_step(task_id, "浏览器已启动，开始创建卡种", "loading")
                success = automation.create_kami_kind(request.kind_name, request.category_id)
                
                if success:
                    logger.info(f"✅ 任务 {task_id} 执行成功")
                    task_manager.complete_task(task_id, True, {'kind_name': request.kind_name})
                else:
                    logger.warning(f"⚠️ 任务 {task_id} 执行失败")
                    task_manager.complete_task(task_id, False, error='创建失败')
            except Exception as e:
                logger.error(f"❌ 任务 {task_id} 执行异常: {e}", exc_info=True)
                task_manager.complete_task(task_id, False, error=str(e))
            finally:
                # 任务结束后关闭浏览器（登录状态已保存）
                try:
                    automation.close()
                except:
                    pass
        
        thread = threading.Thread(target=run_automation, daemon=True)
        thread.start()
        logger.info(f"🧵 任务线程已启动: {task_id}")
        
        return {'success': True, 'task_id': task_id, 'message': '任务已创建，请等待...'}
    
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xianyu/kami/task/{task_id}")
async def get_kami_task_status(task_id: str):
    """获取卡密任务状态"""
    try:
        from backend.utils.task_manager import get_task_manager
        
        task_manager = get_task_manager()
        task = task_manager.get_task(task_id)
        
        if not task:
            logger.warning(f"⚠️ 任务不存在: {task_id}, 当前任务列表: {list(task_manager.tasks.keys())}")
            raise HTTPException(status_code=404, detail='任务不存在')
        
        logger.debug(f"📊 任务状态查询成功: {task_id}, 状态: {task.status}, 步骤数: {len(task.progress)}")
        
        return {
            'success': True,
            'data': task.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xianyu/kami/add-cards")
async def add_kami_cards(request: AddKamiRequest):
    """添加卡密（异步任务）"""
    try:
        from backend.utils.task_manager import get_task_manager
        from backend.utils.xianyu_playwright import KamiAutomation
        import threading
        
        # 创建任务
        task_manager = get_task_manager()
        task_id = task_manager.create_task('add_cards')
        
        # 定义回调函数
        def step_callback(step: str, status: str):
            if status == "qrcode" and step.startswith("QRCODE:"):
                qrcode_base64 = step[7:]
                task_manager.set_qrcode(task_id, qrcode_base64)
            else:
                task_manager.add_step(task_id, step, status)
        
        # 后台线程执行
        def run_automation():
            try:
                # 本地macOS默认使用有头模式，Docker中设置XIANYU_HEADLESS=true
                import os
                import platform
                default_headless = 'false' if platform.system() == 'Darwin' else 'true'
                headless = os.getenv('XIANYU_HEADLESS', default_headless).lower() == 'true'
                logger.info(f"浏览器模式: {'无头' if headless else '有头'}")
                automation = KamiAutomation(headless=headless)
                automation.set_step_callback(step_callback)
                success = automation.add_kami_cards(request.kind_name, request.kami_data, request.repeat_count)
                
                if success:
                    task_manager.complete_task(task_id, True, {'kind_name': request.kind_name})
                else:
                    task_manager.complete_task(task_id, False, error='添加失败')
            except Exception as e:
                logger.error(f"添加卡密失败: {e}", exc_info=True)
                task_manager.complete_task(task_id, False, error=str(e))
            finally:
                # 任务结束后关闭浏览器（登录状态已保存）
                try:
                    automation.close()
                except:
                    pass
        
        thread = threading.Thread(target=run_automation, daemon=True)
        thread.start()
        
        return {'success': True, 'task_id': task_id, 'message': '任务已创建，请等待...'}
    
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xianyu/kami/setup-shipping")
async def setup_auto_shipping(request: AutoShippingRequest):
    """设置自动发货（异步任务）"""
    try:
        logger.info(f"收到设置自动发货请求: kind_name={request.kind_name}, product_title={request.product_title}")
        
        from backend.utils.task_manager import get_task_manager
        from backend.utils.xianyu_playwright import KamiAutomation
        import threading
        
        # 创建任务
        task_manager = get_task_manager()
        task_id = task_manager.create_task('setup_shipping')
        
        # 定义回调函数
        def step_callback(step: str, status: str):
            if status == "qrcode" and step.startswith("QRCODE:"):
                qrcode_base64 = step[7:]
                task_manager.set_qrcode(task_id, qrcode_base64)
            else:
                task_manager.add_step(task_id, step, status)
        
        # 后台线程执行
        def run_automation():
            try:
                # 本地macOS默认使用有头模式，Docker中设置XIANYU_HEADLESS=true
                import os
                import platform
                default_headless = 'false' if platform.system() == 'Darwin' else 'true'
                headless = os.getenv('XIANYU_HEADLESS', default_headless).lower() == 'true'
                logger.info(f"浏览器模式: {'无头' if headless else '有头'}")
                automation = KamiAutomation(headless=headless)
                automation.set_step_callback(step_callback)
                success = automation.setup_auto_shipping(request.kind_name, request.product_title)
                
                if success:
                    task_manager.complete_task(task_id, True, {'kind_name': request.kind_name})
                else:
                    task_manager.complete_task(task_id, False, error='设置失败')
            except Exception as e:
                logger.error(f"设置自动发货失败: {e}", exc_info=True)
                task_manager.complete_task(task_id, False, error=str(e))
            finally:
                # 任务结束后关闭浏览器（登录状态已保存）
                try:
                    automation.close()
                except:
                    pass
        
        thread = threading.Thread(target=run_automation, daemon=True)
        thread.start()
        
        return {'success': True, 'task_id': task_id, 'message': '任务已创建，请等待...'}
    
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xianyu/kami/close-browser")
async def close_browser():
    """手动关闭浏览器会话"""
    try:
        from backend.utils.xianyu_playwright import close_global_browser
        
        close_global_browser()
        
        return {
            'success': True,
            'message': '浏览器已关闭，下次操作将重新创建'
        }
    
    except Exception as e:
        logger.error(f"关闭浏览器失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

