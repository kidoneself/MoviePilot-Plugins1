# TMDb 媒体信息搜索工具

通过 TMDb API 搜索影视作品，自动获取信息并根据 `cat.yaml` 规则进行分类。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install requests pyyaml
```

### 2. 交互式使用

```bash
python3 tmdb_search.py
```

然后输入搜索关键词，如：`三体`、`流浪地球`、`The Witcher` 等。

### 3. 命令行使用

```bash
python3 tmdb_search.py 流浪地球
python3 tmdb_search.py 三体
python3 tmdb_search.py "权力的游戏"
```

### 4. 查看示例

```bash
python3 tmdb_example.py
```

## 📋 功能特性

- ✅ **搜索影视作品** - 支持电影和电视剧
- ✅ **自动分类** - 根据 `cat.yaml` 规则自动分类
- ✅ **获取图片** - 主图（海报）+ 副图（剧照）
- ✅ **详细信息** - 名称、年份、国家、类型、评分、简介等

## 📝 输出示例

```
============================================================
📺 名称: 流浪地球2 (2023)
📁 二级分类: 电影/国产电影
🖼️  主图: https://image.tmdb.org/t/p/original/xxx.jpg

📸 海报 (5 张):
   1. https://image.tmdb.org/t/p/original/xxx.jpg
   2. https://image.tmdb.org/t/p/original/xxx.jpg
   ...

🎬 剧照 (5 张):
   1. https://image.tmdb.org/t/p/original/xxx.jpg
   2. https://image.tmdb.org/t/p/original/xxx.jpg
   ...

📝 简介: 太阳即将毁灭，人类建造行星发动机...
⭐ 评分: 7.5/10
🌍 国家: CN
🏷️  类型: 科幻, 动作, 冒险
============================================================
```

## 🔧 API 集成示例

```python
from tmdb_search import TMDbSearcher

# 初始化
API_KEY = "c7f3349aa08d38fe2e391ec5a4c0279c"
searcher = TMDbSearcher(API_KEY)

# 搜索
results = searcher.search("流浪地球", media_type="movie")

# 获取详细信息
if results:
    movie_id = results[0]['id']
    details = searcher.get_details(movie_id, 'movie')
    images = searcher.get_images(movie_id, 'movie')
    
    # 自动分类
    category = searcher.classify(details, 'movie')
    
    # 获取信息
    title = details.get('title')
    year = details.get('release_date', '')[:4]
    poster = details.get('poster_path')
    
    print(f"{title} ({year}) - {category}")
```

## 📂 分类规则

分类规则定义在 `cat.yaml` 中：

### 电影分类
- **动漫/动画电影** - 动画类型 (genre_ids: 16)
- **电影/国产电影** - 中国大陆 (CN)
- **电影/港台电影** - 台湾香港 (TW, HK)
- **电影/日韩电影** - 日本韩国 (JP, KR)
- **电影/欧美电影** - 其他欧美国家

### 电视剧分类
- **动漫/国产动漫** - 动画 + 中国/台湾/香港
- **动漫/日本番剧** - 动画 + 日本
- **动漫/欧美动漫** - 动画 + 欧美国家
- **剧集/国产剧集** - 中国大陆
- **剧集/港台剧集** - 台湾香港
- **剧集/日韩剧集** - 日本韩国
- **剧集/南亚剧集** - 泰国印度新加坡
- **剧集/欧美剧集** - 其他欧美国家
- **其他/纪录影片** - 纪录片 (genre_ids: 99)
- **其他/综艺节目** - 综艺 (genre_ids: 10764, 10767)

## 📖 相关文档

- [详细使用文档](docs/TMDB_SEARCH_USAGE.md)
- [TMDb API 官方文档](https://developers.themoviedb.org/3)

## ⚙️ 配置说明

### 修改 API Key

如需使用自己的 API Key，编辑 `tmdb_search.py`:

```python
API_KEY = "your_api_key_here"
```

### 自定义分类规则

编辑 `cat.yaml` 文件：

```yaml
movie:
  自定义分类名:
    genre_ids: "16,28"  # 类型ID，逗号分隔
    origin_country: "CN,TW"  # 国家代码，逗号分隔
```

## 💡 使用场景

1. **媒体库管理** - 自动分类整理影视作品
2. **信息查询** - 快速查找影视作品详细信息
3. **刮削辅助** - 获取海报、剧照等素材
4. **数据分析** - 批量获取影视数据

## 🎯 技术栈

- Python 3.x
- requests - HTTP 请求
- PyYAML - 配置文件解析
- TMDb API v3 - 影视数据源

## 📊 测试结果

✅ 搜索功能 - 正常  
✅ 详细信息获取 - 正常  
✅ 自动分类 - 正常  
✅ 图片获取 - 正常  

---

**作者**: 基于 TMDb API 开发  
**版本**: 1.0.0  
**更新**: 2025-12-25

