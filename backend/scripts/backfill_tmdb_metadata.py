#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量补全历史数据的 TMDb 元数据
自动搜索并匹配 TMDb 信息
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import CustomNameMapping
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# TMDb 配置
TMDB_API_KEY = "c7f3349aa08d38fe2e391ec5a4c0279c"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w300"  # 使用小尺寸，加载更快

# 数据库连接
DB_URL = "mysql+pymysql://root:e0237e873f08ad0b@101.35.224.59:3306/file_link_monitor_v2?charset=utf8mb4"


def search_tmdb(query: str, media_type: str = "multi"):
    """搜索 TMDb"""
    url = f"{TMDB_BASE_URL}/search/{media_type}"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "zh-CN",
        "include_adult": False
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return []


def get_tmdb_details(media_id: int, media_type: str):
    """获取 TMDb 详细信息"""
    url = f"{TMDB_BASE_URL}/{media_type}/{media_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "zh-CN"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"获取详情失败: {e}")
        return None


def extract_title_year(original_name: str):
    """从原始名称中提取标题和年份"""
    import re
    
    # 匹配 "剧名 (年份)" 格式
    match = re.match(r'^(.+?)\s*\((\d{4})\)\s*$', original_name)
    if match:
        return match.group(1).strip(), match.group(2)
    
    # 没有年份，返回全名
    return original_name.strip(), None


def match_result(results, title, year):
    """匹配最佳结果"""
    if not results:
        return None
    
    # 优先匹配年份
    if year:
        for item in results:
            item_year = None
            if item.get('media_type') == 'movie' or 'release_date' in item:
                item_year = item.get('release_date', '')[:4]
            elif item.get('media_type') == 'tv' or 'first_air_date' in item:
                item_year = item.get('first_air_date', '')[:4]
            
            if item_year == year:
                return item
    
    # 没有年份或年份不匹配，返回第一个
    return results[0]


def backfill_metadata(dry_run=True, limit=None):
    """
    批量补全元数据
    
    Args:
        dry_run: 如果为 True，只预览不实际更新
        limit: 限制处理数量，None 表示全部
    """
    engine = create_engine(DB_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 查询所有没有 tmdb_id 的记录
        query = session.query(CustomNameMapping).filter(
            CustomNameMapping.tmdb_id.is_(None)
        )
        
        if limit:
            query = query.limit(limit)
        
        mappings = query.all()
        
        logger.info(f"找到 {len(mappings)} 条需要补全的记录")
        
        if dry_run:
            logger.info("=" * 60)
            logger.info("【预览模式】不会实际更新数据库")
            logger.info("=" * 60)
        
        success_count = 0
        failed_count = 0
        
        for idx, mapping in enumerate(mappings, 1):
            original_name = mapping.original_name
            logger.info(f"\n[{idx}/{len(mappings)}] 处理: {original_name}")
            
            # 提取标题和年份
            title, year = extract_title_year(original_name)
            logger.info(f"  提取信息: 标题='{title}', 年份={year}")
            
            # 搜索 TMDb
            results = search_tmdb(title)
            
            if not results:
                logger.warning(f"  ❌ 未找到匹配结果")
                failed_count += 1
                continue
            
            logger.info(f"  找到 {len(results)} 个结果")
            
            # 匹配最佳结果
            best_match = match_result(results, title, year)
            
            if not best_match:
                logger.warning(f"  ❌ 无法匹配结果")
                failed_count += 1
                continue
            
            # 确定媒体类型
            media_type = best_match.get('media_type')
            if not media_type:
                # 根据字段判断
                if 'title' in best_match or 'release_date' in best_match:
                    media_type = 'movie'
                elif 'name' in best_match or 'first_air_date' in best_match:
                    media_type = 'tv'
            
            # 提取信息
            tmdb_id = best_match.get('id')
            
            if media_type == 'movie':
                matched_title = best_match.get('title', '')
                matched_year = best_match.get('release_date', '')[:4]
            else:
                matched_title = best_match.get('name', '')
                matched_year = best_match.get('first_air_date', '')[:4]
            
            poster_path = best_match.get('poster_path')
            poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
            overview = best_match.get('overview', '')
            
            logger.info(f"  ✅ 匹配到: {matched_title} ({matched_year})")
            logger.info(f"     TMDb ID: {tmdb_id}")
            logger.info(f"     类型: {media_type}")
            logger.info(f"     海报: {'有' if poster_url else '无'}")
            logger.info(f"     简介: {overview[:50] if overview else '无'}...")
            
            # 获取详细信息（获取完结状态）
            is_completed = None
            if media_type == 'tv':
                details = get_tmdb_details(tmdb_id, media_type)
                if details:
                    status = details.get('status', '')
                    is_completed = status in ['Ended', 'Canceled']
                    logger.info(f"     状态: {status} -> 完结={is_completed}")
            elif media_type == 'movie':
                is_completed = True
            
            # 更新数据库
            if not dry_run:
                mapping.tmdb_id = tmdb_id
                mapping.poster_url = poster_url
                mapping.overview = overview
                mapping.media_type = media_type
                if is_completed is not None:
                    mapping.is_completed = is_completed
                
                session.commit()
                logger.info(f"  💾 已更新数据库")
            else:
                logger.info(f"  [预览] 将更新: tmdb_id={tmdb_id}, 完结={is_completed}")
            
            success_count += 1
            
            # 避免 API 限流
            time.sleep(0.3)
        
        logger.info("\n" + "=" * 60)
        logger.info(f"处理完成: 成功 {success_count}, 失败 {failed_count}")
        logger.info("=" * 60)
        
        if dry_run:
            logger.info("\n这是预览模式，没有实际更新。")
            logger.info("如需实际更新，运行: python3 backend/scripts/backfill_tmdb_metadata.py --apply")
        
    finally:
        session.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量补全 TMDb 元数据')
    parser.add_argument('--apply', action='store_true', help='实际执行更新（默认只预览）')
    parser.add_argument('--limit', type=int, help='限制处理数量')
    
    args = parser.parse_args()
    
    dry_run = not args.apply
    limit = args.limit
    
    logger.info("=" * 60)
    logger.info("TMDb 元数据批量补全工具")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("⚠️  当前为预览模式，不会更新数据库")
        logger.info("⚠️  如需实际更新，请加 --apply 参数")
    else:
        logger.info("🚀 实际更新模式，将修改数据库")
    
    if limit:
        logger.info(f"📊 限制处理数量: {limit} 条")
    
    logger.info("")
    
    # 确认
    if not dry_run:
        print("确认要更新数据库吗？(yes/no): ", end='')
        confirm = input().strip().lower()
        if confirm != 'yes':
            logger.info("已取消")
            return
    
    backfill_metadata(dry_run=dry_run, limit=limit)


if __name__ == "__main__":
    main()

