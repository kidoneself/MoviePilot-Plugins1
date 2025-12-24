# 三网盘统一转存API

## 概述

`PanTransferAPI` 提供了百度、夸克、迅雷三个网盘的统一转存接口，简化了多网盘转存的开发工作。

## 特性

- ✅ **统一接口**: 一套API适配三个网盘
- ✅ **统一结果**: 返回统一格式的结果，便于处理
- ✅ **自动轮询**: 自动处理异步任务轮询
- ✅ **文件夹处理**: 自动识别并获取文件夹内容
- ✅ **错误处理**: 统一的异常处理和错误消息

## 快速开始

### 1. 导入API

```python
from pan_transfer_api import PanTransferAPI
```

### 2. 初始化

#### 百度网盘
```python
api = PanTransferAPI(
    pan_type='baidu',
    credentials={
        'cookie': 'BDUSS=xxx; STOKEN=xxx; ...'
    }
)
```

#### 夸克网盘
```python
api = PanTransferAPI(
    pan_type='quark',
    credentials={
        'cookie': 'b-user-id=xxx; __puus=xxx; ...'
    }
)
```

#### 迅雷网盘
```python
api = PanTransferAPI(
    pan_type='xunlei',
    credentials={
        'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6...',
        'x_captcha_token': 'ck0.Uz8ySJeyYrC3csvzVinH5Hnh6nsN...',
        'x_client_id': 'Xqp0kJBXWhwaTpB6',
        'x_device_id': 'd765a49124d0b4c8d593d73daa738f51'
    }
)
```

### 3. 执行转存

```python
result = api.transfer(
    share_url='https://pan.baidu.com/s/1xxx',
    pass_code='xihk',  # 可选，无提取码时传 None
    target_path='/电影/华语/钢铁侠3'  # 目标路径（百度）或文件夹ID（夸克/迅雷）
)

if result['success']:
    print(f"✅ 转存成功！文件数: {result['file_count']}")
else:
    print(f"❌ 转存失败: {result['message']}")
```

## 参数说明

### transfer() 方法

| 参数 | 类型 | 说明 |
|------|------|------|
| `share_url` | `str` | 分享链接 |
| `pass_code` | `Optional[str]` | 提取码，无提取码时传 `None` |
| `target_path` | `str` | 目标路径（见下方说明） |

### target_path 格式

| 网盘 | 格式 | 示例 |
|------|------|------|
| **百度** | 完整路径 | `/电影/华语/钢铁侠3` |
| **夸克** | 文件夹ID | `fc187f00e5ef455db7aefd3833922a05` |
| **迅雷** | 文件夹ID | `VOgzQy9ZbNnxrTD95FYf29WGA1` |

> 注意：迅雷使用空字符串 `""` 表示根目录

## 返回结果

所有网盘返回统一格式：

```python
{
    'success': bool,           # 是否成功
    'pan_type': str,          # 网盘类型 ('baidu', 'quark', 'xunlei')
    'file_count': int,        # 转存的文件数量
    'file_ids': List[str],    # 转存后的文件ID列表
    'message': str,           # 状态消息
    'details': Dict           # 网盘特定的详细信息
}
```

### 成功示例

```python
{
    'success': True,
    'pan_type': 'baidu',
    'file_count': 5,
    'file_ids': ['123456', '234567', ...],
    'message': '转存成功',
    'details': {
        'task_id': 0,
        'target_path': '/电影/华语/钢铁侠3'
    }
}
```

### 失败示例

```python
{
    'success': False,
    'pan_type': 'quark',
    'file_count': 0,
    'file_ids': [],
    'message': '转存失败: 验证提取码失败',
    'details': {}
}
```

## 高级用法

### 批量转存

```python
def batch_transfer(share_links):
    """批量转存多个链接"""
    results = []
    
    for link_info in share_links:
        # 初始化API
        api = PanTransferAPI(
            pan_type=link_info['pan_type'],
            credentials=link_info['credentials']
        )
        
        # 执行转存
        result = api.transfer(
            share_url=link_info['share_url'],
            pass_code=link_info.get('pass_code'),
            target_path=link_info['target_path']
        )
        
        results.append(result)
    
    return results
```

### 从数据库读取认证信息

```python
from backend.models import PanCookie, get_session

def get_pan_api(pan_type: str):
    """从数据库获取认证信息并创建API实例"""
    session = get_session(engine)
    cookie_record = session.query(PanCookie).filter_by(pan_type=pan_type).first()
    
    if not cookie_record:
        raise Exception(f"数据库中没有{pan_type}网盘的认证信息")
    
    if pan_type == 'baidu':
        credentials = {'cookie': cookie_record.cookie}
    elif pan_type == 'quark':
        credentials = {'cookie': cookie_record.cookie}
    elif pan_type == 'xunlei':
        # 迅雷需要通过Playwright获取token
        # 或从cookie_record中解析JSON格式的token
        credentials = {
            'authorization': cookie_record.authorization,
            'x_captcha_token': cookie_record.x_captcha_token,
            'x_client_id': 'Xqp0kJBXWhwaTpB6',
            'x_device_id': cookie_record.device_id
        }
    
    return PanTransferAPI(pan_type=pan_type, credentials=credentials)
```

### 智能识别网盘类型

```python
import re

def detect_pan_type(share_url: str) -> str:
    """根据分享链接自动识别网盘类型"""
    if 'pan.baidu.com' in share_url:
        return 'baidu'
    elif 'pan.quark.cn' in share_url:
        return 'quark'
    elif 'pan.xunlei.com' in share_url:
        return 'xunlei'
    else:
        raise ValueError(f"无法识别的分享链接: {share_url}")

# 使用
pan_type = detect_pan_type(share_url)
api = get_pan_api(pan_type)
result = api.transfer(share_url, pass_code, target_path)
```

## 注意事项

### 1. 认证信息

- **百度/夸克**: Cookie可长期有效（几个月）
- **迅雷**: Token会过期，需要定期通过Playwright重新获取

### 2. 目标路径

- **百度**: 
  - 使用完整路径，如 `/电影/华语/钢铁侠3`
  - 如果路径不存在会自动创建
  
- **夸克/迅雷**: 
  - 使用文件夹ID
  - 需要提前创建文件夹或使用已知的文件夹ID
  - 建议建立 `路径 → ID` 的映射缓存

### 3. 异步任务

- 所有网盘的异步任务轮询已内置在API中
- 百度: 每500ms轮询，最多60秒
- 夸克: 每500ms轮询，最多60秒
- 迅雷: 每1秒轮询，最多60秒

### 4. 文件夹处理

API会自动检测：
- 如果分享链接根目录只有一个文件夹
- 自动获取该文件夹内部的文件列表
- 转存文件夹内的所有内容（而非外层文件夹本身）

## 完整示例

```python
from pan_transfer_api import PanTransferAPI

# 1. 准备认证信息（实际使用时从数据库读取）
baidu_credentials = {
    'cookie': 'BDUSS=xxx; STOKEN=xxx; ...'
}

# 2. 创建API实例
api = PanTransferAPI(pan_type='baidu', credentials=baidu_credentials)

# 3. 执行转存
result = api.transfer(
    share_url='https://pan.baidu.com/s/1E6nxtHn61sVLJVmWu3nndw',
    pass_code='xihk',
    target_path='/电影/华语/测试转存'
)

# 4. 处理结果
if result['success']:
    print(f"✅ 转存成功！")
    print(f"   网盘: {result['pan_type']}")
    print(f"   文件数: {result['file_count']}")
    print(f"   文件ID: {result['file_ids']}")
    
    # 保存到数据库或进行后续处理
    save_transfer_record(result)
else:
    print(f"❌ 转存失败: {result['message']}")
    
    # 记录错误日志
    log_error(result)
```

## 相关文档

- [三网盘API使用文档](./三网盘API使用文档.md) - 详细的API文档和curl示例
- [test_unified_transfer.py](./test_unified_transfer.py) - 完整的测试示例
- [test_baidu_full_transfer.py](./test_baidu_full_transfer.py) - 百度转存测试
- [test_quark_full_transfer.py](./test_quark_full_transfer.py) - 夸克转存测试
- [test_xunlei_full_transfer.py](./test_xunlei_full_transfer.py) - 迅雷转存测试

## License

MIT
