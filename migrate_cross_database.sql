-- 跨数据库迁移脚本: 从 V1 数据库迁移到 V2 数据库
-- 请先修改下面的数据库名称
-- 使用前请先备份数据库！

SET @v1_db = 'file_link_monitor';     -- V1数据库名
SET @v2_db = 'file_link_monitor_v2';  -- V2数据库名

-- 确保V2数据库已创建表结构（使用v2.sql创建）

-- ========================================
-- 1. 迁移 custom_name_mapping 表
-- ========================================

-- 清空V2表数据
TRUNCATE TABLE file_link_monitor_v2.custom_name_mapping;

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
FROM file_link_monitor.custom_name_mapping
WHERE original_name NOT LIKE 'Season%'  -- 过滤掉异常的Season数据
  AND original_name != '';


-- ========================================
-- 2. 迁移 link_records 表
-- ========================================

-- 清空V2表数据
TRUNCATE TABLE file_link_monitor_v2.link_records;

-- 从V1迁移数据到V2（合并夸克和百度记录）
INSERT INTO file_link_monitor_v2.link_records 
    (source_file, original_name, file_size, quark_target_file, quark_synced_at, baidu_target_file, baidu_synced_at, created_at, updated_at)
SELECT 
    source_file,
    -- 从文件名中提取剧名
    -- 例如：A Paw Patrol Christmas (2025) - 1080p.mkv → A Paw Patrol Christmas (2025)
    -- 步骤：1.取文件名 2.去扩展名 3.去掉" - "后面的内容
    TRIM(SUBSTRING_INDEX(
        SUBSTRING_INDEX(SUBSTRING_INDEX(source_file, '/', -1), '.', 1),  -- 1.取文件名并去扩展名
        ' - ',  -- 2.在" - "处分割，取前面部分
        1
    )) as original_name,
    MAX(file_size) as file_size,
    MAX(CASE WHEN target_file LIKE '%夸克%' THEN target_file END) as quark_target_file,
    MAX(CASE WHEN target_file LIKE '%夸克%' THEN created_at END) as quark_synced_at,
    MAX(CASE WHEN target_file LIKE '%网盘%' OR target_file NOT LIKE '%夸克%' THEN target_file END) as baidu_target_file,
    MAX(CASE WHEN target_file LIKE '%网盘%' OR target_file NOT LIKE '%夸克%' THEN created_at END) as baidu_synced_at,
    MIN(created_at) as created_at,
    MAX(created_at) as updated_at
FROM file_link_monitor.link_records
GROUP BY source_file;


-- ========================================
-- 3. 迁移 monitor_config 表（如果需要）
-- ========================================

-- 清空V2表数据
TRUNCATE TABLE file_link_monitor_v2.monitor_config;

INSERT INTO file_link_monitor_v2.monitor_config 
    (source_path, target_paths, enabled, exclude_patterns, created_at, updated_at)
SELECT 
    source_path,
    target_paths,
    enabled,
    exclude_patterns,
    created_at,
    updated_at
FROM file_link_monitor.monitor_config;


-- ========================================
-- 迁移完成
-- ========================================
-- 请验证V2数据库中的数据后再使用
