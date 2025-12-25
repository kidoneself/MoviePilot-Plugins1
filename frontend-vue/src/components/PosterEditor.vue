<template>
  <div class="poster-editor">
    <el-row :gutter="20">
      <!-- 左侧：控制面板 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🎨 海报编辑</span>
            </div>
          </template>

          <el-form label-width="100px" size="small">
            <!-- 中心标题 -->
            <el-form-item label="中心标题">
              <el-input v-model="centerTitle" placeholder="如：4K超清" @input="draw" />
            </el-form-item>
            <el-form-item label="标题大小">
              <el-slider v-model="titleSize" :min="20" :max="100" @input="draw" />
            </el-form-item>
            <el-form-item label="标题颜色">
              <el-color-picker v-model="titleColor" @change="draw" />
            </el-form-item>

            <el-divider />

            <!-- 集数 -->
            <el-form-item label="集数">
              <el-input v-model="episodeCount" placeholder="如：24" @input="draw" />
            </el-form-item>

            <el-divider />

            <!-- 底部文字 -->
            <el-form-item label="底部左上">
              <el-input v-model="bottomLeft1" @input="draw" />
            </el-form-item>
            <el-form-item label="底部左下">
              <el-input v-model="bottomLeft2" @input="draw" />
            </el-form-item>
            <el-form-item label="底部右上">
              <el-input v-model="bottomRight1" @input="draw" />
            </el-form-item>
            <el-form-item label="底部右下">
              <el-input v-model="bottomRight2" @input="draw" />
            </el-form-item>

            <el-divider />

            <!-- 左侧竖排文字 -->
            <el-form-item label="左侧文字">
              <el-input
                v-model="leftText"
                type="textarea"
                :rows="3"
                placeholder="竖排显示"
                @input="draw"
              />
            </el-form-item>

            <el-divider />

            <!-- 操作按钮 -->
            <el-space direction="vertical" style="width: 100%">
              <el-button type="primary" @click="generateImage" style="width: 100%">
                生成图片
              </el-button>
              <el-button @click="resetCanvas" style="width: 100%">
                重置
              </el-button>
            </el-space>
          </el-form>
        </el-card>
      </el-col>

      <!-- 中间：Canvas画布 -->
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📐 画布预览</span>
            </div>
          </template>
          <div class="canvas-wrapper">
            <canvas ref="canvasRef" width="800" height="1200"></canvas>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：生成的图片 -->
      <el-col :span="6">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🖼️ 生成结果</span>
            </div>
          </template>
          <div v-if="generatedImages.length > 0" class="generated-images">
            <div v-for="(img, index) in generatedImages" :key="index" class="image-item">
              <img :src="img.url" />
              <div class="image-label">{{ img.label }}</div>
            </div>
          </div>
          <el-empty v-else description="暂无生成图片" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  posterUrl: String,  // TMDB海报URL
  mediaName: String   // 媒体名称
})

const emit = defineEmits(['generated'])

const canvasRef = ref(null)
let ctx = null
let uploadedImage = null

// 三个网盘Logo
const logos = {
  quark: null,
  baidu: null,
  xunlei: null
}
let logosLoaded = 0
const totalLogos = 3

// 表单数据
const centerTitle = ref('4K超清')
const titleSize = ref(48)
const titleColor = ref('#ffffff')
const episodeCount = ref('')
const bottomLeft1 = ref('国语')
const bottomLeft2 = ref('中字')
const bottomRight1 = ref('蓝光')
const bottomRight2 = ref('画质')
const leftText = ref('')

const generatedImages = ref([])

// 加载网盘Logo
const loadLogos = () => {
  const logoUrls = {
    quark: '/svg/夸克网盘.svg',
    baidu: '/svg/百度网盘.svg',
    xunlei: '/svg/迅雷.svg'
  }

  Object.keys(logoUrls).forEach(key => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      logos[key] = img
      logosLoaded++
      if (logosLoaded === totalLogos) {
        draw()
      }
    }
    img.onerror = () => {
      logosLoaded++
      console.warn(`Logo加载失败: ${key}`)
    }
    img.src = logoUrls[key]
  })
}

// 加载海报图片
const loadPoster = () => {
  if (!props.posterUrl) return

  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    uploadedImage = img
    draw()
  }
  img.onerror = () => {
    ElMessage.error('海报加载失败')
  }
  
  // 使用代理URL
  img.src = `/api/media/poster?url=${encodeURIComponent(props.posterUrl)}`
}

// 绘制Canvas
const draw = () => {
  if (!ctx) return

  const canvas = canvasRef.value
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // 绘制背景图
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
    ctx.fillText('加载海报中...', canvas.width / 2, canvas.height / 2)
    return
  }

  // 绘制中心标题徽章
  if (centerTitle.value.trim()) {
    ctx.save()
    
    ctx.font = `bold ${titleSize.value}px Arial`
    const textMetrics = ctx.measureText(centerTitle.value)
    const textWidth = textMetrics.width
    const textHeight = titleSize.value
    
    const paddingX = 30
    const paddingY = 20
    const badgeX = canvas.width / 2 - textWidth / 2 - paddingX
    const badgeY = canvas.height / 2 - 50 - textHeight - paddingY / 2
    const badgeWidth = textWidth + paddingX * 2
    const badgeHeight = textHeight + paddingY
    const radius = 15
    
    // 阴影
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)'
    ctx.shadowBlur = 15
    ctx.shadowOffsetX = 0
    ctx.shadowOffsetY = 8
    
    // 粉色渐变背景
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

  // 绘制集数
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

  // 绘制网盘Logo
  if (logosLoaded === totalLogos) {
    const logoSize = 60
    const spacing = 15
    const totalWidth = logoSize * 3 + spacing * 2
    const startX = (canvas.width - totalWidth) / 2
    const logoY = 25
    
    const badgePaddingX = 25
    const badgePaddingY = 15
    const badgeX = startX - badgePaddingX
    const badgeY = logoY - badgePaddingY
    const badgeWidth = totalWidth + badgePaddingX * 2
    const badgeHeight = logoSize + badgePaddingY * 2
    const badgeRadius = 12
    
    ctx.save()
    
    // 黄色圆角矩形背景
    ctx.shadowColor = 'rgba(0, 0, 0, 0.4)'
    ctx.shadowBlur = 12
    ctx.shadowOffsetX = 0
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
    
    // 绘制Logo
    if (logos.quark) ctx.drawImage(logos.quark, startX, logoY, logoSize, logoSize)
    if (logos.baidu) ctx.drawImage(logos.baidu, startX + logoSize + spacing, logoY, logoSize, logoSize)
    if (logos.xunlei) ctx.drawImage(logos.xunlei, startX + (logoSize + spacing) * 2, logoY, logoSize, logoSize)
    
    ctx.restore()
  }
}

// 生成图片
const generateImage = () => {
  const canvas = canvasRef.value
  const dataUrl = canvas.toDataURL('image/png')
  
  generatedImages.value = [{
    url: dataUrl,
    label: '主图'
  }]
  
  // 通知父组件
  emit('generated', [dataUrl])
  
  ElMessage.success('图片已生成')
}

// 重置
const resetCanvas = () => {
  centerTitle.value = '4K超清'
  titleSize.value = 48
  titleColor.value = '#ffffff'
  episodeCount.value = ''
  bottomLeft1.value = '国语'
  bottomLeft2.value = '中字'
  bottomRight1.value = '蓝光'
  bottomRight2.value = '画质'
  leftText.value = ''
  generatedImages.value = []
  draw()
}

onMounted(() => {
  const canvas = canvasRef.value
  ctx = canvas.getContext('2d')
  
  // 加载Logo和海报
  loadLogos()
  loadPoster()
  
  // 初始绘制
  draw()
})
</script>

<style scoped>
.poster-editor {
  padding: 20px;
}

.canvas-wrapper {
  display: flex;
  justify-content: center;
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
}

canvas {
  max-width: 100%;
  height: auto;
  border: 2px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.generated-images {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.image-item {
  text-align: center;
}

.image-item img {
  width: 100%;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.image-label {
  margin-top: 5px;
  font-size: 12px;
  color: #909399;
}

.card-header {
  font-weight: bold;
}
</style>

