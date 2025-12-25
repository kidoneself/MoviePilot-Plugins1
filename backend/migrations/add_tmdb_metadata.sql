-- 添加 TMDb 元数据字段到 custom_name_mapping 表

-- 添加 TMDb ID
ALTER TABLE custom_name_mapping 
ADD COLUMN tmdb_id INT DEFAULT NULL COMMENT 'TMDb媒体ID';

-- 添加海报链接
ALTER TABLE custom_name_mapping 
ADD COLUMN poster_url VARCHAR(500) DEFAULT NULL COMMENT '海报链接';

-- 添加简介
ALTER TABLE custom_name_mapping 
ADD COLUMN overview TEXT DEFAULT NULL COMMENT '剧情简介';

-- 添加媒体类型
ALTER TABLE custom_name_mapping 
ADD COLUMN media_type VARCHAR(20) DEFAULT NULL COMMENT '媒体类型: movie/tv';

-- 添加索引
CREATE INDEX idx_tmdb_id ON custom_name_mapping(tmdb_id);
CREATE INDEX idx_media_type ON custom_name_mapping(media_type);

-- 查看表结构
-- DESCRIBE custom_name_mapping;

