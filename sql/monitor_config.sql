create table product_template
(
    id               bigint auto_increment
        primary key,
    channel_cat_id   varchar(50)  null,
    content          text         null,
    created_at       datetime(6)  not null,
    express_fee      bigint       not null,
    is_default       bit          not null,
    item_biz_type    int          not null,
    price            bigint       not null,
    publish_accounts varchar(500) null,
    sp_biz_type      int          not null,
    stock            int          not null,
    stuff_status     int          not null,
    template_name    varchar(100) not null,
    title            varchar(200) null,
    updated_at       datetime(6)  not null
);

