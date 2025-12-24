# 三网盘 API 使用文档

## 概览对比

| 网盘 | 认证方式 | Token 获取 | 需要浏览器 | 复杂度 |
|------|---------|-----------|-----------|--------|
| **百度** | Cookie + bdstoken | 访问页面正则提取 | ❌ | ⭐ 简单 |
| **夸克** | Cookie only | 不需要 | ❌ | ⭐ 最简单 |
| **迅雷** | Cookie + authorization + x-captcha-token | Playwright 监听请求 | ✅ | ⭐⭐⭐ 复杂 |

---

## 1. 百度网盘

### 1.1 创建分享链接

**API**: `POST https://pan.baidu.com/share/set`

**认证**:
- Cookie（登录凭证）
- bdstoken（动态 token，从页面提取）

**bdstoken 获取**:
```python
def get_bdstoken(cookies):
    """从网盘页面提取 bdstoken"""
    url = "https://pan.baidu.com/disk/main"
    response = requests.get(url, cookies=cookies)
    
    # 正则匹配
    patterns = [
        r'"bdstoken"\s*:\s*"([^"]+)"',
        r'bdstoken\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, response.text)
        if match:
            return match.group(1)
```

**请求参数**:
```python
data = {
    "fid_list": json.dumps([file_id]),  # 文件ID数组（JSON字符串）
    "schannel": 4,
    "channel_list": "[]",
    "period": 0  # 0=永久, 7=7天
}
params = {
    "bdstoken": bdstoken
}
```

**响应示例**:
```json
{
  "errno": 0,
  "request_id": 123456789,
  "info": {
    "link": "https://pan.baidu.com/s/1abc123",
    "shortlink": "https://pan.baidu.com/s/1abc123"
  }
}
```

### 1.2 创建文件夹

**API**: `POST https://pan.baidu.com/api/create`

**特点**: ✅ 使用**路径**而非 ID（不需要父文件夹 ID）

**请求参数**:
```python
# URL 参数
params = {
    "a": "commit",
    "bdstoken": bdstoken
}

# 表单数据（URL 编码）
data = {
    "path": "/电影/华语/新文件夹",  # 完整路径
    "isdir": 1,
    "block_list": "[]"
}
```

**响应示例**:
```json
{
  "errno": 0,
  "path": "/电影/华语/新文件夹",
  "ctime": 1734760000,
  "mtime": 1734760000
}
```

**实现位置**: `test_baidu_api.py::create_directory()`

### 1.3 转存文件（从分享链接）

**场景**: 从别人的分享链接转存文件到自己的网盘

#### 完整流程（三步）

**步骤 1: 验证提取码（获取 sekey）**

**API**: `POST https://pan.baidu.com/share/verify`

**参数**:
```python
# URL 参数
params = {
    "surl": "E6nxtHn61sVLJVmWu3nndw",  # 从分享链接提取（去掉开头的'1'）
    "channel": "chunlei",
    "web": "1",
    "app_id": "250528",
    "clienttype": "0"
}

# 表单数据
data = {
    "pwd": "uju4"  # 提取码
}
```

**响应**（设置 BDCLND Cookie）:
```json
{
  "errno": 0,
  "request_id": 152464207317440757,
  "randsk": "wpVW4OFNmDsUNUEoDUrZhiYqXmdfSO9dMEwgDHOIiCs%3D"
}
```

**关键**: 验证成功后，服务器会设置 `BDCLND` Cookie，其值就是转存需要的 `sekey` 参数

**步骤 2: 获取分享文件列表**

**API**: `GET https://pan.baidu.com/share/list`

**参数**:
```python
params = {
    "shorturl": "E6nxtHn61sVLJVmWu3nndw",  # 同步骤1（不带'1'）
    "web": "5",
    "app_id": "250528",
    "page": 1,
    "num": 20,
    "order": "time",
    "root": 1,              # 1=根目录
    "bdstoken": bdstoken,
    "channel": "chunlei",
    "web": "1",
    "clienttype": "0"
}
```

**响应**（关键字段）:
```json
{
  "errno": 0,
  "list": [
    {
      "fs_id": "534269644386630",          // ⭐ 文件ID（转存需要）
      "server_filename": "艾米丽在巴黎 第5季",
      "isdir": "1",                        // ⭐ 1=文件夹
      "path": "/电视剧/艾米丽在巴黎 第5季",
      "size": "0"
    }
  ],
  "share_id": 18107935273,               // ⭐ 转存需要的 shareid
  "uk": 1100040907286                    // ⭐ 转存需要的 from (分享者ID)
}
```

**步骤 2.5: 获取文件夹内容**（可选，如果要转存文件夹内部文件）

**API**: `GET https://pan.baidu.com/share/list`（同步骤2，添加 `dir` 参数）

**场景**: 如果根目录只有一个文件夹，可以进入文件夹获取内部文件列表

**参数**:
```python
params = {
    "shorturl": "E6nxtHn61sVLJVmWu3nndw",
    "dir": f"/sharelink{uk}-{folder_fs_id}/{folder_name}",  # ⭐ 文件夹路径
    "root": 0,              # 0=非根目录
    "page": 1,
    "num": 100,
    "bdstoken": bdstoken,
    "web": "1",
    "channel": "chunlei",
    "app_id": "250528",
    "clienttype": "0"
}

# 示例：dir="/sharelink1099580542746-915272190789775/艾米丽在巴黎"
```

**响应**:
```json
{
  "errno": 0,
  "list": [
    {"fs_id": "978112004172056", "server_filename": "S01", "isdir": 1},
    {"fs_id": "220781745600957", "server_filename": "S05E01.mp4", "isdir": 0},
    {"fs_id": "649250816823771", "server_filename": "S05E02.mp4", "isdir": 0}
    // ... 更多文件
  ]
}
```

**步骤 3: 转存文件**

**API**: `POST https://pan.baidu.com/share/transfer`

**参数**:
```python
# URL 参数
params = {
    "shareid": 18107935273,      # 从步骤2获取
    "from": 1100040907286,       # 从步骤2获取（uk字段）
    "sekey": "wpVW4OFNmDs...",   # 从步骤1获取（BDCLND Cookie）
    "ondup": "newcopy",          # 重复处理：newcopy=创建副本
    "async": 1,
    "channel": "chunlei",
    "web": "1",
    "app_id": "250528",
    "bdstoken": bdstoken,
    "clienttype": "0"
}

# 表单数据（URL 编码）
data = {
    "fsidlist": "[534269644386630]",         # ⭐ 文件ID列表（JSON字符串）
    "path": "/测试/测试文件夹"                 # ⭐ 目标路径
}
```

**响应A**（少量文件，同步完成）:
```json
{
  "errno": 0,
  "extra": {
    "list": [
      {
        "from": "/艾米丽在巴黎",
        "from_fs_id": 915272190789775,
        "to": "/测试/测试文件夹/艾米丽在巴黎",
        "to_fs_id": 1056246168912270
      }
    ]
  },
  "task_id": 0  // ✅ 0=同步完成，无需轮询
}
```

**响应B**（大量文件，异步任务）:
```json
{
  "errno": 0,
  "newno": "",
  "request_id": 3167876635400350077,
  "show_msg": "文件转存中",
  "task_id": "469726478407857"  // ⭐ 非0=异步任务，需要轮询
}
```

**步骤 4: 轮询任务状态**（仅当 `task_id != 0` 时需要）

**API**: `GET https://pan.baidu.com/share/taskquery`

**参数**:
```python
params = {
    "taskid": "469726478407857",  # 从步骤3获取
    "channel": "chunlei",
    "web": "1",
    "app_id": "250528",
    "bdstoken": bdstoken,
    "clienttype": "0"
}
```

**轮询策略**:
- 间隔：每 **1秒** 轮询一次
- 超时：最多等待 **60秒**

**响应**（成功）:
```json
{
  "errno": 0,
  "request_id": 152594113859339670,
  "task_errno": 0,
  "status": "success",  // ⭐ "success"=完成
  "list": [
    {
      "from": "/我的资源/艾米丽在巴黎/S05E01.mp4",
      "from_fs_id": 220781745600957,
      "to": "/测试/测试文件夹/S05E01.mp4",
      "to_fs_id": 568832574014676
    },
    {
      "from": "/我的资源/艾米丽在巴黎/S05E02.mp4",
      "from_fs_id": 649250816823771,
      "to": "/测试/测试文件夹/S05E02.mp4",
      "to_fs_id": 30653622941725
    }
    // ... 更多文件
  ],
  "total": 14  // 转存文件总数
}
```

**状态说明**:
- `status: "success"` → 转存完成 ✅
- `status: "running"` → 进行中，继续轮询
- `status: "failed"` → 转存失败 ❌

#### 关键参数说明

| 参数 | 来源 | 说明 |
|------|------|------|
| `surl/shorturl` | 分享URL | 从 `https://pan.baidu.com/s/1E6nxtHn61sVLJVmWu3nndw` 提取，**去掉开头的'1'** |
| `pwd` | 用户输入 | 分享提取码 |
| `sekey` | BDCLND Cookie | 验证提取码后服务器设置的 Cookie |
| `share_id` | 文件列表API | 分享ID |
| `uk (from)` | 文件列表API | 分享者用户ID |
| `fs_id` | 文件列表API | 要转存的文件ID |
| `path` | **用户指定** | 目标文件夹路径 ⭐ |
| `bdstoken` | 页面提取 | 动态token |

#### 实现要点

```python
def save_from_baidu_share(share_url, pwd, target_path, cookie, bdstoken, enter_folder=True):
    """
    从分享链接转存文件
    
    Args:
        share_url: 分享链接（如 https://pan.baidu.com/s/1NBfxUQc0Q6ssVNgoQ2JoIA）
        pwd: 提取码
        target_path: 目标路径（如 /测试/测试文件夹）
        cookie: 百度网盘Cookie
        bdstoken: 从页面提取的token
        enter_folder: 如果根目录是文件夹，是否进入内部获取文件列表
    """
    import re
    import requests
    import json
    import time
    from urllib.parse import unquote
    
    # 1. 提取 shorturl（去掉'1'）
    match = re.search(r'/s/1([^?]+)', share_url)
    shorturl = match.group(1)
    
    # 2. 验证提取码，获取 sekey
    session = requests.Session()
    session.cookies.update(cookie)
    
    # 清除旧的 BDCLND Cookie
    if 'BDCLND' in session.cookies:
        del session.cookies['BDCLND']
    
    verify_url = "https://pan.baidu.com/share/verify"
    verify_params = {"surl": shorturl, "channel": "chunlei", "web": "1", "app_id": "250528"}
    verify_data = {"pwd": pwd}
    
    session.post(verify_url, params=verify_params, data=verify_data)
    
    # 获取 sekey（需要解码，因为 Cookie 中是 URL 编码的）
    sekey_raw = None
    for cookie in session.cookies:
        if cookie.name == "BDCLND":
            sekey_raw = cookie.value
            break
    sekey = unquote(sekey_raw)  # ⭐ 关键：解码后传给 requests
    
    # 3. 获取文件列表
    list_url = "https://pan.baidu.com/share/list"
    list_params = {
        "shorturl": shorturl,
        "root": 1,
        "page": 1,
        "num": 100,
        "bdstoken": bdstoken,
        "web": "1",
        "channel": "chunlei",
        "app_id": "250528"
    }
    
    list_resp = session.get(list_url, params=list_params).json()
    
    share_id = list_resp["share_id"]
    uk = list_resp["uk"]
    file_list = list_resp["list"]
    
    # 3.5. 如果是文件夹，获取内部文件列表
    if enter_folder and len(file_list) == 1 and file_list[0].get('isdir') in [1, '1']:
        folder = file_list[0]
        folder_name = folder['server_filename']
        folder_fs_id = folder['fs_id']
        
        # 构造 dir 路径
        dir_path = f"/sharelink{uk}-{folder_fs_id}/{folder_name}"
        
        list_params['dir'] = dir_path
        list_params['root'] = 0
        
        folder_resp = session.get(list_url, params=list_params).json()
        file_list = folder_resp["list"]
    
    fs_ids = [f["fs_id"] for f in file_list]
    
    # 4. 转存
    transfer_url = "https://pan.baidu.com/share/transfer"
    transfer_params = {
        "shareid": share_id,
        "from": uk,
        "sekey": sekey,
        "ondup": "newcopy",
        "async": 1,
        "bdstoken": bdstoken,
        "channel": "chunlei",
        "web": "1",
        "app_id": "250528"
    }
    
    transfer_data = {
        "fsidlist": json.dumps(fs_ids),
        "path": target_path
    }
    
    result = session.post(transfer_url, params=transfer_params, data=transfer_data).json()
    
    if result["errno"] != 0:
        raise Exception(f"转存失败: {result}")
    
    task_id = result.get('task_id', 0)
    
    # 5. 如果是异步任务，轮询
    if task_id and task_id != 0:
        task_url = "https://pan.baidu.com/share/taskquery"
        task_params = {
            "taskid": task_id,
            "channel": "chunlei",
            "web": "1",
            "app_id": "250528",
            "bdstoken": bdstoken
        }
        
        for retry in range(60):  # 最多等待60秒
            time.sleep(1)
            
            task_resp = session.get(task_url, params=task_params).json()
            
            if task_resp.get('errno') != 0:
                raise Exception(f"查询任务失败: {task_resp}")
            
            status = task_resp.get('status')
            
            if status == 'success':
                return task_resp['list']  # 转存结果列表
            elif status == 'failed':
                raise Exception(f"任务失败: {task_resp}")
        
        raise Exception(f"任务超时")
    else:
        # 同步完成
        return result["extra"]["list"]
```

#### 业务场景

**场景**: 通过盘搜找到分享链接 → 转存到自己网盘

```
1. 用户搜索"艾米丽在巴黎" → 盘搜返回分享链接
2. 输入提取码 → 验证并获取 sekey
3. 获取分享文件列表 → 提取 share_id、uk、fs_id
4. (可选) 如果是文件夹 → 进入文件夹获取内部文件列表
5. 转存到指定路径 → 发起转存请求
6. (如果是大量文件) → 轮询任务状态直到完成 ✅
7. 使用 OpenList 管理转存后的文件
```

#### 关键要点

1. **sekey 处理**：Cookie 中的 `BDCLND` 是 URL 编码的，需要先 `unquote()` 再传给 `requests`
2. **文件夹路径格式**：`/sharelink{uk}-{folder_fs_id}/{folder_name}`
3. **同步 vs 异步**：
   - 少量文件 → `task_id: 0`，同步完成
   - 大量文件 → `task_id: "xxx"`，异步任务，需要轮询
4. **轮询策略**：每 1 秒轮询一次，最多等待 60 秒

**实现位置**: `test_baidu_full_transfer.py::transfer_from_share()`

---

## 2. 夸克网盘

### 2.1 创建分享链接

**API**: `POST https://drive-pc.quark.cn/1/clouddrive/share`

**认证**: ✅ 只需 Cookie（最简单）

**请求参数**:
```python
headers = {
    "cookie": cookie_string,
    "content-type": "application/json"
}

data = {
    "file_ids": [file_id],
    "title": "分享标题",
    "url_type": 1,
    "expired_type": 1  # 1=永久
}
```

**响应示例**（异步任务）:
```json
{
  "status": 200,
  "code": 0,
  "data": {
    "task_id": "abc123..."
  }
}
```

**轮询任务状态**:
```python
# GET https://drive-pc.quark.cn/1/clouddrive/task
params = {"task_id": task_id, "retry_index": 0}

# 成功后响应
{
  "status": 200,
  "data": {
    "status": 2,  # 2=完成
    "share_url": "https://pan.quark.cn/s/xxx",
    "passcode": "1234"
  }
}
```

### 2.2 创建文件夹

**API**: `POST https://drive-pc.quark.cn/1/clouddrive/file`

**特点**: ✅ 需要**父文件夹 ID**，❗ 两步流程（创建临时 → 重命名）

**步骤 1: 创建临时文件夹**:
```python
import time

# 生成临时文件名
temp_name = f"新建文件夹-{time.strftime('%y%m%d-%H%M%S%f')[:-3]}"

data = {
    "pdir_fid": parent_folder_id,  # 父文件夹ID
    "file_name": temp_name,
    "dir_path": "",
    "dir_init_lock": False
}
```

**响应**:
```json
{
  "status": 200,
  "code": 0,
  "data": {
    "fid": "386ac31c517c43eb8d009f7c216a7c32",
    "finish": true
  }
}
```

**步骤 2: 重命名**:
```python
# POST https://drive-pc.quark.cn/1/clouddrive/file/rename
data = {
    "fid": folder_id,  # 刚创建的文件夹ID
    "file_name": "最终文件夹名"
}
```

**实现位置**: `test_quark_api.py::create_folder()`

### 2.3 转存文件（从分享链接）

**场景**: 从别人的分享链接转存文件到自己的网盘

#### 完整流程（三步）

**步骤 1: 获取分享文件列表**

**API**: `GET https://drive-h.quark.cn/1/clouddrive/share/sharepage/detail`

**参数**:
```python
params = {
    "pwd_id": "7729f43ad71d",        # 从分享链接解析
    "stoken": "EQj0I52yUEz0...",     # 访问分享页面获取
    "pdir_fid": "28c6a02e22c7...",   # 源文件夹ID（分享的文件夹）
    "_page": 1,
    "_size": 50,
    "_fetch_total": 1
}
```

**响应**（关键字段）:
```json
{
  "status": 200,
  "code": 0,
  "data": {
    "list": [
      {
        "fid": "0a177b384bde...",           // 文件ID
        "file_name": "Iron.Man.3.2013.mkv",
        "share_fid_token": "edc5489fa0e...", // ⭐ 转存需要的token
        "size": 13355264922,
        "file_type": 1
      }
    ]
  }
}
```

**步骤 2: 发起转存任务**

**API**: `POST https://drive-pc.quark.cn/1/clouddrive/share/sharepage/save`

**两种模式**:

**模式A: 保存全部文件**
```python
data = {
    "pwd_id": "7729f43ad71d",
    "stoken": "EQj0I52y...",
    "pdir_fid": "28c6a02e22c7...",      # 源文件夹ID
    "to_pdir_fid": "a0c40531ee21...",   # 目标文件夹ID（保存到哪里）⭐
    "pdir_save_all": True,              # 保存整个文件夹
    "scene": "link"
}
```

**模式B: 选择性保存**（更灵活）
```python
# 使用步骤1获取的 fid 和 share_fid_token
data = {
    "pwd_id": "7729f43ad71d",
    "stoken": "EQj0I52y...",
    "pdir_fid": "28c6a02e22c7...",
    "to_pdir_fid": "a0c40531ee21...",   # 目标文件夹ID
    "fid_list": [                       # 选择的文件ID列表
        "0a177b384bde...",
        "c41a5e3d50b6..."
    ],
    "fid_token_list": [                 # 对应的token列表
        "edc5489fa0e...",
        "aa6b321507..."
    ],
    "scene": "link"
}
```

**响应**（异步任务）:
```json
{
  "status": 200,
  "code": 0,
  "data": {
    "task_id": "78b44209216347a98298fc9fd99f31d1"
  },
  "metadata": {
    "tq_gap": 500  // 建议轮询间隔（毫秒）
  }
}
```

**步骤 3: 轮询任务状态**

**API**: `GET https://drive-pc.quark.cn/1/clouddrive/task`

**参数**:
```python
params = {
    "task_id": "78b44209216347a98298fc9fd99f31d1",
    "retry_index": 0  # 轮询次数：0, 1, 2...
}
```

**状态判断**:
- `status: 0` - 进行中，继续轮询
- `status: 1` - 失败
- `status: 2` - 成功 ✅

**成功响应**:
```json
{
  "status": 200,
  "code": 0,
  "data": {
    "task_id": "78b44209216347a98298fc9fd99f31d1",
    "status": 2,
    "finished_at": 1766290845716,
    "save_as": {
      "to_pdir_fid": "a0c40531ee21...",
      "save_as_sum_num": 2,           // 转存文件数量
      "save_as_top_fids": [           // 转存后的文件ID列表
        "0f5be79b53dc...",
        "b1898e52f018..."
      ],
      "to_pdir_name": "钢铁侠3",      // 目标文件夹名
      "remain_capacity": 24954977363935
    }
  }
}
```

#### 关键参数说明

| 参数 | 来源 | 说明 |
|------|------|------|
| `pwd_id` | 分享URL | 分享链接ID（如：https://pan.quark.cn/s/**7729f43ad71d**） |
| `stoken` | 访问分享页面 | 分享访问token |
| `pdir_fid` | 分享详情API | 源文件夹ID |
| `to_pdir_fid` | **用户指定** | 目标文件夹ID（需要缓存或动态获取）⭐ |
| `share_fid_token` | 文件列表API | 每个文件的转存token |

#### 实现要点

```python
def save_from_share(pwd_id, stoken, pdir_fid, to_pdir_fid, 
                    cookie, save_all=True, selected_fids=None):
    """
    从分享链接转存文件
    
    Args:
        save_all: True=保存全部，False=选择性保存
        selected_fids: 选择性保存时的文件ID列表（需包含fid_token）
    """
    if not save_all:
        # 1. 获取文件列表（包含share_fid_token）
        files = get_share_file_list(pwd_id, stoken, pdir_fid, cookie)
        
        # 2. 筛选用户选择的文件
        selected_files = [f for f in files if f['fid'] in selected_fids]
        
        data = {
            "fid_list": [f['fid'] for f in selected_files],
            "fid_token_list": [f['share_fid_token'] for f in selected_files]
        }
    else:
        data = {"pdir_save_all": True}
    
    # 3. 发起转存
    data.update({
        "pwd_id": pwd_id,
        "stoken": stoken,
        "pdir_fid": pdir_fid,
        "to_pdir_fid": to_pdir_fid,
        "scene": "link"
    })
    
    response = requests.post(url, json=data, cookies=cookie)
    task_id = response.json()["data"]["task_id"]
    
    # 4. 轮询任务（每500ms，最多60秒）
    for retry in range(120):
        task = check_task(task_id, retry, cookie)
        if task['status'] == 2:  # 成功
            return task['save_as']
        elif task['status'] == 1:  # 失败
            raise Exception("转存失败")
        time.sleep(0.5)
```

#### 业务场景

**场景**: 通过盘搜找到分享链接 → 转存到自己网盘

```
1. 用户搜索"钢铁侠3" → 盘搜返回分享链接
2. 解析分享链接 → 获取文件列表
3. 用户勾选要保存的文件
4. 从映射管理读取目标名称 → 创建/查找目标文件夹
5. 调用转存API → 轮询完成
6. ✅ 文件已保存到指定位置
```

---

## 3. 迅雷网盘

### 3.1 创建分享链接

**API**: `POST https://api-pan.xunlei.com/drive/v1/share`

**认证**: ❗ 需要两个动态 token（通过 Playwright 获取）
- `authorization`: Bearer JWT token
- `x-captcha-token`: 验证码 token

**Token 获取**（Playwright 监听网络请求）:
```python
def _setup_request_listener(self, page, auth_info):
    """监听请求获取 token"""
    def handle_request(request):
        auth = request.headers.get('authorization', '')
        if auth.startswith('Bearer'):
            auth_info['authorization'] = auth
        
        captcha = request.headers.get('x-captcha-token', '')
        if captcha.startswith('ck0.'):
            auth_info['x-captcha-token'] = captcha
    
    page.on('request', handle_request)
```

**请求参数**:
```python
headers = {
    'authorization': auth_info['authorization'],
    'x-captcha-token': auth_info['x-captcha-token'],
    'x-client-id': 'Xqp0kJBXWhwaTpB6',
    'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
    'content-type': 'application/json'
}

data = {
    "file_ids": [file_id],
    "share_to": "copy",
    "params": {
        "subscribe_push": "false",
        "WithPassCodeInLink": "true"
    },
    "title": "云盘资源分享",
    "restore_limit": "-1",
    "expiration_days": "-1"
}
```

**响应示例**:
```json
{
  "share_url": "https://pan.xunlei.com/s/xxx",
  "pass_code": "1234"
}
```

### 3.2 创建文件夹

**API**: `POST https://api-pan.xunlei.com/drive/v1/files`

**特点**: ✅ 需要**父文件夹 ID**，❗ 一步完成（比夸克简单）

**请求参数**:
```python
headers = {
    'authorization': auth_info['authorization'],
    'x-captcha-token': auth_info['x-captcha-token'],
    'x-client-id': 'Xqp0kJBXWhwaTpB6',
    'x-device-id': 'd765a49124d0b4c8d593d73daa738f51',
    'content-type': 'application/json'
}

data = {
    "parent_id": parent_folder_id,  # 父文件夹ID
    "name": "文件夹名",
    "kind": "drive#folder",
    "space": ""
}
```

**响应示例**:
```json
{
  "upload_type": "UPLOAD_TYPE_UNKNOWN",
  "file": {
    "kind": "drive#folder",
    "id": "VOgxKwYKKC7fvF4aytEKdw3qA1",
    "parent_id": "VOgv8DFs2L6m2C-FmgPmglPHA1",
    "name": "测试",
    "user_id": "683676213",
    "created_time": "2025-12-21T03:58:41.882+08:00",
    "folder_type": "NORMAL"
  }
}
```

**实现位置**: `backend/utils/xunlei_api.py::create_folder()`

### 3.3 转存文件（从分享链接）

迅雷转存流程与百度、夸克不同，验证提取码和获取文件列表**合并在一起**。

#### 步骤1: 验证提取码 + 获取根目录文件列表

**API**: `GET https://api-pan.xunlei.com/drive/v1/share`

**请求参数**:
```python
params = {
    "share_id": "VOglGegihS06QVfZhL8gX8WiA1",  # 从分享链接提取
    "pass_code": "xihk",                        # 提取码
    "limit": 100,
    "thumbnail_size": "SIZE_SMALL"
}

headers = {
    'authorization': AUTHORIZATION,
    'x-captcha-token': X_CAPTCHA_TOKEN,
    'x-client-id': X_CLIENT_ID,
    'x-device-id': X_DEVICE_ID
}
```

**响应示例**:
```json
{
  "share_status": "OK",
  "pass_code_token": "dojtaz4Ov5mX6Ca2aMsID80CWc3QApnKwdyYELDcgKn+...",
  "files": [
    {
      "kind": "drive#folder",
      "id": "VOglGaZahS06QVfZhL8gX6FsA1",
      "name": "艾米丽在巴黎",
      "size": "0"
    }
  ],
  "next_page_token": ""
}
```

#### 步骤2: 获取文件夹内部文件列表（如需要）

**API**: `GET https://api-pan.xunlei.com/drive/v1/share/detail`

**请求参数**:
```python
params = {
    "share_id": "VOglGegihS06QVfZhL8gX8WiA1",
    "parent_id": "VOglGaZahS06QVfZhL8gX6FsA1",  # 文件夹ID
    "pass_code_token": "dojtaz4Ov5mX6Ca2...",   # 步骤1获得
    "limit": 100,
    "thumbnail_size": "SIZE_SMALL"
}
```

**响应示例**:
```json
{
  "share_status": "OK",
  "files": [
    {
      "kind": "drive#folder",
      "id": "VOglGaZchS06QVfZhL8gX6FwA1",
      "name": "S01"
    },
    {
      "kind": "drive#file",
      "id": "VOglGaZchS06QVfZhL8gX6FxA1",
      "name": "S05E01.mp4",
      "size": "814486547"
    }
  ]
}
```

#### 步骤3: 发起转存

**API**: `POST https://api-pan.xunlei.com/drive/v1/share/restore`

**请求参数**:
```python
data = {
    "parent_id": "VOgzQy9ZbNnxrTD95FYf29WGA1",  # 目标文件夹ID
    "share_id": "VOglGegihS06QVfZhL8gX8WiA1",
    "pass_code_token": "dojtaz4Ov5mX6Ca2...",
    "ancestor_ids": [],
    "file_ids": [                                # 要转存的文件ID列表
        "VOglGaZchS06QVfZhL8gX6FwA1",
        "VOglGaZchS06QVfZhL8gX6FxA1"
    ],
    "specify_parent_id": True
}
```

**响应示例**:
```json
{
  "share_status": "OK",
  "file_id": "VOgzQy9ZbNnxrTD95FYf29WGA1",
  "restore_status": "RESTORE_START",
  "restore_task_id": "VOgzQyIKOyhGbW7IT9Hz4tlZA1"
}
```

#### 步骤4: 轮询任务状态

**API**: `GET https://api-pan.xunlei.com/drive/v1/tasks/{task_id}`

**请求示例**:
```python
url = f"https://api-pan.xunlei.com/drive/v1/tasks/{task_id}"
response = requests.get(url, headers=headers)
```

**状态判断**:
- `phase: "PHASE_TYPE_RUNNING"` - 进行中，继续轮询
- `phase: "PHASE_TYPE_ERROR"` - 失败
- `phase: "PHASE_TYPE_COMPLETE"` - 成功 ✅

**成功响应**:
```json
{
  "id": "VOgzQyIKOyhGbW7IT9Hz4tlZA1",
  "type": "restore",
  "phase": "PHASE_TYPE_COMPLETE",
  "progress": 100,
  "message": "完成",
  "created_time": "2025-12-21T13:43:54.340+08:00",
  "updated_time": "2025-12-21T13:43:55.120+08:00"
}
```

#### 关键参数说明

| 参数 | 来源 | 说明 |
|------|------|------|
| `share_id` | 分享URL | 分享链接ID（如：https://pan.xunlei.com/s/**VOglGegihS06QVfZhL8gX8WiA1**） |
| `pass_code` | **用户输入** | 提取码 |
| `pass_code_token` | 验证提取码API | 验证成功后获得的token |
| `parent_id` | 文件列表API | 源文件夹ID（可选，获取文件夹内部时需要） |
| `file_ids` | 文件列表API | 要转存的文件ID列表 |
| `parent_id`（转存） | **用户指定** | 目标文件夹ID（需要缓存或动态获取）⭐ |

#### 实现要点

```python
def transfer_from_xunlei_share(share_url, pass_code, target_folder_id, 
                               authorization, x_captcha_token):
    """从迅雷分享链接转存文件"""
    
    # 1. 解析分享链接，提取 share_id
    share_id = re.search(r'/s/([^?]+)', share_url).group(1)
    
    # 2. 验证提取码，获取 pass_code_token 和根目录文件列表
    params = {
        "share_id": share_id,
        "pass_code": pass_code,
        "limit": 100
    }
    share_resp = requests.get(
        "https://api-pan.xunlei.com/drive/v1/share",
        params=params,
        headers=headers
    )
    result = share_resp.json()
    pass_code_token = result['pass_code_token']
    file_list = result['files']
    
    # 3. 如果是文件夹，获取内部文件列表
    if len(file_list) == 1 and file_list[0]['kind'] == 'drive#folder':
        folder_id = file_list[0]['id']
        detail_params = {
            "share_id": share_id,
            "parent_id": folder_id,
            "pass_code_token": pass_code_token,
            "limit": 100
        }
        detail_resp = requests.get(
            "https://api-pan.xunlei.com/drive/v1/share/detail",
            params=detail_params,
            headers=headers
        )
        file_list = detail_resp.json()['files']
    
    # 4. 提取所有文件ID
    file_ids = [f['id'] for f in file_list]
    
    # 5. 发起转存
    restore_data = {
        "parent_id": target_folder_id,
        "share_id": share_id,
        "pass_code_token": pass_code_token,
        "ancestor_ids": [],
        "file_ids": file_ids,
        "specify_parent_id": True
    }
    restore_resp = requests.post(
        "https://api-pan.xunlei.com/drive/v1/share/restore",
        json=restore_data,
        headers=headers
    )
    task_id = restore_resp.json()['restore_task_id']
    
    # 6. 轮询任务（每秒，最多60秒）
    for retry in range(60):
        task_resp = requests.get(
            f"https://api-pan.xunlei.com/drive/v1/tasks/{task_id}",
            headers=headers
        )
        task = task_resp.json()
        
        if task['phase'] == 'PHASE_TYPE_COMPLETE':
            return task
        elif task['phase'] == 'PHASE_TYPE_ERROR':
            raise Exception(f"转存失败: {task['message']}")
        
        time.sleep(1)
```

#### 业务场景

**场景**: 通过盘搜找到迅雷分享链接 → 转存到自己网盘

```
1. 用户搜索"艾米丽在巴黎" → 盘搜返回分享链接
2. 解析分享链接 → 验证提取码 → 获取文件列表
3. 如果是文件夹，获取内部文件列表
4. 从映射管理读取目标名称 → 创建/查找目标文件夹
5. 调用转存API → 轮询完成
6. ✅ 文件已保存到指定位置
```

#### 关键要点

1. **Token动态性**: `authorization` 和 `x-captcha-token` 需要通过Playwright从浏览器获取
2. **验证合并**: 验证提取码和获取文件列表是同一个API
3. **文件夹处理**: 如果根目录是文件夹，需要额外调用`/share/detail`获取内部文件
4. **轮询间隔**: 建议每秒轮询一次，任务通常在1-3秒内完成
5. **根目录表示**: 迅雷使用空字符串`""`表示根目录

---

## 4. 测试脚本使用

### 4.1 百度网盘

```bash
# 测试创建目录
python3 test_baidu_api.py create

# 测试搜索+分享（原有功能）
python3 test_baidu_api.py
```

### 4.2 夸克网盘

```bash
# 测试创建文件夹
python3 test_quark_api.py create

# 测试搜索+分享（原有功能）
python3 test_quark_api.py
```

### 4.3 迅雷网盘

```bash
# 测试创建文件夹（自动从数据库读取 Cookie）
python3 test_xunlei_create_folder.py

# 注意：会自动启动浏览器获取 token
```

---

## 5. 父文件夹 ID 获取方式

### 5.1 百度网盘
✅ **不需要父文件夹 ID**，直接使用完整路径：
```python
path = "/电影/华语/我的电影"  # 路径即 ID
```

### 5.2 夸克网盘
❗ **需要父文件夹 ID**，获取方式：
1. 手动在浏览器开发者工具抓包
2. 通过搜索 API 找到父文件夹后获取其 `fid`
3. **推荐**: 建立路径 → ID 的缓存映射表

### 5.3 迅雷网盘
❗ **需要父文件夹 ID**，获取方式：
1. 手动在浏览器开发者工具抓包
2. 通过搜索 API 找到父文件夹后获取其 `id`
3. **推荐**: 建立路径 → ID 的缓存映射表

---

## 6. 建议的缓存方案

由于夸克和迅雷需要父文件夹 ID，建议建立统一的缓存表：

### 6.1 数据库表设计

```python
class PanFolderCache(Base):
    """网盘文件夹缓存 - 路径到ID的映射"""
    __tablename__ = 'pan_folder_cache'
    
    id = Column(Integer, primary_key=True)
    pan_type = Column(String(20), nullable=False)      # baidu/quark/xunlei
    folder_path = Column(String(500), nullable=False)  # 统一路径: /电影/华语
    folder_id = Column(String(100))                    # 夸克/迅雷的 fid/id
    folder_name = Column(String(200))                  # 文件夹名
    parent_path = Column(String(500))                  # 父路径
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_pan_path', 'pan_type', 'folder_path', unique=True),
    )
```

### 6.2 使用逻辑

```python
def get_folder_id(pan_type: str, path: str) -> str:
    """
    统一获取文件夹 ID
    - 百度: 返回路径本身
    - 夸克/迅雷: 从缓存返回 folder_id
    """
    if pan_type == 'baidu':
        return path  # 百度直接用路径
    
    # 夸克/迅雷从缓存查询
    cache = db.query(PanFolderCache).filter(
        PanFolderCache.pan_type == pan_type,
        PanFolderCache.folder_path == path
    ).first()
    
    return cache.folder_id if cache else None
```

### 6.3 常用目录示例

```python
# 初始化常用目录缓存
COMMON_FOLDERS = {
    'quark': {
        '/电影': '9b1b5c8cd5bd441781e913a11498e1a4',
        '/剧集': 'abc123...',
        '/剧集/国产剧': 'def456...',
    },
    'xunlei': {
        '/电影': 'VOgv8DFs2L6m2C-FmgPmglPHA1',
        '/剧集': 'VOgx...',
        '/剧集/美剧': 'VOgy...',
    }
}
```

---

## 7. Cookie 管理

所有网盘的 Cookie 统一存储在数据库 `pan_cookies` 表中：

```python
class PanCookie(Base):
    """网盘Cookie管理表"""
    __tablename__ = 'pan_cookies'
    
    id = Column(Integer, primary_key=True)
    pan_type = Column(String(20), unique=True)  # baidu/quark/xunlei
    cookie = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    last_check_time = Column(DateTime)
    check_status = Column(String(50))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

**获取 Cookie**:
```python
from models import init_database, get_session, PanCookie

engine = init_database(config['database'])
session = get_session(engine)

cookie = session.query(PanCookie).filter(
    PanCookie.pan_type == 'xunlei',
    PanCookie.is_active == True
).first()
```

---

## 8. 错误处理

### 8.1 百度网盘

**常见错误**:
- `errno=-6`: bdstoken 无效或过期（需重新获取）
- `errno=12`: 路径已存在

### 8.2 夸克网盘

**常见错误**:
- `code=400`: Cookie 过期
- 任务轮询超时: 网络问题或任务失败

### 8.3 迅雷网盘

**常见错误**:
- `error: captcha_invalid`: x-captcha-token 过期（需重新获取）
- `error: unauthorized`: authorization 过期（需重新获取）
- Token 获取超时: Cookie 过期或网络问题

---

## 9. 实现文件位置

| 功能 | 文件位置 |
|------|---------|
| 百度 API | `backend/utils/baidu_api.py` |
| 百度测试 | `test_baidu_api.py` |
| 夸克 API | `backend/utils/quark_api.py` |
| 夸克测试 | `test_quark_api.py` |
| 迅雷 API | `backend/utils/xunlei_api.py` |
| 迅雷测试 | `test_xunlei_create_folder.py` |
| 数据库模型 | `backend/models.py` |

---

## 10. 总结

| 特性 | 百度 | 夸克 | 迅雷 |
|------|------|------|------|
| **认证复杂度** | ⭐ 中等 | ⭐ 简单 | ⭐⭐⭐ 复杂 |
| **需要浏览器** | ❌ | ❌ | ✅ |
| **父文件夹 ID** | ❌ 用路径 | ✅ 需要 | ✅ 需要 |
| **创建文件夹** | 一步 | 两步 | 一步 |
| **分享链接** | 同步 | 异步 | 同步 |
| **适合自动化** | ✅ 容易 | ✅ 容易 | ⚠️ 需要 Playwright |

**推荐使用优先级**（自动化场景）:
1. 🥇 夸克 - 最简单，只需 Cookie
2. 🥈 百度 - 简单，但需提取 bdstoken
3. 🥉 迅雷 - 复杂，需要 Playwright

---

*最后更新: 2025-12-21*
