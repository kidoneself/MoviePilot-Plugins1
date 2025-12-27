# 用户资源请求功能使用说明

## 功能概述

"用户资源请求"功能允许管理员查看和管理用户提交的媒体资源请求。该功能可以帮助你：

- 📊 统计用户最想要的资源
- 🔥 按请求热度排序，优先处理热门资源
- ✅ 标记已完成的请求
- 🗑️ 删除无效请求

## 功能特性

### 1. 请求列表
- **状态筛选**：待处理 / 已完成 / 全部
- **请求热度**：显示每个资源被请求的次数
- **海报展示**：显示媒体海报图片
- **时间跟踪**：记录首次请求和最后请求时间
- **分页功能**：支持自定义每页显示数量

### 2. 操作功能
- **查看TMDB**：直接跳转到TMDB官网查看详情
- **标记完成**：资源已补充后标记为完成状态
- **删除请求**：删除无效或重复的请求

### 3. 统计信息
- 显示总请求数
- 显示待处理请求数
- 按请求次数和更新时间排序

## 数据库表结构

```sql
CREATE TABLE media_requests (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    tmdb_id       INT NOT NULL COMMENT 'TMDB媒体ID',
    media_type    VARCHAR(20) NOT NULL COMMENT '媒体类型: movie/tv',
    title         VARCHAR(255) NOT NULL COMMENT '标题',
    year          VARCHAR(10) NULL COMMENT '年份',
    poster_url    VARCHAR(500) NULL COMMENT '海报URL',
    request_count INT DEFAULT 1 NULL COMMENT '请求次数',
    status        VARCHAR(20) DEFAULT 'pending' NULL COMMENT '状态: pending/completed',
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP NULL COMMENT '首次请求时间',
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '最后请求时间',
    CONSTRAINT uk_tmdb UNIQUE (tmdb_id, media_type)
) COMMENT '用户请求资源记录';
```

## API 接口

### 1. 获取请求列表
```
GET /api/media-requests?status=pending&page=1&page_size=20
```

**参数：**
- `status`: 状态筛选 (pending/completed/all)
- `page`: 页码
- `page_size`: 每页数量

**返回：**
```json
{
  "success": true,
  "data": [...],
  "total": 100,
  "pending_count": 50,
  "page": 1,
  "page_size": 20
}
```

### 2. 创建或增加请求
```
POST /api/media-requests
```

**请求体：**
```json
{
  "tmdb_id": 123,
  "media_type": "movie",
  "title": "测试电影",
  "year": "2024",
  "poster_url": "https://..."
}
```

**说明：**
- 如果已存在相同的 tmdb_id + media_type，则请求次数 +1
- 否则创建新请求记录

### 3. 更新请求状态
```
PUT /api/media-requests/{request_id}
```

**请求体：**
```json
{
  "status": "completed"
}
```

### 4. 删除请求
```
DELETE /api/media-requests/{request_id}
```

### 5. 获取统计信息
```
GET /api/media-requests/stats
```

**返回：**
```json
{
  "success": true,
  "data": {
    "total": 100,
    "pending": 50,
    "completed": 50,
    "hot_requests": [...]
  }
}
```

## 使用流程

### 管理员端（file-link-monitor）

1. **访问页面**
   - 打开系统：http://localhost:8080
   - 点击左侧菜单"用户请求"

2. **查看请求列表**
   - 默认显示"待处理"状态的请求
   - 按请求热度和更新时间排序
   - 查看海报、标题、请求次数等信息

3. **处理请求**
   - 点击"查看TMDB"了解资源详情
   - 补充资源后，点击"标记完成"
   - 无效请求可以点击"删除"

4. **筛选和分页**
   - 使用顶部按钮切换状态筛选
   - 使用底部分页控件浏览更多记录
   - 可调整每页显示数量（10/20/50/100）

### 用户端（mobile-media-search）

用户通过移动端搜索页面提交资源请求：

1. 搜索想要的影视资源
2. 如果资源不存在，点击"请求资源"按钮
3. 系统自动提交请求到 media_requests 表
4. 重复请求会增加 request_count 计数

## 前端页面位置

- **路由路径**：`/media-requests`
- **组件文件**：`frontend-vue/src/views/MediaRequests.vue`
- **菜单位置**：左侧导航栏 - "用户请求"（铃铛图标）

## 注意事项

1. **唯一性约束**
   - 同一个 tmdb_id + media_type 组合在表中是唯一的
   - 重复请求会自动增加 request_count 而不是创建新记录

2. **请求热度**
   - request_count > 10：显示红色标签（高热度）
   - request_count > 5：显示橙色标签（中热度）
   - request_count ≤ 5：显示灰色标签（低热度）

3. **数据同步**
   - 该表数据来自 mobile-media-search 项目
   - 两个项目共享同一个数据库

4. **海报图片**
   - 使用TMDB的图片链接
   - 支持懒加载和错误占位

## 后续扩展建议

1. **通知功能**
   - 请求完成后自动通知用户
   - 集成企业微信通知

2. **批量操作**
   - 批量标记完成
   - 批量删除

3. **导出功能**
   - 导出请求列表为Excel
   - 导出统计报表

4. **优先级管理**
   - 手动设置请求优先级
   - VIP用户请求优先处理

5. **自动匹配**
   - 新资源上架时自动匹配待处理请求
   - 自动标记为完成并通知用户

