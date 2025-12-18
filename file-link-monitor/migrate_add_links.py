"""
数据库迁移脚本：为 custom_name_mapping 表添加网盘链接字段
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str):
    """添加 baidu_link 和 quark_link 字段"""
    
    print(f"开始迁移数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(custom_name_mapping)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加 baidu_link 字段
        if 'baidu_link' not in columns:
            print("添加 baidu_link 字段...")
            cursor.execute("ALTER TABLE custom_name_mapping ADD COLUMN baidu_link VARCHAR(1000)")
            print("✅ baidu_link 字段添加成功")
        else:
            print("⏭️  baidu_link 字段已存在，跳过")
        
        # 添加 quark_link 字段
        if 'quark_link' not in columns:
            print("添加 quark_link 字段...")
            cursor.execute("ALTER TABLE custom_name_mapping ADD COLUMN quark_link VARCHAR(1000)")
            print("✅ quark_link 字段添加成功")
        else:
            print("⏭️  quark_link 字段已存在，跳过")
        
        conn.commit()
        conn.close()
        
        print("\n✅ 数据库迁移完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        return False


if __name__ == "__main__":
    # 默认数据库路径
    db_path = "./data/database.db"
    
    # 如果提供了命令行参数，使用指定路径
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        sys.exit(1)
    
    # 执行迁移
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
