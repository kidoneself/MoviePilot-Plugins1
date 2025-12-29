#!/usr/bin/env python3
"""
列出数据库中的 mapping 记录
"""
import sys
import os

# 添加backend路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import CustomNameMapping

# 数据库配置
DATABASE_URL = "mysql+pymysql://root:e0237e873f08ad0b@101.35.224.59:3306/file_link_monitor_v2?charset=utf8mb4"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def list_mappings(search_keyword=None, limit=20):
    """列出 mapping 记录"""
    db = SessionLocal()
    try:
        query = db.query(CustomNameMapping)
        
        # 如果有搜索关键词，模糊搜索
        if search_keyword:
            query = query.filter(
                CustomNameMapping.original_name.like(f'%{search_keyword}%')
            )
        
        # 只显示有 category 的记录
        query = query.filter(CustomNameMapping.category.isnot(None))
        
        mappings = query.limit(limit).all()
        
        print(f"找到 {len(mappings)} 条记录（最多显示{limit}条）:")
        print("="*80)
        
        for i, m in enumerate(mappings, 1):
            print(f"\n{i}. {m.original_name}")
            print(f"   ID: {m.id}")
            print(f"   分类: {m.category}")
            print(f"   迅雷名称: {m.xunlei_name or '(无)'}")
            print(f"   夸克名称: {m.quark_name or '(无)'}")
            print(f"   百度名称: {m.baidu_name or '(无)'}")
            if m.xunlei_link:
                print(f"   迅雷链接: {m.xunlei_link[:60]}...")
        
        print("\n" + "="*80)
        
    finally:
        db.close()


if __name__ == '__main__':
    import sys
    
    # 支持命令行参数搜索
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        print(f"搜索关键词: {keyword}\n")
        list_mappings(keyword, limit=50)
    else:
        print("显示前20条记录（有 category 的）\n")
        list_mappings(limit=20)
        print("\n💡 提示: 使用 python3 docs/list_mappings.py 关键词  来搜索")

