create table system_config
(
    id           bigint auto_increment
        primary key,
    config_key   varchar(100) null,
    config_value text         null,
    description  varchar(200) null,
    created_at   datetime     null,
    updated_at   datetime     null,
    constraint config_key
        unique (config_key)
);

INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (1, 'defaultTitle', '秒发商品', '默认商品标题', '2025-12-24 17:49:28', '2025-12-24 17:49:28');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (2, 'defaultContent', '✅4K超清
✅完整无删
✅极致高清画质
✅百度网盘+夸克网盘双渠道
✅字幕中文
✅支持在线观看/本地下载/投屏
✅24小时自动发货', '默认商品内容', '2025-12-24 17:49:28', '2025-12-24 17:49:28');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (3, 'defaultPrice', '10', '默认价格（分）', '2025-12-24 17:49:28', '2025-12-24 17:49:28');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (4, 'defaultStock', '100', '默认库存', '2025-12-24 17:49:28', '2025-12-24 17:49:28');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (5, 'publishAccounts', 'xy496523918875,xy904482568771', '发布账号', '2025-12-24 17:49:28', '2025-12-24 17:49:28');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (6, 'expressFee', '0', '运费', '2025-12-24 17:49:28', '2025-12-24 17:49:28');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (7, 'stuffStatus', '100', '成色', '2025-12-24 17:49:29', '2025-12-24 17:49:29');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (8, 'itemBizType', '2', '商品类型', '2025-12-24 17:49:29', '2025-12-24 17:49:29');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (9, 'spBizType', '99', '商品行业', '2025-12-24 17:49:29', '2025-12-24 17:49:29');
INSERT INTO file_link_monitor_v2.system_config (id, config_key, config_value, description, created_at, updated_at) VALUES (10, 'channelCatId', '0625f85b2c607412a7f7e02f36b0b49a', '类目ID', '2025-12-24 17:49:29', '2025-12-24 17:49:29');
