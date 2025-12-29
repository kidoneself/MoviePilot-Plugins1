# 🛡️ API限流功能说明

## 📖 功能概述

基于IP地址的API限流中间件，防止：
- 🚫 恶意请求攻击
- 🤖 爬虫过度抓取
- 🔐 暴力破解尝试
- 💥 DDoS攻击

---

## ⚙️ 工作原理

### 滑动窗口算法

```
时间窗口: 60秒
最大请求: 100次

示例：
10:00:00 - 第1次请求  ✅
10:00:01 - 第2次请求  ✅
...
10:00:30 - 第100次请求 ✅
10:00:31 - 第101次请求 ❌ (超限，返回429)
10:01:01 - 第1次请求过期，可以继续请求 ✅
```

### 响应头说明

每个API响应都会包含限流信息：

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100          # 时间窗口内最大请求数
X-RateLimit-Remaining: 85       # 剩余可用请求数
X-RateLimit-Reset: 1735456789   # 重置时间戳
```

超限时返回：

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1735456789
Retry-After: 60

{
  "error": "Too Many Requests",
  "message": "请求过于频繁，请在60秒后重试",
  "limit": 100,
  "window": 60
}
```

---

## 🔧 配置方式

### 环境变量配置

```bash
# 是否启用限流（默认true）
export RATE_LIMIT_ENABLED=true

# 时间窗口内最大请求数（默认100）
export RATE_LIMIT_REQUESTS=100

# 时间窗口（秒，默认60）
export RATE_LIMIT_WINDOW=60

# 启动服务
python3 -m backend.main
```

### 配置示例

#### 1. 开发环境（宽松）
```bash
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS=1000  # 1000次/分钟
export RATE_LIMIT_WINDOW=60
```

#### 2. 生产环境（标准）
```bash
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS=100   # 100次/分钟
export RATE_LIMIT_WINDOW=60
```

#### 3. 严格模式（防攻击）
```bash
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS=30    # 30次/分钟
export RATE_LIMIT_WINDOW=60
```

#### 4. 禁用限流（测试用）
```bash
export RATE_LIMIT_ENABLED=false
```

---

## 🎯 白名单机制

以下IP自动跳过限流：
- `127.0.0.1` - 本地回环
- `::1` - IPv6本地回环
- `localhost` - 本地主机名

**如需添加其他白名单IP**，修改 `backend/main.py`：

```python
# 添加白名单IP
app.add_middleware(
    RateLimitMiddleware, 
    limiter=rate_limiter,
    whitelist=["127.0.0.1", "::1", "10.10.10.17", "192.168.1.100"]
)
```

---

## 📊 管理API

### 1. 查看限流统计

```bash
curl http://localhost:8080/api/rate-limit/stats
```

响应：
```json
{
  "success": true,
  "data": {
    "enabled": true,
    "max_requests": 100,
    "window_seconds": 60,
    "tracked_ips": 15,
    "total_requests": 234
  }
}
```

### 2. 检查当前IP状态

```bash
curl http://localhost:8080/api/rate-limit/check
```

响应：
```json
{
  "success": true,
  "data": {
    "ip": "192.168.1.100",
    "allowed": true,
    "current": 45,
    "remaining": 55,
    "limit": 100,
    "window": 60
  }
}
```

### 3. 重置指定IP限流

```bash
curl -X POST http://localhost:8080/api/rate-limit/reset \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100"}'
```

### 4. 重置所有限流记录

```bash
curl -X POST http://localhost:8080/api/rate-limit/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🔍 IP识别机制

优先级顺序：

1. **X-Forwarded-For** - nginx/CDN代理
   ```
   X-Forwarded-For: 203.0.113.195, 70.41.3.18
   → 使用第一个IP: 203.0.113.195
   ```

2. **X-Real-IP** - nginx代理
   ```
   X-Real-IP: 203.0.113.195
   ```

3. **直连IP** - 无代理
   ```
   request.client.host
   ```

### Nginx配置示例

```nginx
location /api/ {
    proxy_pass http://localhost:8080;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
}
```

---

## 🚫 跳过限流的路径

以下路径自动跳过限流检查：

- `/health` - 健康检查
- `/docs` - API文档
- `/redoc` - API文档（ReDoc）
- `/openapi.json` - OpenAPI规范
- `/assets/*` - 前端静态资源
- `/uploads/*` - 上传文件
- `/svg/*` - SVG图标

---

## 📈 性能影响

### 内存占用

```
每个IP记录: ~100 bytes
1000个活跃IP: ~100 KB
10000个活跃IP: ~1 MB
```

### 性能开销

- 每次请求检查: **< 1ms**
- 自动清理: 每5分钟执行一次
- 对API响应时间影响: **< 0.1%**

---

## 🧪 测试限流

### 快速触发限流

```bash
# 快速发送150个请求（超过100次限制）
for i in {1..150}; do
  curl -s http://localhost:8080/api/categories > /dev/null
  echo "请求 $i"
done
```

预期结果：
- 前100次: 返回200 OK
- 第101次起: 返回429 Too Many Requests

### 验证响应头

```bash
curl -I http://localhost:8080/api/categories
```

应该看到：
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1735456789
```

---

## 🔧 故障排查

### 问题1: 限流不生效

**检查**:
```bash
# 查看是否启用
curl http://localhost:8080/api/rate-limit/stats

# 检查环境变量
echo $RATE_LIMIT_ENABLED
```

**解决**:
```bash
export RATE_LIMIT_ENABLED=true
```

### 问题2: 误判正常用户

**原因**: 限流阈值太低

**解决**:
```bash
# 提高阈值
export RATE_LIMIT_REQUESTS=200
export RATE_LIMIT_WINDOW=60
```

### 问题3: 内网IP被限流

**解决**: 添加到白名单

```python
# backend/main.py
app.add_middleware(
    RateLimitMiddleware, 
    limiter=rate_limiter,
    whitelist=["127.0.0.1", "::1", "10.10.10.0/24"]  # 添加内网段
)
```

---

## 📊 监控建议

### 日志监控

限流触发时会记录日志：

```
2025-12-29 11:30:45 - backend.common.rate_limiter - WARNING - 🚫 限流触发: IP=203.0.113.195, 请求数=101/100
2025-12-29 11:30:46 - backend.common.rate_limiter - WARNING - 🚫 拒绝请求: IP=203.0.113.195, 路径=/api/tmdb/search
```

### 统计分析

定期查询统计：

```bash
# 每小时查询一次
*/60 * * * * curl -s http://localhost:8080/api/rate-limit/stats >> /var/log/rate-limit-stats.log
```

---

## 🎯 最佳实践

### 1. 分级限流

不同API设置不同阈值：

```python
# 搜索API: 30次/分钟
# 列表API: 100次/分钟
# 详情API: 200次/分钟
```

### 2. 动态调整

根据实际流量调整：

```bash
# 高峰期放宽
export RATE_LIMIT_REQUESTS=200

# 夜间收紧
export RATE_LIMIT_REQUESTS=50
```

### 3. 配合其他防护

- **Nginx限流**: 前置限流
- **CDN防护**: CloudFlare/阿里云CDN
- **WAF防火墙**: 应用层防护

---

## 📚 相关文件

```
backend/common/
├── rate_limiter.py          # 限流核心逻辑
└── ...

backend/api/
├── rate_limit_admin.py      # 限流管理API
└── ...

backend/main.py              # 中间件注册
```

---

## ✅ 总结

- ✅ 自动防护恶意请求
- ✅ 零配置开箱即用
- ✅ 灵活的环境变量配置
- ✅ 完善的管理API
- ✅ 性能开销极小
- ✅ 支持白名单机制

**默认配置已经足够大多数场景使用！**

---

**更新时间**: 2025-12-29
**版本**: 1.0

