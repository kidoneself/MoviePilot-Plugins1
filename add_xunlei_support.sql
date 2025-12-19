-- 添加迅雷网盘支持的数据库迁移脚本
-- 在 V2 数据库上执行

-- 1. custom_name_mapping 表添加迅雷字段
ALTER TABLE `custom_name_mapping`
ADD COLUMN `xunlei_name` VARCHAR(500) NULL COMMENT '迅雷网盘显示名称' AFTER `baidu_name`,
ADD COLUMN `xunlei_link` VARCHAR(1000) NULL COMMENT '迅雷网盘分享链接' AFTER `baidu_link`;

-- 2. link_records 表添加迅雷字段
ALTER TABLE `link_records`
ADD COLUMN `xunlei_target_file` VARCHAR(1000) NULL COMMENT '迅雷网盘目标路径' AFTER `baidu_target_file`,
ADD COLUMN `xunlei_synced_at` DATETIME NULL COMMENT '迅雷网盘同步时间' AFTER `baidu_synced_at`;

-- 3. pan_cookies 表的 pan_type 已支持任意字符串，无需修改
-- 可以直接插入 pan_type='xunlei' 的记录

-- 迁移完成
-- 验证新增字段
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'file_link_monitor_v2'
  AND TABLE_NAME IN ('custom_name_mapping', 'link_records')
  AND COLUMN_NAME LIKE '%xunlei%';
