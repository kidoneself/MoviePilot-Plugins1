<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
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
  quark_name: '',
  baidu_name: '',
  note: '',
  enabled: true
})

const cookieDialogVisible = ref(false)
const cookieDialogTitle = ref('')
const cookiePanType = ref('')
const cookieText = ref('')

const importDialogVisible = ref(false)
const importCsvText = ref('')

const importQuarkDialogVisible = ref(false)
const importQuarkCsvText = ref('')

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
    quark_name: '',
    baidu_name: '',
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
  if (!formData.value.original_name) {
    ElMessage.warning('请填写原名称')
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
      `确定要为"${row.original_name}"生成${panType === 'baidu' ? '百度' : '夸克'}网盘分享链接吗？`,
      '确认生成',
      { type: 'info' }
    )
    
    const res = await api.generateLinks({ 
      pan_type: panType, 
      expire_days: 0,
      original_name: row.original_name  // 传递剧集原始名称，后端会自动查找对应的网盘名称
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
    ElMessage.warning('请粘贴Cookie内容')
    return
  }
  
  try {
    // 直接发送cookie字符串，后端会自动解析
    const res = await api.uploadCookie(cookiePanType.value, cookieText.value.trim())
    
    if (res.data.success) {
      ElMessage.success(res.data.message)
      cookieDialogVisible.value = false
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.message || e.message))
  }
}

const updateMapping = async (row) => {
  try {
    const res = await api.updateMapping(row.id, {
      quark_name: row.quark_name,
      baidu_name: row.baidu_name,
      note: row.note,
      enabled: row.enabled
    })
    
    if (res.data.success) {
      ElMessage.success('更新成功')
    } else {
      ElMessage.error(res.data.message)
      loadMappings()
    }
  } catch (error) {
    ElMessage.error('更新失败')
    loadMappings()
  }
}

const resyncToTarget = async (row, targetType) => {
  try {
    const targetName = targetType === 'quark' ? '夸克' : '百度'
    await ElMessageBox.confirm(
      `确定要重转"${row.original_name}"到${targetName}网盘吗？将删除旧文件并用新名称重新同步。`,
      '确认重转',
      { type: 'warning' }
    )
    
    const loading = ElMessage({
      message: '正在重转，请稍候...',
      type: 'info',
      duration: 0
    })
    
    const res = await api.resyncToTarget({
      original_name: row.original_name,
      target_type: targetType
    })
    
    loading.close()
    
    if (res.data.success) {
      ElMessage.success(res.data.message)
      loadMappings()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重转失败')
    }
  }
}

const copyLinks = async (row) => {
  const links = []
  
  if (row.baidu_link) {
    links.push(`【百度网盘】${row.baidu_link}`)
  }
  
  if (row.quark_link) {
    links.push(`【夸克网盘】${row.quark_link}`)
  }
  
  if (links.length === 0) {
    ElMessage.warning('暂无可复制的链接')
    return
  }
  
  const text = links.join('  ')
  
  try {
    // 尝试使用现代 Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      ElMessage.success('已复制到剪贴板')
    } else {
      // 降级方案：使用传统方法
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      
      if (success) {
        ElMessage.success('已复制到剪贴板')
      } else {
        ElMessage.error('复制失败，请手动复制')
      }
    }
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error(`复制失败: ${error.message || '未知错误'}`)
  }
}

const openImportDialog = () => {
  importCsvText.value = ''
  importDialogVisible.value = true
}

const handleBaiduFileChange = async (file) => {
  const reader = new FileReader()
  reader.onload = async (e) => {
    importCsvText.value = e.target.result
    await importBaiduLinks()
  }
  reader.readAsText(file.raw, 'UTF-8')
  return false
}

const importBaiduLinks = async () => {
  if (!importCsvText.value.trim()) {
    ElMessage.warning('请选择CSV文件')
    return
  }
  
  try {
    const res = await api.importBaiduLinks(importCsvText.value.trim())
    
    if (res.data.success) {
      ElMessage.success(res.data.message)
      importDialogVisible.value = false
      importCsvText.value = ''
      loadMappings()
      
      // 显示详细结果
      if (res.data.details && res.data.details.length > 0) {
        ElMessageBox.alert(
          res.data.details.join('\n'),
          '导入详情',
          { confirmButtonText: '确定' }
        )
      }
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.message || e.message))
  }
}

const openImportQuarkDialog = () => {
  importQuarkCsvText.value = ''
  importQuarkDialogVisible.value = true
}

const handleQuarkFileChange = async (file) => {
  const reader = new FileReader()
  reader.onload = async (e) => {
    importQuarkCsvText.value = e.target.result
    await importQuarkLinks()
  }
  reader.readAsText(file.raw, 'UTF-8')
  return false
}

const importQuarkLinks = async () => {
  if (!importQuarkCsvText.value.trim()) {
    ElMessage.warning('请选择CSV文件')
    return
  }
  
  try {
    const res = await api.importQuarkLinks(importQuarkCsvText.value.trim())
    
    if (res.data.success) {
      ElMessage.success(res.data.message)
      importQuarkDialogVisible.value = false
      importQuarkCsvText.value = ''
      loadMappings()
      
      // 显示详细结果
      if (res.data.details && res.data.details.length > 0) {
        ElMessageBox.alert(
          res.data.details.join('\n'),
          '导入详情',
          { confirmButtonText: '确定' }
        )
      }
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.message || e.message))
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
            <el-button type="info" @click="openImportDialog">导入百度链接</el-button>
            <el-button type="info" @click="openImportQuarkDialog">导入夸克链接</el-button>
            <el-button type="success" @click="generateBaiduLinks">生成百度链接</el-button>
            <el-button type="warning" @click="generateQuarkLinks">生成夸克链接</el-button>
            <el-button @click="showCookieUpload('baidu')">导入百度Cookie</el-button>
            <el-button @click="showCookieUpload('quark')">导入夸克Cookie</el-button>
            <el-button type="primary" @click="handleAdd">添加映射</el-button>
          </el-space>
        </div>
      </template>

      <el-table :data="mappings" v-loading="loading" stripe>
        <el-table-column prop="original_name" label="剧集原名" min-width="150" />
        <el-table-column prop="quark_name" label="夸克显示名" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.quark_name" size="small" @blur="updateMapping(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="baidu_name" label="百度显示名" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.baidu_name" size="small" @blur="updateMapping(row)" />
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
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button size="small" type="success" @click="copyLinks(row)">复制</el-button>
              <el-button size="small" type="warning" @click="resyncToTarget(row, 'quark')">重转夸克</el-button>
              <el-button size="small" type="primary" @click="resyncToTarget(row, 'baidu')">重转百度</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </el-space>
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
        <el-form-item label="夸克显示名">
          <el-input v-model="formData.quark_name" placeholder="请输入夸克显示名（可选）" />
        </el-form-item>
        <el-form-item label="百度显示名">
          <el-input v-model="formData.baidu_name" placeholder="请输入百度显示名（可选）" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.note" placeholder="备注信息（可选）" type="textarea" />
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

    <el-dialog v-model="importDialogVisible" title="批量导入百度链接" width="600px">
      <el-alert type="info" :closable="false" style="margin-bottom: 15px">
        <p><strong>CSV格式说明：</strong></p>
        <p>文件名,链接,提取码,分享时间,分享状态</p>
        <p>灵指,https://pan.baidu.com/s/xxx,yyds,2025-12-19 00:11,生成成功</p>
        <p style="margin-top: 10px; color: #E6A23C;">
          ⚠️ 注意：根据"文件名"匹配"百度显示名"字段，匹配成功才会导入
        </p>
      </el-alert>
      
      <el-upload
        drag
        accept=".csv"
        :auto-upload="false"
        :on-change="handleBaiduFileChange"
        :show-file-list="true"
        :limit="1"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽CSV文件到此处 或 <em>点击选择文件</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只支持.csv格式文件
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importQuarkDialogVisible" title="批量导入夸克链接" width="600px">
      <el-alert type="info" :closable="false" style="margin-bottom: 15px">
        <p><strong>CSV格式说明：</strong></p>
        <p>序号,文件名,分享链接,提取码,状态</p>
        <p>1,斑马英语s1,https://pan.quark.cn/s/xxx,,分享完成</p>
        <p style="margin-top: 10px; color: #E6A23C;">
          ⚠️ 注意：根据"文件名"匹配"夸克显示名"字段，匹配成功才会导入
        </p>
      </el-alert>
      
      <el-upload
        drag
        accept=".csv"
        :auto-upload="false"
        :on-change="handleQuarkFileChange"
        :show-file-list="true"
        :limit="1"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽CSV文件到此处 或 <em>点击选择文件</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只支持.csv格式文件
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="importQuarkDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="cookieDialogVisible" :title="cookieDialogTitle" width="600px">
      <el-alert type="info" :closable="false" style="margin-bottom: 15px">
        <p><strong>如何获取Cookie：</strong></p>
        <p>1. 使用Chrome/Edge浏览器登录{{ cookiePanType === 'baidu' ? '百度' : '夸克' }}网盘</p>
        <p>2. 按F12打开开发者工具</p>
        <p>3. 切换到"Network"（网络）标签</p>
        <p>4. 刷新页面，点击任意请求</p>
        <p>5. 复制完整的Cookie值并粘贴到下方</p>
      </el-alert>
      
      <el-input
        v-model="cookieText"
        type="textarea"
        :rows="10"
        placeholder='直接粘贴浏览器Cookie字符串即可，格式如：name1=value1; name2=value2; ...'
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
