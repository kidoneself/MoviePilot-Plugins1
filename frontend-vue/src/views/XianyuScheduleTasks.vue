<template>
  <div class="schedule-tasks">
    <el-card class="header-card">
      <div class="header-actions">
        <h2 style="margin: 0;">⏰ 定时任务管理</h2>
        <el-space>
          <el-button @click="loadTasks" :loading="loading" :icon="Refresh">
            刷新
          </el-button>
          <el-select v-model="filterStatus" placeholder="状态筛选" style="width: 150px" @change="loadTasks">
            <el-option label="全部" :value="null" />
            <el-option label="⏳ 待执行" value="PENDING" />
            <el-option label="✅ 已完成" value="COMPLETED" />
            <el-option label="❌ 失败" value="FAILED" />
            <el-option label="🚫 已取消" value="CANCELLED" />
          </el-select>
        </el-space>
      </div>
    </el-card>

    <!-- 任务列表 -->
    <el-card style="margin-top: 20px;">
      <el-table 
        v-loading="loading" 
        :data="tasks" 
        style="width: 100%"
        :default-sort="{ prop: 'execute_time', order: 'ascending' }"
      >
        <el-table-column prop="id" label="任务ID" width="80" />
        
        <el-table-column prop="task_type" label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.task_type === 'publish'" type="success">📤 上架</el-tag>
            <el-tag v-else-if="row.task_type === 'downshelf'" type="warning">📥 下架</el-tag>
            <el-tag v-else type="info">{{ row.task_type }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="商品" min-width="250">
          <template #default="{ row }">
            <div v-if="row.product_titles && row.product_titles.length > 0">
              <el-tag 
                v-if="row.product_titles.length === 1" 
                size="small"
                style="max-width: 100%; overflow: hidden; text-overflow: ellipsis;"
              >
                {{ row.product_titles[0] }}
              </el-tag>
              <el-popover
                v-else
                placement="top"
                :width="400"
                trigger="hover"
              >
                <template #reference>
                  <el-tag type="success" size="small">
                    {{ row.product_titles.length }} 个商品
                  </el-tag>
                </template>
                <div style="max-height: 300px; overflow-y: auto;">
                  <div v-for="(title, idx) in row.product_titles" :key="idx" style="padding: 3px 0; font-size: 13px;">
                    {{ idx + 1 }}. {{ title }}
                  </div>
                </div>
              </el-popover>
            </div>
            <span v-else style="color: #909399;">无商品信息</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="execute_time" label="执行时间" width="180" sortable>
          <template #default="{ row }">
            <div>
              <div>{{ formatDateTime(row.execute_time) }}</div>
              <el-tag v-if="row.repeat_daily" size="small" type="info" style="margin-top: 2px;">
                🔁 每日重复
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'PENDING'" type="info">⏳ 待执行</el-tag>
            <el-tag v-else-if="row.status === 'COMPLETED'" type="success">✅ 已完成</el-tag>
            <el-tag v-else-if="row.status === 'FAILED'" type="danger">❌ 失败</el-tag>
            <el-tag v-else-if="row.status === 'CANCELLED'" type="info">🚫 已取消</el-tag>
            <el-tag v-else>{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="last_execute_time" label="最后执行时间" width="180">
          <template #default="{ row }">
            {{ row.last_execute_time ? formatDateTime(row.last_execute_time) : '-' }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'PENDING' || row.status === 'FAILED'"
              size="small"
              type="primary"
              @click="viewDetails(row)"
            >
              详情
            </el-button>
            <el-button
              v-if="row.status === 'PENDING'"
              size="small"
              type="danger"
              @click="deleteTask(row)"
            >
              删除
            </el-button>
            <el-button
              v-if="row.status === 'COMPLETED' || row.status === 'FAILED'"
              size="small"
              @click="viewDetails(row)"
            >
              查看结果
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任务详情对话框 -->
    <el-dialog 
      v-model="detailsVisible" 
      title="任务详情" 
      width="700px"
    >
      <div v-if="currentTask">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ currentTask.id }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">
            <el-tag v-if="currentTask.task_type === 'publish'" type="success">📤 上架</el-tag>
            <el-tag v-else-if="currentTask.task_type === 'downshelf'" type="warning">📥 下架</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">{{ formatDateTime(currentTask.execute_time) }}</el-descriptions-item>
          <el-descriptions-item label="重复">
            <el-tag v-if="currentTask.repeat_daily" type="info">🔁 每日重复</el-tag>
            <el-tag v-else type="info">单次执行</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag v-if="currentTask.status === 'PENDING'" type="info">⏳ 待执行</el-tag>
            <el-tag v-else-if="currentTask.status === 'COMPLETED'" type="success">✅ 已完成</el-tag>
            <el-tag v-else-if="currentTask.status === 'FAILED'" type="danger">❌ 失败</el-tag>
            <el-tag v-else-if="currentTask.status === 'CANCELLED'" type="info">🚫 已取消</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最后执行时间">
            {{ currentTask.last_execute_time ? formatDateTime(currentTask.last_execute_time) : '-' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">商品列表</el-divider>
        <div style="max-height: 200px; overflow-y: auto; padding: 10px; background: #f5f7fa; border-radius: 4px;">
          <div v-for="(title, idx) in currentTask.product_titles" :key="idx" style="padding: 5px 0; font-size: 13px;">
            <strong>{{ idx + 1 }}.</strong> {{ title }}
            <el-tag size="small" style="margin-left: 10px;">ID: {{ currentTask.product_ids[idx] }}</el-tag>
          </div>
        </div>

        <el-divider content-position="left" v-if="currentTask.execute_result">执行结果</el-divider>
        <div 
          v-if="currentTask.execute_result" 
          style="max-height: 300px; overflow-y: auto; padding: 10px; background: #f5f7fa; border-radius: 4px; white-space: pre-wrap; font-size: 13px; font-family: monospace;"
        >
          {{ currentTask.execute_result }}
        </div>
      </div>
      <template #footer>
        <el-button @click="detailsVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import api from '../api'

const loading = ref(false)
const tasks = ref([])
const filterStatus = ref(null)
const detailsVisible = ref(false)
const currentTask = ref(null)

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    
    const res = await api.get('/xianyu/schedule-task/list', { params })
    if (res.data.success) {
      tasks.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 查看详情
const viewDetails = (task) => {
  currentTask.value = task
  detailsVisible.value = true
}

// 删除任务
const deleteTask = async (task) => {
  try {
    await ElMessageBox.confirm(
      `确定删除任务 #${task.id} 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    const res = await api.delete(`/xianyu/schedule-task/${task.id}`)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.schedule-tasks {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

