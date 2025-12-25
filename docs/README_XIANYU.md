# 闲鱼管家集成文档

## 📝 功能概述

已成功将 Java 项目的所有闲鱼管家功能迁移到 Python，实现了完整的闲鱼商品管理和卡密管理系统。

### ✅ 已完成功能

#### 1. **商品管理**
- ✅ 从媒体库一键创建商品（使用TMDB海报）
- ✅ 商品同步（从闲鱼管家后台）
- ✅ 商品上架/下架
- ✅ 商品删除（仅草稿箱/待发布状态）
- ✅ 定时上架/下架
- ✅ 支持多店铺（最多2个）

#### 2. **卡密管理** （Selenium自动化）
- ✅ 创建卡种
- ✅ 添加卡密（支持批量和重复）
- ✅ 设置自动发货

#### 3. **定时任务**
- ✅ 定时上架/下架商品
- ✅ 支持每日重复任务
- ✅ 后台自动调度执行

---

## 📂 项目结构

```
backend/
├── utils/
│   ├── xianyu_api.py          # 闲鱼管家SDK（商品API）
│   └── xianyu_selenium.py     # Selenium自动化（卡密管理）
├── models/
│   └── xianyu.py              # 数据库模型
├── api/
│   └── xianyu.py              # API路由
├── services/
│   ├── image_upload.py        # 图片上传服务
│   └── xianyu_scheduler.py    # 定时任务调度器
└── migrations/
    └── add_xianyu_tables.sql  # 数据库迁移脚本

frontend-vue/
└── src/
    └── views/
        ├── MediaLibrary.vue   # 媒体库（新增创建商品功能）
        ├── XianyuProducts.vue # 商品管理页面
        └── XianyuKami.vue     # 卡密管理页面
```

---

## 🚀 快速开始

### 1. 数据库迁移

运行SQL脚本创建表：

```bash
mysql -u root -p file_link_monitor_v2 < backend/migrations/add_xianyu_tables.sql
```

**创建的表：**
- `goofish_product` - 商品表
- `goofish_config` - 配置表
- `goofish_schedule_task` - 定时任务表

### 2. 安装依赖

```bash
pip install selenium==4.15.0
```

**注意：** 需要安装 ChromeDriver（Selenium会自动下载到 `~/.cache/selenium/`）

### 3. 配置闲鱼管家

访问前端页面，在数据库配置以下项：

| 配置键 | 说明 | 必填 |
|--------|------|------|
| `goofish.app_key` | 闲鱼管家应用KEY | ✅ |
| `goofish.app_secret` | 闲鱼管家应用密钥 | ✅ |
| `username1` | 闲鱼会员名1 | ✅ |
| `username2` | 闲鱼会员名2 | ❌ |
| `product.title.template` | 商品标题模板 | ❌ |
| `product.content.template` | 商品描述模板 | ❌ |
| `product.price` | 默认价格（元） | ❌ |
| `product.express.fee` | 默认运费（元） | ❌ |
| `product.stock` | 默认库存 | ❌ |
| `product.stuff.status` | 默认成色 | ❌ |

**方式1：通过API设置**

```python
import requests

requests.post('http://localhost:8080/api/xianyu/config', json={
    'config_key': 'goofish.app_key',
    'config_value': '你的APP_KEY',
    'description': '闲鱼管家应用KEY'
})
```

**方式2：直接插入数据库**

```sql
INSERT INTO goofish_config (config_key, config_value, description) VALUES
('goofish.app_key', '你的APP_KEY', '闲鱼管家应用KEY'),
('goofish.app_secret', '你的APP_SECRET', '闲鱼管家应用密钥'),
('username1', '你的会员名', '闲鱼会员名1');
```

### 4. 启动服务

```bash
cd /Users/lizhiqiang/coding-my/file-link-monitor
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

### 5. 前端访问

打开浏览器访问：`http://localhost:8080`

导航菜单中会看到：
- 🐟 **闲鱼管家** 区域
  - 商品管理
  - 卡密管理

---

## 💡 使用教程

### 场景1：从媒体库创建商品

1. 进入 **媒体库** 页面
2. 点击任意媒体卡片，查看详情
3. 点击 **🐟 创建闲鱼商品** 按钮
4. 在弹窗中：
   - 确认海报图片（自动使用TMDB海报）
   - 编辑标题/描述（可选）
   - 设置价格、运费、库存
5. 点击 **创建商品**
6. 系统自动：
   - 上传海报到本地
   - 调用闲鱼管家API创建商品
   - 立即上架到配置的店铺
   - 保存到数据库

**特点：**
- ✅ 自动使用TMDB高清海报
- ✅ 支持双店铺同时创建
- ✅ 创建后自动上架
- ✅ 与媒体库关联

### 场景2：商品管理

访问 **商品管理** 页面：

**功能：**
- 📊 **同步商品** - 从闲鱼管家后台同步最新商品数据
- 🔍 **筛选状态** - 按待发布/已上架/已下架筛选
- 📤 **上架** - 一键上架待发布商品
- 📥 **下架** - 一键下架已上架商品
- ⏰ **定时任务** - 设置定时上架/下架
- 🗑️ **删除** - 删除草稿箱商品

**定时任务：**
1. 点击商品的 **定时任务** 按钮
2. 选择任务类型（上架/下架）
3. 选择执行时间
4. 可选：每日重复
5. 创建后自动在后台执行

### 场景3：卡密管理

访问 **卡密管理** 页面：

#### 3.1 创建卡种

1. 切换到 **创建卡种** 标签
2. 输入卡种名称（如：某某影视卡）
3. 点击 **创建卡种**
4. 浏览器会自动打开，需要扫码登录（首次）
5. 等待自动化完成

#### 3.2 添加卡密

1. 切换到 **添加卡密** 标签
2. 输入目标卡种名称
3. 输入卡密数据，格式：
   ```
   CARD001 PASS001
   CARD002 PASS002
   CARD003 PASS003
   ```
4. 设置重复次数（每组卡密可用次数）
5. 点击 **添加卡密**
6. 浏览器自动化完成添加

#### 3.3 设置自动发货

1. 切换到 **自动发货设置** 标签
2. 输入卡种名称
3. 点击 **设置自动发货**
4. 系统会为最新的2个商品设置使用该卡种自动发货

**注意事项：**
- ⚠️ Selenium需要浏览器支持，首次使用需扫码登录
- ⚠️ 建议不要在无头模式下使用（调试时可观察过程）
- ⚠️ 登录后会话保持，后续操作不需要重复登录

---

## 🔧 API文档

### 商品管理 API

#### 1. 从媒体创建商品

```http
POST /api/xianyu/product/create-from-media
Content-Type: application/json

{
  "media_id": 123,
  "title": "商品标题（可选）",
  "content": "商品描述（可选）",
  "price": 0.1,
  "express_fee": 0,
  "stock": 100,
  "image_urls": ["https://..."]
}
```

#### 2. 同步商品列表

```http
POST /api/xianyu/product/sync
Content-Type: application/json

{
  "page_no": 1,
  "page_size": 50,
  "product_status": null
}
```

#### 3. 上架商品

```http
POST /api/xianyu/product/{product_id}/publish
Content-Type: application/json

{
  "user_name": "会员名（可选）"
}
```

#### 4. 下架商品

```http
POST /api/xianyu/product/{product_id}/downshelf
```

#### 5. 删除商品

```http
DELETE /api/xianyu/product/{product_id}
```

#### 6. 商品列表

```http
GET /api/xianyu/product/list?status=1&page=1&page_size=20
```

### 定时任务 API

#### 创建定时任务

```http
POST /api/xianyu/schedule-task
Content-Type: application/json

{
  "task_type": "publish",
  "product_ids": [123456, 789012],
  "execute_time": "2025-12-26T10:00:00",
  "repeat_daily": false
}
```

#### 任务列表

```http
GET /api/xianyu/schedule-task/list?status=PENDING
```

### 卡密管理 API

#### 1. 创建卡种

```http
POST /api/xianyu/kami/create-kind
Content-Type: application/json

{
  "kind_name": "影视卡"
}
```

#### 2. 添加卡密

```http
POST /api/xianyu/kami/add-cards
Content-Type: application/json

{
  "kind_name": "影视卡",
  "kami_data": "CARD001 PASS001\nCARD002 PASS002",
  "repeat_count": 10
}
```

#### 3. 设置自动发货

```http
POST /api/xianyu/kami/setup-shipping
Content-Type: application/json

{
  "kind_name": "影视卡"
}
```

---

## 🗃️ 数据库表结构

### 商品表 (goofish_product)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| product_id | BIGINT | 闲鱼商品ID |
| title | VARCHAR(500) | 商品标题 |
| price | BIGINT | 价格（分） |
| stock | INT | 库存 |
| sold | INT | 已售 |
| product_status | INT | 状态（0=待发布,1=已上架,2=已下架） |
| media_id | BIGINT | 关联媒体库ID |
| sync_time | DATETIME | 同步时间 |
| ... | ... | 其他字段 |

### 配置表 (goofish_config)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| config_key | VARCHAR(100) | 配置键 |
| config_value | TEXT | 配置值 |
| description | VARCHAR(500) | 描述 |

### 定时任务表 (goofish_schedule_task)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| task_type | VARCHAR(20) | 任务类型 |
| product_ids | TEXT | 商品ID列表(JSON) |
| execute_time | DATETIME | 执行时间 |
| repeat_daily | TINYINT(1) | 是否每日重复 |
| status | VARCHAR(20) | 状态 |

---

## 🎯 与Java项目对比

| 功能 | Java | Python | 状态 |
|------|------|--------|------|
| 商品API（创建/上架/下架） | ✅ | ✅ | 完全迁移 |
| 图片上传 | ✅ | ✅ | 完全迁移 |
| 多店铺支持 | ✅ | ✅ | 完全迁移 |
| 定时任务 | ✅ | ✅ | 完全迁移 |
| 卡种管理（Selenium） | ✅ | ✅ | 完全迁移 |
| 卡密添加（Selenium） | ✅ | ✅ | 完全迁移 |
| 自动发货设置（Selenium） | ✅ | ✅ | 完全迁移 |
| Web管理界面 | ✅ | ✅ | Vue3重写 |
| 数据库表 | ✅ | ✅ | 共享表结构 |

**优势：**
- ✅ 与媒体库深度集成
- ✅ 使用TMDB海报，更高质量
- ✅ 统一的Python技术栈
- ✅ 现代化的Vue3界面
- ✅ 自动化定时任务调度

---

## ⚠️ 注意事项

1. **数据库共享**
   - Python和Java项目使用同一个数据库
   - 表结构完全兼容
   - 可以同时运行（不建议）

2. **Selenium依赖**
   - 需要安装Chrome浏览器
   - ChromeDriver自动下载
   - 首次使用卡密功能需要扫码登录

3. **图片存储**
   - 图片保存在 `uploads/` 目录
   - 通过 `/uploads/` 路由访问
   - 建议配置CDN或对象存储

4. **定时任务**
   - 每分钟检查一次待执行任务
   - 任务执行时间误差 ±1分钟
   - 重复任务自动创建下一个

5. **API密钥安全**
   - 不要泄露 app_key 和 app_secret
   - 建议使用环境变量
   - 定期更换密钥

---

## 🐛 故障排查

### 1. "SDK未初始化"错误

**原因：** 未配置 app_key 或 app_secret

**解决：**
```sql
INSERT INTO goofish_config (config_key, config_value) VALUES
('goofish.app_key', '你的KEY'),
('goofish.app_secret', '你的SECRET');
```

### 2. Selenium卡密功能失败

**原因：** ChromeDriver未安装或版本不匹配

**解决：**
```bash
# Selenium会自动下载，如果失败可手动安装
pip install webdriver-manager
```

### 3. 图片上传失败

**原因：** uploads目录权限问题

**解决：**
```bash
mkdir -p uploads
chmod 777 uploads
```

### 4. 定时任务不执行

**原因：** 调度器未启动

**解决：** 检查启动日志是否有"闲鱼定时任务调度器已启动"

---

## 📞 技术支持

- **文档：** `/docs/README_XIANYU.md`
- **API文档：** http://localhost:8080/docs
- **日志查看：** 查看终端输出

---

## 🎊 完成状态

✅ **所有功能已完整迁移！**

- ✅ 闲鱼SDK（Python实现）
- ✅ Selenium自动化（Python实现）
- ✅ 数据库模型
- ✅ API路由
- ✅ 图片上传服务
- ✅ 定时任务调度器
- ✅ 前端管理界面
- ✅ 与媒体库集成

现在您可以：
1. 从媒体库一键创建闲鱼商品
2. 管理所有商品（上架/下架/定时）
3. 自动化卡密管理
4. 统一的Python技术栈

**Happy Coding! 🎉**

