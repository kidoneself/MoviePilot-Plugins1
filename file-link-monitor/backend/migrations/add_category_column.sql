-- 添加category字段到custom_name_mapping表
ALTER TABLE custom_name_mapping 
ADD COLUMN category VARCHAR(100) COMMENT '二级分类：电影/国产电影';
