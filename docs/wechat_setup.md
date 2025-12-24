# 企业微信应用配置指南

## 一、企业微信后台配置

### 1. 创建应用
1. 登录企业微信管理后台：https://work.weixin.qq.com/
2. 导航到：**应用管理** → **自建** → **创建应用**
3. 填写应用信息：
   - 应用名称：剧集搜索助手
   - 应用logo：上传图片
   - 可见范围：选择需要使用的成员
4. 创建完成后，记录：
   - **AgentId**: 1000002
   - **Secret**: wwiLdw2Lcc6JBAhO3unzswP3GgJ3G4Ttf6nN9NQvtCw

### 2. 配置接收消息
1. 进入应用详情页
2. 点击 **接收消息** → **设置API接收**
3. 填写配置：
   - **URL**: `https://你的域名/api/wechat/callback`
   - **Token**: `zFYzEyQDonVV` （随机字符串，需与config.yaml一致）
   - **EncodingAESKey**: `SsZwYFgwmDOfAKIqqQ6GEPjU1ohLVLK2rNcISxYzbOn` （点击随机生成）
4. 点击 **保存**
5. 企业微信会发送验证请求到你的服务器，验证成功后显示"√ URL验证已通过"

### 3. 权限配置
1. **通讯录权限**：应用管理 → 权限管理 → 通讯录
   - 勾选"成员信息读取"
2. **应用权限**：应用详情 → 权限管理
   - 确保"发送消息"权限已开启

### 4. 获取企业ID
1. 导航到：**我的企业** → **企业信息**
2. 记录 **企业ID (CorpID)**: wwdf6106d7f613ab4d

---

## 二、服务器配置

### 1. 修改 config.yaml
```yaml
wechat:
  enabled: true
  corp_id: "wwdf6106d7f613ab4d"
  agent_id: 1000002
  secret: "wwiLdw2Lcc6JBAhO3unzswP3GgJ3G4Ttf6nN9NQvtCw"
  token: "zFYzEyQDonVV"
  encoding_aes_key: "SsZwYFgwmDOfAKIqqQ6GEPjU1ohLVLK2rNcISxYzbOn"
  callback_url: "https://你的域名/api/wechat/callback"  # 修改为实际域名
```

### 2. 安装依赖
```bash
pip install wechatpy==1.8.18
```

### 3. 重启服务
```bash
# Docker部署
docker-compose restart

# 或直接运行
python3 -m backend.main
```

### 4. 验证启动
查看日志，应该看到：
```
✅ 企业微信功能初始化成功
```

---

## 三、使用说明

### 支持的指令

#### 1. 搜索剧集
```
搜索 唐朝诡事录
```
返回该剧的三网盘分享链接

#### 2. 今日更新
```
今日更新
```
查看今天同步的剧集列表

#### 3. 生成链接（开发中）
```
链接 唐朝诡事录
```
自动生成分享链接

#### 4. 盘搜资源（开发中）
```
盘搜 关键词
```
搜索全网资源

#### 5. 帮助
```
帮助
```
显示指令列表

---

## 四、测试步骤

### 1. 验证URL
1. 在企业微信后台配置回调URL
2. 点击保存
3. 查看服务器日志：`✅ 企业微信URL验证成功`

### 2. 测试消息
1. 打开企业微信客户端
2. 找到应用"剧集搜索助手"
3. 发送：`帮助`
4. 应该收到指令列表回复

### 3. 测试搜索
1. 发送：`搜索 唐朝诡事录`
2. 应该收到分享链接（如果数据库中有该剧）

---

## 五、故障排查

### 问题1：URL验证失败
**原因**：
- 回调URL无法访问（防火墙/端口未开放）
- Token或EncodingAESKey配置错误

**解决**：
1. 确保域名可以公网访问（HTTPS）
2. 检查config.yaml中token和encoding_aes_key与企业微信后台一致
3. 查看服务器日志错误信息

### 问题2：发送消息无响应
**原因**：
- Access Token获取失败
- Secret配置错误

**解决**：
1. 查看日志是否有"获取Access Token失败"
2. 确认Secret正确
3. 检查企业微信后台应用权限

### 问题3：收不到消息
**原因**：
- 消息解密失败
- EncodingAESKey配置错误

**解决**：
1. 查看日志"消息签名验证失败"
2. 重新生成EncodingAESKey并更新config.yaml

---

## 六、日志查看

### Docker部署
```bash
docker logs -f file-link-monitor
```

### 直接运行
查看控制台输出，关键日志：
- `✅ 企业微信功能初始化成功`
- `📨 收到消息: type=text`
- `💬 用户消息: xxx -> xxx`
- `✅ 发送消息成功`

---

## 七、安全建议

1. **HTTPS必须**：企业微信要求回调URL必须是HTTPS
2. **Token保密**：不要泄露Secret和Token
3. **签名验证**：代码已实现消息签名验证，防止伪造消息
4. **权限最小化**：只授予必要的API权限

---

## 八、后续功能开发

当前已实现：
- ✅ 搜索剧集
- ✅ 今日更新
- ✅ 帮助信息

待开发：
- ⏳ 生成分享链接
- ⏳ 盘搜资源
- ⏳ 卡片消息展示
- ⏳ 主动推送通知（新剧更新）
