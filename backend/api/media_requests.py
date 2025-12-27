"""
用户资源请求管理 API
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from pydantic import BaseModel

from backend.models import MediaRequest, get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class MediaRequestCreate(BaseModel):
    """创建资源请求"""
    tmdb_id: int
    media_type: str  # movie/tv
    title: str
    year: Optional[str] = None
    poster_url: Optional[str] = None


class MediaRequestUpdate(BaseModel):
    """更新资源请求"""
    status: Optional[str] = None  # pending/completed


@router.get("/media-requests")
async def get_media_requests(
    status: Optional[str] = Query(None, description="状态筛选: pending/completed/all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取资源请求列表
    """
    try:
        query = db.query(MediaRequest)
        
        # 状态筛选
        if status and status != 'all':
            query = query.filter(MediaRequest.status == status)
        
        # 总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        requests = query.order_by(desc(MediaRequest.request_count), desc(MediaRequest.updated_at)).offset(offset).limit(page_size).all()
        
        # 转换为字典
        data = []
        for req in requests:
            data.append({
                "id": req.id,
                "tmdb_id": req.tmdb_id,
                "media_type": req.media_type,
                "title": req.title,
                "year": req.year,
                "poster_url": req.poster_url,
                "request_count": req.request_count,
                "status": req.status,
                "created_at": req.created_at.strftime("%Y-%m-%d %H:%M:%S") if req.created_at else None,
                "updated_at": req.updated_at.strftime("%Y-%m-%d %H:%M:%S") if req.updated_at else None,
            })
        
        # 获取待处理数量
        pending_count = db.query(MediaRequest).filter(MediaRequest.status == 'pending').count()
        
        return {
            "success": True,
            "data": data,
            "total": total,
            "pending_count": pending_count,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"获取资源请求列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/media-requests")
async def create_media_request(
    request_data: MediaRequestCreate,
    db: Session = Depends(get_db)
):
    """
    创建或增加资源请求
    如果已存在，则请求次数+1
    """
    try:
        # 检查是否已存在
        existing = db.query(MediaRequest).filter(
            MediaRequest.tmdb_id == request_data.tmdb_id,
            MediaRequest.media_type == request_data.media_type
        ).first()
        
        if existing:
            # 已存在，增加请求次数
            existing.request_count += 1
            db.commit()
            db.refresh(existing)
            
            return {
                "success": True,
                "message": "请求已记录，计数+1",
                "data": {
                    "id": existing.id,
                    "request_count": existing.request_count
                }
            }
        else:
            # 创建新请求
            new_request = MediaRequest(
                tmdb_id=request_data.tmdb_id,
                media_type=request_data.media_type,
                title=request_data.title,
                year=request_data.year,
                poster_url=request_data.poster_url,
                request_count=1,
                status='pending'
            )
            db.add(new_request)
            db.commit()
            db.refresh(new_request)
            
            return {
                "success": True,
                "message": "资源请求已提交",
                "data": {
                    "id": new_request.id,
                    "request_count": new_request.request_count
                }
            }
    except Exception as e:
        db.rollback()
        logger.error(f"创建资源请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/media-requests/{request_id}")
async def update_media_request(
    request_id: int,
    update_data: MediaRequestUpdate,
    db: Session = Depends(get_db)
):
    """
    更新资源请求（如标记完成）
    """
    try:
        request_obj = db.query(MediaRequest).filter(MediaRequest.id == request_id).first()
        
        if not request_obj:
            raise HTTPException(status_code=404, detail="请求不存在")
        
        # 更新状态
        if update_data.status:
            request_obj.status = update_data.status
        
        db.commit()
        db.refresh(request_obj)
        
        return {
            "success": True,
            "message": "更新成功",
            "data": {
                "id": request_obj.id,
                "status": request_obj.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新资源请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/media-requests/{request_id}")
async def delete_media_request(
    request_id: int,
    db: Session = Depends(get_db)
):
    """
    删除资源请求
    """
    try:
        request_obj = db.query(MediaRequest).filter(MediaRequest.id == request_id).first()
        
        if not request_obj:
            raise HTTPException(status_code=404, detail="请求不存在")
        
        db.delete(request_obj)
        db.commit()
        
        return {
            "success": True,
            "message": "删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除资源请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media-requests/stats")
async def get_media_requests_stats(db: Session = Depends(get_db)):
    """
    获取资源请求统计
    """
    try:
        total = db.query(MediaRequest).count()
        pending = db.query(MediaRequest).filter(MediaRequest.status == 'pending').count()
        completed = db.query(MediaRequest).filter(MediaRequest.status == 'completed').count()
        
        # 最热门的10个请求
        hot_requests = db.query(MediaRequest).filter(
            MediaRequest.status == 'pending'
        ).order_by(desc(MediaRequest.request_count)).limit(10).all()
        
        hot_data = [{
            "id": req.id,
            "title": req.title,
            "media_type": req.media_type,
            "request_count": req.request_count,
            "poster_url": req.poster_url
        } for req in hot_requests]
        
        return {
            "success": True,
            "data": {
                "total": total,
                "pending": pending,
                "completed": completed,
                "hot_requests": hot_data
            }
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

