# TMDb 媒体信息搜索工具使用说明

## 功能介绍

这个工具可以通过 TMDb API 搜索电影和电视剧，并根据 `cat.yaml` 的规则自动分类。

### 主要功能

1. ✅ 搜索电影和电视剧
2. ✅ 获取详细信息（名称、年份、类型、国家、评分等）
3. ✅ 根据 `cat.yaml` 自动分类
4. ✅ 获取主图（海报）
5. ✅ 获取副图（海报和剧照）

## 安装依赖

```bash
pip install requests pyyaml
```

## 使用方法

### 方法 1: 交互模式

直接运行脚本，进入交互模式：

```bash
python tmdb_search.py
```

然后输入搜索关键词，例如：
- `三体`
- `流浪地球`
- `The Witcher`

### 方法 2: 命令行参数模式

直接传入搜索关键词：

```bash
python tmdb_search.py 三体
python tmdb_search.py 流浪地球
python tmdb_search.py "The Witcher"
```

## 使用示例

### 示例 1: 搜索电影

```bash
$ python tmdb_search.py 流浪地球

🔍 搜索: 流浪地球
------------------------------------------------------------

找到 5 个结果:

1. 🎬 流浪地球 (2019)
2. 🎬 流浪地球2 (2023)
...

请选择一个结果（输入序号，0 退出）: 1

⏳ 正在获取详细信息...

============================================================
📺 名称: 流浪地球 (2019)
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

📝 简介: 太阳即将毁灭，人类在地球表面建造出巨大的推进器...
⭐ 评分: 7.5/10
🌍 国家: CN
🏷️  类型: 科幻, 冒险, 动作
============================================================
```

### 示例 2: 搜索电视剧

```bash
$ python tmdb_search.py 三体

🔍 搜索: 三体
------------------------------------------------------------

找到 3 个结果:

1. 📺 三体 (2023)
2. 📺 我的三体 (2014)
...

请选择一个结果（输入序号，0 退出）: 1

⏳ 正在获取详细信息...

============================================================
📺 名称: 三体 (2023)
📁 二级分类: 剧集/国产剧集
🖼️  主图: https://image.tmdb.org/t/p/original/xxx.jpg
...
============================================================
```

## 分类规则说明

工具会根据 `cat.yaml` 中的规则自动分类：

### 电影分类 (movie)

- **动漫/动画电影**: genre_ids 包含 16（动画类型）
- **电影/港台电影**: origin_country 包含 TW、HK
- **电影/国产电影**: origin_country 包含 CN
- **电影/日韩电影**: origin_country 包含 JP、KP、KR
- **电影/欧美电影**: origin_country 为其他国家

### 电视剧分类 (tv)

- **动漫/国产动漫**: genre_ids 包含 16 且 origin_country 包含 CN、TW、HK
- **动漫/欧美动漫**: genre_ids 包含 16 且 origin_country 包含美国等
- **动漫/日本番剧**: genre_ids 包含 16 且 origin_country 包含 JP
- **其他/纪录影片**: genre_ids 包含 99（纪录片类型）
- **其他/综艺节目**: genre_ids 包含 10764、10767
- **剧集/港台剧集**: origin_country 包含 TW、HK
- **剧集/国产剧集**: origin_country 包含 CN
- **剧集/日韩剧集**: origin_country 包含 JP、KP、KR
- **剧集/南亚剧集**: origin_country 包含 TH、IN、SG
- **剧集/欧美剧集**: origin_country 为其他国家

## 输出信息

每个搜索结果会输出以下信息：

- **名称（年份）**: 如 `流浪地球 (2019)`
- **二级分类**: 根据 cat.yaml 规则自动分类
- **主图**: 主海报图片链接
- **海报**: 最多 5 张海报图片
- **剧照**: 最多 5 张剧照图片
- **简介**: 剧情简介
- **评分**: TMDb 评分
- **国家**: 来源国家
- **类型**: 影视类型（如科幻、动作等）

## 注意事项

1. 需要有网络连接访问 TMDb API
2. API Key 已内置在脚本中
3. 图片链接为高清原图（original），可能较大
4. 搜索结果最多显示前 10 个

## 自定义分类

如需修改分类规则，请编辑 `cat.yaml` 文件：

```yaml
movie:
  动漫/动画电影:
    genre_ids: "16"
  电影/港台电影:
    origin_country: "TW,HK"
  # ... 更多规则
```

## 常见问题

### Q: 搜索不到结果？
A: 尝试使用英文名称或者更准确的关键词。

### Q: 分类不准确？
A: 检查 `cat.yaml` 的规则配置，确保规则覆盖了该类型。

### Q: 图片无法访问？
A: 图片托管在 TMDb CDN 上，需要网络访问权限。

## 技术支持

如有问题，请查看：
- TMDb API 文档: https://developers.themoviedb.org/3
- cat.yaml 配置文件

