# File Link Monitor

文件监控硬链接系统 - 自动监控源目录文件变化，创建硬链接到多个目标目录，支持同音字混淆、字幕同步、模板文件链接等功能。

## ✨ 核心功能

### 1. 同音字混淆
- 🔤 **1500+汉字同音字库** - 基于汉字拆字的确定性混淆算法
- 🎯 **自动去年份** - 智能识别并移除剧集名称中的年份标识
- 📁 **分类保护** - 14个一二级分类文件夹保持不混淆
- 🔄 **确定性算法** - 相同名称每次混淆结果一致

### 2. 文件同步
- 📹 **视频文件** - 自动硬链接视频文件
- 📝 **字幕同步** - 支持7种字幕格式（.srt, .ass, .ssa, .sub, .idx, .sup, .vtt）
- 📋 **模板文件链接** - 推广文件、二维码等固定文件自动跟随剧集

### 3. 自定义映射管理
- 🗄️ **数据库存储** - 所有映射规则存储在数据库中
- ✏️ **在线编辑** - Web界面直接编辑原名→混淆名映射
- 🔍 **分页搜索** - 支持模糊搜索，分页浏览
- 🔗 **网盘链接** - 支持添加百度网盘和夸克网盘分享链接
- 📤 **导出Excel** - 一键导出名称映射表和链接记录
- 🔄 **自动写入** - 同步时自动创建映射记录

### 4. Web管理界面
- 🎨 **现代化UI** - 渐变主题、响应式设计
- 🌲 **目录树** - 可视化查看源目录和目标目录结构
- 📊 **统计面板** - 实时显示处理记录、成功率等统计信息
- 🔄 **实时监控** - 自动监控文件变化并处理
- 📥 **全量同步** - 支持一键全量同步所有文件

## 🚀 快速开始

### 部署方式

#### Docker Compose（推荐）

```bash
cd file-link-monitor
docker compose up -d
```

#### 手动部署

```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移（如果数据库已存在）
python3 migrate_add_links.py ./data/database.db

# 启动服务
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

### 配置文件

编辑 `config.yaml` 或使用Docker volume挂载：

```yaml
monitors:
  - source: /path/to/source              # 源目录
    targets:
      - path: /path/to/target1
        name: "百度网盘"
      - path: /path/to/target2
        name: "夸克网盘"
    enabled: true
    obfuscate_enabled: true              # 启用同音字混淆
    template_files_path: /path/to/templates  # 模板文件目录
```

## 📖 使用指南

### 基本流程

1. **启动服务** - 访问 http://localhost:8080
2. **全量同步** - 点击"🔄 全量同步"按钮
3. **查看映射** - 点击"🔄 映射管理"标签
4. **编辑名称** - 点击"编辑"修改混淆名称
5. **清除记录** - 点击"清除记录"删除数据库记录
6. **重新同步** - 再次点击"🔄 全量同步"使用新名称

### 修改剧集名称示例

假设要将"老舅 (2023)"改名为"我的舅舅"：

1. 在映射管理页面找到该记录
2. 点击"编辑"，输入新名称"我的舅舅"
3. 输入网盘链接（可选）
4. 点击"清除记录"删除旧的硬链接记录
5. 点击"全量同步"
6. ✅ 新文件夹已创建：`/网盘/剧集/国产剧集/我的舅舅/`

### 导出功能

- **映射管理导出** - 导出"原名 + 混淆名 + 百度网盘 + 夸克网盘"
- **链接记录导出** - 导出所有硬链接记录详情

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代Python Web框架
- **SQLAlchemy** - ORM数据库操作
- **Watchdog** - 文件系统监控
- **OpenPyXL** - Excel文件生成

### 前端
- **原生JavaScript** - 无框架依赖
- **Modern CSS** - 渐变主题、动画效果

### 数据库
- **SQLite** - 轻量级数据库

## 📁 项目结构

```
file-link-monitor/
├── backend/              # 后端代码
│   ├── api/             # API路由
│   ├── models.py        # 数据库模型
│   ├── monitor.py       # 文件监控核心
│   └── utils/           # 工具模块
│       ├── linker.py    # 硬链接处理
│       ├── obfuscator.py       # 混淆逻辑
│       └── homophone_*.py      # 同音字库
├── frontend/            # 前端代码
│   ├── index.html       # 主页面
│   ├── js/app.js        # 前端逻辑
│   └── css/style.css    # 样式文件
├── config.yaml          # 配置文件
├── docker-compose.yml   # Docker配置
├── requirements.txt     # Python依赖
└── migrate_add_links.py # 数据库迁移脚本
```

## 🔧 高级配置

### 分类文件夹配置

默认不混淆以下分类：
- 一级：剧集、电影、动漫、其他
- 电影：港台电影、国产电影、日韩电影、欧美电影、动画电影
- 剧集：港台剧集、国产剧集、日韩剧集、南亚剧集、欧美剧集
- 动漫：国产动漫、欧美动漫、日本番剧
- 其他：纪录片、综艺、音乐

### Docker卷挂载

```yaml
volumes:
  - /path/to/config.yaml:/app/config.yaml    # 配置文件
  - /path/to/data:/app/data                   # 数据库
  - /path/to/media:/media                     # 媒体目录
  - /path/to/templates:/media/templates       # 模板文件
```

## 🎯 适用场景

- ✅ 多网盘同步（百度、夸克、阿里等）
- ✅ 内容防和谐（自动混淆敏感名称）
- ✅ 批量管理剧集名称
- ✅ 字幕自动跟随
- ✅ 推广文件统一管理

## 📝 更新日志

### v2.0.0 (2025-12-18)
- ✨ 全新的Web管理界面
- ✨ 自定义名称映射功能
- ✨ 网盘链接管理
- ✨ Excel导出功能
- ✨ 数据库自动迁移

### v1.0.0
- 基础硬链接功能
- 同音字混淆
- 字幕同步

## 📄 License

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📮 联系方式

如有问题或建议，请提交Issue。
