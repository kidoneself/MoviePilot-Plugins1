<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const records = ref([])
const total = ref(0)
const loading = ref(false)
const searchText = ref('')
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

// 从路径中提取文件名
const getFileName = (path) => {
  if (!path) return '-'
  const parts = path.split('/')
  return parts[parts.length - 1] || path
}

// 提取集数信息（支持多种格式）
const extractEpisode = (filename) => {
  if (!filename) return ''
  
  // 匹配常见集数格式：S01E01, EP01, E01, 第01集, 01, etc.
  const patterns = [
    /S\d+E(\d+)/i,           // S01E01
    /EP?(\d+)/i,             // EP01, E01
    /第(\d+)[集话]/,         // 第01集
    /\[(\d+)\]/,             // [01]
    /\.(\d+)\./,             // .01.
    /-(\d+)\./,              // -01.
  ]
  
  for (const pattern of patterns) {
    const match = filename.match(pattern)
    if (match) {
      return `第${parseInt(match[1])}集`
    }
  }
  
  return ''
}

// 获取完整的文件显示名（文件名 + 集数）
const getFileDisplay = (path) => {
  const filename = getFileName(path)
  const episode = extractEpisode(filename)
  return episode ? `${episode} - ${filename}` : filename
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
        <el-table-column prop="original_name" label="剧集" width="150" />
        <el-table-column label="文件名/集数" min-width="300">
          <template #default="{ row }">
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <span style="font-weight: 600; color: #409eff;">{{ extractEpisode(row.source_file) || '未识别' }}</span>
              <span style="font-size: 12px; color: #606266;">{{ getFileName(row.source_file) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="网盘" width="100">
          <template #default="{ row }">
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <el-tag v-if="row.quark_target_file" type="warning" size="small">夸克</el-tag>
              <el-tag v-if="row.baidu_target_file" type="primary" size="small">百度</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="source_file" label="源路径" min-width="200" show-overflow-tooltip />
        <el-table-column label="目标路径" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.quark_target_file || row.baidu_target_file || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160" />
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
