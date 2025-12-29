"""
分类管理API
"""
import asyncio
from fastapi import APIRouter, HTTPException
from backend.common.config_cache import get_cat_config

router = APIRouter()


@router.get("/categories")
async def get_categories():
    """
    获取所有二级分类列表（从 cat.yaml 提取，使用缓存）
    """
    try:
        # ✅ 在线程池中读取缓存配置，避免阻塞事件循环
        cat_config = await asyncio.to_thread(get_cat_config)
        
        # 从 cat.yaml 提取所有分类（movie + tv）
        categories = []
        if cat_config:
            for media_type in ['movie', 'tv']:
                if media_type in cat_config:
                    categories.extend(cat_config[media_type].keys())
        
        # 按一级分类分组
        grouped = {
            '动漫': [],
            '电影': [],
            '剧集': [],
            '其他': []
        }
        
        for category in categories:
            if '/' in category:
                level1 = category.split('/')[0]
                if level1 in grouped:
                    grouped[level1].append(category)
        
        return {
            "success": True,
            "categories": categories,
            "grouped": grouped,
            "total": len(categories)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类失败: {str(e)}")
