# 文件监控硬链接系统

一个简单、高效的文件监控和硬链接管理系统，用于自动将源目录的文件硬链接到多个目标目录。

## 功能特性

- ✅ **实时监控**：使用 watchdog 实时监控源目录文件变化
- ✅ **自动硬链接**：新文件自动硬链接到配置的目标目录（一对多）
- ✅ **Web 界面**：纯 HTML 界面，查看目录树、硬链接记录
- ✅ **记录查询**：完整的硬链接记录，支持分页、筛选
- ✅ **统计信息**：实时统计今日处理、总记录、成功率等
- ✅ **Docker 部署**：一键启动，适配飞牛 NAS

## 快速开始

### 1. 配置文件

编辑 `config.yaml`：

```yaml
monitors:
  - source: /media/links           # 源目录
    targets:
      - /media/网盘1               # 目标目录1
      - /media/网盘2               # 目标目录2
    enabled: true
    exclude_patterns:              # 排除文件（可选）
      - "*.tmp"
      - "*.part"
```

### 2. 修改 docker-compose.yml

根据您的 NAS 目录结构修改挂载路径：

```yaml
volumes:
  - /volume1/media:/media          # 改成您的实际路径
```

### 3. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 访问 Web 界面

浏览器打开：`http://您的NAS_IP:8080`

## 目录结构

```
file-link-monitor/
├── backend/              # 后端代码
│   ├── main.py          # 主程序入口
│   ├── models.py        # 数据库模型
│   ├── monitor.py       # 监控服务
│   ├── api/             # API 接口
│   │   ├── tree.py      # 目录树接口
│   │   └── records.py   # 记录查询接口
│   └── utils/           # 工具类
│       └── linker.py    # 硬链接工具
├── frontend/            # 前端页面
│   ├── index.html
│   ├── css/
│   └── js/
├── data/                # 数据目录（持久化）
│   └── database.db      # SQLite 数据库
├── config.yaml          # 配置文件
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API 接口

### 获取目录树
```
GET /api/tree?path=/media/links&depth=3
```

### 获取硬链接记录
```
GET /api/records?page=1&page_size=20&status=success
```

### 获取统计信息
```
GET /api/stats
```

## Web 界面功能

### 📂 目录视图
- 左侧：源目录树
- 右侧：目标目录树（多标签切换）
- 实时刷新

### 📋 链接记录
- 分页展示所有硬链接记录
- 状态筛选（成功/失败）
- 显示源文件、目标文件、大小、时间

### ⚙️ 配置
- 查看当前监控配置
- 源目录、目标目录列表

### 📊 统计栏
- 今日处理文件数
- 总记录数
- 成功/失败数
- 总文件大小

## 工作原理

1. **watchdog** 监控源目录 (`/media/links`)
2. 发现新文件或文件移动事件
3. 排除配置的模式（如 `*.tmp`）
4. 为每个目标目录创建硬链接（保持相对路径）
5. 记录到 SQLite 数据库
6. Web 界面实时查询展示

## 硬链接说明

- **硬链接**：多个文件路径指向同一个文件实体，不占用额外空间
- **限制**：必须在同一文件系统（同一挂载点）
- **降级策略**：如果硬链接失败（跨文件系统），自动降级为文件复制

## 注意事项

1. **源目录和目标目录必须在同一文件系统**（同一挂载点），否则会降级为复制
2. 配置的路径是 **容器内路径**，通过 docker-compose.yml 映射
3. 数据库文件在 `./data/database.db`，可以备份
4. 默认端口 8080，可在 docker-compose.yml 中修改

## 故障排查

### 硬链接失败
- 检查源目录和目标目录是否在同一文件系统
- 查看日志：`docker-compose logs -f`

### 无法访问 Web 界面
- 检查端口映射：`docker ps`
- 检查防火墙设置

### 监控不工作
- 检查源目录路径是否正确
- 查看配置文件中的 `enabled` 是否为 `true`

## 技术栈

- **后端**：FastAPI + SQLAlchemy + watchdog
- **前端**：纯 HTML + CSS + JavaScript
- **数据库**：SQLite
- **部署**：Docker

## 开发

```bash
# 本地运行
pip install -r requirements.txt
python -m backend.main

# 访问
http://localhost:8080
```

## 许可证

MIT License
