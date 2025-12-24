<template>
  <div class="share-links-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分享链接</span>
          <el-button type="primary" size="small" @click="copyAllLinks">📋 一键复制全部</el-button>
        </div>
      </template>

      <div v-if="loading" class="loading">加载中...</div>
      
      <div v-else class="share-list">
        <div v-for="item in shareLinks" :key="item.original_name" class="share-item">
          <div class="show-name">
            {{ item.original_name }}
            <span v-if="item.is_completed" class="completed-tag">【完结】</span>
          </div>
          
          <div class="links">
            <div v-if="item.baidu_link" class="link-row">
              <span class="link-label">BD：</span>
              <a :href="item.baidu_link.split(' ')[0]" target="_blank" class="link-url">{{ item.baidu_link }}</a>
            </div>
            
            <div v-if="item.quark_link" class="link-row">
              <span class="link-label">KK：</span>
              <a :href="item.quark_link.split(' ')[0]" target="_blank" class="link-url">{{ item.quark_link }}</a>
            </div>
            
            <div v-if="item.xunlei_link" class="link-row">
              <span class="link-label">XL：</span>
              <a :href="item.xunlei_link.split(' ')[0]" target="_blank" class="link-url">{{ item.xunlei_link }}</a>
            </div>
          </div>
          
          <el-button size="small" @click="copyItem(item)" class="copy-btn">复制</el-button>
        </div>

        <div v-if="shareLinks.length === 0" class="empty">暂无分享链接</div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const loading = ref(true)
const shareLinks = ref([])

const loadShareLinks = async () => {
  try {
    loading.value = true
    const res = await api.getShareLinks()
    if (res.data.success) {
      shareLinks.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const formatItemText = (item) => {
  let text = `${item.original_name}(尽快保存，以免失效)\n`
  
  if (item.baidu_link) {
    text += `BD：${item.baidu_link}\n`
  }
  
  if (item.quark_link) {
    text += `KK：${item.quark_link}\n`
  }
  
  if (item.xunlei_link) {
    text += `XL：${item.xunlei_link}\n`
  }
  
  return text
}

const copyToClipboard = (text) => {
  // 创建临时textarea元素
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  
  // 选中并复制
  textarea.select()
  textarea.setSelectionRange(0, textarea.value.length)
  
  try {
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    return successful
  } catch (error) {
    document.body.removeChild(textarea)
    return false
  }
}

const copyItem = (item) => {
  const text = formatItemText(item)
  if (copyToClipboard(text)) {
    ElMessage.success('已复制到剪贴板')
  } else {
    ElMessage.error('复制失败')
  }
}

const copyAllLinks = () => {
  const allText = shareLinks.value.map(item => formatItemText(item)).join('\n')
  if (copyToClipboard(allText)) {
    ElMessage.success('已复制全部链接')
  } else {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  loadShareLinks()
})
</script>

<style scoped>
.share-links-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading {
  text-align: center;
  padding: 40px;
  color: #999;
}

.share-list {
  max-width: 1200px;
}

.share-item {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  position: relative;
}

.share-item:hover {
  background-color: #f9f9f9;
}

.show-name {
  font-size: 18px;
  font-weight: bold;
  color: #333;
  margin-bottom: 12px;
}

.completed-tag {
  font-size: 14px;
  color: #67c23a;
  margin-left: 8px;
}

.links {
  margin-bottom: 10px;
}

.link-row {
  margin: 8px 0;
  display: flex;
  align-items: center;
}

.link-label {
  font-weight: bold;
  color: #409eff;
  min-width: 40px;
}

.link-url {
  color: #606266;
  text-decoration: none;
  word-break: break-all;
  flex: 1;
}

.link-url:hover {
  color: #409eff;
  text-decoration: underline;
}

.pwd {
  margin-left: 10px;
  color: #f56c6c;
  font-weight: bold;
}

.copy-btn {
  position: absolute;
  top: 20px;
  right: 20px;
}

.empty {
  text-align: center;
  padding: 60px;
  color: #999;
  font-size: 16px;
}
</style>
