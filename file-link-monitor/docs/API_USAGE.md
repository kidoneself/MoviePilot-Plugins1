# 三网盘转存API使用指南

## 目录
- [方式1：使用PanTransferAPI（直接调用）](#方式1使用pantransferapi直接调用)
- [方式2：使用unified_transfer（OpenList集成）](#方式2使用unified_transferopenlist集成)
- [完整示例](#完整示例)

---

## 方式1：使用PanTransferAPI（直接调用）

### 基本用法

```python
from pan_transfer_api import PanTransferAPI

# 1. 准备认证信息
baidu_credentials = {'cookie': 'your_baidu_cookie_string'}
quark_credentials = {'cookie': 'your_quark_cookie_string'}
xunlei_credentials = {
    'authorization': 'Bearer xxx',
    'x_captcha_token': 'xxx',
    'x_device_id': 'xxx'
}

# 2. 创建API实例
api = PanTransferAPI(pan_type='baidu', credentials=baidu_credentials)

# 3. 调用转存
result = api.transfer(
    share_url='https://pan.baidu.com/s/1xxxxx?pwd=1234',
    pass_code='1234',
    target_path='/baidu/电影/动作片/钢铁侠3'
)

# 4. 处理结果
if result['success']:
    print(f"转存成功！文件数量：{result['file_count']}")
    print(f"文件ID：{result['file_ids']}")
else:
    print(f"转存失败：{result['message']}")
```

### 三网盘示例

```python
from pan_transfer_api import PanTransferAPI

# 分享链接
share_links = {
    'baidu': {
        'url': 'https://pan.baidu.com/s/1xxxxx?pwd=1234',
        'pass_code': '1234'
    },
    'quark': {
        'url': 'https://pan.quark.cn/s/xxxxx',
        'pass_code': None
    },
    'xunlei': {
        'url': 'https://pan.xunlei.com/s/xxxxx',
        'pass_code': None
    }
}

# 认证信息
credentials = {
    'baidu': {'cookie': 'your_baidu_cookie'},
    'quark': {'cookie': 'your_quark_cookie'},
    'xunlei': {
        'authorization': 'Bearer xxx',
        'x_captcha_token': 'xxx',
        'x_device_id': 'xxx'
    }
}

# 目标路径
target_paths = {
    'baidu': '/baidu/电影/动作片/钢铁侠3',
    'quark': '/kuake/电影/动作片/钢铁侠3',
    'xunlei': '/xunlei/电影/动作片/钢铁侠3'
}

# 转存到三个网盘
for pan_type in ['baidu', 'quark', 'xunlei']:
    api = PanTransferAPI(pan_type=pan_type, credentials=credentials[pan_type])
    
    result = api.transfer(
        share_url=share_links[pan_type]['url'],
        pass_code=share_links[pan_type]['pass_code'],
        target_path=target_paths[pan_type]
    )
    
    print(f"{pan_type}: {'成功' if result['success'] else '失败'}")
```

---

## 方式2：使用unified_transfer（OpenList集成）

这个方式会自动处理：
- OpenList路径管理
- 自动创建文件夹
- 获取文件夹ID
- 三网盘统一接口

### 基本用法

```python
from unified_transfer import UnifiedTransfer

# 1. 创建实例
transfer = UnifiedTransfer()

# 2. 调用转存（自动处理路径）
result = transfer.transfer_from_share_link(
    share_url='https://pan.baidu.com/s/1xxxxx?pwd=1234',
    pass_code='1234',
    target_path='/电影/动作片/钢铁侠3',  # 不需要网盘前缀
    pan_type='baidu'
)

if result['success']:
    print(f"转存成功！文件数量：{result['file_count']}")
```

### 三网盘同时转存

```python
from unified_transfer import UnifiedTransfer

transfer = UnifiedTransfer()

share_links = {
    'baidu': {
        'url': 'https://pan.baidu.com/s/1xxxxx?pwd=1234',
        'pass_code': '1234'
    },
    'quark': {
        'url': 'https://pan.quark.cn/s/xxxxx',
        'pass_code': None
    },
    'xunlei': {
        'url': 'https://pan.xunlei.com/s/xxxxx',
        'pass_code': None
    }
}

# 统一路径（自动适配三网盘）
target_path = '/电影/动作片/钢铁侠3'

results = {}
for pan_type, link_info in share_links.items():
    result = transfer.transfer_from_share_link(
        share_url=link_info['url'],
        pass_code=link_info['pass_code'],
        target_path=target_path,
        pan_type=pan_type
    )
    results[pan_type] = result
    
    print(f"{pan_type}: {'✅' if result['success'] else '❌'}")

# 查看总结
success_count = sum(1 for r in results.values() if r['success'])
print(f"\n成功率: {success_count}/{len(results)}")
```

---

## 完整示例

### 示例1：从数据库读取认证信息

```python
import os
import yaml
from pan_transfer_api import PanTransferAPI
from models import init_database, get_session, PanCookie

# 1. 加载配置
config_path = 'config.yaml'
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 2. 初始化数据库
engine = init_database(config['database'])
db_session = get_session(engine)

# 3. 从数据库读取认证信息
baidu_record = db_session.query(PanCookie).filter_by(
    pan_type='baidu', 
    is_active=True
).first()

# 4. 转存
api = PanTransferAPI(pan_type='baidu', credentials={'cookie': baidu_record.cookie})

result = api.transfer(
    share_url='https://pan.baidu.com/s/1xxxxx?pwd=1234',
    pass_code='1234',
    target_path='/baidu/电影/动作片/钢铁侠3'
)

print(f"结果: {result}")
```

### 示例2：批量转存多个分享链接

```python
from pan_transfer_api import PanTransferAPI

# 认证信息
baidu_cookie = 'your_cookie_here'

# 批量分享链接
movies = [
    {
        'name': '钢铁侠3',
        'url': 'https://pan.baidu.com/s/1xxxxx?pwd=1234',
        'pass_code': '1234',
        'target': '/baidu/电影/动作片/钢铁侠3'
    },
    {
        'name': '蜘蛛侠',
        'url': 'https://pan.baidu.com/s/1yyyyy?pwd=5678',
        'pass_code': '5678',
        'target': '/baidu/电影/动作片/蜘蛛侠'
    }
]

# 创建API实例
api = PanTransferAPI(pan_type='baidu', credentials={'cookie': baidu_cookie})

# 批量转存
results = []
for movie in movies:
    print(f"正在转存：{movie['name']}...")
    
    result = api.transfer(
        share_url=movie['url'],
        pass_code=movie['pass_code'],
        target_path=movie['target']
    )
    
    results.append({
        'name': movie['name'],
        'success': result['success'],
        'file_count': result.get('file_count', 0)
    })
    
    if result['success']:
        print(f"  ✅ 成功！文件数：{result['file_count']}")
    else:
        print(f"  ❌ 失败：{result['message']}")

# 总结
success = sum(1 for r in results if r['success'])
print(f"\n转存完成：{success}/{len(movies)} 成功")
```

### 示例3：结合OpenList创建文件夹

```python
import requests
from pan_transfer_api import PanTransferAPI

# OpenList配置
OPENLIST_URL = "http://10.10.10.17:5255"
OPENLIST_TOKEN = "your_token_here"

def create_folder(path):
    """在OpenList创建文件夹"""
    url = f"{OPENLIST_URL}/api/fs/mkdir"
    headers = {
        'Authorization': OPENLIST_TOKEN,
        'Content-Type': 'application/json'
    }
    data = {"path": path}
    response = requests.post(url, json=data, headers=headers)
    return response.json()

# 1. 先创建文件夹
folder_path = '/baidu/电影/动作片/钢铁侠3'
folder_result = create_folder(folder_path)
print(f"创建文件夹: {folder_result.get('message')}")

# 2. 等待1-3秒让文件夹同步
import time
time.sleep(3)

# 3. 转存文件
api = PanTransferAPI(pan_type='baidu', credentials={'cookie': 'your_cookie'})
result = api.transfer(
    share_url='https://pan.baidu.com/s/1xxxxx?pwd=1234',
    pass_code='1234',
    target_path=folder_path
)

print(f"转存结果: {'成功' if result['success'] else '失败'}")
```

---

## 返回结果格式

### 成功时

```python
{
    'success': True,
    'pan_type': 'baidu',
    'file_count': 21,
    'file_ids': ['123456789', '987654321', ...],
    'message': '转存成功',
    'details': {
        'task_id': 0,  # 0表示同步完成，其他表示异步任务ID
        'target_path': '/baidu/电影/动作片/钢铁侠3'
    }
}
```

### 失败时

```python
{
    'success': False,
    'pan_type': 'baidu',
    'file_count': 0,
    'file_ids': [],
    'message': '转存失败: 转存路径不存在',
    'details': {}
}
```

---

## 注意事项

### 1. 路径格式

**百度：**
- 使用 `/baidu/` 前缀（代码会自动去掉）
- 或直接使用 `/电影/动作片/钢铁侠3`

**夸克：**
- 需要提供文件夹ID（通过OpenList获取）
- 或使用 `/kuake/` 前缀

**迅雷：**
- 需要提供文件夹ID
- 或使用 `/xunlei/` 前缀

### 2. 认证信息

**百度：**
```python
{'cookie': 'BDUSS=xxx; STOKEN=xxx; ...'}
```

**夸克：**
```python
{'cookie': '__pus=xxx; __puus=xxx; ...'}
```

**迅雷：**
```python
{
    'authorization': 'Bearer eyJhbGciOiJSUzI1NiIs...',
    'x_captcha_token': 'xxx',
    'x_device_id': 'xxx'
}
```

### 3. 文件夹同步

创建文件夹后建议**等待1-3秒**再转存，让文件夹有时间同步到各网盘。

### 4. 错误处理

```python
try:
    result = api.transfer(...)
    if result['success']:
        print("成功")
    else:
        print(f"失败: {result['message']}")
except Exception as e:
    print(f"异常: {e}")
```

---

## 核心文件

- `pan_transfer_api.py` - 核心API（三网盘转存）
- `unified_transfer.py` - OpenList集成接口
- `get_xunlei_token.py` - 迅雷token获取工具

---

## 相关文档

- `README_PAN_TRANSFER.md` - 功能说明
- `三网盘API使用文档.md` - API详细文档
- `test_full_flow_ironman3.py` - 完整示例
