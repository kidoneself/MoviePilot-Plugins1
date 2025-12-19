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

const todaySync = ref({
  quark: {},
  baidu: {}
})
const showTodayDetail = ref(false)
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

const loadTodaySync = async () => {
  try {
    const res = await api.getTodaySync()
    if (res.data.success) {
      todaySync.value = res.data.data
    }
  } catch (error) {
    console.error('加载今日同步失败:', error)
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
  loadTodaySync()
  setInterval(() => {
    loadStats()
    loadTodaySync()
  }, 30000)
  
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
          <el-button v-if="stats.today_count > 0" type="warning" size="small" @click="showTodayDetail = true">
            📊 今日明细
          </el-button>
          <el-button type="success" @click="syncAll">
            🔄 全量同步
          </el-button>
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
      </el-aside>
      
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
    
    <!-- 今日同步明细弹窗 -->
    <el-dialog v-model="showTodayDetail" title="📊 今日同步明细" width="800px">
      <!-- 夸克网盘 -->
      <div v-if="Object.keys(todaySync.quark).length > 0" class="pan-section">
        <h4>📦 夸克网盘</h4>
        <div v-for="(cat2Items, cat1) in todaySync.quark" :key="'quark-' + cat1" class="category-section">
          <div v-for="(shows, cat2) in cat2Items" :key="'quark-' + cat1 + '-' + cat2">
            <div class="category-title">{{ cat1 }} > {{ cat2 }}</div>
            <div v-for="(files, showName) in shows" :key="'quark-show-' + showName" class="show-item">
              <div class="show-name">{{ showName }}:</div>
              <ul class="file-list">
                <li v-for="(file, idx) in files" :key="idx">{{ file }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 百度网盘 -->
      <div v-if="Object.keys(todaySync.baidu).length > 0" class="pan-section">
        <h4>📦 百度网盘</h4>
        <div v-for="(cat2Items, cat1) in todaySync.baidu" :key="'baidu-' + cat1" class="category-section">
          <div v-for="(shows, cat2) in cat2Items" :key="'baidu-' + cat1 + '-' + cat2">
            <div class="category-title">{{ cat1 }} > {{ cat2 }}</div>
            <div v-for="(files, showName) in shows" :key="'baidu-show-' + showName" class="show-item">
              <div class="show-name">{{ showName }}:</div>
              <ul class="file-list">
                <li v-for="(file, idx) in files" :key="idx">{{ file }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 迅雷网盘 -->
      <div v-if="Object.keys(todaySync.xunlei || {}).length > 0" class="pan-section">
        <h4>📦 迅雷网盘</h4>
        <div v-for="(cat2Items, cat1) in todaySync.xunlei" :key="'xunlei-' + cat1" class="category-section">
          <div v-for="(shows, cat2) in cat2Items" :key="'xunlei-' + cat1 + '-' + cat2">
            <div class="category-title">{{ cat1 }} > {{ cat2 }}</div>
            <div v-for="(files, showName) in shows" :key="'xunlei-show-' + showName" class="show-item">
              <div class="show-name">{{ showName }}:</div>
              <ul class="file-list">
                <li v-for="(file, idx) in files" :key="idx">{{ file }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <div v-if="Object.keys(todaySync.quark).length === 0 && Object.keys(todaySync.baidu).length === 0 && Object.keys(todaySync.xunlei || {}).length === 0" class="empty-tip">
        暂无同步记录
      </div>
    </el-dialog>
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

.today-sync-card {
  margin-bottom: 20px;
}

.today-sync-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.today-sync-card .rotate {
  transition: transform 0.3s;
}

.pan-section {
  margin-bottom: 20px;
}

.pan-section h4 {
  margin: 0 0 10px 0;
  color: #409eff;
  font-size: 16px;
}

.category-section {
  margin-bottom: 15px;
}

.category-title {
  font-weight: bold;
  color: #606266;
  margin-bottom: 5px;
  padding-left: 20px;
}

.show-item {
  padding: 8px 0 8px 40px;
  font-size: 14px;
  margin-bottom: 10px;
}

.show-item .show-name {
  font-weight: 600;
  color: #303133;
  margin-bottom: 5px;
}

.show-item .file-list {
  color: #606266;
  list-style: none;
  padding: 0;
  margin: 0;
}

.show-item .file-list li {
  padding: 3px 0;
  padding-left: 15px;
  position: relative;
}

.show-item .file-list li:before {
  content: "•";
  position: absolute;
  left: 0;
  color: #909399;
}

.empty-tip {
  text-align: center;
  color: #909399;
  padding: 20px;
}
</style>
