"""
配置管理 API
用于管理闲鱼商品模板等配置项
"""
import logging
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.models import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/config/templates/{template_type}")
async def get_templates(template_type: str, db: Session = Depends(get_db)):
    """
    获取指定类型的商品模板
    
    Args:
        template_type: 模板类型，completed（完结）或 updating（更新中）
    
    Returns:
        模板列表，每个模板包含 title 和 content 字段
    """
    try:
        # 验证类型
        if template_type not in ['completed', 'updating']:
            raise HTTPException(status_code=400, detail="模板类型必须是 completed 或 updating")
        
        # 获取通用内容模板
        content_query = text("""
            SELECT config_value 
            FROM goofish_config 
            WHERE config_key = 'template.content.default'
        """)
        content_result = db.execute(content_query).fetchone()
        default_content = content_result[0] if content_result else "商品内容"
        
        # 获取指定类型的所有标题模板
        templates = []
        for i in range(1, 11):  # 查询 1-10 号模板
            title_key = f'template.title.{template_type}.{i}'
            title_query = text("""
                SELECT config_value 
                FROM goofish_config 
                WHERE config_key = :key
            """)
            title_result = db.execute(title_query, {"key": title_key}).fetchone()
            
            if title_result and title_result[0]:
                templates.append({
                    "title": title_result[0],
                    "content": default_content
                })
        
        logger.info(f"获取{template_type}模板成功，共{len(templates)}个")
        
        return {
            "success": True,
            "data": templates
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/list")
async def list_configs(db: Session = Depends(get_db)):
    """获取所有配置项"""
    try:
        query = text("""
            SELECT id, config_key, config_value, config_type, description, 
                   create_time, update_time
            FROM goofish_config
            ORDER BY config_type, config_key
        """)
        result = db.execute(query).fetchall()
        
        configs = []
        for row in result:
            configs.append({
                "id": row[0],
                "configKey": row[1],
                "configValue": row[2],
                "configType": row[3],
                "description": row[4],
                "createTime": row[5].isoformat() if row[5] else None,
                "updateTime": row[6].isoformat() if row[6] else None,
            })
        
        return {
            "success": True,
            "data": configs
        }
        
    except Exception as e:
        logger.error(f"获取配置列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/get/{key}")
async def get_config(key: str, db: Session = Depends(get_db)):
    """根据key获取配置项"""
    try:
        query = text("""
            SELECT id, config_key, config_value, config_type, description,
                   create_time, update_time
            FROM goofish_config
            WHERE config_key = :key
        """)
        result = db.execute(query, {"key": key}).fetchone()
        
        if not result:
            return {
                "success": False,
                "message": "配置不存在"
            }
        
        return {
            "success": True,
            "data": {
                "id": result[0],
                "configKey": result[1],
                "configValue": result[2],
                "configType": result[3],
                "description": result[4],
                "createTime": result[5].isoformat() if result[5] else None,
                "updateTime": result[6].isoformat() if result[6] else None,
            }
        }
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

