<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Document, List, Folder, Setting } from '@element-plus/icons-vue'
import api from './api'

const router = useRouter()
const stats = ref({
  today_count: 0,
  total_count: 0,
  success_count: 0,
  failed_count: 0,
  total_size: '0 B'
})

const activeMenu = ref('mappings')

const loadStats = async () => {
  try {
    const res = await api.getStats()
    if (res.data.success) {
      stats.value = res.data.data
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const handleMenuSelect = (key) => {
  activeMenu.value = key
  router.push(`/${key}`)
}

const syncAll = async () => {
  try {
    const res = await api.syncAll()
    if (res.data.success) {
      ElMessage.success('全量同步已启动')
    } else {
      ElMessage.error('启动失败: ' + res.data.message)
    }
  } catch (error) {
    ElMessage.error('请求失败')
  }
}

onMounted(() => {
  loadStats()
  setInterval(loadStats, 30000)
  
  // 根据当前路由设置active菜单
  const path = router.currentRoute.value.path
  activeMenu.value = path.substring(1) || 'mappings'
})
</script>

<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-title">
        <h2>文件监控硬链接系统</h2>
        <span class="subtitle">File Link Monitor - 实时监控 · 自动硬链接 · 高效管理</span>
      </div>
      
      <div class="header-stats">
        <el-space :size="20">
          <el-statistic title="今日处理" :value="stats.today_count" />
          <el-statistic title="总记录" :value="stats.total_count" />
          <el-statistic title="成功" :value="stats.success_count" value-style="color: #67C23A" />
          <el-statistic title="失败" :value="stats.failed_count" value-style="color: #F56C6C" />
          <el-statistic title="总大小" :value="stats.total_size" />
        </el-space>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="200px" class="app-aside">
        <el-menu
          :default-active="activeMenu"
          class="app-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="mappings">
            <el-icon><Document /></el-icon>
            <span>映射管理</span>
          </el-menu-item>
          <el-menu-item index="records">
            <el-icon><List /></el-icon>
            <span>链接记录</span>
          </el-menu-item>
          <el-menu-item index="tree">
            <el-icon><Folder /></el-icon>
            <span>目录树</span>
          </el-menu-item>
          <el-menu-item index="config">
            <el-icon><Setting /></el-icon>
            <span>配置</span>
          </el-menu-item>
        </el-menu>
        
        <div class="menu-footer">
          <el-button type="primary" @click="syncAll" style="width: 100%">
            全量同步
          </el-button>
        </div>
      </el-aside>
      
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-container {
  height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 30px;
}

.header-title h2 {
  margin: 0;
  font-size: 24px;
}

.header-title .subtitle {
  font-size: 12px;
  opacity: 0.9;
}

.header-stats :deep(.el-statistic__head) {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}

.header-stats :deep(.el-statistic__content) {
  color: white;
  font-size: 20px;
}

.app-aside {
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
}

.app-menu {
  flex: 1;
  border: none;
}

.menu-footer {
  padding: 20px;
  border-top: 1px solid #dcdfe6;
}

.app-main {
  background: #ffffff;
  padding: 20px;
}
</style>
