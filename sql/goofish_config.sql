create table goofish_config
(
    id           bigint auto_increment
        primary key,
    config_key   varchar(100) not null,
    config_type  varchar(50)  null,
    config_value text         null,
    create_time  datetime(6)  null,
    description  varchar(500) null,
    update_time  datetime(6)  null,
    constraint UK_fc93ah796lucs681g2s8m9nlh
        unique (config_key)
);

INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (1, 'username1', 'account', 'xy496523918875', '2025-12-24 23:47:47.285329', '闲鱼会员名1', '2025-12-24 23:47:47.285370');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (2, 'username2', 'account', 'xy904482568771', '2025-12-24 23:47:47.330046', '闲鱼会员名2', '2025-12-24 23:47:47.330088');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (3, 'product.price', 'product', '0.1', '2025-12-24 23:47:47.357723', '商品价格（单位：元）', '2025-12-25 00:10:31.527969');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (4, 'product.stock', 'product', '100', '2025-12-24 23:47:47.381449', '商品库存', '2025-12-24 23:47:47.381460');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (5, 'product.express.fee', 'product', '0', '2025-12-24 23:47:47.400344', '运费（单位：元）', '2025-12-24 23:47:47.400353');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (6, 'product.stuff.status', 'product', '100', '2025-12-24 23:47:47.420003', '新旧程度（100=全新）', '2025-12-24 23:47:47.420011');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (23, 'template.content.default', 'template', '✅4K超清画质
✅百度+夸克+迅雷三网盘
✅中英双字幕
✅支持在线观看/本地下载/投屏
本店24小时自动发货
自动免拼，下单即发，无需咨询

【温馨提示】
① 拍"2人小刀"时，点上方【还差1人刀成，直接刀成无需等待】按钮，自动拼单秒发货
② 在线看高级别画质需要会员，拍下即默认遵守网盘规则，无会员可下载后观看原画质

[送花]', '2025-12-25 00:22:56.941577', '商品内容模板（通用）', '2025-12-25 00:22:56.941620');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (24, 'template.title.completed.1', 'template', '《{name}》完结 4K+1080p 中英双字 可投屏', '2025-12-25 00:22:56.995384', '完结标题模板1', '2025-12-25 00:22:56.995396');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (25, 'template.title.completed.2', 'template', '《{name}》完结 4K+1080p 中英双字 可投屏', '2025-12-25 00:22:57.019680', '完结标题模板2', '2025-12-25 00:22:57.019690');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (26, 'template.title.completed.3', 'template', '全集《{name}》真4K超清！全集 ', '2025-12-25 00:22:57.045080', '完结标题模板3', '2025-12-25 00:22:57.045090');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (27, 'template.title.completed.4', 'template', '《{name}》完结！4K  百度+夸克+迅雷', '2025-12-25 00:22:57.064724', '完结标题模板4', '2025-12-25 00:22:57.064732');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (28, 'template.title.updating.1', 'template', '《{name}》更新中｜实时更新｜包抢先看', '2025-12-25 00:22:57.096668', '更新中标题模板1', '2025-12-25 00:22:57.096715');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (29, 'template.title.updating.2', 'template', '秒发:《{name}》【4K/1080p】更新中', '2025-12-25 00:22:57.120733', '更新中标题模板2', '2025-12-25 00:22:57.120745');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (30, 'template.title.updating.3', 'template', '《{name}》2025 更新中 4K+1080p 中英双字 可投屏', '2025-12-25 00:22:57.152950', '更新中标题模板3', '2025-12-25 00:22:57.152962');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (31, 'template.title.updating.4', 'template', '更新中《{name}》真4K超清！包超前点映！实时更新', '2025-12-25 00:22:57.223087', '更新中标题模板4', '2025-12-25 00:22:57.223097');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (32, 'goofish.app_key', '1359940027532613', '1359940027532613', null, '1359940027532613', '2025-12-25 06:34:32.000000');
INSERT INTO file_link_monitor_v2.goofish_config (id, config_key, config_type, config_value, create_time, description, update_time) VALUES (33, 'goofish.app_secret', 'P9xwVJevmTXpFAOHjr3SDUSu5UVkZkaj', 'P9xwVJevmTXpFAOHjr3SDUSu5UVkZkaj', null, 'P9xwVJevmTXpFAOHjr3SDUSu5UVkZkaj', '2025-12-25 06:34:32.000000');
