-- 跨数据库迁移脚本: 从 V1 数据库迁移到 V2 数据库
-- 请先修改下面的数据库名称
-- 使用前请先备份数据库！

SET @v1_db = 'file_link_monitor_v1';  -- 修改为你的V1数据库名
SET @v2_db = 'file_link_monitor_v2';  -- 修改为你的V2数据库名

-- 确保V2数据库已创建表结构（使用v2.sql创建）

-- ========================================
-- 1. 迁移 custom_name_mapping 表
-- ========================================

-- 从V1迁移数据到V2
INSERT INTO file_link_monitor_v2.custom_name_mapping 
    (original_name, quark_name, baidu_name, quark_link, baidu_link, enabled, note, created_at, updated_at)
SELECT 
    original_name,
    custom_name AS quark_name,
    custom_name AS baidu_name,
    quark_link,
    baidu_link,
    enabled,
    note,
    created_at,
    updated_at
FROM file_link_monitor_v1.custom_name_mapping;


-- ========================================
-- 2. 迁移 link_records 表
-- ========================================

-- 从V1迁移数据到V2
INSERT INTO file_link_monitor_v2.link_records 
    (source_file, file_size, quark_target_file, quark_synced_at, created_at)
SELECT 
    source_file,
    file_size,
    target_file AS quark_target_file,  -- 假设原来的target_file是夸克路径
    created_at AS quark_synced_at,
    created_at
FROM file_link_monitor_v1.link_records;


-- ========================================
-- 3. 迁移 monitor_config 表（如果需要）
-- ========================================

INSERT INTO file_link_monitor_v2.monitor_config 
    (source_path, target_paths, enabled, exclude_patterns, created_at, updated_at)
SELECT 
    source_path,
    target_paths,
    enabled,
    exclude_patterns,
    created_at,
    updated_at
FROM file_link_monitor_v1.monitor_config;


-- ========================================
-- 迁移完成
-- ========================================
-- 请验证V2数据库中的数据后再使用
