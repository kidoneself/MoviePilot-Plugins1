#!/usr/bin/env python3
"""
添加category字段到数据库
"""
import pymysql

# 数据库配置
db_config = {
    'host': '10.10.10.17',
    'port': 3306,
    'user': 'root',
    'password': 'MyStrongPass123',
    'database': 'file_link_monitor_v2',
    'charset': 'utf8mb4'
}

print("连接数据库...")
conn = pymysql.connect(**db_config)
cursor = conn.cursor()

try:
    print("添加category字段...")
    cursor.execute("""
        ALTER TABLE custom_name_mapping 
        ADD COLUMN category VARCHAR(100) COMMENT '二级分类：电影/国产电影'
    """)
    conn.commit()
    print("✅ 字段添加成功！")
except pymysql.err.OperationalError as e:
    if '1060' in str(e):  # Duplicate column
        print("⚠️  字段已存在，跳过")
    else:
        raise
finally:
    cursor.close()
    conn.close()
