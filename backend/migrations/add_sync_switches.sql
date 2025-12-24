-- 添加同步开关字段
ALTER TABLE custom_name_mapping 
ADD COLUMN sync_to_quark TINYINT(1) DEFAULT 1 COMMENT '是否同步到夸克',
ADD COLUMN sync_to_baidu TINYINT(1) DEFAULT 1 COMMENT '是否同步到百度',
ADD COLUMN sync_to_xunlei TINYINT(1) DEFAULT 1 COMMENT '是否同步到迅雷';

-- 为已有记录设置默认值
UPDATE custom_name_mapping 
SET sync_to_quark = 1, sync_to_baidu = 1, sync_to_xunlei = 1 
WHERE sync_to_quark IS NULL OR sync_to_baidu IS NULL OR sync_to_xunlei IS NULL;
