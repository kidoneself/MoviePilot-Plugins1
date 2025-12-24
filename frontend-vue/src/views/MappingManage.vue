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

const categories = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加映射')
const formData = ref({
  id: null,
  original_name: '',
  category: '',
  quark_name: '',
  baidu_name: '',
  xunlei_name: '',
  note: '',
  enabled: true
})

// Cookie管理
const cookieDialogVisible = ref(false)
const cookieDialogTitle = ref('导入Cookie')
const cookiePanType = ref('baidu')  // baidu/quark
const cookieText = ref('')

// 盘搜
const pansouDialogVisible = ref(false)
const pansouKeyword = ref('')
const pansouLoading = ref(false)
const currentMapping = ref(null)  // 当前盘搜对应的映射记录
const activeTab = ref('baidu')
const pansouResults = ref({
  total: 0,
  baidu: [],
  quark: [],
  xunlei: []
})

// 编辑链接
const editLinkDialogVisible = ref(false)
const editLinkData = ref({
  row: null,
  panType: '',
  link: ''
})


const loadCategories = async () => {
  try {
    const res = await api.get('/categories')
    if (res.data.success) {
      categories.value = res.data.categories || []
    }
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

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
    category: '',
    quark_name: '',
    baidu_name: '',
    xunlei_name: '',
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

const handleAutoObfuscate = async () => {
  if (!formData.value.original_name) {
    ElMessage.warning('请先输入原名称')
    return
  }
  
  try {
    const res = await api.obfuscateName(formData.value.original_name)
    if (res.data.success) {
      const obfuscatedName = res.data.data.obfuscated_name
      formData.value.quark_name = obfuscatedName
      formData.value.baidu_name = obfuscatedName
      formData.value.xunlei_name = obfuscatedName
      ElMessage.success(`自动混淆成功: ${obfuscatedName}`)
    } else {
      ElMessage.error(res.data.message || '混淆失败')
    }
  } catch (error) {
    ElMessage.error('混淆失败')
  }
}

const handleOriginalNameBlur = async () => {
  // 只在新增映射且原名称不为空且显示名为空时自动混淆
  if (!formData.value.id && 
      formData.value.original_name && 
      !formData.value.quark_name && 
      !formData.value.baidu_name && 
      !formData.value.xunlei_name) {
    try {
      const res = await api.obfuscateName(formData.value.original_name)
      if (res.data.success) {
        const obfuscatedName = res.data.data.obfuscated_name
        formData.value.quark_name = obfuscatedName
        formData.value.baidu_name = obfuscatedName
        formData.value.xunlei_name = obfuscatedName
      }
    } catch (error) {
      console.error('自动混淆失败:', error)
    }
  }
}

const copyLink = (link) => {
  try {
    // 尝试使用现代API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(link).then(() => {
        ElMessage.success('链接已复制')
      }).catch(() => {
        // 降级到传统方法
        fallbackCopy(link)
      })
    } else {
      // 直接使用传统方法
      fallbackCopy(link)
    }
  } catch (error) {
    console.error('复制失败:', error)
    ElMessage.error('复制失败')
  }
}

const fallbackCopy = (text) => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const success = document.execCommand('copy')
  document.body.removeChild(textarea)
  
  if (success) {
    ElMessage.success('链接已复制')
  } else {
    ElMessage.error('复制失败，请手动复制')
  }
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


const updateMapping = async (row) => {
  try {
    const res = await api.updateMapping(row.id, {
      quark_name: row.quark_name,
      baidu_name: row.baidu_name,
      xunlei_name: row.xunlei_name,
      note: row.note,
      enabled: row.enabled,
      is_completed: row.is_completed
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
    const targetNames = {'quark': '夸克', 'baidu': '百度', 'xunlei': '迅雷'}
    const targetName = targetNames[targetType] || '未知'
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
  
  if (row.xunlei_link) {
    links.push(`【迅雷网盘】${row.xunlei_link}`)
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

// Cookie管理
const openCookieDialog = (panType) => {
  cookiePanType.value = panType
  const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
  cookieDialogTitle.value = `导入${panNames[panType]}网盘Cookie`
  cookieText.value = ''
  cookieDialogVisible.value = true
}

const uploadCookie = async () => {
  if (!cookieText.value.trim()) {
    const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
    const panName = panNames[cookiePanType.value] || '网盘'
    ElMessage.warning(`请粘贴${panName}网盘Cookie`)
    return
  }
  
  try {
    const res = await api.updateCookie(cookiePanType.value, cookieText.value.trim())
    if (res.data.success) {
      ElMessage.success(res.data.message)
      cookieDialogVisible.value = false
    } else {
      ElMessage.error(res.data.message || '上传失败')
    }
  } catch (error) {
    ElMessage.error('上传Cookie失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 从映射转存
const transferFromMapping = async (mappingId, panType) => {
  try {
    loading.value = true
    const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
    const panName = panNames[panType] || '网盘'
    
    ElMessage.info(`正在转存到${panName}...`)
    
    const res = await api.post(`/transfer/from_mapping/${mappingId}?pan_type=${panType}`)
    
    if (res.data.success) {
      ElMessage.success(`${panName}转存成功！文件数：${res.data.file_count}`)
    } else {
      ElMessage.error(res.data.message || '转存失败')
    }
  } catch (error) {
    ElMessage.error('转存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 生成单个分享链接
const generateSingleLink = async (row, panType) => {
  try {
    loading.value = true
    const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
    const panName = panNames[panType] || '网盘'
    const res = await api.generateShareLink(panType, row.original_name)
    
    if (res.data.success) {
      const result = res.data.results[row.original_name]
      if (result.success) {
        ElMessage.success(`${panName}链接生成成功`)
        loadMappings()
      } else {
        ElMessage.error(result.error || '生成失败')
      }
    } else {
      ElMessage.error(res.data.message || '生成失败')
    }
  } catch (error) {
    ElMessage.error('生成链接失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 盘搜
const handlePanSou = async (mappingOrKeyword) => {
  // 判断是映射对象还是关键词字符串
  if (typeof mappingOrKeyword === 'object' && mappingOrKeyword !== null) {
    // 从列表点击，传入的是映射记录
    currentMapping.value = mappingOrKeyword
    pansouKeyword.value = mappingOrKeyword.original_name
    pansouDialogVisible.value = true
    await executePanSou(mappingOrKeyword.original_name)
  } else {
    // 从顶部盘搜按钮点击，传入的是空字符串
    currentMapping.value = null
    pansouKeyword.value = mappingOrKeyword || ''
    pansouDialogVisible.value = true
    
    // 如果有关键词，自动搜索；如果没有，只打开对话框
    if (mappingOrKeyword) {
      await executePanSou(mappingOrKeyword)
    } else {
      // 清空之前的搜索结果
      pansouResults.value = {
        total: 0,
        baidu: [],
        quark: [],
        xunlei: []
      }
    }
  }
}

// 执行盘搜
const executePanSou = async (keyword) => {
  if (!keyword || !keyword.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  pansouLoading.value = true
  pansouKeyword.value = keyword
  
  try {
    ElMessage.info('正在搜索网盘资源...')
    const res = await api.pansouSearch(keyword)
    
    if (res.data.success) {
      const results = res.data.results
      
      // 解析结果
      pansouResults.value = {
        total: res.data.total,
        baidu: results.baidu || [],
        quark: results.quark || [],
        xunlei: results.xunlei || []
      }
      
      ElMessage.success(`搜索完成！找到 ${res.data.total} 条结果`)
    } else {
      ElMessage.error('搜索失败')
    }
  } catch (error) {
    ElMessage.error('搜索失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    pansouLoading.value = false
  }
}

const openPanLink = (url) => {
  window.open(url, '_blank')
}

// 从盘搜结果转存
const confirmTransferFromPansou = async (shareUrl, passCode, panType) => {
  const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
  const panName = panNames[panType] || '网盘'
  
  // 如果没有提取码，尝试从URL中解析
  if (!passCode) {
    const urlMatch = shareUrl.match(/pwd=([a-zA-Z0-9]+)/)
    if (urlMatch) {
      passCode = urlMatch[1]
      console.log('从URL解析提取码:', passCode)
    }
  }
  
  // 使用搜索关键词作为文件夹名
  const folderName = pansouKeyword.value || '未命名'
  
  try {
    // 优先使用 currentMapping（从列表点击盘搜时会有）
    let mapping = currentMapping.value
    
    // 如果没有 currentMapping，再去查找匹配
    if (!mapping) {
      // 先精确匹配
      mapping = mappings.value.find(m => m.original_name === folderName)
      
      if (!mapping) {
        // 尝试包含匹配
        mapping = mappings.value.find(m => 
          m.original_name.includes(folderName) || folderName.includes(m.original_name)
        )
      }
    }
    
    // 确定最终使用的文件夹名称：优先使用对应网盘的自定义名称
    let finalFolderName = folderName
    if (mapping) {
      const panNameField = `${panType}_name`
      finalFolderName = mapping[panNameField] || mapping.original_name || folderName
    }
    
    // 构建目标路径
    const category = mapping?.category || '未分类'
    const targetPath = `/A-闲鱼影视（自动更新）/${category}/${finalFolderName}`
    
    // 显示提示信息
    let confirmMessage = `将转存到【${panName}网盘】\n\n目标路径：\n${targetPath}`
    if (mapping) {
      confirmMessage += `\n\n匹配到映射：${mapping.original_name} (分类: ${mapping.category || '未分类'})`
    } else {
      confirmMessage += `\n\n⚠️ 未找到匹配的映射记录，将使用默认分类`
    }
    confirmMessage += `\n\n确认转存吗？`
    
    // 直接显示路径确认
    await ElMessageBox.confirm(
      confirmMessage,
      '确认转存',
      {
        confirmButtonText: '确认转存',
        cancelButtonText: '取消',
        type: 'info',
        dangerouslyUseHTMLString: false
      }
    )
    
    // 执行转存
    executeTransferFromPansou(shareUrl, passCode, panType, targetPath)
    
  } catch {
    // 用户取消
  }
}

// 执行转存
const executeTransferFromPansou = async (shareUrl, passCode, panType, targetPath) => {
  try {
    loading.value = true
    const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
    const panName = panNames[panType] || '网盘'
    
    console.log('开始转存：', {
      shareUrl,
      passCode,
      panType,
      targetPath
    })
    
    ElMessage.info(`正在转存到${panName}...`)
    
    const res = await api.post('/transfer', {
      share_url: shareUrl,
      pass_code: passCode,
      target_path: targetPath,
      pan_type: panType,
      use_openlist: true
    })
    
    console.log('转存响应：', res.data)
    
    if (res.data.success) {
      ElMessage.success(`${panName}转存成功！文件数：${res.data.file_count}`)
    } else {
      ElMessage.error(res.data.message || '转存失败')
    }
  } catch (error) {
    ElMessage.error('转存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
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

// 打开编辑链接对话框
const openEditLinkDialog = (row, panType) => {
  const panNames = {'baidu': '百度', 'quark': '夸克', 'xunlei': '迅雷'}
  const linkField = `${panType}_link`
  
  editLinkData.value = {
    row: row,
    panType: panType,
    panName: panNames[panType],
    link: row[linkField] || ''
  }
  editLinkDialogVisible.value = true
}

// 保存编辑的链接
const saveEditedLink = async () => {
  if (!editLinkData.value.link.trim()) {
    ElMessage.warning('链接不能为空')
    return
  }
  
  try {
    const linkField = `${editLinkData.value.panType}_link`
    const updateData = {}
    updateData[linkField] = editLinkData.value.link.trim()
    
    const res = await api.updateMapping(editLinkData.value.row.id, updateData)
    
    if (res.data.success) {
      ElMessage.success('链接更新成功')
      editLinkDialogVisible.value = false
      loadMappings()
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error) {
    ElMessage.error('更新失败: ' + (error.response?.data?.detail || error.message))
  }
}

onMounted(() => {
  loadCategories()
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
            <el-button type="primary" @click="handlePanSou('')">🔍 盘搜</el-button>
            <el-button @click="exportMappings">导出Excel</el-button>
            <el-button type="success" @click="openCookieDialog('baidu')">导入百度Cookie</el-button>
            <el-button type="warning" @click="openCookieDialog('quark')">导入夸克Cookie</el-button>
            <el-button type="info" @click="openCookieDialog('xunlei')">导入迅雷Cookie</el-button>
            <el-button type="primary" @click="handleAdd">添加映射</el-button>
          </el-space>
        </div>
      </template>

      <!-- 卡片列表布局 -->
      <div v-loading="loading" class="mapping-cards">
        <el-card v-for="row in mappings" :key="row.id" class="mapping-card" shadow="hover">
          <!-- 卡片头部：剧集名称、状态、操作按钮 -->
          <template #header>
            <div class="card-header-content">
              <div class="show-info">
                <h3>{{ row.original_name }}</h3>
                <el-tag v-if="row.category" type="info" size="small" style="margin-left: 10px;">{{ row.category }}</el-tag>
                <el-button size="small" type="primary" @click="handlePanSou(row)" style="margin-left: 10px;">
                  🔍 盘搜
                </el-button>
                <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                  {{ row.enabled ? '启用' : '禁用' }}
                </el-tag>
                <el-switch 
                  v-model="row.is_completed" 
                  size="small"
                  @change="updateMapping(row)"
                  active-text="完结"
                  inactive-text="更新中"
                />
              </div>
              <div class="show-actions">
                <el-button size="small" type="success" @click="copyLinks(row)">复制</el-button>
                <el-button size="small" @click="handleEdit(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
              </div>
            </div>
          </template>

          <!-- 网盘信息区（三列并排，名称链接同行） -->
          <div class="pan-sections">
            <!-- 百度网盘 -->
            <div class="pan-section baidu-section">
              <div class="pan-row">
                <span class="pan-label">百度</span>
                <el-input 
                  v-model="row.baidu_name" 
                  size="small" 
                  placeholder="原名"
                  @blur="updateMapping(row)" 
                  class="name-input-short"
                />
                <el-button size="small" type="primary" @click="generateSingleLink(row, 'baidu')">获取</el-button>
                <el-button size="small" type="primary" plain @click="resyncToTarget(row, 'baidu')">重转</el-button>
                <el-button size="small" @click="openEditLinkDialog(row, 'baidu')">编辑</el-button>
              </div>
              <div class="pan-row">
                <span class="pan-label">链接</span>
                <a
                  v-if="row.baidu_link"
                  :href="row.baidu_link.split(' ')[0]"
                  target="_blank"
                  class="link-text"
                  @click="(e) => { if (!e.metaKey && !e.ctrlKey) { e.preventDefault(); copyLink(row.baidu_link); } }"
                  :title="row.baidu_link"
                >
                  {{ row.baidu_link }}
                </a>
                <span v-else class="no-link">未生成</span>
              </div>
            </div>

            <!-- 夸克网盘 -->
            <div class="pan-section quark-section">
              <div class="pan-row">
                <span class="pan-label">夸克</span>
                <el-input 
                  v-model="row.quark_name" 
                  size="small" 
                  placeholder="原名"
                  @blur="updateMapping(row)" 
                  class="name-input-short"
                />
                <el-button size="small" type="warning" @click="generateSingleLink(row, 'quark')">获取</el-button>
                <el-button size="small" type="warning" plain @click="resyncToTarget(row, 'quark')">重转</el-button>
                <el-button size="small" @click="openEditLinkDialog(row, 'quark')">编辑</el-button>
              </div>
              <div class="pan-row">
                <span class="pan-label">链接</span>
                <a
                  v-if="row.quark_link"
                  :href="row.quark_link.split(' ')[0]"
                  target="_blank"
                  class="link-text"
                  @click="(e) => { if (!e.metaKey && !e.ctrlKey) { e.preventDefault(); copyLink(row.quark_link); } }"
                  :title="row.quark_link"
                >
                  {{ row.quark_link }}
                </a>
                <span v-else class="no-link">未生成</span>
              </div>
            </div>

            <!-- 迅雷网盘 -->
            <div class="pan-section xunlei-section">
              <div class="pan-row">
                <span class="pan-label">迅雷</span>
                <el-input 
                  v-model="row.xunlei_name" 
                  size="small" 
                  placeholder="原名"
                  @blur="updateMapping(row)" 
                  class="name-input-short"
                />
                <el-button size="small" type="info" @click="generateSingleLink(row, 'xunlei')">获取</el-button>
                <el-button size="small" type="info" plain @click="resyncToTarget(row, 'xunlei')">重转</el-button>
                <el-button size="small" @click="openEditLinkDialog(row, 'xunlei')">编辑</el-button>
              </div>
              <div class="pan-row">
                <span class="pan-label">链接</span>
                <a
                  v-if="row.xunlei_link"
                  :href="row.xunlei_link.split(' ')[0]"
                  target="_blank"
                  class="link-text"
                  @click="(e) => { if (!e.metaKey && !e.ctrlKey) { e.preventDefault(); copyLink(row.xunlei_link); } }"
                  :title="row.xunlei_link"
                >
                  {{ row.xunlei_link }}
                </a>
                <span v-else class="no-link">未生成</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

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
          <el-input 
            v-model="formData.original_name" 
            placeholder="请输入原名称（输入后自动混淆）" 
            @blur="handleOriginalNameBlur"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="formData.category" placeholder="请选择分类" clearable filterable style="width: 100%">
            <el-option-group label="动漫">
              <el-option v-for="cat in categories.filter(c => c.startsWith('动漫/'))"
                :key="cat" :label="cat" :value="cat" />
            </el-option-group>
            <el-option-group label="电影">
              <el-option v-for="cat in categories.filter(c => c.startsWith('电影/'))"
                :key="cat" :label="cat" :value="cat" />
            </el-option-group>
            <el-option-group label="剧集">
              <el-option v-for="cat in categories.filter(c => c.startsWith('剧集/'))"
                :key="cat" :label="cat" :value="cat" />
            </el-option-group>
            <el-option-group label="其他">
              <el-option v-for="cat in categories.filter(c => c.startsWith('其他/'))"
                :key="cat" :label="cat" :value="cat" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="显示名">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <el-button type="primary" size="small" @click="handleAutoObfuscate">自动混淆</el-button>
            <span style="font-size: 12px; color: #909399;">点击后自动填充混淆后的名称到下方三个网盘</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <el-input v-model="formData.quark_name" placeholder="夸克显示名（可选）">
              <template #prepend>夸克</template>
            </el-input>
            <el-input v-model="formData.baidu_name" placeholder="百度显示名（可选）">
              <template #prepend>百度</template>
            </el-input>
            <el-input v-model="formData.xunlei_name" placeholder="迅雷显示名（可选）">
              <template #prepend>迅雷</template>
            </el-input>
          </div>
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

    <!-- Cookie导入对话框 -->
    <el-dialog v-model="cookieDialogVisible" :title="cookieDialogTitle" width="600px">
      <el-alert type="info" :closable="false" style="margin-bottom: 15px">
        <p><strong>如何获取Cookie：</strong></p>
        <p>1. 使用Chrome/Edge浏览器登录{{ cookiePanType === 'baidu' ? '百度' : '夸克' }}网盘</p>
        <p>2. 按F12打开开发者工具</p>
        <p>3. 切换到"Network"（网络）标签</p>
        <p>4. 刷新页面，点击任意请求</p>
        <p>5. 在请求头中找到Cookie，复制完整的Cookie值并粘贴到下方</p>
      </el-alert>
      
      <el-input
        v-model="cookieText"
        type="textarea"
        :rows="10"
        :placeholder="`直接粘贴浏览器Cookie字符串即可，格式如：${cookiePanType === 'baidu' ? 'BAIDUID=xxx; BDUSS=xxx' : 'b-user-id=xxx; __uid=xxx'}; ...`"
      />
      
      <template #footer>
        <el-button @click="cookieDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="uploadCookie">上传</el-button>
      </template>
    </el-dialog>

    <!-- 盘搜结果弹窗 -->
    <el-dialog 
      v-model="pansouDialogVisible" 
      :title="pansouKeyword ? `搜索结果：${pansouKeyword}` : '盘搜'" 
      width="900px"
      :close-on-click-modal="false"
    >
      <div v-loading="pansouLoading">
        <!-- 搜索输入框 -->
        <div style="margin-bottom: 20px;">
          <el-input
            v-model="pansouKeyword"
            placeholder="请输入搜索关键词..."
            style="width: 70%;"
            @keyup.enter="executePanSou(pansouKeyword)"
          >
            <template #prepend>🔍 关键词</template>
          </el-input>
          <el-button type="primary" @click="executePanSou(pansouKeyword)" style="margin-left: 10px;">搜索</el-button>
        </div>

        <!-- 统计信息 -->
        <div class="pansou-stats">
          <span class="stat-item">
            <span class="stat-label">📊 搜索结果</span>
            <span class="stat-value">{{ pansouResults.total }}</span>
          </span>
          <span class="stat-item">
            <span class="stat-label">📁 网盘类型</span>
            <span class="stat-value">{{ (pansouResults.baidu.length > 0 ? 1 : 0) + (pansouResults.quark.length > 0 ? 1 : 0) + (pansouResults.xunlei.length > 0 ? 1 : 0) }}</span>
          </span>
        </div>

        <!-- Tab切换 -->
        <el-tabs v-model="activeTab" class="pansou-tabs">
          <!-- 百度网盘 -->
          <el-tab-pane :label="`百度 (${pansouResults.baidu.length})`" name="baidu">
            <el-scrollbar max-height="500px">
              <div v-if="pansouResults.baidu.length > 0">
                <div v-for="(item, idx) in pansouResults.baidu" :key="'baidu-' + idx" class="result-item">
                  <div class="result-content">
                    <div class="result-title">{{ item.note || '无标题' }}</div>
                    <a :href="item.url" target="_blank" class="result-link">{{ item.url }}</a>
                  </div>
                  <div class="result-actions">
                    <span v-if="item.password" class="result-pwd">提取码: {{ item.password }}</span>
                    <el-button size="small" type="primary" @click="openPanLink(item.url)">
                      打开链接
                    </el-button>
                    <el-button size="small" type="success" @click="confirmTransferFromPansou(item.url, item.password, 'baidu')">
                      转存
                    </el-button>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无百度网盘资源" />
            </el-scrollbar>
          </el-tab-pane>

          <!-- 夸克网盘 -->
          <el-tab-pane :label="`夸克 (${pansouResults.quark.length})`" name="quark">
            <el-scrollbar max-height="500px">
              <div v-if="pansouResults.quark.length > 0">
                <div v-for="(item, idx) in pansouResults.quark" :key="'quark-' + idx" class="result-item">
                  <div class="result-content">
                    <div class="result-title">{{ item.note || '无标题' }}</div>
                    <a :href="item.url" target="_blank" class="result-link">{{ item.url }}</a>
                  </div>
                  <div class="result-actions">
                    <span v-if="item.password" class="result-pwd">提取码: {{ item.password }}</span>
                    <el-button size="small" type="success" @click="openPanLink(item.url)">
                      打开链接
                    </el-button>
                    <el-button size="small" type="warning" @click="confirmTransferFromPansou(item.url, item.password, 'quark')">
                      转存
                    </el-button>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无夸克网盘资源" />
            </el-scrollbar>
          </el-tab-pane>

          <!-- 迅雷网盘 -->
          <el-tab-pane :label="`迅雷 (${pansouResults.xunlei.length})`" name="xunlei">
            <el-scrollbar max-height="500px">
              <div v-if="pansouResults.xunlei.length > 0">
                <div v-for="(item, idx) in pansouResults.xunlei" :key="'xunlei-' + idx" class="result-item">
                  <div class="result-content">
                    <div class="result-title">{{ item.note || '无标题' }}</div>
                    <a :href="item.url" target="_blank" class="result-link">{{ item.url }}</a>
                  </div>
                  <div class="result-actions">
                    <span v-if="item.password" class="result-pwd">提取码: {{ item.password }}</span>
                    <el-button size="small" type="warning" @click="openPanLink(item.url)">
                      打开链接
                    </el-button>
                    <el-button size="small" type="info" @click="confirmTransferFromPansou(item.url, item.password, 'xunlei')">
                      转存
                    </el-button>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无迅雷网盘资源" />
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>

    <!-- 编辑链接对话框 -->
    <el-dialog 
      v-model="editLinkDialogVisible" 
      :title="`编辑${editLinkData.panName}链接`" 
      width="600px"
    >
      <el-form label-width="80px">
        <el-form-item label="剧集名称">
          <el-input :value="editLinkData.row?.original_name" disabled />
        </el-form-item>
        <el-form-item label="分享链接">
          <el-input 
            v-model="editLinkData.link" 
            type="textarea" 
            :rows="3"
            placeholder="请输入分享链接"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="editLinkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEditedLink">保存</el-button>
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

/* 卡片列表布局 */
.mapping-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mapping-card {
  transition: all 0.2s;
}

.mapping-card:hover {
  transform: translateY(-1px);
}

/* 卡片头部 */
.card-header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}

.show-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.show-info h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.show-actions {
  display: flex;
  gap: 4px;
}

/* 网盘区块容器 - 三列并排 */
.pan-sections {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

/* 网盘区块 */
.pan-section {
  padding: 6px;
  background-color: #f5f7fa;
  border-radius: 4px;
  border-left: 3px solid;
}

.baidu-section {
  border-left-color: #409eff;
}

.quark-section {
  border-left-color: #e6a23c;
}

.xunlei-section {
  border-left-color: #909399;
}

/* 网盘行（名称和链接同行显示） */
.pan-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.pan-row:last-child {
  margin-bottom: 0;
}

.pan-label {
  min-width: 50px;
  font-size: 12px;
  color: #606266;
  font-weight: 500;
  flex-shrink: 0;
}

.name-input {
  flex: 1;
}

.name-input-short {
  width: 200px;
  flex-shrink: 0;
}

.link-text {
  flex: 1;
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.link-text:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.no-link {
  flex: 1;
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .card-header-content {
    flex-wrap: wrap;
  }
  
  .show-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .pan-sections {
    grid-template-columns: 1fr;
  }
  
  .pan-row {
    flex-wrap: wrap;
  }
  
  .pan-label {
    min-width: 100%;
  }
}

/* 盘搜结果样式 */
.pansou-stats {
  display: flex;
  gap: 30px;
  padding: 15px;
  background-color: #f7f8fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-label {
  color: #606266;
  font-size: 14px;
}

.stat-value {
  color: #303133;
  font-size: 18px;
  font-weight: bold;
}

.pansou-tabs {
  margin-top: 10px;
}

.result-item {
  padding: 16px;
  margin-bottom: 12px;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s;
}

.result-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}

.result-content {
  margin-bottom: 10px;
}

.result-title {
  color: #303133;
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 6px;
  line-height: 1.5;
}

.result-link {
  color: #409eff;
  font-size: 13px;
  text-decoration: none;
  word-break: break-all;
  display: block;
}

.result-link:hover {
  text-decoration: underline;
}

.result-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
}

.result-pwd {
  color: #f56c6c;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  background-color: #fef0f0;
  border-radius: 4px;
  border: 1px solid #fde2e2;
}
</style>
