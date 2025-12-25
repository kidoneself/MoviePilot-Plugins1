<template>
  <div class="create-product-page">
    <div class="main-container">
      <!-- 左侧：控制面板 -->
      <div class="left-panel">
        <el-card class="control-card">
          <template #header>
            <span>📝 商品信息</span>
          </template>
          
          <el-form label-width="100px" size="small">
            <el-form-item label="商品标题">
              <el-input v-model="productTitle" placeholder="商品标题" />
            </el-form-item>
            
            <el-form-item label="商品描述">
              <el-input v-model="productContent" type="textarea" :rows="3" />
            </el-form-item>
            
            <el-form-item label="价格(元)">
              <el-input-number v-model="productPrice" :min="0.01" :step="0.1" :precision="2" />
            </el-form-item>
            
            <el-form-item label="库存">
              <el-input-number v-model="productStock" :min="1" :step="1" />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="control-card" style="margin-top: 10px;">
          <template #header>
            <span>🎨 海报编辑</span>
          </template>
          
          <el-form label-width="100px" size="small">
            <el-form-item label="上传海报">
              <input type="file" accept="image/*" @change="handleFileUpload" style="font-size: 13px;" />
            </el-form-item>
            
            <el-divider />
            
            <el-form-item label="中心标题">
              <el-input v-model="centerTitle" placeholder="如：4K超清" @input="drawCanvas" />
            </el-form-item>
            
            <el-form-item label="标题大小">
              <el-slider v-model="titleSize" :min="20" :max="100" @input="drawCanvas" show-input />
            </el-form-item>
            
            <el-form-item label="标题颜色">
              <el-color-picker v-model="titleColor" @change="drawCanvas" />
            </el-form-item>
            
            <el-divider />
            
            <el-form-item label="集数">
              <el-input v-model="episodeCount" placeholder="如：24" @input="drawCanvas" />
            </el-form-item>
            
            <el-divider />
            
            <el-form-item label="底部左上">
              <el-input v-model="bottomLeft1" @input="drawCanvas" />
            </el-form-item>
            
            <el-form-item label="底部左下">
              <el-input v-model="bottomLeft2" @input="drawCanvas" />
            </el-form-item>
            
            <el-form-item label="底部右上">
              <el-input v-model="bottomRight1" @input="drawCanvas" />
            </el-form-item>
            
            <el-form-item label="底部右下">
              <el-input v-model="bottomRight2" @input="drawCanvas" />
            </el-form-item>
            
            <el-divider />
            
            <el-form-item label="左侧文字">
              <el-input v-model="leftText" type="textarea" :rows="2" placeholder="竖排显示" @input="drawCanvas" />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="control-card" style="margin-top: 10px;">
          <el-button type="primary" @click="createProduct" :loading="creating" style="width: 100%;" size="large">
            🐟 创建闲鱼商品
          </el-button>
          <el-button @click="goBack" style="width: 100%; margin-top: 10px;">
            返回媒体库
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
            <canvas ref="canvasRef" width="800" height="1200"></canvas>
          </div>
        </el-card>
      </div>

      <!-- 右侧：额外图片（可选） -->
      <div class="right-panel">
        <el-card>
          <template #header>
            <span>📷 生成结果</span>
          </template>
          <div v-if="generatedImage" class="preview-image">
            <img :src="generatedImage" />
            <p style="color: #67C23A; margin-top: 10px;">✓ 主图已生成</p>
          </div>
          <el-empty v-else description="Canvas实时预览" />
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const route = useRoute()

const canvasRef = ref(null)
let ctx = null
let uploadedImage = null

// 商品信息
const productTitle = ref('')
const productContent = ref('')
const productPrice = ref(0.1)
const productStock = ref(100)
const creating = ref(false)
const generatedImage = ref('')

// 画图参数
const centerTitle = ref('4K超清')
const titleSize = ref(48)
const titleColor = ref('#ffffff')
const episodeCount = ref('')
const bottomLeft1 = ref('国语')
const bottomLeft2 = ref('中字')
const bottomRight1 = ref('蓝光')
const bottomRight2 = ref('画质')
const leftText = ref('')

// Logo
const logos = { baidu: null, quark: null, xunlei: null }
let logosLoaded = 0

// 从路由获取媒体信息
const mediaId = ref(null)
const mediaData = ref(null)

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

// 加载媒体海报
const loadMediaPoster = async () => {
  if (!mediaData.value || !mediaData.value.poster_url) return

  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    uploadedImage = img
    drawCanvas()
  }
  img.onerror = () => {
    ElMessage.error('海报加载失败')
  }
  
  img.src = `/api/media/poster?url=${encodeURIComponent(mediaData.value.poster_url)}`
}

// 文件上传
const handleFileUpload = (e) => {
  const file = e.target.files[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (event) => {
    const img = new Image()
    img.onload = () => {
      uploadedImage = img
      drawCanvas()
    }
    img.src = event.target.result
  }
  reader.readAsDataURL(file)
}

// 绘制Canvas（完全按照Java版本）
const drawCanvas = () => {
  if (!ctx) return

  const canvas = canvasRef.value
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // 背景图
  if (uploadedImage) {
    const scale = Math.max(canvas.width / uploadedImage.width, canvas.height / uploadedImage.height)
    const x = (canvas.width - uploadedImage.width * scale) / 2
    const y = (canvas.height - uploadedImage.height * scale) / 2
    ctx.drawImage(uploadedImage, x, y, uploadedImage.width * scale, uploadedImage.height * scale)
  } else {
    ctx.fillStyle = '#f0f0f0'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#999'
    ctx.font = '24px Arial'
    ctx.textAlign = 'center'
    ctx.fillText('请上传海报或等待加载', canvas.width / 2, canvas.height / 2)
    return
  }

  // 中心标题徽章
  if (centerTitle.value.trim()) {
    ctx.save()
    ctx.font = `bold ${titleSize.value}px Arial`
    const textWidth = ctx.measureText(centerTitle.value).width
    const textHeight = titleSize.value
    
    const paddingX = 30, paddingY = 20
    const badgeX = canvas.width / 2 - textWidth / 2 - paddingX
    const badgeY = canvas.height / 2 - 50 - textHeight - paddingY / 2
    const badgeWidth = textWidth + paddingX * 2
    const badgeHeight = textHeight + paddingY
    const radius = 15
    
    // 阴影
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)'
    ctx.shadowBlur = 15
    ctx.shadowOffsetY = 8
    
    // 粉色渐变
    const gradient = ctx.createLinearGradient(badgeX, badgeY, badgeX, badgeY + badgeHeight)
    gradient.addColorStop(0, '#ff69b4')
    gradient.addColorStop(1, '#ff1493')
    ctx.fillStyle = gradient
    
    // 圆角矩形
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
    
    // 白色描边
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'white'
    ctx.lineWidth = 4
    ctx.stroke()
    
    // 文字
    ctx.fillStyle = titleColor.value
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(centerTitle.value, canvas.width / 2, badgeY + badgeHeight / 2)
    ctx.restore()
  }

  // 集数
  if (episodeCount.value.trim()) {
    ctx.save()
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 20
    ctx.font = 'bold 80px Arial'
    ctx.fillStyle = 'white'
    ctx.textAlign = 'center'
    ctx.fillText(`全${episodeCount.value}集`, canvas.width / 2, canvas.height - 280)
    ctx.restore()
  }

  // 底部三色条
  const bottomBarHeight = canvas.height * 0.2
  const bottomY = canvas.height - bottomBarHeight
  const thirdWidth = canvas.width / 3

  ctx.fillStyle = '#1e3a8a'
  ctx.fillRect(0, bottomY, thirdWidth, bottomBarHeight)
  
  ctx.fillStyle = '#fbbf24'
  ctx.fillRect(thirdWidth, bottomY, thirdWidth, bottomBarHeight)
  
  ctx.fillStyle = '#1e3a8a'
  ctx.fillRect(thirdWidth * 2, bottomY, thirdWidth, bottomBarHeight)

  // 底部文字
  ctx.fillStyle = 'white'
  const fontSize = Math.floor(canvas.height * 0.037)
  ctx.font = `bold ${fontSize}px Arial`
  ctx.textAlign = 'center'
  
  ctx.fillText(bottomLeft1.value, thirdWidth / 2, bottomY + bottomBarHeight * 0.37)
  ctx.fillText(bottomLeft2.value, thirdWidth / 2, bottomY + bottomBarHeight * 0.63)
  ctx.fillText(bottomRight1.value, thirdWidth * 2 + thirdWidth / 2, bottomY + bottomBarHeight * 0.37)
  ctx.fillText(bottomRight2.value, thirdWidth * 2 + thirdWidth / 2, bottomY + bottomBarHeight * 0.63)

  // 中间4K
  ctx.fillStyle = 'white'
  const centerFontSize = Math.floor(canvas.height * 0.08)
  ctx.font = `bold ${centerFontSize}px Arial`
  ctx.fillText('4K', thirdWidth + thirdWidth / 2, bottomY + bottomBarHeight * 0.43)
  
  ctx.fillStyle = 'black'
  const ultraFontSize = Math.floor(canvas.height * 0.037)
  ctx.font = `bold ${ultraFontSize}px Arial`
  ctx.fillText('ULTRA HD', thirdWidth + thirdWidth / 2, bottomY + bottomBarHeight * 0.7)

  // 左侧竖排文字
  if (leftText.value.trim()) {
    ctx.save()
    ctx.fillStyle = 'white'
    ctx.font = 'bold 22px Arial'
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 10
    
    const chars = leftText.value.split('')
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
    const logoSize = 60
    const spacing = 15
    const totalWidth = logoSize * 3 + spacing * 2
    const startX = (canvas.width - totalWidth) / 2
    const logoY = 25
    
    const badgePaddingX = 25, badgePaddingY = 15
    const badgeX = startX - badgePaddingX
    const badgeY = logoY - badgePaddingY
    const badgeWidth = totalWidth + badgePaddingX * 2
    const badgeHeight = logoSize + badgePaddingY * 2
    const badgeRadius = 12
    
    ctx.save()
    
    // 阴影
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)'
    ctx.shadowBlur = 12
    ctx.shadowOffsetY = 6
    
    // 黄色渐变背景
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
    
    // 白色描边
    ctx.shadowColor = 'transparent'
    ctx.strokeStyle = 'white'
    ctx.lineWidth = 3
    ctx.stroke()
    
    // 绘制Logo（顺序：百度、夸克、迅雷）
    const logoOrder = ['baidu', 'quark', 'xunlei']
    logoOrder.forEach((name, i) => {
      if (logos[name]) {
        const logoX = startX + i * (logoSize + spacing)
        const logoCenterX = logoX + logoSize / 2
        const logoCenterY = logoY + logoSize / 2
        
        // 白色圆形背景
        ctx.shadowColor = 'rgba(0, 0, 0, 0.2)'
        ctx.shadowBlur = 5
        ctx.fillStyle = 'white'
        ctx.beginPath()
        ctx.arc(logoCenterX, logoCenterY, logoSize / 2 + 5, 0, Math.PI * 2)
        ctx.fill()
        
        // 绘制Logo
        ctx.shadowColor = 'transparent'
        ctx.drawImage(logos[name], logoX, logoY, logoSize, logoSize)
      }
    })
    
    ctx.restore()
  }
}

// 创建商品
const createProduct = async () => {
  if (!uploadedImage) {
    ElMessage.warning('请先上传海报图片')
    return
  }

  creating.value = true
  try {
    // 生成最终图片
    const canvas = canvasRef.value
    const imageBlob = await new Promise(resolve => {
      canvas.toBlob(resolve, 'image/png', 0.95)
    })
    
    // 上传图片
    const formData = new FormData()
    formData.append('files', imageBlob, 'poster.png')
    
    const uploadRes = await api.post('/xianyu/product/upload-images-only', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (!uploadRes.data.success) {
      throw new Error(uploadRes.data.message || '图片上传失败')
    }
    
    const imageUrls = uploadRes.data.image_urls
    
    // 创建商品
    if (mediaId.value) {
      const res = await api.post('/xianyu/product/create-from-media', {
        media_id: mediaId.value,
        title: productTitle.value,
        content: productContent.value,
        price: productPrice.value,
        express_fee: 0,
        stock: productStock.value,
        image_urls: imageUrls
      })
      
      if (res.data.success) {
        ElMessage.success(res.data.message || '商品创建成功')
        setTimeout(() => router.push('/xianyu/products'), 1500)
      }
    }
  } catch (error) {
    console.error('创建失败:', error)
    ElMessage.error(error.response?.data?.detail || error.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const goBack = () => {
  router.push('/media')
}

onMounted(async () => {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  
  // 加载Logo
  loadLogos()
  
  // 获取媒体信息
  mediaId.value = route.query.media_id
  if (mediaId.value) {
    try {
      const res = await api.get(`/mappings/${mediaId.value}`)
      if (res.data.success) {
        mediaData.value = res.data.data
        productTitle.value = mediaData.value.original_name
        productContent.value = mediaData.value.overview || ''
        leftText.value = mediaData.value.original_name.substring(0, 6)
        
        // 自动加载海报
        loadMediaPoster()
      }
    } catch (error) {
      console.error('加载媒体失败:', error)
    }
  }
})
</script>

<style scoped>
.create-product-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.main-container {
  display: grid;
  grid-template-columns: 350px 1fr 350px;
  gap: 20px;
  max-width: 1800px;
  margin: 0 auto;
}

.left-panel, .right-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.control-card {
  height: fit-content;
}

.canvas-wrapper {
  display: flex;
  justify-content: center;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

canvas {
  max-width: 100%;
  height: auto;
  border: 2px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.preview-image {
  text-align: center;
}

.preview-image img {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #ddd;
}
</style>

