from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import requests
import yaml
import logging
from pathlib import Path
from pydantic import BaseModel

from backend.models import CustomNameMapping, get_session
from backend.utils.obfuscator import FolderObfuscator

router = APIRouter()
logger = logging.getLogger(__name__)

# TMDb API 配置
TMDB_API_KEY = "c7f3349aa08d38fe2e391ec5a4c0279c"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
TMDB_IMAGE_W500 = "https://image.tmdb.org/t/p/w500"  # 中等尺寸（详情页用）
TMDB_IMAGE_W300 = "https://image.tmdb.org/t/p/w300"  # 小尺寸（列表用）

# 加载分类配置
try:
    cat_file = Path(__file__).parent.parent.parent / "cat.yaml"
    with open(cat_file, 'r', encoding='utf-8') as f:
        CATEGORIES = yaml.safe_load(f)
except Exception as e:
    logger.error(f"加载分类配置失败: {e}")
    CATEGORIES = {"movie": {}, "tv": {}}


def get_db():
    """依赖注入：获取数据库会话"""
    from backend.main import db_engine
    session = get_session(db_engine)
    try:
        yield session
    finally:
        session.close()


def classify_media(details: Dict, media_type: str) -> Optional[str]:
    """
    根据 cat.yaml 规则进行分类
    
    Args:
        details: 媒体详细信息
        media_type: 媒体类型 (movie 或 tv)
        
    Returns:
        分类名称（如: "电影/国产电影"）
    """
    if media_type not in CATEGORIES:
        return None
    
    # 获取媒体的类型ID和来源国家
    genre_ids = [str(g['id']) for g in details.get('genres', [])]
    origin_countries = details.get('origin_country', [])
    production_countries = [c['iso_3166_1'] for c in details.get('production_countries', [])]
    
    # 合并国家信息
    all_countries = set(origin_countries + production_countries)
    
    # 遍历分类规则
    for cat_name, cat_rule in CATEGORIES[media_type].items():
        rule_genre_ids = cat_rule.get('genre_ids', '')
        rule_countries = cat_rule.get('origin_country', '')
        
        # 检查类型ID匹配
        genre_match = True
        if rule_genre_ids:
            rule_genres = [g.strip() for g in rule_genre_ids.split(',')]
            genre_match = any(g in genre_ids for g in rule_genres)
        
        # 检查国家匹配
        country_match = True
        if rule_countries:
            rule_country_list = [c.strip() for c in rule_countries.split(',')]
            country_match = any(c in all_countries for c in rule_country_list)
        elif rule_countries == "":  # 空字符串，不检查国家
            country_match = True
        elif rule_countries is None:  # null 表示欧美（排除法）
            # 欧美：不是亚洲国家
            asian_countries = {'CN', 'TW', 'HK', 'JP', 'KR', 'KP', 'TH', 'IN', 'SG'}
            country_match = not any(c in asian_countries for c in all_countries)
        
        # 如果都匹配，返回分类
        if genre_match and country_match:
            return cat_name
    
    return None


@router.get("/tmdb/search")
async def search_media(
    query: str,
    media_type: str = "multi",
    language: str = "zh-CN"
):
    """
    搜索影视作品
    
    Args:
        query: 搜索关键词
        media_type: 媒体类型 (movie, tv, multi)
        language: 语言
    """
    try:
        url = f"{TMDB_BASE_URL}/search/{media_type}"
        params = {
            "api_key": TMDB_API_KEY,
            "query": query,
            "language": language,
            "include_adult": False
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 处理结果
        results = []
        for item in data.get("results", [])[:10]:  # 只返回前10个
            m_type = item.get('media_type', media_type if media_type != 'multi' else 'unknown')
            
            if m_type == 'movie':
                results.append({
                    "id": item.get('id'),
                    "media_type": "movie",
                    "title": item.get('title', item.get('original_title', '')),
                    "year": item.get('release_date', '')[:4],
                    "poster_path": f"{TMDB_IMAGE_W300}{item['poster_path']}" if item.get('poster_path') else None,
                    "overview": item.get('overview', ''),
                    "vote_average": item.get('vote_average', 0)
                })
            elif m_type == 'tv':
                results.append({
                    "id": item.get('id'),
                    "media_type": "tv",
                    "title": item.get('name', item.get('original_name', '')),
                    "year": item.get('first_air_date', '')[:4],
                    "poster_path": f"{TMDB_IMAGE_W300}{item['poster_path']}" if item.get('poster_path') else None,
                    "overview": item.get('overview', ''),
                    "vote_average": item.get('vote_average', 0)
                })
        
        return {
            "success": True,
            "data": results
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tmdb/details/{media_type}/{media_id}")
async def get_media_details(
    media_type: str,
    media_id: int,
    language: str = "zh-CN"
):
    """
    获取媒体详细信息
    
    Args:
        media_type: 媒体类型 (movie 或 tv)
        media_id: 媒体ID
        language: 语言
    """
    try:
        # 获取详细信息
        url = f"{TMDB_BASE_URL}/{media_type}/{media_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "language": language
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        details = response.json()
        
        # 获取图片
        images_url = f"{TMDB_BASE_URL}/{media_type}/{media_id}/images"
        images_params = {
            "api_key": TMDB_API_KEY,
            "include_image_language": "zh,en,null"
        }
        
        images_response = requests.get(images_url, params=images_params, timeout=10)
        images_data = images_response.json() if images_response.ok else {}
        
        # 处理海报和剧照（使用 w500 尺寸，加载更快）
        posters = [f"{TMDB_IMAGE_W500}{img['file_path']}" 
                  for img in images_data.get("posters", [])[:5]]
        backdrops = [f"{TMDB_IMAGE_W500}{img['file_path']}" 
                    for img in images_data.get("backdrops", [])[:5]]
        
        # 获取分类
        category = classify_media(details, media_type)
        
        # 获取基本信息
        if media_type == "movie":
            title = details.get('title', details.get('original_title', ''))
            year = details.get('release_date', '')[:4]
        else:
            title = details.get('name', details.get('original_name', ''))
            year = details.get('first_air_date', '')[:4]
        
        # 获取主图（使用 w500 尺寸）
        poster_path = details.get('poster_path')
        main_poster = f"{TMDB_IMAGE_W500}{poster_path}" if poster_path else None
        
        # 获取类型
        genres = [g['name'] for g in details.get('genres', [])]
        
        return {
            "success": True,
            "data": {
                "id": media_id,
                "media_type": media_type,
                "title": title,
                "year": year,
                "category": category,
                "main_poster": main_poster,
                "posters": posters,
                "backdrops": backdrops,
                "overview": details.get('overview', ''),
                "vote_average": details.get('vote_average', 0),
                "origin_country": details.get('origin_country', []),
                "genres": genres,
                "runtime": details.get('runtime') if media_type == 'movie' else None,
                "number_of_seasons": details.get('number_of_seasons') if media_type == 'tv' else None,
                "number_of_episodes": details.get('number_of_episodes') if media_type == 'tv' else None
            }
        }
    except Exception as e:
        logger.error(f"获取详细信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tmdb/images/{media_type}/{media_id}")
async def get_media_images(
    media_type: str,
    media_id: int
):
    """
    获取媒体图片（海报和剧照）
    
    Args:
        media_type: 媒体类型
        media_id: 媒体ID
    """
    try:
        url = f"{TMDB_BASE_URL}/{media_type}/{media_id}/images"
        params = {
            "api_key": TMDB_API_KEY,
            "include_image_language": "zh,en,null"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 获取海报和剧照
        posters = [
            {
                "url": f"{TMDB_IMAGE_BASE_URL}{img['file_path']}",
                "width": img.get('width'),
                "height": img.get('height'),
                "aspect_ratio": img.get('aspect_ratio')
            }
            for img in data.get("posters", [])[:10]
        ]
        
        backdrops = [
            {
                "url": f"{TMDB_IMAGE_BASE_URL}{img['file_path']}",
                "width": img.get('width'),
                "height": img.get('height'),
                "aspect_ratio": img.get('aspect_ratio')
            }
            for img in data.get("backdrops", [])[:10]
        ]
        
        return {
            "success": True,
            "data": {
                "posters": posters,
                "backdrops": backdrops
            }
        }
    except Exception as e:
        logger.error(f"获取图片失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tmdb/categories")
async def get_categories():
    """
    获取所有分类配置
    """
    try:
        return {
            "success": True,
            "data": CATEGORIES
        }
    except Exception as e:
        logger.error(f"获取分类配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateMappingRequest(BaseModel):
    """创建映射请求"""
    title: str
    year: str
    category: str
    media_type: str
    tmdb_id: int
    poster_url: str = None  # 海报链接
    overview: str = None    # 简介


@router.post("/tmdb/create-mapping")
async def create_mapping(
    request: CreateMappingRequest,
    db: Session = Depends(get_db)
):
    """
    从 TMDb 信息创建名称映射
    
    功能：
    1. 生成原始名称（如: "流浪地球2 (2023)"）
    2. 使用混淆器生成三网盘的混淆名称
    3. 创建 CustomNameMapping 记录
    """
    try:
        # 1. 生成原始名称
        original_name = f"{request.title} ({request.year})"
        logger.info(f"创建映射: {original_name}")
        
        # 2. 检查是否已存在
        existing = db.query(CustomNameMapping).filter_by(
            original_name=original_name
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": f"映射已存在: {original_name}"
            }
        
        # 3. 判断是否完结
        is_completed = False
        if request.media_type == "movie":
            # 电影默认完结
            is_completed = True
        else:
            # 电视剧需要查询 TMDb 状态
            try:
                details_url = f"{TMDB_BASE_URL}/tv/{request.tmdb_id}"
                details_response = requests.get(details_url, params={"api_key": TMDB_API_KEY}, timeout=10)
                if details_response.ok:
                    details_data = details_response.json()
                    status = details_data.get('status', '')
                    # Ended = 完结, Returning Series = 更新中, Canceled = 已取消
                    is_completed = status in ['Ended', 'Canceled']
                    logger.info(f"  电视剧状态: {status} -> 完结={is_completed}")
            except Exception as e:
                logger.warning(f"获取完结状态失败: {e}")
        
        # 4. 使用混淆器生成三网盘的名称
        obfuscator = FolderObfuscator()
        
        # 直接使用公共混淆方法（去年份 + 同音字替换 + 添加首字母）
        # 这个方法不检查 enabled 标志，直接返回混淆后的名称
        quark_name = obfuscator.obfuscate_with_initial(original_name)
        baidu_name = obfuscator.obfuscate_with_initial(original_name)
        xunlei_name = obfuscator.obfuscate_with_initial(original_name)
        
        logger.info(f"  原始名: {original_name}")
        logger.info(f"  夸克名: {quark_name}")
        logger.info(f"  百度名: {baidu_name}")
        logger.info(f"  迅雷名: {xunlei_name}")
        logger.info(f"  完结状态: {is_completed}")
        
        # 5. 创建映射记录
        mapping = CustomNameMapping(
            original_name=original_name,
            category=request.category,
            quark_name=quark_name,
            baidu_name=baidu_name,
            xunlei_name=xunlei_name,
            enabled=True,
            is_completed=is_completed,  # 自动判断完结状态
            sync_to_quark=True,
            sync_to_baidu=True,
            sync_to_xunlei=True,
            # TMDb 元数据
            tmdb_id=request.tmdb_id,
            poster_url=request.poster_url,
            overview=request.overview,
            media_type=request.media_type
        )
        
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        
        logger.info(f"✅ 映射创建成功: {original_name}")
        
        return {
            "success": True,
            "message": "映射创建成功",
            "data": {
                "id": mapping.id,
                "original_name": mapping.original_name,
                "category": mapping.category,
                "quark_name": mapping.quark_name,
                "baidu_name": mapping.baidu_name,
                "xunlei_name": mapping.xunlei_name
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建映射失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
