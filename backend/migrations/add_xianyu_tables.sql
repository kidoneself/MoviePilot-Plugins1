-- 闲鱼管家相关表
-- 这些表与 Java 项目共享

-- 商品表
CREATE TABLE IF NOT EXISTS `goofish_product` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `product_id` BIGINT NOT NULL UNIQUE COMMENT '闲鱼商品ID',
  `title` VARCHAR(500) COMMENT '商品标题',
  `outer_id` VARCHAR(100) COMMENT '外部ID',
  `price` BIGINT COMMENT '价格（分）',
  `original_price` BIGINT COMMENT '原价（分）',
  `stock` INT COMMENT '库存',
  `sold` INT COMMENT '已售',
  `product_status` INT COMMENT '商品状态',
  `item_biz_type` INT COMMENT '商品业务类型',
  `sp_biz_type` INT COMMENT 'SP业务类型',
  `channel_cat_id` VARCHAR(100) COMMENT '类目ID',
  `district_id` INT COMMENT '地区ID',
  `stuff_status` INT COMMENT '成色',
  `express_fee` BIGINT COMMENT '运费（分）',
  `spec_type` INT COMMENT '规格类型',
  `source` INT COMMENT '来源',
  `specify_publish_time` BIGINT COMMENT '指定发布时间',
  `online_time` BIGINT COMMENT '上架时间',
  `offline_time` BIGINT COMMENT '下架时间',
  `sold_time` BIGINT COMMENT '售出时间',
  `update_time_remote` BIGINT COMMENT '远程更新时间',
  `create_time_remote` BIGINT COMMENT '远程创建时间',
  `is_selected` TINYINT(1) DEFAULT 0 COMMENT '是否选中',
  `sync_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '同步时间',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `media_id` BIGINT COMMENT '关联媒体库ID',
  INDEX `idx_product_id` (`product_id`),
  INDEX `idx_media_id` (`media_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='闲鱼商品表';

-- 配置表
CREATE TABLE IF NOT EXISTS `goofish_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
  `config_value` TEXT COMMENT '配置值',
  `config_type` VARCHAR(50) COMMENT '配置类型',
  `description` VARCHAR(500) COMMENT '描述',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  INDEX `idx_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='闲鱼配置表';

-- 定时任务表
CREATE TABLE IF NOT EXISTS `goofish_schedule_task` (
  `id` BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `task_type` VARCHAR(20) NOT NULL COMMENT '任务类型: publish/downshelf',
  `product_ids` TEXT COMMENT '商品ID列表（JSON）',
  `product_titles` TEXT COMMENT '商品标题列表（JSON）',
  `execute_time` DATETIME NOT NULL COMMENT '执行时间',
  `repeat_daily` TINYINT(1) DEFAULT 0 COMMENT '是否每日重复',
  `status` VARCHAR(20) DEFAULT 'PENDING' COMMENT '状态: PENDING/COMPLETED/FAILED/CANCELLED',
  `execute_result` TEXT COMMENT '执行结果',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `last_execute_time` DATETIME COMMENT '最后执行时间',
  INDEX `idx_status` (`status`),
  INDEX `idx_execute_time` (`execute_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='闲鱼定时任务表';

-- 插入默认配置
INSERT IGNORE INTO `goofish_config` (`config_key`, `config_value`, `description`) VALUES
('goofish.app_key', '', '闲鱼管家应用KEY'),
('goofish.app_secret', '', '闲鱼管家应用密钥'),
('username1', '', '闲鱼会员名1'),
('username2', '', '闲鱼会员名2（可选）'),
('product.title.template', '秒发商品', '商品标题模板'),
('product.content.template', '商品内容', '商品描述模板'),
('product.price', '0.1', '默认价格（元）'),
('product.express.fee', '0', '默认运费（元）'),
('product.stock', '100', '默认库存'),
('product.stuff.status', '100', '默认成色');

