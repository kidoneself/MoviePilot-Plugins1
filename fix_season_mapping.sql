-- 清理错误的Season和子目录映射记录
-- 执行前请备份数据库

-- 1. 删除Season目录记录
DELETE FROM custom_name_mapping
WHERE original_name REGEXP '^Season\\s+[0-9]+$';

-- 2. 删除extras等子目录记录
DELETE FROM custom_name_mapping
WHERE LOWER(original_name) IN ('extras', 'bonus', 'specials', 'featurettes', 'behind the scenes', 'deleted scenes');

-- 3. 更新老记录的xunlei_name字段（如果为空，复制quark_name）
UPDATE custom_name_mapping
SET xunlei_name = quark_name
WHERE (xunlei_name IS NULL OR xunlei_name = '')
  AND quark_name IS NOT NULL
  AND quark_name != '';

-- 4. 验证清理结果
SELECT COUNT(*) as total_mappings FROM custom_name_mapping;
SELECT original_name, quark_name, xunlei_name 
FROM custom_name_mapping 
WHERE original_name LIKE '%哑舍%' OR original_name LIKE '%大唐%'
LIMIT 5;
