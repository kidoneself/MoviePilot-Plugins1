# 部署说明 - 2025-12-26

## 本次更新内容

### 1. 修复百度网盘目录匹配逻辑 ✅
**文件**: `backend/services/unified_transfer.py`

**问题**: 百度网盘转存时一直创建新文件夹

**修复**: 
- 更新目录匹配逻辑，同时检查 `is_dir` 和 `mount_details`（挂载点）
- 添加名称标准化处理（去除空格）
- 确保能正确识别 OpenList 中的挂载点和目录

### 2. 添加 Selenium 支持（闲鱼卡密管理） ⚠️ **需要重新构建镜像**
**文件**: `Dockerfile`, `backend/utils/xianyu_selenium.py`

**新增功能**:
- 安装 Google Chrome 浏览器
- 自动下载并安装 ChromeDriver
- 支持闲鱼卡密创建自动化功能

**重要变更**:
```dockerfile
# 新增 Chrome 安装
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# 新增 ChromeDriver 安装
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1-3) \
    ...
```

**代码优化**:
- ChromeDriver 自动查找逻辑（支持多版本、多路径）
- 降级失败时自动使用 Selenium Manager

---

## 部署步骤

### ⚠️ 重要提示
由于修改了 Dockerfile（添加了 Chrome 和 ChromeDriver），**必须重新构建镜像**，不能只重启容器！

### 方式1：完整重新构建（推荐）

```bash
# 1. 提交代码
git add .
git commit -m "修复百度网盘目录匹配 + 添加Selenium支持（闲鱼卡密）"
git push

# 2. 在服务器上拉取代码
ssh your-server
cd /path/to/file-link-monitor
git pull

# 3. 停止并删除旧容器
docker compose down

# 4. 重新构建镜像（这会安装 Chrome 和 ChromeDriver）
docker compose build --no-cache

# 5. 启动新容器
docker compose up -d

# 6. 查看启动日志
docker logs -f file-link-monitor
```

### 方式2：快速构建（如果不需要清除缓存）

```bash
cd /path/to/file-link-monitor
git pull
docker compose up -d --build
```

### 方式3：使用部署脚本（需要更新）

部署脚本 `deploy.sh` 目前只支持重启，不支持重新构建。
如果要使用脚本，需要手动构建一次：

```bash
# 首次部署（安装 Chrome）
docker compose down
docker compose build --no-cache
docker compose up -d

# 之后的代码更新可以使用
./deploy.sh
```

---

## 验证部署

### 1. 检查容器状态
```bash
docker ps | grep file-link-monitor
```

### 2. 验证 Chrome 安装
```bash
docker exec file-link-monitor google-chrome --version
docker exec file-link-monitor chromedriver --version
```

预期输出：
```
Google Chrome 130.x.x.x
ChromeDriver 130.x.x.x
```

### 3. 验证百度网盘修复
- 进行一次百度网盘转存操作
- 查看日志应显示：`✅ 找到目录: baidu`
- 不应出现：`⚠️ 目录不存在，正在创建`

```bash
docker logs -f file-link-monitor | grep "找到目录"
```

### 4. 测试闲鱼卡密功能
- 访问闲鱼卡密管理页面
- 尝试创建卡种（会启动 Selenium）
- 观察日志确认浏览器正常启动

---

## 构建时间预估

- 首次构建（下载 Chrome）：约 5-10 分钟
- 后续构建（有缓存）：约 2-3 分钟

---

## 常见问题

### Q1: 构建时 Chrome 下载很慢？
A: 可以使用国内镜像或提前下载好 deb 包

### Q2: ChromeDriver 版本不匹配？
A: 代码会自动查找多个版本，或使用 Selenium Manager 自动下载

### Q3: 只修复了目录匹配，不需要闲鱼功能，必须重新构建吗？
A: 
- 如果不使用闲鱼卡密功能：只需 `docker restart file-link-monitor`
- 如果要使用闲鱼功能：必须重新构建镜像

---

## 回滚方案

如果部署出现问题，可以回滚到之前的版本：

```bash
# 1. 回滚代码
git checkout HEAD~1

# 2. 重新构建
docker compose down
docker compose build
docker compose up -d

# 或者使用之前的镜像（如果有保存）
docker compose down
docker pull your-registry/file-link-monitor:previous-tag
docker compose up -d
```

---

## 更新日志

- **2025-12-26**: 修复百度网盘目录匹配 + 添加 Selenium/Chrome 支持
- 相关文件：`Dockerfile`, `backend/services/unified_transfer.py`, `backend/utils/xianyu_selenium.py`

