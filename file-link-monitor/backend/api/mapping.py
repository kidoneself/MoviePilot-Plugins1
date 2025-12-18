from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from backend.models import CustomNameMapping, LinkRecord, get_session

router = APIRouter()
logger = logging.getLogger(__name__)


def get_db():
    """依赖注入：获取数据库会话"""
    from backend.main import db_engine
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()


class MappingCreate(BaseModel):
    """创建映射请求"""
    original_name: str
    custom_name: str
    note: Optional[str] = None


class MappingUpdate(BaseModel):
    """更新映射请求"""
    custom_name: Optional[str] = None
    enabled: Optional[bool] = None
    note: Optional[str] = None


@router.get("/mappings")
async def get_mappings(
    page: int = 1,
    page_size: int = 20,
    enabled: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有自定义名称映射（分页）
    
    Args:
        page: 页码（从1开始）
        page_size: 每页数量
        enabled: 过滤启用状态
        search: 搜索原名或自定义名
    """
    try:
        query = db.query(CustomNameMapping)
        
        if enabled is not None:
            query = query.filter(CustomNameMapping.enabled == enabled)
        
        if search:
            query = query.filter(
                (CustomNameMapping.original_name.like(f'%{search}%')) |
                (CustomNameMapping.custom_name.like(f'%{search}%'))
            )
        
        # 总数
        total = query.count()
        
        # 分页
        mappings = query.order_by(CustomNameMapping.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        
        return {
            "success": True,
            "data": [
                {
                    "id": m.id,
                    "original_name": m.original_name,
                    "custom_name": m.custom_name,
                    "enabled": m.enabled,
                    "note": m.note,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None
                }
                for m in mappings
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    except Exception as e:
        logger.error(f"获取映射失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/mappings")
async def create_mapping(mapping: MappingCreate, db: Session = Depends(get_db)):
    """
    创建自定义名称映射
    
    Args:
        mapping: 映射数据
    """
    try:
        # 检查是否已存在
        existing = db.query(CustomNameMapping).filter(
            CustomNameMapping.original_name == mapping.original_name
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": f"映射已存在: {mapping.original_name}"
            }
        
        # 创建映射
        new_mapping = CustomNameMapping(
            original_name=mapping.original_name,
            custom_name=mapping.custom_name,
            note=mapping.note
        )
        db.add(new_mapping)
        db.commit()
        db.refresh(new_mapping)
        
        logger.info(f"✅ 创建映射: {mapping.original_name} -> {mapping.custom_name}")
        
        return {
            "success": True,
            "message": "映射创建成功",
            "data": {
                "id": new_mapping.id,
                "original_name": new_mapping.original_name,
                "custom_name": new_mapping.custom_name,
                "enabled": new_mapping.enabled,
                "note": new_mapping.note
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"创建映射失败: {e}")
        return {"success": False, "message": str(e)}


@router.put("/mappings/{mapping_id}")
async def update_mapping(
    mapping_id: int,
    mapping: MappingUpdate,
    db: Session = Depends(get_db)
):
    """
    更新自定义名称映射
    
    Args:
        mapping_id: 映射ID
        mapping: 更新数据
    """
    try:
        existing = db.query(CustomNameMapping).filter(
            CustomNameMapping.id == mapping_id
        ).first()
        
        if not existing:
            return {"success": False, "message": "映射不存在"}
        
        # 更新字段
        if mapping.custom_name is not None:
            existing.custom_name = mapping.custom_name
        if mapping.enabled is not None:
            existing.enabled = mapping.enabled
        if mapping.note is not None:
            existing.note = mapping.note
        
        db.commit()
        db.refresh(existing)
        
        logger.info(f"✅ 更新映射: {existing.original_name} -> {existing.custom_name}")
        
        return {
            "success": True,
            "message": "映射更新成功",
            "data": {
                "id": existing.id,
                "original_name": existing.original_name,
                "custom_name": existing.custom_name,
                "enabled": existing.enabled,
                "note": existing.note
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"更新映射失败: {e}")
        return {"success": False, "message": str(e)}


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """
    删除自定义名称映射
    
    Args:
        mapping_id: 映射ID
    """
    try:
        mapping = db.query(CustomNameMapping).filter(
            CustomNameMapping.id == mapping_id
        ).first()
        
        if not mapping:
            return {"success": False, "message": "映射不存在"}
        
        original_name = mapping.original_name
        db.delete(mapping)
        db.commit()
        
        logger.info(f"✅ 删除映射: {original_name}")
        
        return {
            "success": True,
            "message": "映射删除成功"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"删除映射失败: {e}")
        return {"success": False, "message": str(e)}


@router.delete("/records/by-show")
async def delete_records_by_show(
    show_name: str,
    db: Session = Depends(get_db)
):
    """
    删除指定剧集的所有硬链接记录
    
    Args:
        show_name: 剧集名称（原始名称，会匹配路径中包含该名称的所有记录）
    """
    try:
        # 查询包含该剧集名称的所有记录
        records = db.query(LinkRecord).filter(
            LinkRecord.source_file.like(f'%{show_name}%')
        ).all()
        
        if not records:
            return {
                "success": False,
                "message": f"未找到包含 '{show_name}' 的记录"
            }
        
        count = len(records)
        
        # 删除所有匹配的记录
        for record in records:
            db.delete(record)
        
        db.commit()
        
        logger.info(f"✅ 删除 {count} 条记录: {show_name}")
        
        return {
            "success": True,
            "message": f"成功删除 {count} 条记录",
            "deleted_count": count
        }
    except Exception as e:
        db.rollback()
        logger.error(f"删除记录失败: {e}")
        return {"success": False, "message": str(e)}
