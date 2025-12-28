<template>
  <div class="media-library">
    <!-- 搜索和筛选 -->
    <el-card class="search-card">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-input
            v-model="searchText"
            placeholder="搜索剧名..."
            size="large"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #append>
              <el-button :icon="Search" @click="handleSearch">搜索</el-button>
            </template>
          </el-input>
        </el-col>
        <el-col :span="12">
          <el-space wrap>
            <el-button type="primary" @click="showTmdbDialog">
              ➕ 添加媒体
            </el-button>
            <el-button type="success" @click="handleAutoFillTmdb" :loading="autoFilling">
              🔄 补齐TMDB信息
            </el-button>
            <el-select v-model="filterType" placeholder="类型" style="width: 120px" @change="handleSearch">
              <el-option label="全部类型" value="" />
              <el-option label="电影" value="movie" />
              <el-option label="电视剧" value="tv" />
            </el-select>
            <el-select v-model="filterCompleted" placeholder="状态" style="width: 120px" @change="handleSearch">
              <el-option label="全部状态" value="" />
              <el-option label="完结" value="completed" />
              <el-option label="更新中" value="ongoing" />
            </el-select>
            <el-select v-model="filterCategory" placeholder="分类" style="width: 150px" clearable @change="handleSearch">
              <el-option label="全部分类" value="" />
              <el-option-group v-for="(cats, group) in groupedCategories" :key="group" :label="group">
                <el-option v-for="cat in cats" :key="cat" :label="cat" :value="cat" />
              </el-option-group>
            </el-select>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <!-- 统计 -->
    <div class="stats-container">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
          <el-icon size="24"><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">总计</div>
          <div class="stat-value">{{ total }}<span class="stat-unit">部</span></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
          <el-icon size="24"><Film /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">电影</div>
          <div class="stat-value">{{ stats.movies }}<span class="stat-unit">部</span></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
          <el-icon size="24"><VideoPlay /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">剧集</div>
          <div class="stat-value">{{ stats.tvs }}<span class="stat-unit">部</span></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
          <el-icon size="24"><CircleCheck /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-label">完结</div>
          <div class="stat-value">{{ stats.completed }}<span class="stat-unit">部</span></div>
        </div>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-loading="loading" class="media-grid" style="margin-top: 20px;">
      <el-card
        v-for="item in mediaList"
        :key="item.id"
        class="media-card"
        shadow="hover"
        @click="showDetails(item)"
      >
        <!-- 海报 -->
        <div class="poster-wrapper">
          <el-image
            :src="getPosterUrl(item.poster_url)"
            fit="cover"
            class="poster"
            lazy
          >
            <template #error>
              <div class="image-placeholder">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          
          <!-- 状态标签 - 右上角 -->
          <div class="status-badges">
            <el-tag v-if="item.is_completed" type="success" size="small">完结</el-tag>
            <el-tag v-else type="warning" size="small">更新中</el-tag>
            
            <el-tag v-if="item.media_type === 'movie'" type="info" size="small">电影</el-tag>
            <el-tag v-else-if="item.media_type === 'tv'" type="primary" size="small">剧集</el-tag>
          </div>
          
          <!-- 分类标签 - 左下角 -->
          <div class="category-badge">
            <el-tag size="small" effect="dark">{{ item.category || '未分类' }}</el-tag>
          </div>
        </div>

        <!-- 信息 -->
        <div class="media-info">
          <div class="title">{{ item.original_name }}</div>
        </div>
      </el-card>

      <!-- 空状态 -->
      <el-empty v-if="!loading && mediaList.length === 0" description="暂无媒体">
        <el-button type="primary" @click="showTmdbDialog">去添加媒体</el-button>
      </el-empty>
    </div>

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[12, 24, 48, 96]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="loadMediaList"
      @size-change="loadMediaList"
      style="margin-top: 20px; justify-content: center;"
    />

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="detailsVisible"
      :title="currentItem?.original_name"
      size="60%"
    >
      <div v-if="currentItem" class="details-content">
        <el-row :gutter="20">
          <!-- 左侧：海报 -->
          <el-col :span="8">
            <el-image
              :src="getPosterUrl(currentItem.poster_url)"
              fit="cover"
              style="width: 100%; border-radius: 8px;"
            >
              <template #error>
                <div class="image-placeholder" style="height: 400px;">
                  <el-icon><Picture /></el-icon>
                </div>
              </template>
            </el-image>
          </el-col>

          <!-- 右侧：信息 -->
          <el-col :span="16">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="分类">
                {{ currentItem.category || '未分类' }}
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag v-if="currentItem.is_completed" type="success">完结</el-tag>
                <el-tag v-else type="warning">更新中</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="类型">
                <el-tag v-if="currentItem.media_type === 'movie'">电影</el-tag>
                <el-tag v-else-if="currentItem.media_type === 'tv'">电视剧</el-tag>
                <el-tag v-else type="info">未知</el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <el-divider content-position="left">简介</el-divider>
            <p style="line-height: 1.8; color: #606266;">
              {{ currentItem.overview || '暂无简介' }}
            </p>

            <el-divider content-position="left">映射名称</el-divider>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="夸克">
                {{ currentItem.quark_name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="百度">
                {{ currentItem.baidu_name || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="迅雷">
                {{ currentItem.xunlei_name || '-' }}
              </el-descriptions-item>
            </el-descriptions>

            <el-divider content-position="left">分享链接</el-divider>
            <div class="share-links">
              <div v-if="currentItem.quark_link" class="link-item">
                <span class="link-label">夸克：</span>
                <el-input :value="currentItem.quark_link" readonly size="small">
                  <template #append>
                    <el-button @click="copyLink(currentItem.quark_link)">复制</el-button>
                  </template>
                </el-input>
              </div>
              <div v-if="currentItem.baidu_link" class="link-item">
                <span class="link-label">百度：</span>
                <el-input :value="currentItem.baidu_link" readonly size="small">
                  <template #append>
                    <el-button @click="copyLink(currentItem.baidu_link)">复制</el-button>
                  </template>
                </el-input>
              </div>
              <div v-if="currentItem.xunlei_link" class="link-item">
                <span class="link-label">迅雷：</span>
                <el-input :value="currentItem.xunlei_link" readonly size="small">
                  <template #append>
                    <el-button @click="copyLink(currentItem.xunlei_link)">复制</el-button>
                  </template>
                </el-input>
              </div>
              <el-empty v-if="!currentItem.quark_link && !currentItem.baidu_link && !currentItem.xunlei_link" 
                description="暂无分享链接" />
            </div>

            <el-divider />
            
            <el-space>
              <el-button type="primary" @click="editItem(currentItem)">编辑映射</el-button>
              <el-button v-if="currentItem.tmdb_id" @click="viewOnTmdb(currentItem.tmdb_id, currentItem.media_type)">
                查看 TMDb
              </el-button>
              <el-button type="success" @click="createXianyuProduct(currentItem)">
                🐟 创建闲鱼商品
              </el-button>
              <el-button type="danger" @click="deleteItem(currentItem)">删除</el-button>
            </el-space>
          </el-col>
        </el-row>
      </div>
    </el-drawer>

    <!-- 编辑对话框（保留原有功能） -->
    <el-dialog v-model="editVisible" title="编辑映射" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="原始名称">
          <el-input v-model="editForm.original_name" disabled />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="editForm.category" placeholder="如：电影/国产电影" />
        </el-form-item>
        <el-form-item label="夸克名称">
          <el-input v-model="editForm.quark_name" />
        </el-form-item>
        <el-form-item label="百度名称">
          <el-input v-model="editForm.baidu_name" />
        </el-form-item>
        <el-form-item label="迅雷名称">
          <el-input v-model="editForm.xunlei_name" />
        </el-form-item>
        <el-form-item label="完结状态">
          <el-switch v-model="editForm.is_completed" active-text="完结" inactive-text="更新中" />
        </el-form-item>
        <el-form-item label="夸克链接">
          <el-input v-model="editForm.quark_link" placeholder="https://pan.quark.cn/s/xxx" />
        </el-form-item>
        <el-form-item label="百度链接">
          <el-input v-model="editForm.baidu_link" placeholder="https://pan.baidu.com/s/xxx" />
        </el-form-item>
        <el-form-item label="迅雷链接">
          <el-input v-model="editForm.xunlei_link" placeholder="https://pan.xunlei.com/s/xxx" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.note" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- TMDb 搜索对话框 -->
    <el-dialog
      v-model="tmdbDialogVisible"
      title="🎬 TMDb 影视搜索"
      width="90%"
      top="5vh"
    >
      <div class="tmdb-search-content">
        <!-- 搜索区域 -->
        <div class="search-area" style="margin-bottom: 20px;">
          <el-input
            v-model="tmdbSearchQuery"
            placeholder="输入影视作品名称搜索..."
            size="large"
            clearable
            @keyup.enter="handleTmdbSearch"
          >
            <template #prepend>
              <el-select v-model="tmdbMediaType" placeholder="类型" style="width: 100px">
                <el-option label="全部" value="multi" />
                <el-option label="电影" value="movie" />
                <el-option label="电视剧" value="tv" />
              </el-select>
            </template>
            <template #append>
              <el-button :icon="Search" @click="handleTmdbSearch" :loading="tmdbSearching">
                搜索
              </el-button>
            </template>
          </el-input>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
            <el-tag type="info" size="small">根据 cat.yaml 自动分类</el-tag>
            <el-button 
              type="warning" 
              size="small" 
              :loading="checkingUpdates"
              @click="handleCheckUpdates"
            >
              🔔 检查剧集更新
            </el-button>
          </div>
        </div>

        <!-- 搜索结果 -->
        <div v-if="tmdbSearchResults.length > 0" class="results-section">
          <h3>搜索结果 ({{ tmdbSearchResults.length }} 个)</h3>
          <div class="results-grid">
            <div
              v-for="item in tmdbSearchResults"
              :key="item.id"
              class="result-item"
              @click="showTmdbDetails(item)"
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
        </div>
      </div>
    </el-dialog>

    <!-- TMDb 详情对话框 -->
    <el-dialog
      v-model="tmdbDetailsVisible"
      :title="tmdbCurrentDetails?.title"
      width="90%"
      top="5vh"
      class="details-dialog"
    >
      <div v-if="tmdbCurrentDetails" class="details-content">
        <el-row :gutter="20">
          <!-- 左侧：海报和基本信息 -->
          <el-col :span="8">
            <el-image
              :src="tmdbCurrentDetails.main_poster"
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
                {{ tmdbCurrentDetails.title }} ({{ tmdbCurrentDetails.year }})
              </el-descriptions-item>
              <el-descriptions-item label="二级分类">
                <el-tag v-if="tmdbCurrentDetails.category" type="success">
                  {{ tmdbCurrentDetails.category }}
                </el-tag>
                <el-tag v-else type="info">未分类</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="类型">
                {{ tmdbCurrentDetails.genres.join(', ') }}
              </el-descriptions-item>
              <el-descriptions-item label="国家">
                {{ tmdbCurrentDetails.origin_country.join(', ') }}
              </el-descriptions-item>
              <el-descriptions-item label="评分">
                <el-rate
                  v-model="tmdbCurrentDetails.vote_average"
                  disabled
                  show-score
                  text-color="#ff9900"
                  score-template="{value}/10"
                  :max="10"
                />
              </el-descriptions-item>
              <el-descriptions-item v-if="tmdbCurrentDetails.runtime" label="时长">
                {{ tmdbCurrentDetails.runtime }} 分钟
              </el-descriptions-item>
              <el-descriptions-item v-if="tmdbCurrentDetails.number_of_seasons" label="季数">
                {{ tmdbCurrentDetails.number_of_seasons }} 季
              </el-descriptions-item>
              <el-descriptions-item v-if="tmdbCurrentDetails.number_of_episodes" label="集数">
                {{ tmdbCurrentDetails.number_of_episodes }} 集
              </el-descriptions-item>
            </el-descriptions>
          </el-col>

          <!-- 右侧：简介和图片 -->
          <el-col :span="16">
            <div class="overview-section">
              <h3>简介</h3>
              <p>{{ tmdbCurrentDetails.overview || '暂无简介' }}</p>
            </div>

            <el-divider />

            <!-- 主图链接 -->
            <div class="image-urls">
              <h3>🖼️ 主图链接</h3>
              <el-input
                :value="tmdbCurrentDetails.main_poster"
                readonly
                class="url-input"
              >
                <template #append>
                  <el-button @click="copyUrl(tmdbCurrentDetails.main_poster)">
                    复制
                  </el-button>
                </template>
              </el-input>
            </div>

            <el-divider />

            <!-- 海报图片 -->
            <div v-if="tmdbCurrentDetails.posters.length > 0" class="gallery">
              <h3>📸 海报 ({{ tmdbCurrentDetails.posters.length }} 张)</h3>
              <div class="gallery-grid">
                <div v-for="(poster, index) in tmdbCurrentDetails.posters" :key="index" class="gallery-item">
                  <el-image
                    :src="poster"
                    fit="cover"
                    class="gallery-image"
                    :preview-src-list="tmdbCurrentDetails.posters"
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
            <div v-if="tmdbCurrentDetails.backdrops.length > 0" class="gallery">
              <h3>🎬 剧照 ({{ tmdbCurrentDetails.backdrops.length }} 张)</h3>
              <div class="gallery-grid">
                <div v-for="(backdrop, index) in tmdbCurrentDetails.backdrops" :key="index" class="gallery-item">
                  <el-image
                    :src="backdrop"
                    fit="cover"
                    class="gallery-image"
                    :preview-src-list="tmdbCurrentDetails.backdrops"
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
          <el-button @click="tmdbDetailsVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 创建闲鱼商品对话框 -->
    <el-dialog v-model="xianyuVisible" title="🐟 创建闲鱼商品" width="600px">
      <el-form :model="xianyuForm" label-width="100px" v-if="xianyuForm.media">
        <el-alert
          title="一键创建"
          type="success"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <p>✨ 将使用 TMDB 高清海报作为商品图</p>
          <p>🤖 点击"创建商品"后自动完成：创建 → 上架到闲鱼</p>
        </el-alert>

        <el-form-item label="媒体名称">
          <el-input :value="xianyuForm.media.original_name" disabled />
        </el-form-item>

        <el-form-item label="原始海报">
          <el-image
            :src="getPosterUrl(xianyuForm.media.poster_url)"
            style="width: 120px; height: 180px; border-radius: 4px;"
            fit="cover"
          >
            <template #error>
              <div style="width: 120px; height: 180px; background: #f5f7fa; display: flex; align-items: center; justify-content: center;">
                <el-icon><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          <div style="margin-top: 8px; color: #909399; font-size: 13px;">
            将直接使用此海报作为商品图
          </div>
        </el-form-item>

        <el-form-item label="商品标题">
          <el-input v-model="xianyuForm.title" placeholder="留空使用默认模板" />
        </el-form-item>

        <el-form-item label="商品描述">
          <el-input
            v-model="xianyuForm.content"
            type="textarea"
            :rows="4"
            placeholder="留空使用媒体简介"
          />
        </el-form-item>

        <el-form-item label="价格（元）">
          <el-input-number v-model="xianyuForm.price" :min="0.01" :step="0.1" :precision="2" />
        </el-form-item>

        <el-form-item label="运费（元）">
          <el-input-number v-model="xianyuForm.expressFee" :min="0" :step="1" :precision="2" />
        </el-form-item>

        <el-form-item label="库存">
          <el-input-number v-model="xianyuForm.stock" :min="1" :step="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="xianyuVisible = false">取消</el-button>
        <el-button type="primary" @click="submitXianyuProduct" :loading="xianyuCreating">
          {{ xianyuCreating ? '创建中...' : '创建商品' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Picture, Link, Collection, Film, VideoPlay, CircleCheck } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()

const mediaList = ref([])
const total = ref(0)
const loading = ref(false)
const searchText = ref('')
const filterType = ref('')
const filterCompleted = ref('')
const filterCategory = ref('')
const currentPage = ref(1)
const pageSize = ref(24)

// 分类列表
const categories = ref([])
const groupedCategories = ref({})

const detailsVisible = ref(false)
const currentItem = ref(null)

const editVisible = ref(false)
const saving = ref(false)
const editForm = ref({})

const xianyuVisible = ref(false)
const xianyuCreating = ref(false)
const xianyuForm = ref({
  media: null,
  title: '',
  content: '',
  price: 0.1,
  expressFee: 0,
  stock: 100
})

// TMDb 搜索相关
const tmdbDialogVisible = ref(false)
const tmdbSearchQuery = ref('')
const tmdbMediaType = ref('multi')
const tmdbSearching = ref(false)
const tmdbSearchResults = ref([])

const tmdbDetailsVisible = ref(false)
const tmdbCurrentDetails = ref(null)
const creatingMapping = ref(false)
const checkingUpdates = ref(false)
const autoFilling = ref(false)

// 统计
const stats = computed(() => {
  return {
    movies: mediaList.value.filter(m => m.media_type === 'movie').length,
    tvs: mediaList.value.filter(m => m.media_type === 'tv').length,
    completed: mediaList.value.filter(m => m.is_completed).length
  }
})

// 加载媒体列表
const loadMediaList = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (searchText.value) {
      params.search = searchText.value
    }
    
    // 类型筛选
    if (filterType.value) {
      params.media_type = filterType.value
    }
    
    // 完结状态筛选
    if (filterCompleted.value) {
      if (filterCompleted.value === 'completed') {
        params.is_completed = true
      } else if (filterCompleted.value === 'ongoing') {
        params.is_completed = false
      }
    }
    
    // 分类筛选
    if (filterCategory.value) {
      params.category = filterCategory.value
    }
    
    const res = await api.getMappings(params)
    if (res.data.success) {
      mediaList.value = res.data.data
      total.value = res.data.total
    }
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 加载分类列表
const loadCategories = async () => {
  try {
    const res = await api.get('/categories')
    if (res.data.success) {
      categories.value = res.data.categories || []
      groupedCategories.value = res.data.grouped || {}
    }
  } catch (error) {
    console.error('加载分类失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  loadMediaList()
}

// 显示 TMDb 搜索对话框
const showTmdbDialog = () => {
  tmdbDialogVisible.value = true
  tmdbSearchQuery.value = ''
  tmdbSearchResults.value = []
}

// TMDb 搜索
const handleTmdbSearch = async () => {
  if (!tmdbSearchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  tmdbSearching.value = true
  try {
    const res = await api.searchTmdb({
      query: tmdbSearchQuery.value,
      media_type: tmdbMediaType.value
    })

    if (res.data.success) {
      tmdbSearchResults.value = res.data.data
      if (tmdbSearchResults.value.length === 0) {
        ElMessage.info('未找到相关结果')
      }
    } else {
      ElMessage.error('搜索失败')
    }
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败：' + (error.message || '未知错误'))
  } finally {
    tmdbSearching.value = false
  }
}

// 显示 TMDb 详情
const showTmdbDetails = async (item) => {
  tmdbDetailsVisible.value = true
  tmdbCurrentDetails.value = null

  try {
    const res = await api.getTmdbDetails(item.media_type, item.id)
    if (res.data.success) {
      tmdbCurrentDetails.value = res.data.data
    } else {
      ElMessage.error('获取详情失败')
    }
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

// 创建映射
const handleCreateMapping = async () => {
  if (!tmdbCurrentDetails.value) {
    return
  }

  const { id, title, year, category, media_type, main_poster, overview } = tmdbCurrentDetails.value

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
      
      // 关闭对话框并刷新列表
      tmdbDetailsVisible.value = false
      tmdbDialogVisible.value = false
      loadMediaList()
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

// 复制 URL
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

// 补齐TMDB信息
const handleAutoFillTmdb = async () => {
  try {
    await ElMessageBox.confirm(
      '将自动补全所有缺失的TMDB信息（分类、海报、简介等），是否继续？',
      '确认补齐',
      {
        confirmButtonText: '开始补齐',
        cancelButtonText: '取消',
        type: 'info',
      }
    )
    
    autoFilling.value = true
    ElMessage.info('开始补齐TMDB信息，请稍候...')
    
    const res = await api.post('/tmdb/auto-fill', {}, {
      params: { only_missing: true }
    })
    
    if (res.data.success) {
      ElMessage.success({
        message: `✅ 补齐完成！\n处理: ${res.data.total} 条\n更新: ${res.data.updated} 条\n失败: ${res.data.failed || 0} 条`,
        duration: 5000,
        showClose: true,
        dangerouslyUseHTMLString: true
      })
      
      // 刷新列表
      loadMediaList()
    } else {
      ElMessage.error(res.data.message || '补齐失败')
    }
  } catch (error) {
    if (error === 'cancel') {
      ElMessage.info('已取消')
    } else {
      console.error('补齐失败:', error)
      ElMessage.error('补齐失败：' + (error.response?.data?.detail || error.message || '未知错误'))
    }
  } finally {
    autoFilling.value = false
  }
}

// 显示详情
const showDetails = (item) => {
  currentItem.value = item
  detailsVisible.value = true
}

// 查看详情
const viewDetails = (item) => {
  showDetails(item)
}

// 编辑
const editItem = (item) => {
  detailsVisible.value = false
  editForm.value = { ...item }
  editVisible.value = true
}

const editMapping = (item) => {
  editItem(item)
}

// 保存编辑
const saveEdit = async () => {
  saving.value = true
  try {
    const res = await api.updateMapping(editForm.value.id, {
      category: editForm.value.category,
      quark_name: editForm.value.quark_name,
      baidu_name: editForm.value.baidu_name,
      xunlei_name: editForm.value.xunlei_name,
      is_completed: editForm.value.is_completed,
      note: editForm.value.note,
      quark_link: editForm.value.quark_link,
      baidu_link: editForm.value.baidu_link,
      xunlei_link: editForm.value.xunlei_link
    })
    
    if (res.data.success) {
      ElMessage.success('保存成功')
      editVisible.value = false
      loadMediaList()
    } else {
      ElMessage.error(res.data.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 删除
const deleteItem = async (item) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${item.original_name}」吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    const res = await api.deleteMapping(item.id)
    if (res.data.success) {
      ElMessage.success('删除成功')
      detailsVisible.value = false
      loadMediaList()
    } else {
      ElMessage.error(res.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 查看 TMDb
const viewOnTmdb = (tmdbId, mediaType) => {
  // 可以跳转到 TMDb 页面，或者打开新标签
  window.open(`https://www.themoviedb.org/${mediaType}/${tmdbId}`, '_blank')
}

// 复制链接
const copyLink = (link) => {
  navigator.clipboard.writeText(link).then(() => {
    ElMessage.success('链接已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

// 获取海报 URL（使用代理缓存）
const getPosterUrl = (posterUrl) => {
  if (!posterUrl) {
    return '/placeholder.jpg'
  }
  
  // 如果已经是代理地址，直接返回
  if (posterUrl.startsWith('/api/')) {
    return posterUrl
  }
  
  // 使用后端代理（会自动缓存）
  return `/api/media/poster?url=${encodeURIComponent(posterUrl)}`
}

// 创建闲鱼商品（跳转到自动化工作流页面）
const createXianyuProduct = (item) => {
  if (!item.poster_url) {
    ElMessage.warning('该媒体没有海报图片，无法创建商品')
    return
  }
  
  // 关闭详情抽屉
  detailsVisible.value = false
  
  // 跳转到自动化工作流页面，带上媒体ID
  router.push({
    path: '/xianyu/auto-workflow',
    query: { media_id: item.id }
  })
}

// 提交创建闲鱼商品（后端自动生成海报）
const submitXianyuProduct = async () => {
  if (!xianyuForm.value.media.poster_url) {
    ElMessage.error('该媒体没有海报图片')
    return
  }
  
  xianyuCreating.value = true
  try {
    const res = await api.post('/xianyu/product/create-from-media', {
      media_id: xianyuForm.value.media.id,
      title: xianyuForm.value.title || null,
      content: xianyuForm.value.content || null,
      price: xianyuForm.value.price,
      express_fee: xianyuForm.value.expressFee,
      stock: xianyuForm.value.stock,
      image_urls: []  // 空数组，后端会自动生成
    })
    
    if (res.data.success) {
      ElMessage.success(res.data.message || '商品创建成功')
      xianyuVisible.value = false
    } else {
      ElMessage.error(res.data.message || '创建失败')
    }
  } catch (error) {
    console.error('创建闲鱼商品失败:', error)
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    xianyuCreating.value = false
  }
}

onMounted(() => {
  loadCategories()
  loadMediaList()
})
</script>

<style scoped>
.media-library {
  padding: 20px;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  min-height: 400px;
}

.media-card {
  cursor: pointer;
  transition: all 0.3s;
}

.media-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

.poster-wrapper {
  position: relative;
  width: 100%;
  height: 240px;
  overflow: hidden;
  border-radius: 4px;
  margin-bottom: 8px;
}

.poster {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #909399;
  font-size: 40px;
}

.status-badges {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  z-index: 10;
}

.media-info {
  padding: 8px 4px 4px;
}

.title {
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  min-height: 36px;
  color: #303133;
}

.details-content {
  padding: 0 20px;
}

.share-links {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.link-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.link-label {
  min-width: 50px;
  font-weight: 500;
}

/* 统计卡片 */
.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 20px;
  margin-bottom: 20px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-unit {
  font-size: 14px;
  font-weight: normal;
  color: #909399;
  margin-left: 4px;
}

/* TMDb 搜索对话框样式 */
.tmdb-search-content {
  max-height: 70vh;
  overflow-y: auto;
}

.results-section h3 {
  margin-bottom: 16px;
  font-size: 18px;
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

