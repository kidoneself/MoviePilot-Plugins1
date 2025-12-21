#!/usr/bin/env python3
"""
数据库迁移脚本：添加category字段并从路径提取补全历史数据
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.models import init_database, get_session, CustomNameMapping, LinkRecord


def extract_category_from_path(file_path: str) -> str:
    """从路径提取分类"""
    if not file_path:
        return None
    
    # 路径格式: /media/夸克网盘/剧集/国产剧集/剧名/...
    #          [0]  [1]    [2]  [3]    [4]
    parts = Path(file_path).parts
    
    if len(parts) >= 5:
        # 一级分类/二级分类
        level1 = parts[3]  # 剧集/电影/动漫/其他
        level2 = parts[4]  # 国产剧集/欧美电影等
        return f"{level1}/{level2}"
    
    return None


def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          数据库迁移：添加category字段                          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # 1. 初始化数据库（会自动创建新字段）
    print("步骤1: 初始化数据库（创建category字段）...")
    engine = init_database()
    print("✅ 数据库初始化完成")
    print()
    
    # 2. 补全历史数据
    print("步骤2: 从路径提取分类，补全历史数据...")
    db = get_session(engine)
    
    try:
        # 获取所有映射记录
        mappings = db.query(CustomNameMapping).all()
        print(f"找到 {len(mappings)} 条映射记录")
        print()
        
        updated_count = 0
        failed_count = 0
        
        for mapping in mappings:
            # 如果已有category，跳过
            if mapping.category:
                print(f"  [{mapping.original_name}] 已有分类: {mapping.category}")
                continue
            
            # 从硬链接记录中查找对应的路径
            # 通过名称模糊匹配
            link_record = db.query(LinkRecord).filter(
                LinkRecord.source_file.like(f'%{mapping.original_name}%')
            ).first()
            
            if link_record:
                # 尝试从夸克或百度路径提取分类
                category = None
                
                if link_record.quark_target_file:
                    category = extract_category_from_path(link_record.quark_target_file)
                
                if not category and link_record.baidu_target_file:
                    category = extract_category_from_path(link_record.baidu_target_file)
                
                if not category and link_record.xunlei_target_file:
                    category = extract_category_from_path(link_record.xunlei_target_file)
                
                if category:
                    mapping.category = category
                    updated_count += 1
                    print(f"  ✅ [{mapping.original_name}] → {category}")
                else:
                    failed_count += 1
                    print(f"  ⚠️  [{mapping.original_name}] 无法提取分类")
            else:
                failed_count += 1
                print(f"  ⚠️  [{mapping.original_name}] 未找到对应的硬链接记录")
        
        # 提交更改
        db.commit()
        print()
        print("="*60)
        print(f"迁移完成！")
        print(f"  成功更新: {updated_count} 条")
        print(f"  无法提取: {failed_count} 条")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
