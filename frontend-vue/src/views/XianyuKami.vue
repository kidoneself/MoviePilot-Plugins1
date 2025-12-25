<template>
  <div class="xianyu-kami">
    <el-card>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin: 0;">🎫 卡密管理</h2>
        <el-button size="small" type="warning" @click="closeBrowser">
          关闭浏览器会话
        </el-button>
      </div>
      <el-alert
        title="功能说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <p>通过 Selenium 自动化浏览器操作（<strong>无头模式</strong>），实现卡种创建、卡密添加和自动发货设置</p>
        <p><strong>注意：</strong>首次使用需要扫码登录，登录后会话保持，无需重复登录</p>
        <p><strong>提示：</strong>如需重新登录，请点击右上角"关闭浏览器会话"</p>
      </el-alert>

      <el-tabs v-model="activeTab">
        <!-- 创建卡种 -->
        <el-tab-pane label="创建卡种" name="kind">
          <el-form :model="kindForm" label-width="120px" style="max-width: 600px;">
            <el-form-item label="卡种名称">
              <el-input v-model="kindForm.kind_name" placeholder="如：某某影视卡" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="createKind" :loading="kindCreating">
                创建卡种
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 添加卡密 -->
        <el-tab-pane label="添加卡密" name="cards">
          <el-form :model="cardsForm" label-width="120px" style="max-width: 600px;">
            <el-form-item label="卡种名称">
              <el-input v-model="cardsForm.kind_name" placeholder="目标卡种名称" />
            </el-form-item>
            <el-form-item label="卡密数据">
              <el-input
                v-model="cardsForm.kami_data"
                type="textarea"
                :rows="8"
                placeholder="每行一组，格式: 卡号 密码&#10;示例:&#10;CARD001 PASS001&#10;CARD002 PASS002"
              />
            </el-form-item>
            <el-form-item label="重复次数">
              <el-input-number v-model="cardsForm.repeat_count" :min="1" :max="1000" />
              <span style="margin-left: 10px; color: #909399; font-size: 13px;">
                每组卡密将被重复使用指定次数
              </span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="addCards" :loading="cardsAdding">
                添加卡密
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 设置自动发货 -->
        <el-tab-pane label="自动发货设置" name="shipping">
          <el-form :model="shippingForm" label-width="120px" style="max-width: 600px;">
            <el-form-item label="卡种名称">
              <el-input v-model="shippingForm.kind_name" placeholder="目标卡种名称" />
            </el-form-item>
            <el-form-item label="商品标题">
              <el-input v-model="shippingForm.product_title" placeholder="商品标题（用于搜索定位商品）" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="setupShipping" :loading="shippingSetup">
                设置自动发货
              </el-button>
            </el-form-item>
            <el-alert
              type="warning"
              :closable="false"
              style="margin-top: 10px;"
            >
              将为最新的2个商品设置自动发货，使用指定的卡种发货
            </el-alert>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <!-- 操作日志 -->
      <el-divider content-position="left">操作日志</el-divider>
      <div class="log-container">
        <div v-for="(log, index) in logs" :key="index" class="log-item">
          <el-tag :type="getLogType(log.status)" size="small" style="margin-right: 10px;">
            {{ log.status }}
          </el-tag>
          <span>{{ log.message }}</span>
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">
            {{ formatTime(log.time) }}
          </span>
        </div>
        <el-empty v-if="logs.length === 0" description="暂无日志" />
      </div>
    </el-card>

    <!-- 二维码对话框 -->
    <el-dialog v-model="qrcodeVisible" title="扫码登录" width="400px" :close-on-click-modal="false">
      <div style="text-align: center;">
        <p style="margin-bottom: 20px; color: #606266;">请使用微信扫描二维码登录闲鱼管家</p>
        <img v-if="qrcodeImage" :src="qrcodeImage" style="width: 250px; height: 250px;" />
        <p style="margin-top: 20px; color: #909399; font-size: 13px;">
          登录成功后对话框会自动关闭
        </p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const activeTab = ref('kind')
const logs = ref([])

const kindForm = ref({
  kind_name: ''
})
const kindCreating = ref(false)

const cardsForm = ref({
  kind_name: '',
  kami_data: '',
  repeat_count: 1
})
const cardsAdding = ref(false)

const shippingForm = ref({
  kind_name: '',
  product_title: ''
})
const shippingSetup = ref(false)

// 添加日志
const addLog = (message, status = 'info') => {
  logs.value.unshift({
    message,
    status,
    time: new Date()
  })
  
  // 最多保留50条
  if (logs.value.length > 50) {
    logs.value.pop()
  }
}

// 二维码对话框
const qrcodeVisible = ref(false)
const qrcodeImage = ref('')
const currentTaskId = ref('')

// 创建卡种
const createKind = async () => {
  if (!kindForm.value.kind_name) {
    ElMessage.warning('请输入卡种名称')
    return
  }
  
  kindCreating.value = true
  addLog(`开始创建卡种: ${kindForm.value.kind_name}`, 'loading')
  
  try {
    const res = await api.post('/xianyu/kami/create-kind', {
      kind_name: kindForm.value.kind_name
    })
    
    if (res.data.success && res.data.task_id) {
      // 开始轮询任务状态
      currentTaskId.value = res.data.task_id
      pollTaskStatus(res.data.task_id, 'create_kind')
    }
  } catch (error) {
    const msg = error.response?.data?.detail || '创建失败'
    ElMessage.error(msg)
    addLog(`创建失败: ${msg}`, 'error')
    kindCreating.value = false
  }
}

// 轮询任务状态
const pollTaskStatus = async (taskId, taskType) => {
  const poll = async () => {
    try {
      const res = await api.get(`/xianyu/kami/task/${taskId}`)
      
      if (res.data.success) {
        const task = res.data.data
        
        // 显示二维码
        if (task.qrcode && !qrcodeVisible.value) {
          qrcodeImage.value = task.qrcode
          qrcodeVisible.value = true
          addLog('请扫描二维码登录', 'info')
        }
        
        // 更新日志（只添加新的步骤）
        if (task.progress && task.progress.length > 0) {
          const latestStep = task.progress[task.progress.length - 1]
          // 简单去重：检查最后一条日志
          if (logs.value.length === 0 || logs.value[0].message !== latestStep.step) {
            addLog(latestStep.step, latestStep.status)
          }
        }
        
        // 检查是否完成
        if (task.status === 'completed') {
          if (taskType === 'create_kind') kindCreating.value = false
          if (taskType === 'add_cards') cardsAdding.value = false
          if (taskType === 'setup_shipping') shippingSetup.value = false
          
          qrcodeVisible.value = false
          
          if (task.result) {
            ElMessage.success('操作成功')
            // 清空表单
            if (taskType === 'create_kind') kindForm.value.kind_name = ''
            if (taskType === 'add_cards') cardsForm.value.kami_data = ''
          }
          return // 停止轮询
        } else if (task.status === 'failed') {
          if (taskType === 'create_kind') kindCreating.value = false
          if (taskType === 'add_cards') cardsAdding.value = false
          if (taskType === 'setup_shipping') shippingSetup.value = false
          
          qrcodeVisible.value = false
          ElMessage.error(task.error || '操作失败')
          return // 停止轮询
        }
        
        // 继续轮询
        setTimeout(poll, 1000) // 1秒轮询一次
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error)
      setTimeout(poll, 2000) // 出错后2秒重试
    }
  }
  
  poll()
}

// 添加卡密
const addCards = async () => {
  if (!cardsForm.value.kind_name) {
    ElMessage.warning('请输入卡种名称')
    return
  }
  
  if (!cardsForm.value.kami_data) {
    ElMessage.warning('请输入卡密数据')
    return
  }
  
  cardsAdding.value = true
  addLog(`开始添加卡密到: ${cardsForm.value.kind_name}`, 'loading')
  
  try {
    const res = await api.post('/xianyu/kami/add-cards', {
      kind_name: cardsForm.value.kind_name,
      kami_data: cardsForm.value.kami_data,
      repeat_count: cardsForm.value.repeat_count
    })
    
    if (res.data.success && res.data.task_id) {
      // 开始轮询任务状态
      currentTaskId.value = res.data.task_id
      pollTaskStatus(res.data.task_id, 'add_cards')
    }
  } catch (error) {
    const msg = error.response?.data?.detail || '添加失败'
    ElMessage.error(msg)
    addLog(`添加失败: ${msg}`, 'error')
    cardsAdding.value = false
  }
}

// 设置自动发货
const setupShipping = async () => {
  if (!shippingForm.value.kind_name) {
    ElMessage.warning('请输入卡种名称')
    return
  }
  
  if (!shippingForm.value.product_title) {
    ElMessage.warning('请输入商品标题')
    return
  }
  
  shippingSetup.value = true
  addLog(`开始设置自动发货: ${shippingForm.value.kind_name}`, 'loading')
  
  try {
    const res = await api.post('/xianyu/kami/setup-shipping', {
      kind_name: shippingForm.value.kind_name,
      product_title: shippingForm.value.product_title
    })
    
    if (res.data.success && res.data.task_id) {
      // 开始轮询任务状态
      currentTaskId.value = res.data.task_id
      pollTaskStatus(res.data.task_id, 'setup_shipping')
    }
  } catch (error) {
    const msg = error.response?.data?.detail || '设置失败'
    ElMessage.error(msg)
    addLog(`设置失败: ${msg}`, 'error')
    shippingSetup.value = false
  }
}

// 获取日志类型
const getLogType = (status) => {
  const map = {
    'loading': 'info',
    'success': 'success',
    'error': 'danger',
    'warning': 'warning',
    'info': ''
  }
  return map[status] || ''
}

// 格式化时间
const formatTime = (time) => {
  return time.toLocaleTimeString('zh-CN')
}

// 关闭浏览器会话
const closeBrowser = async () => {
  try {
    await ElMessageBox.confirm(
      '关闭浏览器会话后，下次操作需要重新登录。确定关闭吗？',
      '确认',
      { type: 'warning' }
    )
    
    const res = await api.post('/xianyu/kami/close-browser')
    if (res.data.success) {
      ElMessage.success('浏览器会话已关闭')
      addLog('浏览器会话已关闭', 'info')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}
</script>

<style scoped>
.xianyu-kami {
  padding: 20px;
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.log-item {
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
  font-size: 14px;
}

.log-item:last-child {
  border-bottom: none;
}
</style>

