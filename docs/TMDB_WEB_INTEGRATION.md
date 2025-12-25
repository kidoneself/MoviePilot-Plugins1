# TMDb 搜索功能 - Web 集成说明

## 📝 概述

TMDb 搜索功能已成功集成到 Web 系统中，提供影视作品搜索、详情查看和自动分类功能。

## 🎯 功能特性

### 1. 搜索功能
- ✅ 支持电影、电视剧、全部类型搜索
- ✅ 中文搜索支持
- ✅ 实时搜索结果展示
- ✅ 海报预览

### 2. 详情展示
- ✅ 名称（年份）
- ✅ 自动二级分类（根据 cat.yaml）
- ✅ 主图（海报）链接
- ✅ 多张海报图片（最多5张）
- ✅ 多张剧照图片（最多5张）
- ✅ 简介、评分、国家、类型等详细信息

### 3. 图片管理
- ✅ 图片预览（点击放大）
- ✅ 一键复制图片链接
- ✅ 高清原图（TMDb CDN）

## 📂 文件结构

```
backend/
  api/
    tmdb.py                 # 后端 API 接口

frontend-vue/
  src/
    views/
      TmdbSearch.vue        # 前端搜索页面
    api/
      index.js              # API 接口定义（已添加 TMDb 方法）
    router/
      index.js              # 路由配置（已添加 /tmdb 路由）
    App.vue                 # 主应用（已添加菜单项）

cat.yaml                    # 分类规则配置
```

## 🚀 使用方法

### 访问页面

1. 启动后端服务：
```bash
cd /Users/lizhiqiang/coding-my/file-link-monitor
python3 backend/main.py
```

2. 打开浏览器访问：
```
http://localhost:8080/tmdb
```

3. 在左侧菜单点击 **"TMDb搜索"** 进入搜索页面

### 搜索步骤

1. 选择媒体类型（全部/电影/电视剧）
2. 输入搜索关键词（如：流浪地球、三体）
3. 点击搜索按钮或按回车
4. 在搜索结果中点击任意作品查看详情
5. 在详情页面可以：
   - 查看自动分类结果
   - 复制主图链接
   - 预览和复制海报/剧照链接

## 🔧 API 接口

### 1. 搜索影视作品

**接口**: `GET /api/tmdb/search`

**参数**:
- `query`: 搜索关键词（必填）
- `media_type`: 媒体类型（movie/tv/multi，默认 multi）
- `language`: 语言（默认 zh-CN）

**返回示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 123456,
      "media_type": "movie",
      "title": "流浪地球2",
      "year": "2023",
      "poster_path": "https://image.tmdb.org/t/p/original/xxx.jpg",
      "overview": "简介...",
      "vote_average": 7.5
    }
  ]
}
```

### 2. 获取详细信息

**接口**: `GET /api/tmdb/details/{media_type}/{media_id}`

**参数**:
- `media_type`: 媒体类型（movie 或 tv）
- `media_id`: 媒体ID
- `language`: 语言（默认 zh-CN）

**返回示例**:
```json
{
  "success": true,
  "data": {
    "id": 123456,
    "media_type": "movie",
    "title": "流浪地球2",
    "year": "2023",
    "category": "电影/国产电影",
    "main_poster": "https://image.tmdb.org/t/p/original/xxx.jpg",
    "posters": ["url1", "url2", ...],
    "backdrops": ["url1", "url2", ...],
    "overview": "简介...",
    "vote_average": 7.5,
    "origin_country": ["CN"],
    "genres": ["科幻", "动作"],
    "runtime": 120
  }
}
```

### 3. 获取图片

**接口**: `GET /api/tmdb/images/{media_type}/{media_id}`

**参数**:
- `media_type`: 媒体类型
- `media_id`: 媒体ID

**返回示例**:
```json
{
  "success": true,
  "data": {
    "posters": [
      {
        "url": "https://image.tmdb.org/t/p/original/xxx.jpg",
        "width": 2000,
        "height": 3000,
        "aspect_ratio": 0.667
      }
    ],
    "backdrops": [...]
  }
}
```

### 4. 获取分类配置

**接口**: `GET /api/tmdb/categories`

**返回**: cat.yaml 的完整配置

## 🎨 前端集成

### 在其他页面调用 TMDb 搜索

```vue
<script setup>
import api from '../api'

const searchMedia = async (query) => {
  const res = await api.searchTmdb({ query, media_type: 'multi' })
  if (res.data.success) {
    const results = res.data.data
    // 处理结果
  }
}

const getDetails = async (mediaType, mediaId) => {
  const res = await api.getTmdbDetails(mediaType, mediaId)
  if (res.data.success) {
    const details = res.data.data
    console.log('分类:', details.category)
    console.log('主图:', details.main_poster)
  }
}
</script>
```

## 📋 分类规则

分类规则由 `cat.yaml` 定义，自动根据以下信息进行分类：
- 类型ID（genre_ids）：如 16=动画、99=纪录片
- 来源国家（origin_country）：如 CN=中国、JP=日本

### 电影分类示例
- **动漫/动画电影**: genre_ids 包含 16
- **电影/国产电影**: origin_country 包含 CN
- **电影/欧美电影**: 其他国家（排除亚洲）

### 电视剧分类示例
- **动漫/日本番剧**: genre_ids 包含 16 且 origin_country 包含 JP
- **剧集/国产剧集**: origin_country 包含 CN
- **剧集/欧美剧集**: 其他国家（排除亚洲）

## 🔍 测试示例

### 搜索示例
- **国产电影**: 流浪地球、战狼、红海行动
- **国产剧集**: 三体、开端、隐秘的角落
- **日本番剧**: 鬼灭之刃、进击的巨人、火影忍者
- **欧美电影**: 阿凡达、复仇者联盟、盗梦空间
- **欧美剧集**: 权力的游戏、绝命毒师、怪奇物语

## ⚙️ 配置说明

### 修改 API Key

如需使用自己的 TMDb API Key，修改 `backend/api/tmdb.py`:

```python
TMDB_API_KEY = "your_api_key_here"
```

### 修改分类规则

编辑 `cat.yaml` 文件即可，系统会自动重新加载。

## 🐛 常见问题

### Q: 搜索不到结果？
A: 尝试使用英文名或更准确的关键词。

### Q: 图片无法显示？
A: 检查网络连接，图片托管在 TMDb CDN 上。

### Q: 分类显示"未分类"？
A: 检查 cat.yaml 规则是否完整，或者该作品的类型/国家不在规则内。

### Q: 如何获取自己的 TMDb API Key？
A: 访问 https://www.themoviedb.org/settings/api 注册并申请。

## 📊 性能优化

- ✅ 搜索结果限制为前10个
- ✅ 图片数量限制（海报5张、剧照5张）
- ✅ 请求超时设置（10秒）
- ✅ 图片懒加载

## 🎯 后续扩展

可以考虑添加以下功能：
- [ ] 搜索历史记录
- [ ] 收藏功能
- [ ] 批量搜索
- [ ] 导出搜索结果
- [ ] 与映射管理集成（搜索后直接创建映射）

---

**更新日期**: 2025-12-25
**版本**: 1.0.0

