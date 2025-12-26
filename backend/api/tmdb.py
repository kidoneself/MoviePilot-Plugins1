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
    根据 cat.yaml 规则进行分类（兼容 MoviePilot 逻辑）
    
    Args:
        details: 媒体详细信息
        media_type: 媒体类型 (movie 或 tv)
        
    Returns:
        分类名称（如: "电影/国产电影"）
    
    匹配规则：
    1. 按 YAML 顺序从上到下匹配，先匹配到就返回
    2. 如果规则有 genre_ids，必须匹配
    3. 如果规则有 origin_country（且不为null），必须匹配
    4. origin_country 为 null 时，使用排除法（非亚洲国家）
    5. 同时有多个条件时，必须全部满足（AND关系）
    """
    if media_type not in CATEGORIES:
        return None
    
    # 获取媒体的类型ID和来源国家
    genre_ids = [str(g['id']) for g in details.get('genres', [])]
    origin_countries = details.get('origin_country', [])
    production_countries = [c['iso_3166_1'] for c in details.get('production_countries', [])]
    
    # 合并国家信息
    all_countries = set(origin_countries + production_countries)
    
    logger.debug(f"分类匹配 - 类型:{media_type}, genre_ids:{genre_ids}, countries:{all_countries}")
    
    # 遍历分类规则（保持 YAML 顺序）
    for cat_name, cat_rule in CATEGORIES[media_type].items():
        # 获取规则（注意：不设置默认值，让未定义的返回 None）
        rule_genre_ids = cat_rule.get('genre_ids')
        rule_countries = cat_rule.get('origin_country')
        
        # 检查 genre_ids 匹配
        genre_match = True
        if rule_genre_ids:  # 规则定义了 genre_ids
            rule_genres = [g.strip() for g in str(rule_genre_ids).split(',')]
            genre_match = any(g in genre_ids for g in rule_genres)
            if not genre_match:
                continue  # genre 不匹配，跳过
        
        # 检查 origin_country 匹配
        country_match = True
        if rule_countries is None:  # YAML 中配置为 null
            # 欧美分类：排除法（不是亚洲国家，或者没有国家信息时也默认为欧美）
            asian_countries = {'CN', 'TW', 'HK', 'JP', 'KR', 'KP', 'TH', 'IN', 'SG'}
            if all_countries:  # 如果有国家信息
                country_match = not any(c in asian_countries for c in all_countries)
            else:  # 没有国家信息，默认匹配欧美（兼容 MoviePilot 逻辑）
                country_match = True
            if not country_match:
                continue  # 不是欧美，跳过
        elif rule_countries:  # YAML 中配置了具体国家
            rule_country_list = [c.strip() for c in str(rule_countries).split(',')]
            country_match = any(c in all_countries for c in rule_country_list)
            if not country_match:
                continue  # 国家不匹配，跳过
        # 如果 rule_countries 不存在或为空字符串，则不检查国家（保持 country_match=True）
        
        # 所有条件都满足，返回该分类
        logger.debug(f"  ✓ 匹配到分类: {cat_name}")
        return cat_name
    
    # 兜底分类逻辑：如果没有匹配到任何分类，根据国家和媒体类型给一个默认分类
    logger.debug(f"  ⚠️ 未匹配到任何分类，使用兜底逻辑")
    asian_countries = {'CN', 'TW', 'HK', 'JP', 'KR', 'KP', 'TH', 'IN', 'SG'}
    is_asian = any(c in asian_countries for c in all_countries) if all_countries else False
    
    # 兜底分类映射
    fallback_mapping = {
        'movie': {
            True: '电影/国产电影',      # 亚洲电影默认为国产
            False: '电影/欧美电影'       # 非亚洲电影默认为欧美
        },
        'tv': {
            True: '其他/综艺节目',       # 亚洲剧集默认为综艺（因为很多综艺节目可能没有genre_ids）
            False: '剧集/欧美剧集'       # 非亚洲剧集默认为欧美剧集
        }
    }
    
    fallback_category = fallback_mapping.get(media_type, {}).get(is_asian)
    if fallback_category:
        logger.info(f"  🔄 使用兜底分类: {fallback_category} (亚洲={is_asian})")
        return fallback_category
    
    logger.warning(f"  ✗ 无法分类，连兜底分类也失败")
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


@router.post("/tmdb/check-updates")
async def check_updates_now():
    """
    手动触发TMDB剧集更新检查
    
    用于测试和立即检查更新
    """
    try:
        from backend.services.tmdb_scheduler import get_checker
        
        checker = get_checker()
        if not checker or not checker.running:
            return {
                "success": False,
                "message": "TMDB检查器未运行"
            }
        
        # 手动触发检查
        import asyncio
        asyncio.create_task(checker._check_tv_updates())
        
        return {
            "success": True,
            "message": "已触发TMDB剧集更新检查，请稍后查看微信通知"
        }
    except Exception as e:
        logger.error(f"触发更新检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tmdb/send-unfinished-list")
async def send_unfinished_list_now():
    """
    手动推送未完结剧集列表
    
    用于测试和立即推送
    """
    try:
        from backend.services.tmdb_scheduler import get_checker
        
        checker = get_checker()
        if not checker or not checker.running:
            return {
                "success": False,
                "message": "TMDB检查器未运行"
            }
        
        # 手动触发推送
        import asyncio
        asyncio.create_task(checker._send_unfinished_shows_list())
        
        return {
            "success": True,
            "message": "已触发推送未完结剧集列表，请稍后查看微信通知"
        }
    except Exception as e:
        logger.error(f"触发推送失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tmdb/auto-fill")
async def auto_fill_missing_data(
    db: Session = Depends(get_db),
    only_missing: bool = True
):
    """
    批量补全缺失的 TMDB 信息（分类、图片、元数据）
    
    功能：
    1. 查找没有 tmdb_id 或 poster_url 或 category 的记录
    2. 根据 original_name 搜索 TMDB
    3. 自动匹配并补全信息
    
    Args:
        only_missing: 是否只处理缺失信息的记录（默认 True）
    """
    try:
        import re
        from sqlalchemy import or_
        
        # 查询需要补全的记录
        query = db.query(CustomNameMapping)
        if only_missing:
            query = query.filter(
                or_(
                    CustomNameMapping.tmdb_id.is_(None),
                    CustomNameMapping.poster_url.is_(None),
                    CustomNameMapping.category.is_(None)
                )
            )
        
        mappings = query.all()
        
        if not mappings:
            return {
                "success": True,
                "message": "没有需要补全的记录",
                "total": 0,
                "updated": 0
            }
        
        logger.info(f"开始补全 {len(mappings)} 条记录...")
        
        updated_count = 0
        failed_list = []
        
        for mapping in mappings:
            try:
                original_name = mapping.original_name
                logger.info(f"\n处理: {original_name}")
                
                # 解析标题和年份（格式：标题 (年份)）
                match = re.match(r"^(.+?)\s*\((\d{4})\)$", original_name)
                if match:
                    title = match.group(1).strip()
                    year = match.group(2)
                    logger.info(f"  解析: 标题={title}, 年份={year}")
                else:
                    # 没有年份，使用原始名称
                    title = original_name.strip()
                    year = None
                    logger.info(f"  解析: 标题={title}, 年份=无")
                
                # 如果已有 tmdb_id，直接获取详情
                if mapping.tmdb_id:
                    logger.info(f"  已有 tmdb_id={mapping.tmdb_id}，获取详情...")
                    media_type = mapping.media_type or "movie"
                    
                    # 获取详细信息
                    url = f"{TMDB_BASE_URL}/{media_type}/{mapping.tmdb_id}"
                    params = {"api_key": TMDB_API_KEY, "language": "zh-CN"}
                    response = requests.get(url, params=params, timeout=10)
                    
                    if not response.ok:
                        logger.warning(f"  ✗ 获取详情失败: {response.status_code}")
                        failed_list.append({"name": original_name, "reason": "获取TMDB详情失败"})
                        continue
                    
                    details = response.json()
                    
                    # 补全分类
                    if not mapping.category:
                        category = classify_media(details, media_type)
                        if category:
                            mapping.category = category
                            logger.info(f"  ✓ 补全分类: {category}")
                    
                    # 补全海报
                    if not mapping.poster_url:
                        poster_path = details.get('poster_path')
                        if poster_path:
                            mapping.poster_url = f"{TMDB_IMAGE_W500}{poster_path}"
                            logger.info(f"  ✓ 补全海报")
                    
                    # 补全简介
                    if not mapping.overview:
                        overview = details.get('overview')
                        if overview:
                            mapping.overview = overview
                            logger.info(f"  ✓ 补全简介")
                    
                    updated_count += 1
                    
                else:
                    # 没有 tmdb_id，需要搜索
                    if year:
                        logger.info(f"  搜索 TMDB: {title} ({year})...")
                    else:
                        logger.info(f"  搜索 TMDB: {title} (无年份)...")
                    
                    # 先尝试电影
                    search_url = f"{TMDB_BASE_URL}/search/movie"
                    search_params = {
                        "api_key": TMDB_API_KEY,
                        "query": title,
                        "language": "zh-CN"
                    }
                    # 如果有年份，添加年份筛选
                    if year:
                        search_params["year"] = year
                    
                    response = requests.get(search_url, params=search_params, timeout=10)
                    results = response.json().get("results", []) if response.ok else []
                    
                    media_type = "movie"
                    
                    # 如果电影没找到，尝试剧集
                    if not results:
                        search_url = f"{TMDB_BASE_URL}/search/tv"
                        search_params.pop("year", None)  # 移除 year 参数
                        # 如果有年份，添加剧集的年份筛选
                        if year:
                            search_params["first_air_date_year"] = year
                        response = requests.get(search_url, params=search_params, timeout=10)
                        results = response.json().get("results", []) if response.ok else []
                        media_type = "tv"
                    
                    if not results:
                        logger.warning(f"  ✗ 未找到匹配结果")
                        failed_list.append({"name": original_name, "reason": "TMDB未找到"})
                        continue
                    
                    # 使用第一个结果
                    first_result = results[0]
                    tmdb_id = first_result['id']
                    
                    logger.info(f"  找到 TMDB ID: {tmdb_id} ({media_type})")
                    
                    # 获取详细信息
                    details_url = f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}"
                    details_params = {"api_key": TMDB_API_KEY, "language": "zh-CN"}
                    details_response = requests.get(details_url, params=details_params, timeout=10)
                    
                    if not details_response.ok:
                        logger.warning(f"  ✗ 获取详情失败")
                        failed_list.append({"name": original_name, "reason": "获取详情失败"})
                        continue
                    
                    details = details_response.json()
                    
                    # 补全所有信息
                    mapping.tmdb_id = tmdb_id
                    mapping.media_type = media_type
                    
                    # 补全分类
                    if not mapping.category:
                        category = classify_media(details, media_type)
                        if category:
                            mapping.category = category
                            logger.info(f"  ✓ 补全分类: {category}")
                    
                    # 补全海报
                    poster_path = details.get('poster_path')
                    if poster_path:
                        mapping.poster_url = f"{TMDB_IMAGE_W500}{poster_path}"
                        logger.info(f"  ✓ 补全海报")
                    
                    # 补全简介
                    overview = details.get('overview')
                    if overview:
                        mapping.overview = overview
                        logger.info(f"  ✓ 补全简介")
                    
                    # 判断完结状态
                    if media_type == "movie":
                        mapping.is_completed = True
                    else:
                        status = details.get('status', '')
                        mapping.is_completed = status in ['Ended', 'Canceled']
                    
                    updated_count += 1
                    logger.info(f"  ✅ 补全成功")
                
            except Exception as e:
                logger.error(f"  ✗ 处理失败: {e}")
                failed_list.append({"name": original_name, "reason": str(e)})
                continue
        
        # 提交数据库更新
        db.commit()
        
        logger.info(f"\n补全完成: 成功 {updated_count}/{len(mappings)}")
        
        return {
            "success": True,
            "message": f"补全完成: 成功 {updated_count} 条，失败 {len(failed_list)} 条",
            "total": len(mappings),
            "updated": updated_count,
            "failed": len(failed_list),
            "failed_list": failed_list[:10] if failed_list else []  # 只返回前10个失败记录
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"批量补全失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
