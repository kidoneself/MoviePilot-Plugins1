# 定时任务清理指南

## 问题说明

当你删除数据库所有数据后，可能会遇到以下错误：
```
加载失败: Extra data: line 1 column 17 (char 16)
```

这是因为定时任务表中有残留的数据，而这些数据的 `product_ids` 或 `product_titles` 字段包含不正确的JSON格式。

## 解决方案

### 方案1: 使用Python脚本清理（推荐）

1. **只清理有问题的任务**（推荐）:
```bash
cd /Users/lizhiqiang/coding-my/file-link-monitor
python backend/scripts/cleanup_tasks.py
```

这个脚本会：
- 检查所有待执行的任务
- 验证JSON格式
- 只删除有问题的任务
- 在删除前会让你确认

2. **清理所有待执行和失败的任务**（谨慎使用）:
```bash
python backend/scripts/cleanup_tasks.py --all
```

这会删除所有状态为 `PENDING` 和 `FAILED` 的任务。

### 方案2: 使用API清理

如果你的后端服务正在运行，可以使用以下API：

#### 1. 清理有问题的任务
```bash
curl -X POST http://localhost:8000/api/xianyu/schedule-task/cleanup
```

返回示例：
```json
{
  "success": true,
  "message": "清理完成，删除了 3 个有问题的任务",
  "deleted_count": 3,
  "error_tasks": [
    {
      "id": 1,
      "task_type": "publish",
      "error": "Extra data: line 1 column 17 (char 16)"
    }
  ]
}
```

#### 2. 清理所有任务（谨慎使用）
```bash
curl -X POST http://localhost:8000/api/xianyu/schedule-task/cleanup-all
```

### 方案3: 直接在数据库中清理

如果上述方法都不行，可以直接在数据库中执行：

```sql
-- 查看有问题的任务
SELECT id, task_type, status, product_ids, product_titles 
FROM goofish_schedule_task 
WHERE status = 'PENDING';

-- 删除所有待执行和失败的任务
DELETE FROM goofish_schedule_task 
WHERE status IN ('PENDING', 'FAILED');
```

## 预防措施

1. **不要直接删除数据库所有数据**
   - 如果需要清理，请使用提供的API或脚本
   - 或者分表清理，避免破坏外键关联

2. **定期检查定时任务**
   - 使用 `GET /api/xianyu/schedule-task` 查看所有任务
   - 及时删除不需要的任务

3. **备份数据库**
   - 在进行重大操作前，先备份数据库

## 已修复的问题

本次更新已经修复了以下问题：

1. **增强的JSON解析错误处理**
   - 在 `xianyu_scheduler.py` 中添加了 try-catch 来捕获 JSON 解析错误
   - 当遇到格式错误时，会记录日志并优雅地处理，不会中断整个调度器

2. **新增清理API**
   - `/api/xianyu/schedule-task/cleanup` - 智能清理有问题的任务
   - `/api/xianyu/schedule-task/cleanup-all` - 清理所有待执行和失败的任务

3. **新增清理脚本**
   - `backend/scripts/cleanup_tasks.py` - 命令行工具清理任务

## 验证修复

运行以下命令验证问题已解决：

```bash
# 1. 清理有问题的任务
python backend/scripts/cleanup_tasks.py

# 2. 重启后端服务
# 使用 Ctrl+C 停止当前服务，然后重新启动

# 3. 检查日志
tail -f backend.log
```

如果一切正常，你应该不会再看到 "Extra data" 错误。

