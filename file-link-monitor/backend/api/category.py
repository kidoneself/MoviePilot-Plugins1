"""
分类管理API
"""
import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/categories")
async def get_categories():
    """
    获取所有二级分类列表
    """
    try:
        # 读取二级分类配置
        config_path = Path(__file__).parent.parent / 'categories.yaml'
        
        if not config_path.exists():
            return {
                "success": False,
                "message": "分类配置文件不存在"
            }
        
        with open(config_path, 'r', encoding='utf-8') as f:
            categories_config = yaml.safe_load(f)
        
        # 提取分类列表
        categories = list(categories_config.keys()) if categories_config else []
        
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
