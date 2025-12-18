<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const records = ref([])
const total = ref(0)
const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const groupByFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const loadRecords = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchText.value) params.search = searchText.value
    if (statusFilter.value) params.status = statusFilter.value
    if (groupByFilter.value) params.group_by = groupByFilter.value
    
    const res = await api.getRecords(params)
    if (res.data.success) {
      records.value = res.data.data
      total.value = res.data.total
    }
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleBatchDelete = async () => {
  if (!searchText.value) {
    ElMessage.warning('请先输入搜索条件')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除搜索结果中的所有记录吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    // 实现批量删除逻辑
    ElMessage.info('批量删除功能开发中')
  } catch (error) {
    // 取消操作
  }
}

const exportRecords = () => {
  const params = {}
  if (searchText.value) params.search = searchText.value
  if (statusFilter.value) params.status = statusFilter.value
  
  api.exportRecords(params).then(res => {
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '硬链接记录.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  }).catch(() => {
    ElMessage.error('导出失败')
  })
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

onMounted(() => {
  loadRecords()
})
</script>

<template>
  <div class="link-records">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">硬链接记录</span>
        </div>
      </template>

      <div class="toolbar">
        <el-space>
          <el-input
            v-model="searchText"
            placeholder="搜索剧名或文件名..."
            style="width: 300px"
            clearable
            @keyup.enter="loadRecords"
          />
          <el-button type="primary" @click="loadRecords">搜索</el-button>
          
          <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="loadRecords" style="width: 120px">
            <el-option label="全部状态" value="" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
          
          <el-select v-model="groupByFilter" placeholder="列表视图" clearable @change="loadRecords" style="width: 150px">
            <el-option label="列表视图" value="" />
            <el-option label="按源文件分组" value="source_file" />
            <el-option label="按网盘统计" value="target_show" />
            <el-option label="按目录分组" value="source_dir" />
          </el-select>
          
          <el-button @click="loadRecords">刷新</el-button>
          <el-button type="success" @click="exportRecords">导出Excel</el-button>
        </el-space>
      </div>

      <el-table :data="records" v-loading="loading" stripe style="margin-top: 20px">
        <el-table-column prop="source_file" label="源文件" min-width="200" show-overflow-tooltip />
        <el-table-column prop="target_show" label="网盘目录" min-width="150" />
        <el-table-column prop="target_file" label="目标文件" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadRecords"
        @size-change="loadRecords"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 18px;
  font-weight: bold;
}

.toolbar {
  margin-bottom: 20px;
}
</style>
