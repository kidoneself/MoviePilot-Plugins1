"""
媒体相关 API
包括图片代理和缓存
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pathlib import Path
import requests
import logging
import hashlib

router = APIRouter()
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(__file__).parent.parent.parent / "cache" / "posters"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_path(url: str) -> Path:
    """根据 URL 生成缓存文件路径"""
    # 使用 URL 的 MD5 作为文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()
    # 从 URL 提取文件扩展名
    ext = ".jpg"
    if url:
        if url.endswith('.png'):
            ext = ".png"
        elif url.endswith('.webp'):
            ext = ".webp"
    
    return CACHE_DIR / f"{url_hash}{ext}"


@router.get("/media/poster")
async def get_poster(url: str):
    """
    代理海报图片（带本地缓存）
    
    Args:
        url: TMDb 图片完整 URL
    """
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL 不能为空")
        
        # 检查缓存
        cache_file = get_cache_path(url)
        
        if cache_file.exists():
            logger.debug(f"✅ 缓存命中: {cache_file.name}")
            return FileResponse(cache_file)
        
        # 缓存未命中，下载图片
        logger.info(f"📥 下载图片: {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # 保存到缓存
        cache_file.write_bytes(response.content)
        logger.info(f"💾 已缓存: {cache_file.name}")
        
        # 返回图片
        return Response(
            content=response.content,
            media_type=response.headers.get('content-type', 'image/jpeg')
        )
        
    except requests.RequestException as e:
        logger.error(f"下载图片失败: {e}")
        raise HTTPException(status_code=502, detail=f"下载失败: {str(e)}")
    except Exception as e:
        logger.error(f"获取图片失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media/cache-stats")
async def get_cache_stats():
    """获取缓存统计"""
    try:
        cache_files = list(CACHE_DIR.glob("*"))
        total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
        
        return {
            "success": True,
            "data": {
                "cache_count": len(cache_files),
                "total_size": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "cache_dir": str(CACHE_DIR)
            }
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/media/clear-cache")
async def clear_cache():
    """清空图片缓存"""
    try:
        import shutil
        
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "message": "缓存已清空"
        }
    except Exception as e:
        logger.error(f"清空缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

