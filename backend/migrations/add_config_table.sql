-- 配置表（用于存储模板等配置）
CREATE TABLE IF NOT EXISTS `goofish_config` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
  `config_value` TEXT COMMENT '配置值',
  `config_type` VARCHAR(50) COMMENT '配置类型',
  `description` VARCHAR(500) COMMENT '描述',
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_config_key` (`config_key`),
  INDEX `idx_config_type` (`config_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置表';

-- 插入默认模板数据
INSERT INTO `goofish_config` (`config_key`, `config_value`, `config_type`, `description`) VALUES
-- 通用内容模板
('template.content.default', '✅4K超清画质\n✅百度+夸克+迅雷三网盘\n✅中英双字幕\n✅支持在线观看/本地下载/投屏\n本店24小时自动发货\n自动免拼，下单即发，无需咨询\n\n【温馨提示】\n① 拍"2人小刀"时，点上方【还差1人刀成，直接刀成无需等待】按钮，自动拼单秒发货\n② 在线看高级别画质需要会员，拍下即默认遵守网盘规则，无会员可下载后观看原画质\n\n[送花]', 'template', '商品内容模板（通用）'),

-- 完结标题模板
('template.title.completed.1', '《{name}》包完结 4K+1080p 中英双字 可投屏', 'template', '完结标题模板1'),
('template.title.completed.2', '《{name}》2025 包完结 4K+1080p 中英双字 可投屏', 'template', '完结标题模板2'),
('template.title.completed.3', '全集《{name}》真4K超清！全集 大结局，包超前点映！', 'template', '完结标题模板3'),
('template.title.completed.4', '《{name}》完结！4K HDR 杜比+原盘 百度网盘+夸克网盘', 'template', '完结标题模板4'),

-- 更新中标题模板
('template.title.updating.1', '《{name}》更新中｜实时更新｜包抢先看', 'template', '更新中标题模板1'),
('template.title.updating.2', '秒发:《{name}》【4K/1080p】【HDR+SDR】【杜比视界】', 'template', '更新中标题模板2'),
('template.title.updating.3', '《{name}》2025 更新中 4K+1080p 中英双字 可投屏', 'template', '更新中标题模板3'),
('template.title.updating.4', '更新中《{name}》真4K超清！包超前点映！实时更新', 'template', '更新中标题模板4')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`);

