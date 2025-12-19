"""
分享链接生成API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from backend.models import PanCookie, CustomNameMapping, get_session
from backend.utils.baidu_api import BaiduPanAPI
from backend.utils.quark_api import QuarkAPI
from backend.utils.xunlei_api import XunleiAPI

router = APIRouter()
logger = logging.getLogger(__name__)


class UpdateCookieRequest(BaseModel):
    """更新Cookie请求"""
    pan_type: str  # baidu/quark
    cookie: str


class GenerateLinkRequest(BaseModel):
    """生成链接请求"""
    pan_type: str  # baidu/quark
    original_name: Optional[str] = None  # 指定单个剧集，为空则批量处理


def get_db():
    """依赖注入：获取数据库会话"""
    from backend.main import db_engine
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()


@router.post('/cookie')
async def update_cookie(request: UpdateCookieRequest, db: Session = Depends(get_db)):
    """
    更新网盘Cookie
    """
    try:
        pan_type = request.pan_type.lower()
        if pan_type not in ['baidu', 'quark', 'xunlei']:
            raise HTTPException(status_code=400, detail="不支持的网盘类型")
        
        # 查找或创建
        cookie_obj = db.query(PanCookie).filter(PanCookie.pan_type == pan_type).first()
        
        if cookie_obj:
            # 更新现有Cookie
            cookie_obj.cookie = request.cookie
            cookie_obj.is_active = True
            cookie_obj.check_status = 'unknown'
            cookie_obj.check_error = None
            cookie_obj.last_check_time = None
            logger.info(f"更新{pan_type}网盘Cookie")
        else:
            # 创建新Cookie
            cookie_obj = PanCookie(
                pan_type=pan_type,
                cookie=request.cookie,
                is_active=True,
                check_status='unknown'
            )
            db.add(cookie_obj)
            logger.info(f"创建{pan_type}网盘Cookie")
        
        db.commit()
        
        return {
            'success': True,
            'message': f'{pan_type}网盘Cookie更新成功'
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"更新Cookie失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get('/cookie/{pan_type}')
async def get_cookie_status(pan_type: str, db: Session = Depends(get_db)):
    """
    获取Cookie状态
    """
    try:
        pan_type = pan_type.lower()
        cookie_obj = db.query(PanCookie).filter(PanCookie.pan_type == pan_type).first()
        
        if not cookie_obj:
            return {
                'exists': False,
                'is_active': False,
                'check_status': 'unknown'
            }
        
        return {
            'exists': True,
            'is_active': cookie_obj.is_active,
            'check_status': cookie_obj.check_status,
            'check_error': cookie_obj.check_error,
            'last_check_time': cookie_obj.last_check_time.isoformat() if cookie_obj.last_check_time else None
        }
        
    except Exception as e:
        logger.error(f"查询Cookie状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post('/generate-link')
async def generate_share_link(request: GenerateLinkRequest, db: Session = Depends(get_db)):
    """
    生成分享链接
    """
    try:
        pan_type = request.pan_type.lower()
        
        # 1. 获取Cookie
        cookie_obj = db.query(PanCookie).filter(
            PanCookie.pan_type == pan_type,
            PanCookie.is_active == True
        ).first()
        
        if not cookie_obj:
            raise HTTPException(status_code=400, detail=f"未配置{pan_type}网盘Cookie，请先上传")
        
        # 2. 查询要处理的映射
        query = db.query(CustomNameMapping).filter(CustomNameMapping.enabled == True)
        
        if request.original_name:
            # 单个剧集
            query = query.filter(CustomNameMapping.original_name == request.original_name)
            mappings = query.all()
            if not mappings:
                raise HTTPException(status_code=404, detail=f"未找到映射: {request.original_name}")
        else:
            # 批量处理：查找未生成链接的
            if pan_type == 'baidu':
                query = query.filter(
                    (CustomNameMapping.baidu_link == None) | (CustomNameMapping.baidu_link == '')
                )
            elif pan_type == 'quark':
                query = query.filter(
                    (CustomNameMapping.quark_link == None) | (CustomNameMapping.quark_link == '')
                )
            else:  # xunlei
                query = query.filter(
                    (CustomNameMapping.xunlei_link == None) | (CustomNameMapping.xunlei_link == '')
                )
            mappings = query.all()
        
        if not mappings:
            return {
                'success': True,
                'message': '没有需要处理的映射',
                'results': {}
            }
        
        # 3. 初始化API
        if pan_type == 'baidu':
            api = BaiduPanAPI(cookie_obj.cookie)
        elif pan_type == 'quark':
            api = QuarkAPI(cookie_obj.cookie)
        else:  # xunlei
            api = XunleiAPI(cookie_obj.cookie)
        
        # 4. 批量生成链接
        results = {}
        success_count = 0
        fail_count = 0
        
        for mapping in mappings:
            # 确定文件名
            if pan_type == 'baidu':
                folder_name = mapping.baidu_name or mapping.original_name
            elif pan_type == 'quark':
                folder_name = mapping.quark_name or mapping.original_name
            else:  # xunlei
                folder_name = mapping.xunlei_name or mapping.original_name
            
            logger.info(f"处理: {mapping.original_name} -> {folder_name}")
            
            # 生成链接
            link, error = api.generate_share_link(folder_name)
            
            if error:
                # 失败
                results[mapping.original_name] = {
                    'success': False,
                    'error': error
                }
                fail_count += 1
                logger.warning(f"❌ 失败: {mapping.original_name} - {error}")
            else:
                # 成功，更新数据库
                if pan_type == 'baidu':
                    mapping.baidu_link = link
                elif pan_type == 'quark':
                    mapping.quark_link = link
                else:  # xunlei
                    mapping.xunlei_link = link
                
                results[mapping.original_name] = {
                    'success': True,
                    'link': link
                }
                success_count += 1
                logger.info(f"✅ 成功: {mapping.original_name}")
        
        # 5. 提交数据库
        db.commit()
        
        return {
            'success': True,
            'message': f'处理完成：成功{success_count}个，失败{fail_count}个',
            'total': len(mappings),
            'success_count': success_count,
            'fail_count': fail_count,
            'results': results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"生成链接失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成链接失败: {str(e)}")


@router.get("/share-links")
def get_all_share_links(db: Session = Depends(get_db)):
    """获取所有剧集的分享链接"""
    try:
        # 查询所有有分享链接的映射
        mappings = db.query(CustomNameMapping).filter(
            (CustomNameMapping.baidu_link.isnot(None)) |
            (CustomNameMapping.quark_link.isnot(None)) |
            (CustomNameMapping.xunlei_link.isnot(None))
        ).order_by(CustomNameMapping.original_name).all()
        
        result = []
        for mapping in mappings:
            import re
            
            # 处理百度链接和提取码
            baidu_pwd = None
            baidu_link = mapping.baidu_link
            
            # 如果baidu_link包含提取码文本，清理掉
            if baidu_link:
                # 移除多余的提取码文本
                if '提取码:' in baidu_link or '提取码：' in baidu_link:
                    # 提取URL部分（只保留链接）
                    url_match = re.search(r'(https://pan\.baidu\.com/s/[^\s]+)', baidu_link)
                    if url_match:
                        baidu_link = url_match.group(1)
                
                # 从URL参数提取提取码
                if '?pwd=' in baidu_link:
                    parts = baidu_link.split('?pwd=')
                    if len(parts) == 2:
                        baidu_link = parts[0]  # 只保留链接部分
                        baidu_pwd = parts[1].split()[0]  # 提取码可能后面还有文字
            
            # 处理迅雷链接和提取码
            xunlei_pwd = None
            xunlei_link = mapping.xunlei_link
            
            if xunlei_link:
                # 从URL参数提取提取码
                if '?pwd=' in xunlei_link:
                    parts = xunlei_link.split('?pwd=')
                    if len(parts) == 2:
                        xunlei_link = parts[0]  # 只保留链接部分
                        xunlei_pwd = parts[1].split()[0]  # 提取码可能后面还有文字
                
                # 如果链接中包含"提取码:"文本，也清理
                if '提取码:' in xunlei_link or '提取码：' in xunlei_link:
                    url_match = re.search(r'(https://pan\.xunlei\.com/s/[^\s]+)', xunlei_link)
                    if url_match:
                        xunlei_link = url_match.group(1)
            
            item = {
                "original_name": mapping.original_name,
                "is_completed": mapping.is_completed or False,
                "baidu_link": baidu_link,
                "baidu_pwd": baidu_pwd,
                "quark_link": mapping.quark_link,
                "xunlei_link": xunlei_link,
                "xunlei_pwd": xunlei_pwd
            }
            result.append(item)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"获取分享链接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
