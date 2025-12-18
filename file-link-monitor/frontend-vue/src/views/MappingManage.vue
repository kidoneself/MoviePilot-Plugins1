<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const mappings = ref([])
const total = ref(0)
const loading = ref(false)
const searchText = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const dialogVisible = ref(false)
const dialogTitle = ref('添加映射')
const formData = ref({
  id: null,
  original_name: '',
  custom_name: '',
  note: '',
  enabled: true
})

const cookieDialogVisible = ref(false)
const cookieDialogTitle = ref('')
const cookiePanType = ref('')
const cookieText = ref('')

const loadMappings = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchText.value) {
      params.search = searchText.value
    }
    
    const res = await api.getMappings(params)
    if (res.data.success) {
      mappings.value = res.data.data
      total.value = res.data.total
    }
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加映射'
  formData.value = {
    id: null,
    original_name: '',
    custom_name: '',
    note: '',
    enabled: true
  }
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑映射'
  formData.value = { ...row }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!formData.value.original_name || !formData.value.custom_name) {
    ElMessage.warning('请填写原名称和自定义名称')
    return
  }
  
  try {
    let res
    if (formData.value.id) {
      res = await api.updateMapping(formData.value.id, formData.value)
    } else {
      res = await api.createMapping(formData.value)
    }
    
    if (res.data.success) {
      ElMessage.success(formData.value.id ? '更新成功' : '添加成功')
      dialogVisible.value = false
      loadMappings()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除映射"${row.original_name}"吗？`, '确认删除', {
      type: 'warning'
    })
    
    const res = await api.deleteMapping(row.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      loadMappings()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleClearRecords = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要清除"${row.original_name}"的所有硬链接记录吗？\n\n清除后可以重新同步以使用新的映射名称。`,
      '确认清除',
      { type: 'warning' }
    )
    
    const res = await api.deleteRecordsByShow(row.original_name)
    if (res.data.success) {
      ElMessage.success(`成功清除 ${res.data.deleted_count} 条记录！\n\n现在可以重新同步以使用新名称。`)
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清除失败')
    }
  }
}

const copyLink = (link) => {
  navigator.clipboard.writeText(link).then(() => {
    ElMessage.success('链接已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const generateBaiduLinks = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要批量生成百度网盘分享链接吗？\n\n将会打开浏览器窗口，请在窗口中完成登录操作。\n处理过程可能需要较长时间，请耐心等待。',
      '确认生成',
      { type: 'info' }
    )
    
    const res = await api.generateLinks({ pan_type: 'baidu', expire_days: 0 })
    if (res.data.success) {
      ElMessage.success(res.data.message + '\n\n处理完成后会自动更新到映射表中。')
    } else {
      ElMessage.error('启动失败: ' + res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('请求失败')
    }
  }
}

const generateQuarkLinks = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要批量生成夸克网盘分享链接吗？\n\n将会打开浏览器窗口，请在窗口中完成登录操作。\n处理过程可能需要较长时间，请耐心等待。',
      '确认生成',
      { type: 'info' }
    )
    
    const res = await api.generateLinks({ pan_type: 'quark', expire_days: 0 })
    if (res.data.success) {
      ElMessage.success(res.data.message + '\n\n处理完成后会自动更新到映射表中。')
    } else {
      ElMessage.error('启动失败: ' + res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('请求失败')
    }
  }
}

const generateSingleLink = async (row, panType) => {
  try {
    await ElMessageBox.confirm(
      `确定要为"${row.custom_name}"生成${panType === 'baidu' ? '百度' : '夸克'}网盘分享链接吗？`,
      '确认生成',
      { type: 'info' }
    )
    
    const res = await api.generateLinks({ 
      pan_type: panType, 
      expire_days: 0,
      target_path: row.custom_name  // 只生成这一个
    })
    
    if (res.data.success) {
      ElMessage.success(res.data.message + '\n\n处理完成后会自动更新。')
      // 3秒后刷新列表查看结果
      setTimeout(() => {
        loadMappings()
      }, 3000)
    } else {
      ElMessage.error('启动失败: ' + res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('请求失败')
    }
  }
}

const showCookieUpload = (panType) => {
  cookiePanType.value = panType
  cookieDialogTitle.value = `导入${panType === 'baidu' ? '百度' : '夸克'}网盘Cookie`
  cookieText.value = ''
  cookieDialogVisible.value = true
}

const uploadCookie = async () => {
  if (!cookieText.value.trim()) {
    ElMessage.warning('请粘贴Cookie JSON内容')
    return
  }
  
  try {
    // 解析JSON
    const cookieData = JSON.parse(cookieText.value)
    
    // 上传Cookie
    const res = await api.uploadCookie(cookiePanType.value, cookieData)
    
    if (res.data.success) {
      ElMessage.success(res.data.message)
      cookieDialogVisible.value = false
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    if (e instanceof SyntaxError) {
      ElMessage.error('Cookie格式错误，请确保是有效的JSON格式')
    } else {
      ElMessage.error('上传失败')
    }
  }
}

const exportMappings = () => {
  const params = {}
  if (searchText.value) {
    params.search = searchText.value
  }
  
  api.exportMappings(params).then(res => {
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '名称映射.xlsx'
    a.click()
    window.URL.revokeObjectURL(url)
  }).catch(() => {
    ElMessage.error('导出失败')
  })
}

onMounted(() => {
  loadMappings()
})
</script>

<template>
  <div class="mapping-manage">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">自定义名称映射</span>
          <el-space>
            <el-input
              v-model="searchText"
              placeholder="搜索原名或自定义名..."
              style="width: 250px"
              clearable
              @keyup.enter="loadMappings"
            />
            <el-button type="primary" @click="loadMappings">搜索</el-button>
            <el-button @click="exportMappings">导出Excel</el-button>
            <el-button type="success" @click="generateBaiduLinks">生成百度链接</el-button>
            <el-button type="warning" @click="generateQuarkLinks">生成夸克链接</el-button>
            <el-button @click="showCookieUpload('baidu')">导入百度Cookie</el-button>
            <el-button @click="showCookieUpload('quark')">导入夸克Cookie</el-button>
            <el-button type="primary" @click="handleAdd">添加映射</el-button>
          </el-space>
        </div>
      </template>

      <el-table :data="mappings" v-loading="loading" stripe>
        <el-table-column prop="original_name" label="原名称" min-width="150" />
        <el-table-column prop="custom_name" label="自定义名称" min-width="150">
          <template #default="{ row }">
            <strong>{{ row.custom_name }}</strong>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="baidu_link" label="百度网盘" min-width="220">
          <template #default="{ row }">
            <div v-if="row.baidu_link" style="display: flex; align-items: center; gap: 8px;">
              <a
                :href="row.baidu_link"
                target="_blank"
                class="link-text"
                @click.prevent="(e) => { if (!e.metaKey && !e.ctrlKey) copyLink(row.baidu_link) }"
                :title="row.baidu_link"
                style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
              >
                {{ row.baidu_link }}
              </a>
              <el-button size="small" @click="generateSingleLink(row, 'baidu')">重新获取</el-button>
            </div>
            <el-button v-else type="primary" size="small" @click="generateSingleLink(row, 'baidu')">
              获取链接
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="quark_link" label="夸克网盘" min-width="220">
          <template #default="{ row }">
            <div v-if="row.quark_link" style="display: flex; align-items: center; gap: 8px;">
              <a
                :href="row.quark_link"
                target="_blank"
                class="link-text"
                @click.prevent="(e) => { if (!e.metaKey && !e.ctrlKey) copyLink(row.quark_link) }"
                :title="row.quark_link"
                style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
              >
                {{ row.quark_link }}
              </a>
              <el-button size="small" @click="generateSingleLink(row, 'quark')">重新获取</el-button>
            </div>
            <el-button v-else type="warning" size="small" @click="generateSingleLink(row, 'quark')">
              获取链接
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            <el-button size="small" @click="handleClearRecords(row)">清除记录</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadMappings"
        @size-change="loadMappings"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="原名称" required>
          <el-input v-model="formData.original_name" placeholder="请输入原名称" />
        </el-form-item>
        <el-form-item label="自定义名称" required>
          <el-input v-model="formData.custom_name" placeholder="请输入自定义名称" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- Cookie导入对话框 -->
    <el-dialog
      v-model="cookieDialogVisible"
      :title="cookieDialogTitle"
      width="600px"
    >
      <el-alert
        title="使用说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <p>1. 在本地浏览器中登录网盘</p>
        <p>2. 打开浏览器开发者工具（F12）</p>
        <p>3. 在Console中运行：<code>JSON.stringify(await navigator.storage.getDirectory().then(d=>d.getFileHandle('cookies')))</code></p>
        <p>或者从已保存的 <code>{{ cookiePanType }}_cookies.json</code> 文件中复制内容</p>
        <p>4. 将JSON内容粘贴到下方文本框</p>
      </el-alert>
      
      <el-input
        v-model="cookieText"
        type="textarea"
        :rows="10"
        placeholder='粘贴Cookie JSON内容，格式如：[{"name":"BDUSS","value":"xxx",...},...]'
      />
      
      <template #footer>
        <el-button @click="cookieDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="uploadCookie">上传</el-button>
      </template>
    </el-dialog>
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

.link-text {
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
  word-break: break-all;
}

.link-text:hover {
  color: #66b1ff;
  text-decoration: underline;
}
</style>
