# 闲鱼创建商品页面使用指南

## 功能说明

这是一个独立的闲鱼商品创建页面，支持海报编辑和商品创建。

## 使用流程

### 1. 从媒体库进入
- 打开媒体库页面 `/media`
- 点击任意媒体项，打开详情抽屉
- 点击 **"🐟 创建闲鱼商品"** 按钮
- 自动跳转到创建商品页面 `/xianyu/create-product?media_id=xxx`

### 2. 编辑海报
左侧面板提供以下编辑选项：
- **上传海报**：可以手动上传自定义海报图片
- **中心标题**：设置中心显示的标题文字（如"4K超清"）
- **标题大小**：调整标题字号（20-100）
- **标题颜色**：选择标题颜色
- **集数**：输入集数信息（如"24"）
- **底部文字**：
  - 左上、左下（如"国语"、"中字"）
  - 右上、右下（如"蓝光"、"画质"）
- **左侧文字**：竖排显示的文字

### 3. 设置商品信息
- **商品标题**：默认使用媒体名称
- **商品描述**：默认使用媒体简介
- **价格(元)**：默认0.1元
- **库存**：默认100

### 4. 创建商品
- 点击 **"🐟 创建闲鱼商品"** 按钮
- 系统会：
  1. 将Canvas生成的海报上传到服务器
  2. 调用闲鱼API创建商品
  3. 自动上架到配置的店铺
  4. 保存到本地数据库
- 创建成功后自动跳转到商品列表页面

## 技术实现

### 后端API

#### 1. 只上传图片接口
```
POST /api/xianyu/product/upload-images-only
```
- 只上传图片文件，返回图片URL列表
- 不创建商品

#### 2. 从媒体创建商品接口
```
POST /api/xianyu/product/create-from-media
```
请求参数：
```json
{
  "media_id": 123,
  "title": "商品标题",
  "content": "商品描述",
  "price": 0.1,
  "express_fee": 0,
  "stock": 100,
  "image_urls": ["https://example.com/image1.png"]
}
```

- 如果提供 `image_urls`，使用前端上传的海报
- 如果 `image_urls` 为空，使用TMDB原图

### 前端页面

#### Canvas海报绘制
- 使用HTML5 Canvas API
- 支持实时预览
- 自动加载网盘Logo（百度、夸克、迅雷）
- 支持多种文字样式和徽章效果

#### 路由配置
```javascript
{
  path: '/xianyu/create-product',
  name: 'XianyuCreateProduct',
  component: XianyuCreateProduct
}
```

## 配置要求

在配置页面设置以下参数：
- `username1`: 闲鱼会员名1（必填）
- `username2`: 闲鱼会员名2（可选，双店铺）
- `goofish.app_key`: 闲鱼API Key
- `goofish.app_secret`: 闲鱼API Secret
- `product.price`: 默认价格（元）
- `product.stock`: 默认库存
- `product.express.fee`: 默认运费（元）
- `product.stuff.status`: 商品成色（100=全新）

## 常见问题

### Q: 点击创建按钮没有反应？
A: 请先上传或加载海报图片。

### Q: 创建失败提示"请先配置闲鱼会员名1"？
A: 请在配置页面设置 `username1` 参数。

### Q: 图片上传失败？
A: 检查：
1. 后端服务是否正常运行
2. `uploads/` 目录是否有写入权限
3. 文件大小是否超过限制

### Q: 商品创建成功但无法查看？
A: 请到商品列表页面 `/xianyu/products` 查看。

## 更新日志

### 2024-12-25
- ✅ 创建独立的商品创建页面
- ✅ 支持Canvas海报编辑
- ✅ 修复后端API重复创建问题
- ✅ 添加只上传图片的接口
- ✅ 媒体库按钮跳转到独立页面

