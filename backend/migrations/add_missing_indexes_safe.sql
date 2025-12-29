-- 性能优化：安全地添加缺失的数据库索引（MySQL 5.7+）
-- 执行时间：2025-12-29
-- 说明：使用存储过程，如果索引已存在则跳过

DELIMITER $$

-- 创建索引的安全存储过程
DROP PROCEDURE IF EXISTS create_index_if_not_exists$$
CREATE PROCEDURE create_index_if_not_exists(
    IN table_name VARCHAR(128),
    IN index_name VARCHAR(128),
    IN index_columns VARCHAR(255)
)
BEGIN
    DECLARE index_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO index_exists
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
        AND table_name = table_name
        AND index_name = index_name;
    
    IF index_exists = 0 THEN
        SET @sql = CONCAT('CREATE INDEX ', index_name, ' ON ', table_name, ' (', index_columns, ')');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('✅ 创建索引: ', index_name) AS result;
    ELSE
        SELECT CONCAT('⏭ 索引已存在: ', index_name) AS result;
    END IF;
END$$

DELIMITER ;

-- 执行创建索引
-- LinkRecord表
CALL create_index_if_not_exists('link_records', 'idx_link_records_original_name', 'original_name');
CALL create_index_if_not_exists('link_records', 'idx_link_records_created_at', 'created_at');
CALL create_index_if_not_exists('link_records', 'idx_link_records_source_file', 'source_file(255)');

-- CustomNameMapping表
CALL create_index_if_not_exists('custom_name_mapping', 'idx_custom_name_mapping_category', 'category');
CALL create_index_if_not_exists('custom_name_mapping', 'idx_custom_name_mapping_enabled', 'enabled');
CALL create_index_if_not_exists('custom_name_mapping', 'idx_custom_name_mapping_completed', 'is_completed');
CALL create_index_if_not_exists('custom_name_mapping', 'idx_custom_name_mapping_tmdb_id', 'tmdb_id');

-- 清理存储过程
DROP PROCEDURE IF EXISTS create_index_if_not_exists;

-- 查看所有索引
SELECT 
    TABLE_NAME as '表名',
    INDEX_NAME as '索引名',
    COLUMN_NAME as '列名',
    INDEX_TYPE as '索引类型'
FROM information_schema.statistics
WHERE table_schema = DATABASE()
    AND TABLE_NAME IN ('link_records', 'custom_name_mapping')
    AND INDEX_NAME != 'PRIMARY'
ORDER BY TABLE_NAME, INDEX_NAME;

