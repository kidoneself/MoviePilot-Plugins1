create table custom_name_mapping
(
    id            int auto_increment
        primary key,
    original_name varchar(500)  not null,
    custom_name   varchar(500)  not null,
    enabled       tinyint(1)    null,
    note          varchar(500)  null,
    baidu_link    varchar(1000) null,
    quark_link    varchar(1000) null,
    created_at    datetime      null,
    updated_at    datetime      null,
    constraint original_name
        unique (original_name)
);

create index idx_original_name
    on custom_name_mapping (original_name);

create table link_records
(
    id          int auto_increment
        primary key,
    source_file varchar(1000) not null,
    target_file varchar(1000) not null,
    file_size   bigint        null,
    link_method varchar(20)   null,
    status      varchar(20)   null,
    error_msg   text          null,
    created_at  datetime      null
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

