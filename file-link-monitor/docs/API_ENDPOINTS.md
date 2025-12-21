# 网盘转存API接口文档

## 基础信息

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`
- **认证**: 需要在数据库中配置各网盘的Cookie

---

## API列表

### 1. 获取转存功能状态

**GET** `/transfer/status`

获取当前支持的网盘列表和认证状态。

**响应示例：**
```json
{
  "success": true,
  "supported_platforms": {
    "baidu": {
      "available": true,
      "name": "百度网盘"
    },
    "quark": {
      "available": true,
      "name": "夸克网盘"
    },
    "xunlei": {
      "available": true,
      "name": "迅雷网盘"
    }
  },
  "features": {
    "openlist_integration": true,
    "direct_api": true,
    "batch_transfer": true
  }
}
```

---

### 2. 单个文件转存

**POST** `/transfer`

转存单个分享链接到指定网盘。

**请求参数：**
```json
{
  "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
  "pass_code": "1234",
  "target_path": "/电影/动作片/钢铁侠3",
  "pan_type": "baidu",
  "use_openlist": true
}
```

**参数说明：**
- `share_url` (必需): 分享链接
- `pass_code` (可选): 提取码
- `target_path` (必需): 目标路径（不需要网盘前缀）
- `pan_type` (必需): 网盘类型 `baidu`/`quark`/`xunlei`
- `use_openlist` (可选): 是否使用OpenList管理路径，默认`true`

**响应示例（成功）：**
```json
{
  "success": true,
  "pan_type": "baidu",
  "file_count": 21,
  "file_ids": ["123456", "789012", ...],
  "message": "转存成功",
  "details": {
    "task_id": 0,
    "target_path": "/baidu/电影/动作片/钢铁侠3"
  }
}
```

**响应示例（失败）：**
```json
{
  "success": false,
  "pan_type": "baidu",
  "file_count": 0,
  "file_ids": [],
  "message": "转存失败: 转存路径不存在",
  "details": {}
}
```

---

### 3. 批量转存

**POST** `/transfer/batch`

批量转存多个分享链接（支持三网盘同时转存）。

**请求参数：**
```json
{
  "share_links": [
    {
      "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
      "pass_code": "1234",
      "pan_type": "baidu"
    },
    {
      "share_url": "https://pan.quark.cn/s/xxxxx",
      "pass_code": null,
      "pan_type": "quark"
    },
    {
      "share_url": "https://pan.xunlei.com/s/xxxxx",
      "pass_code": null,
      "pan_type": "xunlei"
    }
  ],
  "target_path": "/电影/动作片/钢铁侠3",
  "use_openlist": true
}
```

**响应示例：**
```json
{
  "success": true,
  "total": 3,
  "success_count": 3,
  "failed_count": 0,
  "results": [
    {
      "success": true,
      "pan_type": "baidu",
      "file_count": 21,
      "file_ids": ["123", "456"],
      "message": "转存成功",
      "details": {...}
    },
    {
      "success": true,
      "pan_type": "quark",
      "file_count": 1,
      "file_ids": ["789"],
      "message": "转存成功",
      "details": {...}
    },
    {
      "success": true,
      "pan_type": "xunlei",
      "file_count": 1,
      "file_ids": ["abc"],
      "message": "转存成功",
      "details": {...}
    }
  ]
}
```

---

## 使用示例

### curl 示例

**1. 获取状态：**
```bash
curl http://localhost:8000/api/transfer/status
```

**2. 单个转存：**
```bash
curl -X POST http://localhost:8000/api/transfer \
  -H "Content-Type: application/json" \
  -d '{
    "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
    "pass_code": "1234",
    "target_path": "/电影/动作片/钢铁侠3",
    "pan_type": "baidu",
    "use_openlist": true
  }'
```

**3. 批量转存：**
```bash
curl -X POST http://localhost:8000/api/transfer/batch \
  -H "Content-Type: application/json" \
  -d '{
    "share_links": [
      {
        "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
        "pass_code": "1234",
        "pan_type": "baidu"
      }
    ],
    "target_path": "/电影/动作片/钢铁侠3",
    "use_openlist": true
  }'
```

---

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000/api"

# 1. 获取状态
response = requests.get(f"{BASE_URL}/transfer/status")
print(response.json())

# 2. 单个转存
data = {
    "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
    "pass_code": "1234",
    "target_path": "/电影/动作片/钢铁侠3",
    "pan_type": "baidu",
    "use_openlist": True
}
response = requests.post(f"{BASE_URL}/transfer", json=data)
print(response.json())

# 3. 批量转存（三网盘）
data = {
    "share_links": [
        {
            "share_url": "https://pan.baidu.com/s/1xxxxx?pwd=1234",
            "pass_code": "1234",
            "pan_type": "baidu"
        },
        {
            "share_url": "https://pan.quark.cn/s/xxxxx",
            "pan_type": "quark"
        },
        {
            "share_url": "https://pan.xunlei.com/s/xxxxx",
            "pan_type": "xunlei"
        }
    ],
    "target_path": "/电影/动作片/钢铁侠3",
    "use_openlist": True
}
response = requests.post(f"{BASE_URL}/transfer/batch", json=data)
result = response.json()

print(f"成功: {result['success_count']}/{result['total']}")
for r in result['results']:
    print(f"{r['pan_type']}: {'✅' if r['success'] else '❌'}")
```

---

### JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:8000/api';

// 1. 获取状态
fetch(`${BASE_URL}/transfer/status`)
  .then(res => res.json())
  .then(data => console.log(data));

// 2. 单个转存
fetch(`${BASE_URL}/transfer`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    share_url: 'https://pan.baidu.com/s/1xxxxx?pwd=1234',
    pass_code: '1234',
    target_path: '/电影/动作片/钢铁侠3',
    pan_type: 'baidu',
    use_openlist: true
  })
})
.then(res => res.json())
.then(data => console.log(data));

// 3. 批量转存
fetch(`${BASE_URL}/transfer/batch`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    share_links: [
      {
        share_url: 'https://pan.baidu.com/s/1xxxxx?pwd=1234',
        pass_code: '1234',
        pan_type: 'baidu'
      },
      {
        share_url: 'https://pan.quark.cn/s/xxxxx',
        pan_type: 'quark'
      }
    ],
    target_path: '/电影/动作片/钢铁侠3',
    use_openlist: true
  })
})
.then(res => res.json())
.then(data => {
  console.log(`成功: ${data.success_count}/${data.total}`);
  data.results.forEach(r => {
    console.log(`${r.pan_type}: ${r.success ? '✅' : '❌'}`);
  });
});
```

---

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 未找到网盘认证信息 |
| 500 | 服务器内部错误 |

---

## 注意事项

1. **认证配置**：使用前需要在数据库 `pan_cookie` 表中配置各网盘的Cookie
2. **OpenList依赖**：`use_openlist=true` 时需要OpenList服务正常运行
3. **路径格式**：`target_path` 不需要添加网盘前缀（如 `/baidu/`），系统会自动处理
4. **文件夹同步**：使用OpenList时会自动创建文件夹并等待同步
5. **批量限制**：批量转存建议不超过10个链接，避免超时

---

## Swagger文档

启动后端服务后，访问以下地址查看交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 启动服务

```bash
cd backend
python main.py
```

默认端口：8000

---

## 测试脚本

使用提供的测试脚本：

```bash
python test_transfer_api.py
```
