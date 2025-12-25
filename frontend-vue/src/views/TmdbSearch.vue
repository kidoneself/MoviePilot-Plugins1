<template>
  <div class="tmdb-search">
    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <span>🎬 TMDb 影视搜索</span>
          <div class="header-right">
            <el-button 
              type="warning" 
              size="small" 
              :loading="checkingUpdates"
              @click="handleCheckUpdates"
            >
              🔔 检查剧集更新
            </el-button>
            <el-tag type="info" size="small">根据 cat.yaml 自动分类</el-tag>
          </div>
        </div>
      </template>

      <!-- 搜索区域 -->
      <div class="search-area">
        <el-input
          v-model="searchQuery"
          placeholder="输入影视作品名称搜索..."
          size="large"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #prepend>
            <el-select v-model="mediaType" placeholder="类型" style="width: 100px">
              <el-option label="全部" value="multi" />
              <el-option label="电影" value="movie" />
              <el-option label="电视剧" value="tv" />
            </el-select>
          </template>
          <template #append>
            <el-button :icon="Search" @click="handleSearch" :loading="searching">
              搜索
            </el-button>
          </template>
        </el-input>
      </div>
    </el-card>

    <!-- 搜索结果 -->
    <el-card v-if="searchResults.length > 0" class="results-card" style="margin-top: 20px;">
      <template #header>
        <span>搜索结果 ({{ searchResults.length }} 个)</span>
      </template>

      <div class="results-grid">
        <div
          v-for="item in searchResults"
          :key="item.id"
          class="result-item"
          @click="showDetails(item)"
        >
          <el-image
            :src="item.poster_path || '/placeholder.jpg'"
            fit="cover"
            class="poster"
            lazy
          >
            <template #error>
              <div class="image-slot">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          
          <div class="info">
            <div class="title">{{ item.title }}</div>
            <div class="meta">
              <el-tag :type="item.media_type === 'movie' ? 'success' : 'primary'" size="small">
                {{ item.media_type === 'movie' ? '电影' : '电视剧' }}
              </el-tag>
              <span class="year">{{ item.year }}</span>
            </div>
            <div class="rating">
              <el-rate
                v-model="item.vote_average"
                disabled
                show-score
                text-color="#ff9900"
                score-template="{value}"
                :max="10"
              />
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailsVisible"
      :title="currentDetails?.title"
      width="90%"
      top="5vh"
      class="details-dialog"
    >
      <div v-if="currentDetails" class="details-content">
        <el-row :gutter="20">
          <!-- 左侧：海报和基本信息 -->
          <el-col :span="8">
            <el-image
              :src="currentDetails.main_poster"
              fit="cover"
              class="main-poster"
            >
              <template #error>
                <div class="image-slot">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>

            <el-descriptions :column="1" border class="info-box" style="margin-top: 20px;">
              <el-descriptions-item label="名称">
                {{ currentDetails.title }} ({{ currentDetails.year }})
              </el-descriptions-item>
              <el-descriptions-item label="二级分类">
                <el-tag v-if="currentDetails.category" type="success">
                  {{ currentDetails.category }}
                </el-tag>
                <el-tag v-else type="info">未分类</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="类型">
                {{ currentDetails.genres.join(', ') }}
              </el-descriptions-item>
              <el-descriptions-item label="国家">
                {{ currentDetails.origin_country.join(', ') }}
              </el-descriptions-item>
              <el-descriptions-item label="评分">
                <el-rate
                  v-model="currentDetails.vote_average"
                  disabled
                  show-score
                  text-color="#ff9900"
                  score-template="{value}/10"
                  :max="10"
                />
              </el-descriptions-item>
              <el-descriptions-item v-if="currentDetails.runtime" label="时长">
                {{ currentDetails.runtime }} 分钟
              </el-descriptions-item>
              <el-descriptions-item v-if="currentDetails.number_of_seasons" label="季数">
                {{ currentDetails.number_of_seasons }} 季
              </el-descriptions-item>
              <el-descriptions-item v-if="currentDetails.number_of_episodes" label="集数">
                {{ currentDetails.number_of_episodes }} 集
              </el-descriptions-item>
            </el-descriptions>
          </el-col>

          <!-- 右侧：简介和图片 -->
          <el-col :span="16">
            <div class="overview-section">
              <h3>简介</h3>
              <p>{{ currentDetails.overview || '暂无简介' }}</p>
            </div>

            <el-divider />

            <!-- 主图链接 -->
            <div class="image-urls">
              <h3>🖼️ 主图链接</h3>
              <el-input
                :value="currentDetails.main_poster"
                readonly
                class="url-input"
              >
                <template #append>
                  <el-button @click="copyUrl(currentDetails.main_poster)">
                    复制
                  </el-button>
                </template>
              </el-input>
            </div>

            <el-divider />

            <!-- 海报图片 -->
            <div v-if="currentDetails.posters.length > 0" class="gallery">
              <h3>📸 海报 ({{ currentDetails.posters.length }} 张)</h3>
              <div class="gallery-grid">
                <div v-for="(poster, index) in currentDetails.posters" :key="index" class="gallery-item">
                  <el-image
                    :src="poster"
                    fit="cover"
                    class="gallery-image"
                    :preview-src-list="currentDetails.posters"
                    :initial-index="index"
                  />
                  <el-button size="small" @click="copyUrl(poster)" class="copy-btn">
                    复制链接
                  </el-button>
                </div>
              </div>
            </div>

            <el-divider />

            <!-- 剧照图片 -->
            <div v-if="currentDetails.backdrops.length > 0" class="gallery">
              <h3>🎬 剧照 ({{ currentDetails.backdrops.length }} 张)</h3>
              <div class="gallery-grid">
                <div v-for="(backdrop, index) in currentDetails.backdrops" :key="index" class="gallery-item">
                  <el-image
                    :src="backdrop"
                    fit="cover"
                    class="gallery-image"
                    :preview-src-list="currentDetails.backdrops"
                    :initial-index="index"
                  />
                  <el-button size="small" @click="copyUrl(backdrop)" class="copy-btn">
                    复制链接
                  </el-button>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>

      <template #footer>
        <div style="display: flex; justify-content: space-between; width: 100%;">
          <el-button 
            type="primary" 
            :loading="creatingMapping"
            @click="handleCreateMapping"
          >
            ✅ 添加到映射
          </el-button>
          <el-button @click="detailsVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Picture } from '@element-plus/icons-vue'
import api from '../api'

const searchQuery = ref('')
const mediaType = ref('multi')
const searching = ref(false)
const searchResults = ref([])

const detailsVisible = ref(false)
const currentDetails = ref(null)
const loadingDetails = ref(false)
const creatingMapping = ref(false)
const checkingUpdates = ref(false)

// 搜索
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  searching.value = true
  try {
    const res = await api.searchTmdb({
      query: searchQuery.value,
      media_type: mediaType.value
    })

    if (res.data.success) {
      searchResults.value = res.data.data
      if (searchResults.value.length === 0) {
        ElMessage.info('未找到相关结果')
      }
    } else {
      ElMessage.error('搜索失败')
    }
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败：' + (error.message || '未知错误'))
  } finally {
    searching.value = false
  }
}

// 显示详情
const showDetails = async (item) => {
  loadingDetails.value = true
  detailsVisible.value = true
  currentDetails.value = null

  try {
    const res = await api.getTmdbDetails(item.media_type, item.id)
    if (res.data.success) {
      currentDetails.value = res.data.data
    } else {
      ElMessage.error('获取详情失败')
    }
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  } finally {
    loadingDetails.value = false
  }
}

// 复制链接
const copyUrl = (url) => {
  if (!url) {
    ElMessage.warning('链接为空')
    return
  }

  navigator.clipboard.writeText(url).then(() => {
    ElMessage.success('链接已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// 创建映射
const handleCreateMapping = async () => {
  if (!currentDetails.value) {
    return
  }

  const { id, title, year, category, media_type, main_poster, overview } = currentDetails.value

  if (!category) {
    ElMessage.warning('该作品无法自动分类，请在映射管理中手动添加')
    return
  }

  creatingMapping.value = true

  try {
    const res = await api.post('/tmdb/create-mapping', {
      title,
      year,
      category,
      media_type,
      tmdb_id: id,
      poster_url: main_poster,
      overview: overview
    })

    if (res.data.success) {
      ElMessage.success({
        message: `✅ 映射创建成功！\n原始名: ${res.data.data.original_name}\n夸克名: ${res.data.data.quark_name}`,
        duration: 5000,
        showClose: true
      })
      
      // 可选：关闭详情对话框
      // detailsVisible.value = false
    } else {
      ElMessage.error(res.data.message || '创建失败')
    }
  } catch (error) {
    console.error('创建映射失败:', error)
    ElMessage.error('创建失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    creatingMapping.value = false
  }
}

// 检查剧集更新
const handleCheckUpdates = async () => {
  checkingUpdates.value = true
  
  try {
    const res = await api.checkTmdbUpdates()
    
    if (res.data.success) {
      ElMessage.success({
        message: '🔔 已触发剧集更新检查！\n检查结果将通过企业微信通知您',
        duration: 5000,
        showClose: true
      })
    } else {
      ElMessage.error(res.data.message || '触发失败')
    }
  } catch (error) {
    console.error('触发检查失败:', error)
    ElMessage.error('触发失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    checkingUpdates.value = false
  }
}
</script>

<style scoped>
.tmdb-search {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-area {
  width: 100%;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.result-item {
  cursor: pointer;
  transition: transform 0.2s;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #eee;
}

.result-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.result-item .poster {
  width: 100%;
  height: 270px;
}

.result-item .info {
  padding: 12px;
}

.result-item .title {
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-item .meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #666;
}

.result-item .rating {
  font-size: 12px;
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
  font-size: 30px;
}

.details-content {
  max-height: 70vh;
  overflow-y: auto;
}

.main-poster {
  width: 100%;
  border-radius: 8px;
}

.info-box {
  margin-top: 20px;
}

.overview-section {
  margin-bottom: 20px;
}

.overview-section h3 {
  margin-bottom: 12px;
  font-size: 18px;
}

.overview-section p {
  line-height: 1.8;
  color: #606266;
  text-align: justify;
}

.image-urls {
  margin-bottom: 20px;
}

.image-urls h3 {
  margin-bottom: 12px;
  font-size: 16px;
}

.url-input {
  margin-bottom: 10px;
}

.gallery h3 {
  margin-bottom: 12px;
  font-size: 16px;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 15px;
}

.gallery-item {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #eee;
}

.gallery-image {
  width: 100%;
  height: 120px;
  cursor: pointer;
}

.gallery-item .copy-btn {
  position: absolute;
  bottom: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.gallery-item:hover .copy-btn {
  opacity: 1;
}
</style>

