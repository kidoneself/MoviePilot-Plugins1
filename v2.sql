create table custom_name_mapping
(
    id            int auto_increment
        primary key,
    original_name varchar(191)         not null,
    quark_name    varchar(500)         null,
    baidu_name    varchar(500)         null,
    quark_link    varchar(1000)        null,
    baidu_link    varchar(1000)        null,
    enabled       tinyint(1)           null,
    is_completed  tinyint(1) default 0 not null comment '是否完结',
    note          varchar(500)         null,
    created_at    datetime             null,
    updated_at    datetime             null,
    constraint original_name
        unique (original_name)
);

create index idx_original_name
    on custom_name_mapping (original_name);

create table link_records
(
    id                int auto_increment
        primary key,
    source_file       varchar(768)  not null,
    original_name     varchar(191)  null,
    file_size         bigint        null,
    quark_target_file varchar(1000) null,
    quark_synced_at   datetime      null,
    baidu_target_file varchar(1000) null,
    baidu_synced_at   datetime      null,
    created_at        datetime      null,
    updated_at        datetime      null,
    constraint source_file
        unique (source_file)
);

create table monitor_config
(
    id               int auto_increment
        primary key,
    source_path      varchar(500) not null,
    target_paths     text         not null,
    enabled          tinyint(1)   null,
    exclude_patterns text         null,
    created_at       datetime     null,
    updated_at       datetime     null
);

create table pan_cookies
(
    id              int auto_increment comment '主键ID'
        primary key,
    pan_type        varchar(20)                          not null comment '网盘类型: baidu/quark',
    cookie          text                                 not null comment 'Cookie字符串',
    is_active       tinyint(1) default 1                 null comment '是否启用',
    last_check_time datetime                             null comment '最后检查时间',
    check_status    varchar(50)                          null comment '检查状态: valid/invalid/unknown',
    check_error     text                                 null comment '检查错误信息',
    created_at      datetime   default CURRENT_TIMESTAMP null comment '创建时间',
    updated_at      datetime   default CURRENT_TIMESTAMP null on update CURRENT_TIMESTAMP comment '更新时间',
    constraint uk_pan_type
        unique (pan_type) comment '同类型网盘只保留一个Cookie'
)
    comment '网盘Cookie管理表' charset = utf8mb4;

