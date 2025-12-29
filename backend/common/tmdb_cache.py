"""
TMDB API 缓存 - 减少外部API调用
"""
from functools import lru_cache
from typing import Dict, Optional
import requests
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

# TMDB API 配置
TMDB_API_KEY = "c7f3349aa08d38fe2e391ec5a4c0279c"
TMDB_BASE_URL = "https://api.themoviedb.org/3"


class TMDBCache:
    """
    TMDB API 响应缓存
    
    优化:
    - 使用 functools.lru_cache 缓存热门查询
    - 减少外部 API 调用
    - 提升响应速度
    """
    
    def __init__(self, cache_size: int = 128):
        self.cache_size = cache_size
    
    def _make_cache_key(self, url: str, params: Dict) -> str:
        """生成缓存键"""
        # 对参数排序以确保一致性
        sorted_params = json.dumps(params, sort_keys=True)
        key_str = f"{url}:{sorted_params}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @lru_cache(maxsize=128)
    def search_movie(self, query: str, year: Optional[str] = None, language: str = "zh-CN") -> Dict:
        """
        搜索电影（带缓存）
        
        Args:
            query: 搜索关键词
            year: 年份（可选）
            language: 语言
        """
        try:
            url = f"{TMDB_BASE_URL}/search/movie"
            params = {
                "api_key": TMDB_API_KEY,
                "query": query,
                "language": language
            }
            if year:
                params["year"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"TMDB缓存: 搜索电影 '{query}' (年份={year})")
            return response.json()
        except Exception as e:
            logger.error(f"TMDB搜索失败: {e}")
            return {"results": []}
    
    @lru_cache(maxsize=128)
    def search_tv(self, query: str, year: Optional[str] = None, language: str = "zh-CN") -> Dict:
        """
        搜索剧集（带缓存）
        
        Args:
            query: 搜索关键词
            year: 首播年份（可选）
            language: 语言
        """
        try:
            url = f"{TMDB_BASE_URL}/search/tv"
            params = {
                "api_key": TMDB_API_KEY,
                "query": query,
                "language": language
            }
            if year:
                params["first_air_date_year"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"TMDB缓存: 搜索剧集 '{query}' (年份={year})")
            return response.json()
        except Exception as e:
            logger.error(f"TMDB搜索失败: {e}")
            return {"results": []}
    
    @lru_cache(maxsize=256)
    def get_details(self, media_type: str, media_id: int, language: str = "zh-CN") -> Dict:
        """
        获取媒体详情（带缓存）
        
        Args:
            media_type: 媒体类型 (movie 或 tv)
            media_id: TMDB ID
            language: 语言
        """
        try:
            url = f"{TMDB_BASE_URL}/{media_type}/{media_id}"
            params = {
                "api_key": TMDB_API_KEY,
                "language": language
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"TMDB缓存: 获取详情 {media_type}/{media_id}")
            return response.json()
        except Exception as e:
            logger.error(f"TMDB获取详情失败: {e}")
            return {}
    
    @lru_cache(maxsize=128)
    def get_images(self, media_type: str, media_id: int) -> Dict:
        """
        获取媒体图片（带缓存）
        
        Args:
            media_type: 媒体类型 (movie 或 tv)
            media_id: TMDB ID
        """
        try:
            url = f"{TMDB_BASE_URL}/{media_type}/{media_id}/images"
            params = {
                "api_key": TMDB_API_KEY,
                "include_image_language": "zh,en,null"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            logger.debug(f"TMDB缓存: 获取图片 {media_type}/{media_id}")
            return response.json()
        except Exception as e:
            logger.error(f"TMDB获取图片失败: {e}")
            return {"posters": [], "backdrops": []}
    
    def clear_cache(self):
        """清空缓存"""
        self.search_movie.cache_clear()
        self.search_tv.cache_clear()
        self.get_details.cache_clear()
        self.get_images.cache_clear()
        logger.info("✅ TMDB缓存已清空")
    
    def get_cache_info(self) -> Dict:
        """获取缓存统计"""
        return {
            "search_movie": self.search_movie.cache_info()._asdict(),
            "search_tv": self.search_tv.cache_info()._asdict(),
            "get_details": self.get_details.cache_info()._asdict(),
            "get_images": self.get_images.cache_info()._asdict(),
        }


# 全局单例
tmdb_cache = TMDBCache()

