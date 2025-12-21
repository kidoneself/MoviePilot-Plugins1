# 文件整理说明

## ✅ 核心文件（保留）

### 生产代码
- `pan_transfer_api.py` - **核心！** 三网盘转存API封装
- `unified_transfer.py` - **核心！** OpenList集成的统一转存接口
- `get_xunlei_token.py` - **工具！** 迅雷token自动获取（定期需要）

### 配置和文档
- `config.yaml` - 数据库配置
- `requirements.txt` - Python依赖
- `README.md` - 项目说明
- `README_PAN_TRANSFER.md` - 转存功能文档
- `三网盘API使用文档.md` - API详细文档

### 后端核心
- `backend/` - 后端代码目录（保留整个目录）
  - `models.py` - 数据库模型
  - `api/` - API接口
  - `utils/` - 工具函数

### 前端（如需要Web界面）
- `frontend/` - 前端代码
- `frontend-vue/` - Vue前端代码

---

## 🗑️ 可以删除的临时测试文件

### 百度测试文件（大量重复）
- `test_baidu_api.py` - 早期测试
- `test_baidu_share_verify.py` - 临时验证测试
- `test_baidu_specific_link.py` - 临时链接测试
- `test_baidu_spiderman.py` - 临时测试
- `test_baidu_upstream.py` - 临时测试
- `test_baidu_verify.py` - 临时测试
- `test_baidu_only.py` - 临时测试
- `check_baidu_dir.py` - 调试脚本
- `check_baidu_files.py` - 调试脚本
- `debug_baidu_response.py` - 调试脚本

### 夸克测试文件
- `test_quark_api.py` - 早期测试
- `test_quark_share_parse.py` - 临时测试

### 迅雷测试文件
- `test_xunlei_api.py` - 早期测试
- `test_xunlei_simple.py` - 临时测试
- `test_xunlei_create_folder.py` - 临时测试
- `test_xunlei_playwright.py` - 早期测试
- `check_db_xunlei.py` - 调试脚本

### OpenList测试文件
- `test_openlist_api.py` - 早期测试
- `test_openlist_simple.py` - 临时测试
- `test_openlist_mkdir_new.py` - 临时测试
- `test_openlist_path_to_id.py` - 临时测试

### 统一转存测试
- `test_final_unified_transfer.py` - 临时测试
- `test_same_path_all_pans.py` - 临时测试

### 其他临时测试
- `test_pansou.py` - 其他功能测试
- `test_serverchan_notification.py` - 通知测试
- `test_taosync_multi_jobs.py` - 其他功能测试
- `test_get_transfer_params.py` - 临时测试

---

## 📝 可选保留（作为示例）

### 完整流程示例（三选一即可）
- `test_baidu_full_transfer.py` - 百度完整流程示例
- `test_quark_full_transfer.py` - 夸克完整流程示例
- `test_xunlei_full_transfer.py` - 迅雷完整流程示例
- `test_full_flow_ironman3.py` - **推荐保留** 三网盘完整示例
- `test_nixingrengshen.py` - 另一个完整示例
- `test_spiderman2.py` - 另一个完整示例

### OpenList示例
- `test_openlist_mkdir.py` - OpenList文件夹创建示例
- `test_unified_transfer.py` - 统一转存接口示例

---

## 📊 推荐保留的最小文件集

### 必需文件（14个）
```
pan_transfer_api.py          # 核心API
unified_transfer.py          # 统一接口
get_xunlei_token.py         # 工具脚本
config.yaml                 # 配置
requirements.txt            # 依赖
*.md                        # 文档（3个）
backend/                    # 后端目录
```

### 示例文件（2个）
```
test_full_flow_ironman3.py  # 完整示例
test_openlist_mkdir.py      # OpenList示例
```

### 其他
```
logs/                       # 日志目录（可选保留）
frontend/                   # 前端（按需）
```

---

## 🚀 执行清理命令

### 删除所有临时测试文件
```bash
cd /Users/lizhiqiang/coding-my/plugin/MoviePilot-Plugins1/file-link-monitor

# 删除百度临时测试
rm test_baidu_api.py test_baidu_share_verify.py test_baidu_specific_link.py \
   test_baidu_spiderman.py test_baidu_upstream.py test_baidu_verify.py \
   test_baidu_only.py check_baidu_dir.py check_baidu_files.py \
   debug_baidu_response.py

# 删除夸克临时测试
rm test_quark_api.py test_quark_share_parse.py

# 删除迅雷临时测试
rm test_xunlei_api.py test_xunlei_simple.py test_xunlei_create_folder.py \
   test_xunlei_playwright.py check_db_xunlei.py

# 删除OpenList临时测试
rm test_openlist_api.py test_openlist_simple.py test_openlist_mkdir_new.py \
   test_openlist_path_to_id.py

# 删除其他临时测试
rm test_final_unified_transfer.py test_same_path_all_pans.py \
   test_pansou.py test_serverchan_notification.py test_taosync_multi_jobs.py \
   test_get_transfer_params.py

# 删除重复的流程示例（可选，保留一个即可）
rm test_nixingrengshen.py test_spiderman2.py test_unified_transfer.py
```

### 只保留核心文件和一个示例
```bash
# 核心文件
pan_transfer_api.py
unified_transfer.py
get_xunlei_token.py

# 示例文件（保留一个）
test_full_flow_ironman3.py

# 单独测试示例（可选）
test_baidu_full_transfer.py
test_quark_full_transfer.py
test_xunlei_full_transfer.py
test_openlist_mkdir.py
```

---

## 📁 最终建议的目录结构

```
file-link-monitor/
├── backend/                    # 后端核心代码
├── frontend/                   # 前端代码（可选）
├── logs/                       # 日志文件
├── pan_transfer_api.py        # ⭐ 核心：三网盘API
├── unified_transfer.py        # ⭐ 核心：统一接口
├── get_xunlei_token.py        # ⭐ 工具：获取token
├── test_full_flow_ironman3.py # 📝 示例：完整流程
├── test_openlist_mkdir.py     # 📝 示例：OpenList
├── config.yaml                # 配置
├── requirements.txt           # 依赖
├── README.md                  # 文档
├── README_PAN_TRANSFER.md     # 文档
└── 三网盘API使用文档.md        # 文档
```

**清理后文件数量：从 44个 减少到 12个核心文件** ✅
