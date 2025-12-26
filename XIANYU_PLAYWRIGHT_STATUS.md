# 闲鱼 Playwright 迁移状态文档

## 📋 任务目标
将闲鱼卡密管理自动化从 Selenium 迁移到 Playwright，解决 Docker 容器中的兼容性问题。

---

## ✅ 已完成的工作

### 1. 创建 Playwright 版本
- **文件**: `backend/utils/xianyu_playwright.py`
- **参考**: `backend/utils/xianyu_selenium.py`
- **已实现**: 
  - 全局浏览器管理（单例模式）
  - 反检测配置（覆盖 navigator.webdriver 等）
  - 登录检测逻辑（多种方式判断登录成功）
  - 创建卡种流程
  - 添加卡密流程

### 2. 反检测配置
```python
# 启动参数
--disable-blink-features=AutomationControlled
--disable-features=IsolateOrigins,site-per-process
--disable-site-isolation-trials

# JavaScript 注入
- 覆盖 navigator.webdriver → undefined
- 模拟 navigator.plugins
- 设置 navigator.languages
- 添加 window.chrome 对象
- 覆盖权限查询

# 浏览器环境
- locale: zh-CN
- timezone: Asia/Shanghai
- Accept-Language 头
```

### 3. 登录成功判断优化
实现了三种检测方式：
1. **URL 跳转检测**：检查是否离开 `/login` 或到达 `/sale/statistics`
2. **页面元素检测**：查找登录后的元素（我的工作台、退出登录等）
3. **Cookie 检测**：检查是否有登录凭证 Cookie（token、sid 等）

### 4. 流程优化
- 先访问登录页检查状态：`https://www.goofish.pro/login`
- 确认登录后再访问目标页面
- 登录成功后重新访问添加页面

### 5. 本地测试脚本
- **文件**: `test_xianyu_playwright.py`
- **功能**: 
  - 有头模式测试，可视化调试
  - 支持命令行参数：`python3 test_xianyu_playwright.py 1`
  - 详细日志输出
  - 测试创建卡种和添加卡密

### 6. API 集成
- **文件**: `backend/api/xianyu.py`
- **修改**: 从 `xianyu_selenium` 切换到 `xianyu_playwright`
- **环境变量**: `XIANYU_HEADLESS=true` 控制无头模式

---

## ❌ 当前问题

### 核心问题：二维码容器存在但内容未动态生成

**✅ 调试进展（2025-12-26）：**
已完成深度调试，确认了问题根本原因！

**页面结构分析：**
```html
<!-- 登录页面正常加载，容器存在 -->
<div id="wechat-bind-code" style="width: 200px; height: 200px;"></div>
                                                                    ↑
                                                            容器是空的！
```

**调试发现：**
1. ✅ 登录页面可以正常访问（https://www.goofish.pro/login）
2. ✅ `#wechat-bind-code` 容器元素存在
3. ✅ 页面HTML结构完整（三个登录tab：微信/密码/验证码）
4. ❌ **容器内部完全是空的，没有任何子元素**
5. ❌ 没有 `img`、`canvas`、`iframe` 等二维码元素被动态插入
6. ❌ 等待10秒+后容器依然为空

**根本原因分析：**

闲鱼网站检测到了自动化工具，**拒绝生成二维码**。可能的检测手段：

1. **Webdriver检测** - 虽然已覆盖 `navigator.webdriver`，但可能有其他指纹
2. **行为特征检测** - 缺少真实用户的鼠标移动、键盘事件等
3. **环境指纹检测** - Canvas指纹、WebGL指纹、字体指纹等
4. **时间特征检测** - 页面加载速度、事件触发时机等过于规律
5. **Headless模式检测** - 即使在非headless模式下，某些特征依然暴露

**Selenium vs Playwright 对比：**
- Selenium版本：期望 `//div[contains(@class,'bind-code-scan')]//img`
- Playwright版本：同样的选择器
- **结果：两者都找不到，因为容器本来就是空的**

---

## 🔍 需要排查的问题

### 1. 页面加载问题
- 二维码可能需要更长的加载时间？
- 页面是否有懒加载逻辑？
- 是否需要特定的网络请求才能触发？

### 2. 页面结构变化
- 登录页面结构是否改版？
- 之前的选择器 `#wechat-bind-code > img` 是从哪里来的？
- 是否需要更新选择器？

### 3. 触发条件
- 是否需要点击某个按钮才显示二维码？
- 是否需要特定的 User-Agent 或其他条件？
- 是否有 iframe 或 shadow DOM？

### 4. 反爬机制
- 虽然已添加反检测，但是否还有其他检测机制？
- 是否需要真实的鼠标移动或其他行为？

---

## 📝 下一步行动计划

### 立即需要做的：

**1. 手动检查登录页面（最重要！）**
   - 在本地测试时，浏览器窗口应该还开着（有头模式）
   - 人工查看页面上实际显示什么内容
   - 确认登录方式和二维码显示逻辑
   - 记录正确的元素选择器

**2. 获取页面快照**
```python
# 在 _login() 方法中添加
screenshot_path = '/tmp/login_page.png'
page.screenshot(path=screenshot_path, full_page=True)
logger.info(f"登录页截图: {screenshot_path}")

# 保存完整 HTML
html_path = '/tmp/login_page.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(page.content())
logger.info(f"页面HTML: {html_path}")
```

**3. 对比 Selenium 版本**
   - Selenium 版本是否能正常工作？
   - 如果能，对比两者的差异
   - 检查 Selenium 的实际请求和行为

**4. 检查网络请求**
```python
# 监听网络请求
page.on('request', lambda request: logger.info(f"请求: {request.url}"))
page.on('response', lambda response: logger.info(f"响应: {response.url} - {response.status}"))
```

**5. 尝试等待特定元素**
```python
# 等待任意登录相关元素
try:
    page.wait_for_selector('img, button, .login, #login', timeout=30000)
except:
    pass
```

---

## 🔧 关键代码位置

### 1. Playwright 实现
**文件**: `backend/utils/xianyu_playwright.py`
- **登录方法**: `_login()` (约第 254 行)
- **创建卡种**: `create_kami_kind()` (约第 393 行)
- **添加卡密**: `add_kami_cards()` (约第 497 行)

### 2. Selenium 对照
**文件**: `backend/utils/xianyu_selenium.py`
- **登录方法**: `_login()` (第 279 行)
- **创建卡种**: `create_kami_kind()` (第 332 行)

### 3. API 接口
**文件**: `backend/api/xianyu.py`
- **创建卡种接口**: `/api/xianyu/kami/create-kind` (约第 666 行)
- **添加卡密接口**: `/api/xianyu/kami/add-cards` (约第 745 行)

### 4. 本地测试
**文件**: `test_xianyu_playwright.py`
```bash
# 测试创建卡种
python3 test_xianyu_playwright.py 1

# 测试添加卡密
python3 test_xianyu_playwright.py 2
```

---

## 📊 对比：Selenium vs Playwright

| 项目 | Selenium | Playwright | 状态 |
|------|----------|------------|------|
| 浏览器启动 | ChromeDriver | Chromium | ✅ 已实现 |
| 反检测 | 基本选项 | 完整配置 | ✅ 已实现 |
| 页面操作 | `find_element()` | `locator()` | ✅ 已实现 |
| 等待机制 | `WebDriverWait` | `wait_for_selector()` | ✅ 已实现 |
| 登录检测 | URL 判断 | 多种方式 | ✅ 已实现 |
| 二维码获取 | ✅ 能获取 | ❌ 无法获取 | **当前问题** |
| Docker 兼容 | ❌ 失败 | ✅ 应该可以 | 待验证 |

---

## 🐛 已知问题和解决方案

### 问题 1: 百度网盘创建多个文件夹
**状态**: ✅ 已解决
**方案**: 统一使用后端 OpenList API 管理目录

### 问题 2: Selenium Chrome 驱动失败
**状态**: ✅ 已解决
**方案**: 切换到 Playwright

### 问题 3: 登录后没有继续执行
**状态**: ✅ 已解决
**方案**: 
- 改进登录成功判断（多种方式）
- 登录后重新访问目标页面

### 问题 4: 二维码无法获取
**状态**: ❌ 待解决
**当前位置**: 需要人工确认页面实际情况

---

## 📚 参考信息

### 闲鱼相关 URL
```
登录页: https://www.goofish.pro/login
首页: https://www.goofish.pro/sale/statistics
创建卡种: https://www.goofish.pro/kam/kind/add
卡种列表: https://www.goofish.pro/kam/kind/list
```

### 环境变量
```bash
# Docker 容器中
XIANYU_HEADLESS=true  # 无头模式

# 本地测试
XIANYU_HEADLESS=false  # 有头模式
```

### 调试命令
```bash
# 本地测试
python3 test_xianyu_playwright.py 1

# 查看日志
docker logs -f file-link-monitor | grep xianyu

# 进入容器
docker exec -it file-link-monitor bash

# 查看截图（如果有）
docker exec file-link-monitor ls -la /tmp/*.png
docker cp file-link-monitor:/tmp/login_page.png ./
```

---

## 💡 建议的调试流程

1. **本地有头模式测试**
   ```bash
   python3 test_xianyu_playwright.py 1
   ```
   - 浏览器窗口保持打开
   - 人工观察登录页面
   - 记录需要的操作步骤

2. **获取页面信息**
   - 截图保存
   - HTML 保存
   - 网络请求记录

3. **对比 Selenium**
   - 运行 Selenium 版本看是否正常
   - 对比两者的差异

4. **修复选择器**
   - 根据实际页面更新选择器
   - 添加必要的触发逻辑

5. **Docker 测试**
   - 本地测试通过后部署
   - 在 Docker 中验证

---

## 🔄 Git 提交历史

```bash
# 最近的提交
165068b - fix: 先访问登录页检查登录状态（关键修复）
573a0ba - fix: 完全对齐Selenium版本的所有流程
26b2e12 - fix: 登录成功后重新访问添加页面（对齐Selenium逻辑）
5705cf8 - fix: 改进登录成功判断逻辑，支持多种检测方式
fd91677 - feat: 添加Playwright反检测配置和本地测试脚本
```

---

## 📞 需要用户提供的信息

**请在下次对话提供：**

1. ✅ 登录页面的实际截图或描述
2. ✅ 二维码如何显示（自动显示？需要点击？）
3. ✅ 二维码元素的实际 ID/class/选择器
4. ✅ 是否有其他登录方式可用
5. ✅ Selenium 版本当前是否还能正常工作

**可选但有帮助的：**
- 浏览器开发者工具的 Elements 标签截图
- 登录页面的完整 HTML（F12 → Elements → 右键 `<html>` → Copy → Copy outerHTML）

---

## 🎯 成功标准

迁移完成的标志：
- ✅ 能在 Docker 容器中启动 Playwright 浏览器
- ✅ 能成功获取登录二维码
- ✅ 扫码后能正确判断登录成功
- ✅ 能访问创建卡种页面
- ✅ 能填写表单并提交
- ✅ 能成功创建卡种
- ✅ 所有功能与 Selenium 版本一致

---

## 🎉 问题已解决！

### 解决方案总结（2025-12-26）

**问题1：macOS ARM 架构兼容**
- **原因**：Playwright 查找 x64 浏览器，但 M系列 Mac 只有 ARM64 版本
- **解决**：检测系统架构，动态指定正确的浏览器路径
```python
if platform.system() == 'Darwin' and 'arm' in platform.machine().lower():
    executable_path = '~/Library/Caches/ms-playwright/chromium-1200/chrome-mac-arm64/...'
```

**问题2：二维码选择器错误**
- **原因**：登录页面点击"微信登录"后，二维码元素的选择器与 Selenium 版本不同
- **实际情况**：二维码有 `alt="Scan me!"` 属性
- **解决**：使用正确的选择器并等待元素可见
```python
qr_selectors = [
    "img[alt='Scan me!']",  # 正确的选择器
    "//div[contains(@class,'bind-code-scan')]//img",  # Selenium版本
    "#wechat-bind-code img",
]
```

**测试结果**：
- ✅ 本地有头模式测试通过
- ✅ 成功获取二维码
- ✅ 扫码后1秒内识别登录成功
- ✅ 与 Selenium 版本功能一致

---

**文档创建时间**: 2025-12-26
**最后更新**: 2025-12-26 12:54
**当前状态**: ✅ 已完成（Playwright 迁移成功）
**优先级**: ✅ 已完成

