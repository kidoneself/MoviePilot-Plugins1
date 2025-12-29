# 数据库迁移脚本

## 索引优化脚本

### 方式1：简单版本（推荐）

**不需要手动执行！**

代码中已经在模型定义中添加了 `index=True`，SQLAlchemy会在下次启动时自动创建索引。

### 方式2：手动执行（可选）

如果你想立即创建索引而不重启服务：

#### 使用安全版本（推荐）

```bash
mysql -h 101.35.224.59 -u root -p file_link_monitor_v2 < backend/migrations/add_missing_indexes_safe.sql
```

特点：
- ✅ 检查索引是否存在
- ✅ 已存在则跳过
- ✅ 显示创建结果

#### 使用简单版本

```bash
mysql -h 101.35.224.59 -u root -p file_link_monitor_v2 < backend/migrations/add_missing_indexes.sql
```

注意：
- ⚠️ 如果索引已存在会报错
- ⚠️ 但不影响系统运行

### 查看当前索引

```sql
SHOW INDEX FROM link_records;
SHOW INDEX FROM custom_name_mapping;
```

### 删除索引（如需重建）

```sql
-- LinkRecord
DROP INDEX idx_link_records_original_name ON link_records;
DROP INDEX idx_link_records_created_at ON link_records;
DROP INDEX idx_link_records_source_file ON link_records;

-- CustomNameMapping  
DROP INDEX idx_custom_name_mapping_category ON custom_name_mapping;
DROP INDEX idx_custom_name_mapping_enabled ON custom_name_mapping;
DROP INDEX idx_custom_name_mapping_completed ON custom_name_mapping;
DROP INDEX idx_custom_name_mapping_tmdb_id ON custom_name_mapping;
```

## 索引说明

| 表名 | 索引列 | 用途 | 预期提升 |
|------|--------|------|----------|
| link_records | original_name | 分组查询 | 70-90% |
| link_records | created_at | 时间排序 | 50-70% |
| link_records | source_file | 搜索过滤 | 60-80% |
| custom_name_mapping | category | 分类筛选 | 80-90% |
| custom_name_mapping | enabled | 状态筛选 | 90%+ |
| custom_name_mapping | is_completed | 完结筛选 | 90%+ |
| custom_name_mapping | tmdb_id | TMDB关联 | 70-90% |

## 验证索引效果

```sql
-- 查看查询执行计划（使用索引会显示 key）
EXPLAIN SELECT * FROM link_records WHERE original_name = '罚罪2 (2025)';
EXPLAIN SELECT * FROM link_records ORDER BY created_at DESC LIMIT 10;
EXPLAIN SELECT * FROM custom_name_mapping WHERE category = '剧集/国产剧集';
```

如果 `key` 列显示索引名，说明索引已生效！

