create table goofish_schedule_task
(
    id                bigint auto_increment
        primary key,
    create_time       datetime(6) null,
    execute_result    text        null,
    execute_time      datetime(6) not null,
    last_execute_time datetime(6) null,
    product_ids       text        null,
    product_titles    text        null,
    repeat_daily      bit         null,
    status            varchar(20) null,
    task_type         varchar(20) not null,
    update_time       datetime(6) null
);

INSERT INTO file_link_monitor_v2.goofish_schedule_task (id, create_time, execute_result, execute_time, last_execute_time, product_ids, product_titles, repeat_daily, status, task_type, update_time) VALUES (2, '2025-12-25 01:52:41.390610', 'Extra data: line 1 column 17 (char 16)', '2025-12-26 05:00:00.000000', '2025-12-25 05:00:55.007635', '1382714823673413,1381086771037765,1381307165148741,1380009142929221,1381086764074693,1380009149400646,1379985230693765', '《长安24计》更24｜实时更新｜包抢先看,《一路繁花》2025 包完结 4K+1080p 中英双字 可投屏,《长安24计》更新中｜实时更新｜包抢先看,《奇迹》2025 包完结 可投屏,《一路繁花》2025 包完结 4K+1080p 中英双字 可投屏,《奇迹》2025 包完结 可投屏,全集《双轨》真4K超清！全集  大结局，包超前点映！⛽超前。点。', true, 'FAILED', 'DOWNSHELF', '2025-12-25 21:00:26.000000');
INSERT INTO file_link_monitor_v2.goofish_schedule_task (id, create_time, execute_result, execute_time, last_execute_time, product_ids, product_titles, repeat_daily, status, task_type, update_time) VALUES (4, '2025-12-25 17:49:13.984238', '成功:7, 失败:0
商品1382714823673413上架成功
商品1381086771037765上架成功
商品1381307165148741上架成功
商品1380009142929221上架成功
商品1381086764074693上架成功
商品1380009149400646上架成功
商品1379985230693765上架成功', '2025-12-25 17:55:00.000000', '2025-12-25 17:55:54.995639', '1382714823673413,1381086771037765,1381307165148741,1380009142929221,1381086764074693,1380009149400646,1379985230693765', '《长安24计》更24｜实时更新｜包抢先看,《一路繁花》2025 包完结 4K+1080p 中英双字 可投屏,《长安24计》更新中｜实时更新｜包抢先看,《奇迹》2025 包完结 可投屏,《一路繁花》2025 包完结 4K+1080p 中英双字 可投屏,《奇迹》2025 包完结 可投屏,全集《双轨》真4K超清！全集  大结局，包超前点映！⛽超前。点。', false, 'SUCCESS', 'PUBLISH', '2025-12-25 17:55:58.187253');
