<template>
  <div class="xianyu-products">
    <el-card class="header-card">
      <div class="header-actions">
        <h2 style="margin: 0;">🐟 闲鱼商品管理</h2>
        <el-space>
          <el-button type="primary" @click="syncProducts" :loading="syncing">
            同步商品
          </el-button>
          <el-select v-model="filterStatus" placeholder="状态筛选" style="width: 150px" @change="loadProducts">
            <el-option label="全部" :value="null" />
            <el-option label="待发布" :value="0" />
            <el-option label="已上架" :value="1" />
            <el-option label="已下架" :value="2" />
          </el-select>
        </el-space>
      </div>
    </el-card>

    <!-- 商品列表 -->
    <el-card style="margin-top: 20px;">
      <el-table v-loading="loading" :data="products" style="width: 100%">
        <el-table-column prop="product_id" label="商品ID" width="120" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">
            ¥{{ row.price ? (row.price / 100).toFixed(2) : '0.00' }}
          </template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="80" />
        <el-table-column prop="sold" label="已售" width="80" />
        <el-table-column prop="product_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.product_status === 0" type="info">待发布</el-tag>
            <el-tag v-else-if="row.product_status === 1" type="success">已上架</el-tag>
            <el-tag v-else-if="row.product_status === 2" type="warning">已下架</el-tag>
            <el-tag v-else type="info">{{ row.product_status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sync_time" label="同步时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.sync_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.product_status !== 1"
              size="small"
              type="primary"
              @click="publishProduct(row)"
            >
              上架
            </el-button>
            <el-button
              v-if="row.product_status === 1"
              size="small"
              type="warning"
              @click="downshelfProduct(row)"
            >
              下架
            </el-button>
            <el-button
              size="small"
              @click="createScheduleTask(row)"
            >
              定时任务
            </el-button>
            <el-button
              v-if="row.product_status === 0"
              size="small"
              type="danger"
              @click="deleteProduct(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-if="total > 0"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="loadProducts"
        @size-change="loadProducts"
        style="margin-top: 20px; justify-content: center;"
      />
    </el-card>

    <!-- 定时任务对话框 -->
    <el-dialog v-model="scheduleVisible" title="创建定时任务" width="500px">
      <el-form :model="scheduleForm" label-width="120px">
        <el-form-item label="商品">
          <el-input :value="scheduleForm.product?.title" disabled />
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="scheduleForm.task_type" style="width: 100%">
            <el-option label="定时上架" value="publish" />
            <el-option label="定时下架" value="downshelf" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行时间">
          <el-date-picker
            v-model="scheduleForm.execute_time"
            type="datetime"
            placeholder="选择时间"
            style="width: 100%"
            format="YYYY-MM-DD HH:mm"
          />
        </el-form-item>
        <el-form-item label="每日重复">
          <el-switch v-model="scheduleForm.repeat_daily" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scheduleVisible = false">取消</el-button>
        <el-button type="primary" @click="submitScheduleTask" :loading="scheduling">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const loading = ref(false)
const syncing = ref(false)
const scheduling = ref(false)
const products = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterStatus = ref(null)

const scheduleVisible = ref(false)
const scheduleForm = ref({
  product: null,
  task_type: 'publish',
  execute_time: null,
  repeat_daily: false
})

// 加载商品列表
const loadProducts = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (filterStatus.value !== null) {
      params.status = filterStatus.value
    }
    
    const res = await api.get('/xianyu/product/list', { params })
    if (res.data.success) {
      products.value = res.data.data
      total.value = res.data.total
    }
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 同步商品
const syncProducts = async () => {
  syncing.value = true
  try {
    const res = await api.post('/xianyu/product/sync', {
      page_no: 1,
      page_size: 100,
      clear_history: true  // 清除历史数据
    })
    if (res.data.success) {
      const { deleted_count, synced_count, message } = res.data
      if (deleted_count > 0) {
        ElMessage.success(`${message}，新增 ${synced_count} 个商品`)
      } else {
        ElMessage.success(`同步成功，共 ${synced_count} 个商品`)
      }
      loadProducts()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '同步失败')
  } finally {
    syncing.value = false
  }
}

// 上架商品
const publishProduct = async (product) => {
  try {
    const res = await api.post(`/xianyu/product/${product.product_id}/publish`)
    if (res.data.success) {
      ElMessage.success('上架成功')
      loadProducts()
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '上架失败')
  }
}

// 下架商品
const downshelfProduct = async (product) => {
  try {
    await ElMessageBox.confirm('确定下架该商品吗？', '确认', { type: 'warning' })
    
    const res = await api.post(`/xianyu/product/${product.product_id}/downshelf`)
    if (res.data.success) {
      ElMessage.success('下架成功')
      loadProducts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '下架失败')
    }
  }
}

// 删除商品
const deleteProduct = async (product) => {
  try {
    await ElMessageBox.confirm(
      '确定删除该商品吗？（仅草稿箱/待发布状态可删除）',
      '确认删除',
      { type: 'warning' }
    )
    
    const res = await api.delete(`/xianyu/product/${product.product_id}`)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadProducts()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 创建定时任务
const createScheduleTask = (product) => {
  scheduleForm.value = {
    product: product,
    task_type: product.product_status === 1 ? 'downshelf' : 'publish',
    execute_time: null,
    repeat_daily: false
  }
  scheduleVisible.value = true
}

// 提交定时任务
const submitScheduleTask = async () => {
  if (!scheduleForm.value.execute_time) {
    ElMessage.warning('请选择执行时间')
    return
  }
  
  scheduling.value = true
  try {
    const res = await api.post('/xianyu/schedule-task', {
      task_type: scheduleForm.value.task_type,
      product_ids: [scheduleForm.value.product.product_id],
      execute_time: scheduleForm.value.execute_time.toISOString(),
      repeat_daily: scheduleForm.value.repeat_daily
    })
    
    if (res.data.success) {
      ElMessage.success('定时任务创建成功')
      scheduleVisible.value = false
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    scheduling.value = false
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadProducts()
})
</script>

<style scoped>
.xianyu-products {
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

