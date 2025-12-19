-- 数据库迁移脚本: V1 -> V2
-- 使用前请先备份数据库！

-- ========================================
-- 1. 迁移 custom_name_mapping 表
-- ========================================

-- 添加新字段
ALTER TABLE `custom_name_mapping` 
ADD COLUMN `quark_name` varchar(500) NULL AFTER `original_name`,
ADD COLUMN `baidu_name` varchar(500) NULL AFTER `quark_name`,
ADD COLUMN `is_completed` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否完结' AFTER `enabled`;

-- 将旧的 custom_name 数据迁移到 baidu_name 和 quark_name
UPDATE `custom_name_mapping` 
SET `baidu_name` = `custom_name`,
    `quark_name` = `custom_name`;

-- 删除旧字段
ALTER TABLE `custom_name_mapping` 
DROP COLUMN `custom_name`;

-- 修改 original_name 字段长度
ALTER TABLE `custom_name_mapping` 
MODIFY COLUMN `original_name` varchar(191) NOT NULL;


-- ========================================
-- 2. 迁移 link_records 表
-- ========================================

-- 添加新字段
ALTER TABLE `link_records` 
ADD COLUMN `original_name` varchar(191) NULL AFTER `source_file`,
ADD COLUMN `quark_target_file` varchar(1000) NULL AFTER `file_size`,
ADD COLUMN `quark_synced_at` datetime NULL AFTER `quark_target_file`,
ADD COLUMN `baidu_target_file` varchar(1000) NULL AFTER `quark_synced_at`,
ADD COLUMN `baidu_synced_at` datetime NULL AFTER `baidu_target_file`,
ADD COLUMN `updated_at` datetime NULL AFTER `created_at`;

-- 迁移旧的 target_file 到新字段（根据实际情况调整）
-- 假设原来的 target_file 是夸克路径
UPDATE `link_records` 
SET `quark_target_file` = `target_file`,
    `quark_synced_at` = `created_at`
WHERE `target_file` IS NOT NULL;

-- 删除旧字段
ALTER TABLE `link_records` 
DROP COLUMN `target_file`,
DROP COLUMN `link_method`,
DROP COLUMN `status`,
DROP COLUMN `error_msg`;

-- 修改 source_file 字段长度并添加唯一索引
ALTER TABLE `link_records` 
MODIFY COLUMN `source_file` varchar(768) NOT NULL;

ALTER TABLE `link_records` 
ADD CONSTRAINT `source_file` UNIQUE (`source_file`);


-- ========================================
-- 3. 创建新表 pan_cookies
-- ========================================

CREATE TABLE IF NOT EXISTS `pan_cookies` (
    `id` int AUTO_INCREMENT COMMENT '主键ID' PRIMARY KEY,
    `pan_type` varchar(20) NOT NULL COMMENT '网盘类型: baidu/quark',
    `cookie` text NOT NULL COMMENT 'Cookie字符串',
    `is_active` tinyint(1) DEFAULT 1 NULL COMMENT '是否启用',
    `last_check_time` datetime NULL COMMENT '最后检查时间',
    `check_status` varchar(50) NULL COMMENT '检查状态: valid/invalid/unknown',
    `check_error` text NULL COMMENT '检查错误信息',
    `created_at` datetime DEFAULT CURRENT_TIMESTAMP NULL COMMENT '创建时间',
    `updated_at` datetime DEFAULT CURRENT_TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT `uk_pan_type` UNIQUE (`pan_type`) COMMENT '同类型网盘只保留一个Cookie'
) COMMENT '网盘Cookie管理表' CHARSET=utf8mb4;


-- ========================================
-- 迁移完成
-- ========================================
-- 请验证数据迁移结果后再部署到生产环境
