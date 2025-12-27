-- 用户请求资源记录表
CREATE TABLE IF NOT EXISTS media_requests (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    tmdb_id       INT                                   NOT NULL COMMENT 'TMDB媒体ID',
    media_type    VARCHAR(20)                           NOT NULL COMMENT '媒体类型: movie/tv',
    title         VARCHAR(255)                          NOT NULL COMMENT '标题',
    year          VARCHAR(10)                           NULL COMMENT '年份',
    poster_url    VARCHAR(500)                          NULL COMMENT '海报URL',
    request_count INT         DEFAULT 1                 NULL COMMENT '请求次数',
    status        VARCHAR(20) DEFAULT 'pending'         NULL COMMENT '状态: pending/completed',
    created_at    DATETIME    DEFAULT CURRENT_TIMESTAMP NULL COMMENT '首次请求时间',
    updated_at    DATETIME    DEFAULT CURRENT_TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后请求时间',
    CONSTRAINT uk_tmdb UNIQUE (tmdb_id, media_type)
) COMMENT '用户请求资源记录';

-- 创建索引
CREATE INDEX idx_created_at ON media_requests (created_at);
CREATE INDEX idx_request_count ON media_requests (request_count);
CREATE INDEX idx_status ON media_requests (status);

