<template>
  <div class="media-requests">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📱 用户资源请求</span>
          <div class="header-actions">
            <el-radio-group v-model="statusFilter" size="small" @change="loadRequests">
              <el-radio-button label="pending">待处理</el-radio-button>
              <el-radio-button label="completed">已完成</el-radio-button>
              <el-radio-button label="all">全部</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" @click="loadRequests" :loading="loading">
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 统计信息 -->
      <el-alert
        :title="`共 ${total} 个请求，其中 ${pendingCount} 个待处理`"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      />

      <!-- 请求列表 -->
      <el-table 
        :data="requests" 
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column label="海报" width="100">
          <template #default="{ row }">
            <el-image
              :src="row.poster_url"
              fit="cover"
              style="width: 60px; height: 90px; border-radius: 4px;"
              lazy
            >
              <template #error>
                <div style="width: 60px; height: 90px; background: #f5f7fa; display: flex; align-items: center; justify-content: center;">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
          </template>
        </el-table-column>

        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <div>
              <div style="font-weight: 600; font-size: 15px;">{{ row.title }}</div>
              <div style="color: #909399; font-size: 13px; margin-top: 4px;">
                <el-tag :type="row.media_type === 'movie' ? 'success' : 'primary'" size="small">
                  {{ row.media_type === 'movie' ? '电影' : '电视剧' }}
                </el-tag>
                <span style="margin-left: 8px;">{{ row.year }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="请求热度" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.request_count > 10 ? 'danger' : row.request_count > 5 ? 'warning' : 'info'" effect="dark" size="large">
              {{ row.request_count }} 次
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="首次请求" width="180">
          <template #default="{ row }">
            {{ row.created_at }}
          </template>
        </el-table-column>

        <el-table-column label="最后请求" width="180">
          <template #default="{ row }">
            {{ row.updated_at }}
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">
              {{ row.status === 'completed' ? '已完成' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                type="primary" 
                size="small"
                @click="goToTmdb(row)"
              >
                查看TMDB
              </el-button>
              <el-button 
                v-if="row.status === 'pending'"
                type="success" 
                size="small"
                @click="markCompleted(row)"
              >
                标记完成
              </el-button>
              <el-button 
                type="danger" 
                size="small"
                @click="deleteRequest(row)"
              >
                删除
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadRequests"
        @size-change="loadRequests"
        style="margin-top: 20px; justify-content: center;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture } from '@element-plus/icons-vue'
import api from '../api'

const loading = ref(false)
const requests = ref([])
const total = ref(0)
const pendingCount = ref(0)
const page = ref(1)
const pageSize = ref(20)
const statusFilter = ref('pending')

// 加载请求列表
const loadRequests = async () => {
  loading.value = true
  
  try {
    const response = await api.getMediaRequests({
      status: statusFilter.value,
      page: page.value,
      page_size: pageSize.value
    })
    
    if (response.data.success) {
      requests.value = response.data.data
      total.value = response.data.total
      pendingCount.value = response.data.pending_count || 0
    } else {
      ElMessage.error('加载失败：' + (response.data.message || '未知错误'))
    }
  } catch (error) {
    console.error('加载请求列表失败:', error)
    ElMessage.error('加载失败：' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 跳转到TMDB搜索页面
const goToTmdb = (row) => {
  // 打开TMDB官网查看详情
  window.open(`https://www.themoviedb.org/${row.media_type}/${row.tmdb_id}`, '_blank')
}

// 标记完成
const markCompleted = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认已补充《${row.title}》的资源？`,
      '标记完成',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'success'
      }
    )
    
    const response = await api.updateMediaRequest(row.id, { status: 'completed' })
    
    if (response.data.success) {
      ElMessage.success('已标记为完成')
      // 重新加载列表
      loadRequests()
    } else {
      ElMessage.error('操作失败：' + (response.data.message || '未知错误'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('标记完成失败:', error)
      ElMessage.error('操作失败：' + (error.message || '未知错误'))
    }
  }
}

// 删除请求
const deleteRequest = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认删除《${row.title}》的请求吗？`,
      '删除请求',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await api.deleteMediaRequest(row.id)
    
    if (response.data.success) {
      ElMessage.success('删除成功')
      // 重新加载列表
      loadRequests()
    } else {
      ElMessage.error('删除失败：' + (response.data.message || '未知错误'))
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除请求失败:', error)
      ElMessage.error('删除失败：' + (error.message || '未知错误'))
    }
  }
}

onMounted(() => {
  loadRequests()
})
</script>

<style scoped>
.media-requests {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
</style>

