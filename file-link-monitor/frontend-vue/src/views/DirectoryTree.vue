<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const sourceTree = ref([])
const targetTree = ref([])
const targets = ref([])
const selectedTarget = ref('')
const sourceLoading = ref(false)
const targetLoading = ref(false)

const loadSourceTree = async () => {
  sourceLoading.value = true
  try {
    const res = await api.getTree({ path: '/path/to/your/source', depth: 2 })
    if (res.data.success) {
      sourceTree.value = convertToTreeData(res.data.data)
    }
  } catch (error) {
    console.error('加载源目录失败:', error)
  } finally {
    sourceLoading.value = false
  }
}

const loadTargets = async () => {
  try {
    const res = await api.getConfig()
    if (res.data.success && res.data.data.targets) {
      targets.value = res.data.data.targets
    }
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const loadTargetTree = async () => {
  if (!selectedTarget.value) return
  
  targetLoading.value = true
  try {
    const res = await api.getTree({ path: selectedTarget.value, depth: 2 })
    if (res.data.success) {
      targetTree.value = convertToTreeData(res.data.data)
    }
  } catch (error) {
    console.error('加载目标目录失败:', error)
  } finally {
    targetLoading.value = false
  }
}

const convertToTreeData = (data) => {
  if (!data || !data.children) return []
  
  const convert = (node) => {
    return {
      label: node.name,
      children: node.children ? node.children.map(convert) : undefined
    }
  }
  
  return data.children.map(convert)
}

onMounted(() => {
  loadSourceTree()
  loadTargets()
})
</script>

<template>
  <div class="directory-tree">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="title">源目录</span>
              <el-button @click="loadSourceTree">刷新</el-button>
            </div>
          </template>
          
          <el-tree
            :data="sourceTree"
            v-loading="sourceLoading"
            default-expand-all
            :props="{ children: 'children', label: 'label' }"
          />
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="title">目标目录</span>
              <el-space>
                <el-select
                  v-model="selectedTarget"
                  placeholder="选择目标目录"
                  @change="loadTargetTree"
                  style="width: 200px"
                >
                  <el-option
                    v-for="(target, index) in targets"
                    :key="index"
                    :label="target.name || target.path"
                    :value="target.path"
                  />
                </el-select>
                <el-button @click="loadTargetTree" :disabled="!selectedTarget">刷新</el-button>
              </el-space>
            </div>
          </template>
          
          <div v-if="!selectedTarget" style="text-align: center; padding: 40px; color: #909399;">
            请选择目标目录
          </div>
          <el-tree
            v-else
            :data="targetTree"
            v-loading="targetLoading"
            default-expand-all
            :props="{ children: 'children', label: 'label' }"
          />
        </el-card>
      </el-col>
    </el-row>
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
</style>
