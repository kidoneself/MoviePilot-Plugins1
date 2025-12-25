<template>
  <div class="auto-workflow-page">
    <!-- 媒体信息提示 -->
    <el-alert 
      v-if="mediaData" 
      :title="`正在为《${mediaData.original_name}》创建商品`"
      type="info" 
      :closable="false"
      style="margin-bottom: 10px;"
    >
      <template #default>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>已自动加载媒体信息和海报</span>
          <el-button size="small" @click="$router.push('/media')">返回媒体库</el-button>
        </div>
      </template>
    </el-alert>
    
    <div class="main-container">
      <!-- 左侧：配置和控制 -->
      <div class="left-panel">
        <!-- 图片上传 -->
        <el-card class="panel-card">
          <template #header>
            <span>🖼️ 海报图片</span>
          </template>
          <div class="upload-section">
            <input 
              type="file" 
              ref="fileInput" 
              accept="image/*" 
              @change="handleFileUpload" 
              style="display: none;"
            />
            <el-button type="primary" @click="$refs.fileInput.click()" style="width: 100%;">
              {{ uploadedImage ? '更换海报' : '上传海报图片' }}
            </el-button>
            <div class="info-text">支持拖拽、粘贴（Ctrl+V）或点击上传</div>
          </div>
        </el-card>

        <!-- Canvas参数 -->
        <el-card class="panel-card">
          <template #header>
            <span>🎨 海报编辑</span>
          </template>
          <el-form label-width="90px" size="small">
            <el-form-item label="中心标题">
              <el-input v-model="canvas.centerTitle" placeholder="如：4K超清" @input="drawCanvas" />
            </el-form-item>
            
            <el-form-item label="集数">
              <el-input v-model="canvas.episodeCount" placeholder="如：24" @input="drawCanvas" />
            </el-form-item>
            
            <!-- 高级选项（默认收起） -->
            <el-collapse style="margin-top: 10px;">
              <el-collapse-item title="🔧 高级选项（水印和底部文字）" name="1">
                <el-form-item label="左侧文字">
                  <el-input v-model="canvas.leftText" type="textarea" :rows="2" placeholder="竖排显示" @input="drawCanvas" />
                </el-form-item>
                
                <el-form-item label="底部左上">
                  <el-input v-model="canvas.bottomLeft1" @input="drawCanvas" />
                </el-form-item>
                
                <el-form-item label="底部左下">
                  <el-input v-model="canvas.bottomLeft2" @input="drawCanvas" />
                </el-form-item>
                
                <el-form-item label="底部右上">
                  <el-input v-model="canvas.bottomRight1" @input="drawCanvas" />
                </el-form-item>
                
                <el-form-item label="底部右下">
                  <el-input v-model="canvas.bottomRight2" @input="drawCanvas" />
                </el-form-item>
              </el-collapse-item>
            </el-collapse>
          </el-form>
        </el-card>

        <!-- 商品信息 -->
        <el-card class="panel-card">
          <template #header>
            <span>📝 商品信息</span>
          </template>
          <el-form label-width="90px" size="small">
            <el-form-item label="模板类型">
              <el-radio-group v-model="templateType" @change="updateTemplate">
                <el-radio label="updating">更新中</el-radio>
                <el-radio label="completed">完结</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="商品标题">
              <el-input v-model="form.title" />
              <div style="font-size: 12px; color: #888; margin-top: 4px;">根据模板自动生成</div>
            </el-form-item>
            
            <el-form-item label="商品描述">
              <el-input v-model="form.content" type="textarea" :rows="8" />
              <div style="font-size: 12px; color: #888; margin-top: 4px;">根据模板自动生成，可修改</div>
            </el-form-item>
            
            <el-form-item label="价格(元)">
              <el-input-number v-model="form.price" :min="0.01" :step="0.1" :precision="2" style="width: 100%;" />
            </el-form-item>
            
            <el-form-item label="库存">
              <el-input-number v-model="form.stock" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 卡密信息 -->
        <el-card class="panel-card">
          <template #header>
            <span>🎫 卡密信息</span>
          </template>
          <el-form label-width="90px" size="small">
            <el-form-item label="卡种名称">
              <el-input v-model="form.kindName" placeholder="如：网盘会员卡" />
            </el-form-item>
            
            <el-form-item label="卡密数据">
              <el-input 
                v-model="form.kamiData" 
                type="textarea" 
                :rows="4" 
                placeholder="账号----密码----到期时间&#10;每行一组"
              />
            </el-form-item>
            
            <el-form-item label="重复次数">
              <el-input-number v-model="form.repeatCount" :min="1" :max="1000" style="width: 100%;" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 执行按钮 -->
        <el-card class="panel-card">
          <el-button 
            type="primary" 
            size="large" 
            style="width: 100%;" 
            @click="startWorkflow"
            :loading="running"
            :disabled="!canStart"
          >
            <span v-if="!running">🚀 开始自动化流程</span>
            <span v-else>⏳ 执行中...</span>
          </el-button>
          
          <el-button 
            style="width: 100%; margin-top: 10px;" 
            @click="resetAll"
            :disabled="running"
          >
            🔄 重置全部
          </el-button>
        </el-card>
      </div>

      <!-- 中间：Canvas预览 -->
      <div class="center-panel">
        <el-card>
          <template #header>
            <span>🖼️ 海报预览</span>
          </template>
          <div class="canvas-wrapper">
            <canvas ref="canvasRef" width="600" height="900"></canvas>
          </div>
        </el-card>
      </div>

      <!-- 右侧：执行日志 -->
      <div class="right-panel">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>📊 执行日志</span>
              <el-button size="small" @click="clearLogs" :disabled="running">清空</el-button>
            </div>
          </template>

          <div class="log-container" ref="logContainer">
            <el-timeline v-if="logs.length > 0">
              <el-timeline-item 
                v-for="(log, index) in logs" 
                :key="index"
                :type="log.type"
                :timestamp="log.time"
                :icon="log.icon"
              >
                <div :class="'log-' + log.type">
                  <strong>{{ log.step }}</strong>
                  <p v-if="log.message" style="margin: 5px 0 0 0;">{{ log.message }}</p>
                  <div v-if="log.qrcode" style="margin-top: 10px;">
                    <el-image 
                      :src="log.qrcode" 
                      style="width: 200px; height: 200px; border: 1px solid #ddd;"
                      fit="contain"
                    />
                    <p style="color: #E6A23C; margin-top: 5px;">⚠️ 请使用闲鱼App扫码登录</p>
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="等待开始执行..." />
          </div>
        </el-card>

        <!-- 执行结果 -->
        <el-card v-if="result" style="margin-top: 15px;">
          <template #header>
            <span>{{ result.success ? '✅ 执行成功' : '❌ 执行失败' }}</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="商品ID" v-if="result.productId">
              {{ result.productId }}
            </el-descriptions-item>
            <el-descriptions-item label="卡种名称" v-if="result.kindName">
              {{ result.kindName }}
            </el-descriptions-item>
            <el-descriptions-item label="总耗时">
              {{ result.duration }}秒
            </el-descriptions-item>
          </el-descriptions>
          
          <el-space style="margin-top: 15px; width: 100%;">
            <el-button type="primary" size="small" @click="$router.push('/xianyu/products')">
              查看商品
            </el-button>
            <el-button size="small" @click="resetResult" :disabled="running">
              再次执行
            </el-button>
          </el-space>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const route = useRoute()

// Canvas相关
const canvasRef = ref(null)
const logContainer = ref(null)
let ctx = null
let uploadedImage = null
const hasUploadedImage = ref(false)  // 响应式的图片标志
const logos = { baidu: null, quark: null, xunlei: null }
let logosLoaded = 0

// 媒体信息
const mediaId = ref(null)
const mediaData = ref(null)

// Canvas参数
const canvas = ref({
  centerTitle: '4K超清',
  episodeCount: '',
  leftText: '闲鱼店铺 无名之辈 同行请勿盗图',
  bottomLeft1: '包更新至',
  bottomLeft2: '完结全集',
  bottomRight1: '百度夸克迅雷',
  bottomRight2: '24H自动发货'
})

// 模板相关
const templateType = ref('updating') // 默认为"更新中"
const templatesPool = ref({
  completed: [],
  updating: []
})

// 表单数据
const form = ref({
  title: '网盘会员账号',
  content: '百度网盘+夸克网盘+迅雷网盘会员账号，超大容量，高速下载！',
  price: 0.1,
  stock: 100,
  kindName: '网盘会员卡',
  kamiData: '',
  repeatCount: 100
})

// 执行状态
const running = ref(false)
const logs = ref([])
const result = ref(null)
const startTime = ref(null)
let pollingTimer = null

// 是否可以开始
const canStart = computed(() => {
  const hasImage = hasUploadedImage.value
  const hasTitle = !!form.value.title
  const hasContent = !!form.value.content
  const hasKindName = !!form.value.kindName
  const hasKamiData = form.value.kamiData.trim().length > 0
  
  console.log('按钮启用检查:', {
    hasImage,
    hasTitle,
    hasContent,
    hasKindName,
    hasKamiData
  })
  
  return hasImage && hasTitle && hasContent && hasKindName && hasKamiData
})

// 加载Logo
const loadLogos = () => {
  const logoUrls = {
    baidu: '/svg/百度网盘.svg',
    quark: '/svg/夸克网盘.svg',
    xunlei: '/svg/迅雷.svg'
  }

  Object.keys(logoUrls).forEach(key => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      logos[key] = img
      logosLoaded++
      if (logosLoaded === 3) {
        drawCanvas()
      }
    }
    img.onerror = () => {
      logosLoaded++
      console.warn(`Logo加载失败: ${key}`)
    }
    img.src = logoUrls[key]
  })
}

// 文件上传
const fileInput = ref(null)
const handleFileUpload = (e) => {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    const img = new Image()
    img.onload = () => {
      uploadedImage = img
      hasUploadedImage.value = true
      drawCanvas()
    }
    img.src = event.target.result
  }
  reader.readAsDataURL(file)
}

// 绘制Canvas（参考Java版本）
const drawCanvas = () => {
  if (!ctx) return

  const cvs = canvasRef.value
  ctx.clearRect(0, 0, cvs.width, cvs.height)

  // 背景图
  if (uploadedImage) {
    const scale = Math.max(cvs.width / uploadedImage.width, cvs.height / uploadedImage.height)
    const x = (cvs.width - uploadedImage.width * scale) / 2
    const y = (cvs.height - uploadedImage.height * scale) / 2
    ctx.drawImage(uploadedImage, x, y, uploadedImage.width * scale, uploadedImage.height * scale)
  } else {
    ctx.fillStyle = '#f0f0f0'
    ctx.fillRect(0, 0, cvs.width, cvs.height)
    ctx.fillStyle = '#999'
    ctx.font = '24px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('请上传海报图片', cvs.width / 2, cvs.height / 2)
    return
  }

  // 中心标题徽章
  if (canvas.value.centerTitle.trim()) {
    ctx.save()
    
    // 🔥 根据字数自动计算字体大小（等比例）
    // 6个字或更少 = 100（最大），字越多字体越小
    const charCount = canvas.value.centerTitle.length
    const autoFontSize = Math.min(100, Math.max(30, 600 / charCount))
    
    ctx.font = `bold ${autoFontSize}px Arial`
    const textWidth = ctx.measureText(canvas.value.centerTitle).width
    const textHeight = autoFontSize
    
    const paddingX = 30, paddingY = 20
    const badgeX = cvs.width / 2 - textWidth / 2 - paddingX
    const badgeY = cvs.height / 2 - 50 - textHeight - paddingY / 2
    const badgeWidth = textWidth + paddingX * 2
    const badgeHeight = textHeight + paddingY
    const radius = 15
    
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)'
    ctx.shadowBlur = 15
    ctx.shadowOffsetY = 8
    
    const gradient = ctx.createLinearGradient(badgeX, badgeY, badgeX, badgeY + badgeHeight)
    gradient.addColorStop(0, '#ff69b4')
    gradient.addColorStop(1, '#ff1493')
    ctx.fillStyle = gradient
    
    ctx.beginPath()
    ctx.moveTo(badgeX + radius, badgeY)
    ctx.lineTo(badgeX + badgeWidth - radius, badgeY)
    ctx.quadraticCurveTo(badgeX + badgeWidth, badgeY, badgeX + badgeWidth, badgeY + radius)
    ctx.lineTo(badgeX + badgeWidth, badgeY + badgeHeight - radius)
    ctx.quadraticCurveTo(badgeX + badgeWidth, badgeY + badgeHeight, badgeX + badgeWidth - radius, badgeY + badgeHeight)
    ctx.lineTo(badgeX + radius, badgeY + badgeHeight)
    ctx.quadraticCurveTo(badgeX, badgeY + badgeHeight, badgeX, badgeY + badgeHeight - radius)
    ctx.lineTo(badgeX, badgeY + radius)
    ctx.quadraticCurveTo(badgeX, badgeY, badgeX + radius, badgeY)
    ctx.closePath()
    ctx.fill()
    
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'white'
    ctx.lineWidth = 4
    ctx.stroke()
    
    ctx.fillStyle = 'white'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(canvas.value.centerTitle, cvs.width / 2, badgeY + badgeHeight / 2)
    ctx.restore()
  }

  // 集数
  if (canvas.value.episodeCount.trim()) {
    ctx.save()
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 20
    ctx.font = 'bold 80px Arial'
    ctx.fillStyle = 'white'
    ctx.textAlign = 'center'
    ctx.fillText(`全${canvas.value.episodeCount}集`, cvs.width / 2, cvs.height - 280)
    ctx.restore()
  }

  // 底部三色条
  const bottomBarHeight = cvs.height * 0.2
  const bottomY = cvs.height - bottomBarHeight
  const thirdWidth = cvs.width / 3

  ctx.fillStyle = '#1e3a8a'
  ctx.fillRect(0, bottomY, thirdWidth, bottomBarHeight)
  
  ctx.fillStyle = '#fbbf24'
  ctx.fillRect(thirdWidth, bottomY, thirdWidth, bottomBarHeight)
  
  ctx.fillStyle = '#1e3a8a'
  ctx.fillRect(thirdWidth * 2, bottomY, thirdWidth, bottomBarHeight)

  // 底部文字
  ctx.fillStyle = 'white'
  const fontSize = Math.floor(cvs.height * 0.037)
  ctx.font = `bold ${fontSize}px Arial`
  ctx.textAlign = 'center'
  
  ctx.fillText(canvas.value.bottomLeft1, thirdWidth / 2, bottomY + bottomBarHeight * 0.37)
  ctx.fillText(canvas.value.bottomLeft2, thirdWidth / 2, bottomY + bottomBarHeight * 0.63)
  ctx.fillText(canvas.value.bottomRight1, thirdWidth * 2 + thirdWidth / 2, bottomY + bottomBarHeight * 0.37)
  ctx.fillText(canvas.value.bottomRight2, thirdWidth * 2 + thirdWidth / 2, bottomY + bottomBarHeight * 0.63)

  // 中间4K
  ctx.fillStyle = 'white'
  const centerFontSize = Math.floor(cvs.height * 0.08)
  ctx.font = `bold ${centerFontSize}px Arial`
  ctx.fillText('4K', thirdWidth + thirdWidth / 2, bottomY + bottomBarHeight * 0.43)
  
  ctx.fillStyle = 'black'
  const ultraFontSize = Math.floor(cvs.height * 0.037)
  ctx.font = `bold ${ultraFontSize}px Arial`
  ctx.fillText('ULTRA HD', thirdWidth + thirdWidth / 2, bottomY + bottomBarHeight * 0.7)

  // 左侧竖排文字
  if (canvas.value.leftText.trim()) {
    ctx.save()
    ctx.fillStyle = 'white'
    ctx.font = 'bold 22px Arial'
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 10
    
    const chars = canvas.value.leftText.split('')
    let y = 100
    chars.forEach(char => {
      if (char !== ' ' && char !== '\n') {
        ctx.fillText(char, 30, y)
        y += 30
      } else {
        y += 15
      }
    })
    ctx.restore()
  }

  // 顶部Logo徽章
  if (logosLoaded === 3) {
    const logoSize = 80  // 从60放大到80
    const spacing = 20   // 间距也相应增加
    const totalWidth = logoSize * 3 + spacing * 2
    const startX = (cvs.width - totalWidth) / 2
    const logoY = 60     // 从25往下移到60
    
    const badgePaddingX = 30, badgePaddingY = 20  // padding也增加
    const badgeX = startX - badgePaddingX
    const badgeY = logoY - badgePaddingY
    const badgeWidth = totalWidth + badgePaddingX * 2
    const badgeHeight = logoSize + badgePaddingY * 2
    const badgeRadius = 12
    
    ctx.save()
    
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)'
    ctx.shadowBlur = 12
    ctx.shadowOffsetY = 6
    
    const gradient = ctx.createLinearGradient(badgeX, badgeY, badgeX, badgeY + badgeHeight)
    gradient.addColorStop(0, '#ffd700')
    gradient.addColorStop(1, '#ffa500')
    ctx.fillStyle = gradient
    
    ctx.beginPath()
    ctx.moveTo(badgeX + badgeRadius, badgeY)
    ctx.lineTo(badgeX + badgeWidth - badgeRadius, badgeY)
    ctx.quadraticCurveTo(badgeX + badgeWidth, badgeY, badgeX + badgeWidth, badgeY + badgeRadius)
    ctx.lineTo(badgeX + badgeWidth, badgeY + badgeHeight - badgeRadius)
    ctx.quadraticCurveTo(badgeX + badgeWidth, badgeY + badgeHeight, badgeX + badgeWidth - badgeRadius, badgeY + badgeHeight)
    ctx.lineTo(badgeX + badgeRadius, badgeY + badgeHeight)
    ctx.quadraticCurveTo(badgeX, badgeY + badgeHeight, badgeX, badgeY + badgeHeight - badgeRadius)
    ctx.lineTo(badgeX, badgeY + badgeRadius)
    ctx.quadraticCurveTo(badgeX, badgeY, badgeX + badgeRadius, badgeY)
    ctx.closePath()
    ctx.fill()
    
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'white'
    ctx.lineWidth = 3
    ctx.stroke()
    
    // 绘制Logo
    const logoOrder = ['baidu', 'quark', 'xunlei']
    logoOrder.forEach((name, i) => {
      if (logos[name]) {
        const logoX = startX + i * (logoSize + spacing)
        const logoCenterX = logoX + logoSize / 2
        const logoCenterY = logoY + logoSize / 2
        
        ctx.shadowColor = 'rgba(0, 0, 0, 0.2)'
        ctx.shadowBlur = 5
        ctx.fillStyle = 'white'
        ctx.beginPath()
        ctx.arc(logoCenterX, logoCenterY, logoSize / 2 + 5, 0, Math.PI * 2)
        ctx.fill()
        
        ctx.shadowColor = 'transparent'
        ctx.drawImage(logos[name], logoX, logoY, logoSize, logoSize)
      }
    })
    
    ctx.restore()
  }
}

// 加载模板数据
const loadTemplates = async () => {
  try {
    // 加载完结模板
    const completedRes = await api.get('/config/templates/completed')
    if (completedRes.data.success && completedRes.data.data) {
      templatesPool.value.completed = completedRes.data.data
    }
    
    // 加载更新中模板
    const updatingRes = await api.get('/config/templates/updating')
    if (updatingRes.data.success && updatingRes.data.data) {
      templatesPool.value.updating = updatingRes.data.data
    }
    
    console.log('✅ 模板加载成功', templatesPool.value)
  } catch (error) {
    console.error('❌ 模板加载失败', error)
    // 使用后备模板
    templatesPool.value.completed = [{
      title: '《{name}》已完结｜秒发',
      content: '已完结全集\n✅4K超清\n✅24小时自动发货'
    }]
    templatesPool.value.updating = [{
      title: '《{name}》更新中｜实时更新',
      content: '持续更新中\n✅4K超清\n✅24小时自动发货'
    }]
  }
}

// 随机选择模板并生成标题和内容
const updateTemplate = () => {
  const centerTitle = canvas.value.centerTitle.trim()
  if (!centerTitle) return
  
  const pool = templatesPool.value[templateType.value]
  if (!pool || pool.length === 0) return
  
  // 随机选择一个模板
  const template = pool[Math.floor(Math.random() * pool.length)]
  
  // 替换{name}为实际名称
  form.value.title = template.title.replace(/{name}/g, centerTitle)
  
  // 模板内容 + TMDb简介
  let content = template.content
  if (mediaData.value && mediaData.value.overview) {
    content += '\n\n【剧情简介】\n' + mediaData.value.overview
  }
  form.value.content = content
  
  console.log('📝 模板已更新:', { type: templateType.value, title: form.value.title, hasOverview: !!mediaData.value?.overview })
}

// 添加日志
const addLog = (step, message, type = 'primary', icon = null) => {
  logs.value.push({
    step,
    message,
    type,
    icon: icon || (type === 'success' ? 'Check' : type === 'danger' ? 'Close' : 'Clock'),
    time: new Date().toLocaleTimeString(),
    qrcode: null
  })
  // 自动滚动到底部
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

// 添加二维码日志
const addQrcodeLog = (step, qrcodeBase64) => {
  // 如果已经包含了 data:image 前缀，就直接使用；否则添加前缀
  const qrcodeData = qrcodeBase64.startsWith('data:') 
    ? qrcodeBase64 
    : `data:image/png;base64,${qrcodeBase64}`
  
  logs.value.push({
    step,
    message: '需要扫码登录',
    type: 'warning',
    icon: 'Warning',
    time: new Date().toLocaleTimeString(),
    qrcode: qrcodeData
  })
  
  console.log('✅ 二维码已添加到日志，长度:', qrcodeData.length)
  
  // 自动滚动到底部
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

// 清空日志
const clearLogs = () => {
  logs.value = []
}

// 重置结果
const resetResult = () => {
  result.value = null
  clearLogs()
}

// 重置全部
const resetAll = () => {
  // 重置Canvas
  uploadedImage = null
  hasUploadedImage.value = false
  canvas.value = {
    centerTitle: '4K超清',
    episodeCount: '',
    leftText: '闲鱼店铺 无名之辈 同行请勿盗图',
    bottomLeft1: '包更新至',
    bottomLeft2: '完结全集',
    bottomRight1: '百度夸克迅雷',
    bottomRight2: '24H自动发货'
  }
  drawCanvas()
  
  // 重置表单
  form.value = {
    title: '网盘会员账号',
    content: '百度网盘+夸克网盘+迅雷网盘会员账号，超大容量，高速下载！',
    price: 0.1,
    stock: 100,
    kindName: '网盘会员卡',
    kamiData: '',
    repeatCount: 1
  }
  
  // 清空日志和结果
  clearLogs()
  result.value = null
}

// 轮询任务状态
const pollTaskStatus = (taskId, onSuccess, onError) => {
  pollingTimer = setInterval(async () => {
    try {
      const res = await api.get(`/xianyu/kami/task/${taskId}`)
      if (res.data.success) {
        const task = res.data.data
        console.log('📊 任务轮询:', {
          task_id: taskId,
          status: task.status,
          steps: task.steps?.length || 0,
          has_qrcode: !!task.qrcode_base64,
          qrcode_prefix: task.qrcode_base64?.substring(0, 30)
        })
        
        if (task.steps && task.steps.length > 0) {
          task.steps.forEach(step => {
            // 统一的状态映射函数
            const mapStatus = (status) => {
              if (status === 'success') return 'success'
              if (status === 'error') return 'danger'
              if (status === 'loading') return 'primary'
              return 'info'
            }
            
            // 使用步骤内容+映射后的状态作为唯一标识
            const mappedType = mapStatus(step.status)
            const existing = logs.value.find(log => 
              log.step === step.step && log.type === mappedType
            )
            
            if (!existing) {
              addLog(step.step, '', mappedType)
            }
          })
        }
        
        if (task.qrcode_base64 && !logs.value.some(log => log.qrcode)) {
          console.log('🔍 检测到二维码，准备添加到日志')
          addQrcodeLog('等待扫码登录', task.qrcode_base64)
        }
        
        if (task.status === 'completed') {
          clearInterval(pollingTimer)
          onSuccess(task.result)
        } else if (task.status === 'failed') {
          clearInterval(pollingTimer)
          onError(task.error || '任务执行失败')
        }
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error)
    }
  }, 2000)
}

// 开始工作流
const startWorkflow = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要开始自动化流程吗？此过程可能需要几分钟时间。',
      '确认执行',
      {
        confirmButtonText: '开始',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  running.value = true
  clearLogs()
  startTime.value = Date.now()
  
  try {
    // ========== 步骤1：生成并上传图片 ==========
    addLog('步骤 1/5', '正在生成海报图片...', 'primary')
    
    const cvs = canvasRef.value
    const imageBlob = await new Promise(resolve => {
      cvs.toBlob(resolve, 'image/png', 0.95)
    })
    
    const formData = new FormData()
    formData.append('files', imageBlob, 'poster.png')
    
    const uploadRes = await api.post('/xianyu/product/upload-images-only', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (!uploadRes.data.success) {
      throw new Error(uploadRes.data.message || '图片上传失败')
    }
    
    const imageUrls = uploadRes.data.image_urls
    addLog('步骤 1/5', '海报图片生成并上传成功', 'success')
    
    // ========== 步骤2：创建并上架商品 ==========
    addLog('步骤 2/5', '正在创建闲鱼商品...', 'primary')
    
    let productId = null
    
    // 如果有媒体ID，使用create-from-media接口
    if (mediaId.value) {
      const createRes = await api.post('/xianyu/product/create-from-media', {
        media_id: mediaId.value,
        title: form.value.title,
        content: form.value.content,
        price: form.value.price,
        express_fee: 0,
        stock: form.value.stock,
        image_urls: imageUrls
      })
      
      if (!createRes.data.success) {
        throw new Error(createRes.data.message || '创建商品失败')
      }
      
      productId = createRes.data.product_id
    } else {
      // 否则使用upload-images接口
      const createFormData = new FormData()
      createFormData.append('files', imageBlob, 'poster.png')
      createFormData.append('title', form.value.title)
      createFormData.append('content', form.value.content)
      
      const createRes = await api.post('/xianyu/product/upload-images', createFormData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      if (!createRes.data.success) {
        throw new Error(createRes.data.message || '创建商品失败')
      }
      
      productId = createRes.data.product_id
    }
    
    addLog('步骤 2/5', `商品创建并上架成功，ID: ${productId}`, 'success')
    
    // ========== 步骤3：创建卡种 ==========
    addLog('步骤 3/5', '正在创建卡种...', 'primary')
    
    const createKindRes = await api.post('/xianyu/kami/create-kind', {
      kind_name: form.value.kindName,
      category_id: null
    })
    
    if (!createKindRes.data.success) {
      throw new Error('创建卡种失败')
    }
    
    let taskId = createKindRes.data.task_id
    addLog('步骤 3/5', `任务已创建，ID: ${taskId}`, 'info')
    
    await new Promise((resolve, reject) => {
      pollTaskStatus(
        taskId,
        () => {
          addLog('步骤 3/5', '卡种创建成功', 'success')
          resolve()
        },
        (error) => {
          reject(new Error(`创建卡种失败: ${error}`))
        }
      )
    })
    
    // ========== 步骤4：添加卡密 ==========
    addLog('步骤 4/5', '正在添加卡密...', 'primary')
    
    const addCardsRes = await api.post('/xianyu/kami/add-cards', {
      kind_name: form.value.kindName,
      kami_data: form.value.kamiData,
      repeat_count: form.value.repeatCount
    })
    
    if (!addCardsRes.data.success) {
      throw new Error('添加卡密失败')
    }
    
    taskId = addCardsRes.data.task_id
    addLog('步骤 4/5', `任务已创建，ID: ${taskId}`, 'info')
    
    await new Promise((resolve, reject) => {
      pollTaskStatus(
        taskId,
        () => {
          addLog('步骤 4/5', '卡密添加成功', 'success')
          resolve()
        },
        (error) => {
          reject(new Error(`添加卡密失败: ${error}`))
        }
      )
    })
    
    // ========== 步骤5：设置自动发货 ==========
    addLog('步骤 5/5', '正在设置自动发货...', 'primary')
    
    const setupShippingRes = await api.post('/xianyu/kami/setup-shipping', {
      kind_name: form.value.kindName,
      product_title: form.value.title
    })
    
    if (!setupShippingRes.data.success) {
      throw new Error('设置自动发货失败')
    }
    
    taskId = setupShippingRes.data.task_id
    addLog('步骤 5/5', `任务已创建，ID: ${taskId}`, 'info')
    
    await new Promise((resolve, reject) => {
      pollTaskStatus(
        taskId,
        () => {
          addLog('步骤 5/5', '自动发货设置成功', 'success')
          resolve()
        },
        (error) => {
          reject(new Error(`设置自动发货失败: ${error}`))
        }
      )
    })
    
    // ========== 完成 ==========
    const duration = ((Date.now() - startTime.value) / 1000).toFixed(1)
    
    result.value = {
      success: true,
      productId: productId,
      kindName: form.value.kindName,
      duration: duration
    }
    
    addLog('✅ 全部完成', '所有步骤执行成功！', 'success')
    ElMessage.success('自动化流程执行成功！')
    
  } catch (error) {
    console.error('工作流执行失败:', error)
    addLog('❌ 执行失败', error.message, 'danger')
    
    const duration = ((Date.now() - startTime.value) / 1000).toFixed(1)
    result.value = {
      success: false,
      duration: duration
    }
    
    ElMessage.error(error.message || '执行失败')
  } finally {
    running.value = false
    if (pollingTimer) {
      clearInterval(pollingTimer)
    }
  }
}

// 粘贴图片
document.addEventListener('paste', (e) => {
  const items = e.clipboardData.items
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.indexOf('image') !== -1) {
      const file = items[i].getAsFile()
      const reader = new FileReader()
      reader.onload = (event) => {
        const img = new Image()
        img.onload = () => {
          uploadedImage = img
          hasUploadedImage.value = true
          drawCanvas()
        }
        img.src = event.target.result
      }
      reader.readAsDataURL(file)
      e.preventDefault()
      break
    }
  }
})

// 加载媒体海报
const loadMediaPoster = () => {
  return new Promise((resolve, reject) => {
    if (!mediaData.value || !mediaData.value.poster_url) {
      console.log('没有海报URL')
      reject('没有海报URL')
      return
    }

    console.log('开始加载海报:', mediaData.value.poster_url)
    
    const img = new Image()
    img.crossOrigin = 'anonymous'
    
    img.onload = () => {
      console.log('海报加载成功')
      uploadedImage = img
      hasUploadedImage.value = true
      drawCanvas()
      ElMessage.success('海报加载成功')
      resolve()
    }
    
    img.onerror = (err) => {
      console.error('海报加载失败:', err)
      ElMessage.error('海报加载失败，请手动上传')
      reject(err)
    }
    
    // 使用后端代理加载海报
    const posterUrl = `/api/media/poster?url=${encodeURIComponent(mediaData.value.poster_url)}`
    console.log('海报代理URL:', posterUrl)
    img.src = posterUrl
  })
}

onMounted(async () => {
  const cvs = canvasRef.value
  ctx = cvs.getContext('2d')
  loadLogos()
  
  // 加载模板
  await loadTemplates()
  
  // 获取媒体信息
  mediaId.value = route.query.media_id
  if (mediaId.value) {
    try {
      console.log('正在加载媒体信息, ID:', mediaId.value)
      const res = await api.get(`/mappings/${mediaId.value}`)
      console.log('媒体信息响应:', res.data)
      
      if (res.data.success) {
        mediaData.value = res.data.data
        console.log('媒体数据:', mediaData.value)
        
        // 自动填充表单（去掉年份）
        const cleanTitle = (mediaData.value.original_name || '')
          .replace(/\s*[\(（]\d{4}(-\d{4})?[\)）]\s*/g, '')
          .replace(/\s*[\[【]\d{4}(-\d{4})?[\]】]\s*/g, '')
          .trim()
        form.value.title = cleanTitle || form.value.title
        form.value.content = mediaData.value.overview || form.value.content
        
        // 自动填充Canvas参数
        // 去掉标题中的年份，如 "长安十二时辰 (2019)" -> "长安十二时辰"
        const titleWithoutYear = (mediaData.value.original_name || '')
          .replace(/\s*[\(（]\d{4}(-\d{4})?[\)）]\s*/g, '') // 去掉 (2019) 或 （2019） 或 (2019-2020)
          .replace(/\s*[\[【]\d{4}(-\d{4})?[\]】]\s*/g, '') // 去掉 [2019] 或 【2019】
          .trim()
        
        canvas.value.centerTitle = titleWithoutYear || '4K超清'
        // 左侧文字保持默认值不变，不自动填充
        
        // 🔥 同步设置卡种名称
        form.value.kindName = titleWithoutYear || '网盘会员卡'
        
        // 🔥 根据是否完结自动选择模板类型
        if (mediaData.value.is_completed) {
          templateType.value = 'completed'
        } else {
          templateType.value = 'updating'
        }
        
        // 🔥 自动生成商品标题和内容（使用模板）
        updateTemplate()
        
        // 🔥 自动生成卡密数据（从网盘链接）
        const kamiParts = []
        
        if (mediaData.value.baidu_link) {
          const baiduMatch = mediaData.value.baidu_link.match(/https?:\/\/[^\s]+/)
          const pwdMatch = mediaData.value.baidu_link.match(/(?:pwd|提取码)[：:]\s*(\S+)/)
          if (baiduMatch) {
            let baiduText = `【百度网盘】${baiduMatch[0]}`
            if (pwdMatch) {
              baiduText += ` 提取码: ${pwdMatch[1]}`
            }
            kamiParts.push(baiduText)
          }
        }
        
        if (mediaData.value.quark_link) {
          const quarkMatch = mediaData.value.quark_link.match(/https?:\/\/[^\s]+/)
          if (quarkMatch) {
            kamiParts.push(`【夸克网盘】${quarkMatch[0]}`)
          }
        }
        
        if (mediaData.value.xunlei_link) {
          const xunleiMatch = mediaData.value.xunlei_link.match(/https?:\/\/[^\s]+/)
          const pwdMatch = mediaData.value.xunlei_link.match(/(?:pwd|提取码)[：:]\s*(\S+)/)
          if (xunleiMatch) {
            let xunleiText = `【迅雷网盘】${xunleiMatch[0]}`
            if (pwdMatch) {
              xunleiText += ` 提取码: ${pwdMatch[1]}`
            }
            kamiParts.push(xunleiText)
          }
        }
        
        if (kamiParts.length > 0) {
          form.value.kamiData = kamiParts.join('  ')
          console.log('✅ 自动生成卡密数据:', form.value.kamiData)
          ElMessage.success(`已自动填充${kamiParts.length}个网盘链接`)
        } else {
          console.warn('⚠️ 该媒体没有网盘链接')
        }
        
        // 自动加载海报
        try {
          await loadMediaPoster()
        } catch (error) {
          console.error('加载海报失败:', error)
          drawCanvas() // 即使失败也要绘制Canvas
        }
      }
    } catch (error) {
      console.error('加载媒体失败:', error)
      ElMessage.error('加载媒体信息失败')
      drawCanvas()
    }
  } else {
    drawCanvas()
  }
})

// 监听中心标题变化，自动更新商品标题、内容和卡种名称
watch(() => canvas.value.centerTitle, (newTitle) => {
  if (newTitle && newTitle.trim()) {
    updateTemplate()
    // 同步更新卡种名称
    form.value.kindName = newTitle.trim()
  }
})

// 监听模板类型变化，自动更新商品标题和内容
watch(templateType, () => {
  updateTemplate()
})
</script>

<style scoped>
.auto-workflow-page {
  background: #f5f7fa;
  min-height: 100vh;
  padding: 10px;
}

.main-container {
  display: grid;
  grid-template-columns: 350px 1fr 350px;
  gap: 10px;
  max-width: 1800px;
  margin: 0 auto;
  height: calc(100vh - 20px);
}

.main-container:has(~ .el-alert) {
  height: calc(100vh - 80px);
}

.left-panel, .right-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  height: 100%;
}

.left-panel::-webkit-scrollbar,
.right-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-thumb,
.right-panel::-webkit-scrollbar-thumb {
  background: #667eea;
  border-radius: 10px;
}

.panel-card {
  flex-shrink: 0;
}

.panel-card :deep(.el-card__header) {
  padding: 12px 15px;
  font-size: 14px;
  font-weight: 600;
}

.panel-card :deep(.el-card__body) {
  padding: 15px;
}

.upload-section {
  text-align: center;
}

.info-text {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.center-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.center-panel :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.center-panel :deep(.el-card__body) {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.canvas-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
}

canvas {
  max-width: 100%;
  max-height: calc(100vh - 150px);
  height: auto;
  border: 2px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.log-container {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  padding: 10px;
  scroll-behavior: smooth;
}

.log-success { color: #67C23A; }
.log-danger { color: #F56C6C; }
.log-warning { color: #E6A23C; }
.log-info { color: #909399; }
.log-primary { color: #409EFF; }

@media (max-width: 1600px) {
  .main-container {
    grid-template-columns: 350px 1fr 350px;
  }
}
</style>
