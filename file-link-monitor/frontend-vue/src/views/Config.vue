<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const loading = ref(false)
const activeNames = ref(['monitor', 'notification', 'taosync'])
const formData = ref({
  // 监控配置
  source_dir: '',
  targets: [],
  enabled: true,
  obfuscate_enabled: true,
  template_files_path: '',
  exclude_patterns: [],
  scan_interval: 60,
  
  // 通知配置
  notification_enabled: false,
  serverchan_url: '',
  serverchan_sendkey: '',
  
  // TaoSync配置
  taosync_enabled: false,
  taosync_url: '',
  taosync_username: '',
  taosync_password: '',
  taosync_job_id: 1,
  taosync_check_interval: 60
})

const loadConfig = async () => {
  loading.value = true
  try {
    const res = await api.getConfig()
    if (res.data.success) {
      formData.value = res.data.data
    }
  } catch (error) {
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

const addTarget = () => {
  formData.value.targets.push({
    path: '',
    name: ''
  })
}

const removeTarget = (index) => {
  formData.value.targets.splice(index, 1)
}

const saveConfig = async () => {
  try {
    const res = await api.updateConfig(formData.value)
    if (res.data.success) {
      ElMessage.success(res.data.message || '保存成功')
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div class="config-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">系统配置</span>
          <el-button type="primary" @click="saveConfig" :loading="loading">保存所有配置</el-button>
        </div>
      </template>

      <el-collapse v-model="activeNames" v-loading="loading">
        <!-- 监控配置 -->
        <el-collapse-item title="监控配置" name="monitor">
          <el-form :model="formData" label-width="140px">
            <el-form-item label="启用监控">
              <el-switch v-model="formData.enabled" />
            </el-form-item>
            
            <el-form-item label="源目录">
              <el-input v-model="formData.source_dir" placeholder="请输入源目录路径" />
            </el-form-item>
            
            <el-form-item label="目标目录">
              <div v-for="(target, index) in formData.targets" :key="index" class="target-item">
                <div class="target-header">
                  <span class="target-label">目标 {{ index + 1 }}</span>
                  <el-button type="danger" size="small" @click="removeTarget(index)">删除</el-button>
                </div>
                <el-input v-model="target.name" placeholder="名称，如：阿里云盘" style="margin-bottom: 8px;" />
                <el-input v-model="target.path" placeholder="路径，如：/media/aliyun" />
              </div>
              <el-button type="primary" plain @click="addTarget" style="width: 100%; margin-top: 10px;">
                添加目标目录
              </el-button>
              <div class="form-tip">可以添加多个目标目录，每个目录可以设置名称</div>
            </el-form-item>
            
            <el-form-item label="启用文件夹名混淆">
              <el-switch v-model="formData.obfuscate_enabled" />
              <div class="form-tip">同音字方案，确定性算法，自动去除年份</div>
            </el-form-item>
            
            <el-form-item label="模板文件目录">
              <el-input v-model="formData.template_files_path" placeholder="可选，如：/path/to/templates" />
              <div class="form-tip">固定文件模板目录，如推广.txt、群二维码.jpg等</div>
            </el-form-item>
            
            <el-form-item label="排除模式">
              <el-select
                v-model="formData.exclude_patterns"
                multiple
                placeholder="请选择或输入排除模式"
                allow-create
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="pattern in formData.exclude_patterns"
                  :key="pattern"
                  :label="pattern"
                  :value="pattern"
                />
              </el-select>
              <div class="form-tip">支持通配符，如：*.tmp、*.part、.DS_Store</div>
            </el-form-item>
          </el-form>
        </el-collapse-item>

        <!-- 通知配置 -->
        <el-collapse-item title="通知配置（Server酱）" name="notification">
          <el-form :model="formData" label-width="140px">
            <el-form-item label="启用通知">
              <el-switch v-model="formData.notification_enabled" />
            </el-form-item>
            
            <el-form-item label="Server酱 URL">
              <el-input v-model="formData.serverchan_url" placeholder="https://xxx.push.ft07.com/send/xxx.send" />
            </el-form-item>
            
            <el-form-item label="SendKey">
              <el-input v-model="formData.serverchan_sendkey" placeholder="sctp..." />
            </el-form-item>
          </el-form>
        </el-collapse-item>

        <!-- TaoSync配置 -->
        <el-collapse-item title="TaoSync 同步配置" name="taosync">
          <el-form :model="formData" label-width="140px">
            <el-form-item label="启用 TaoSync">
              <el-switch v-model="formData.taosync_enabled" />
            </el-form-item>
            
            <el-form-item label="TaoSync URL">
              <el-input v-model="formData.taosync_url" placeholder="http://10.10.10.17:8023" />
            </el-form-item>
            
            <el-form-item label="用户名">
              <el-input v-model="formData.taosync_username" placeholder="admin" />
            </el-form-item>
            
            <el-form-item label="密码">
              <el-input v-model="formData.taosync_password" type="password" placeholder="请输入密码" show-password />
            </el-form-item>
            
            <el-form-item label="任务ID">
              <el-input-number v-model="formData.taosync_job_id" :min="1" />
            </el-form-item>
            
            <el-form-item label="检查间隔">
              <el-input-number v-model="formData.taosync_check_interval" :min="10" :max="3600" />
              <span style="margin-left: 10px; color: #909399;">秒</span>
              <div class="form-tip">当任务执行中时，每隔N秒检查是否空闲并重试</div>
            </el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
      
      <div style="margin-top: 20px; text-align: center;">
        <el-button type="primary" size="large" @click="saveConfig" :loading="loading">
          保存所有配置
        </el-button>
      </div>
    </el-card>
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

.form-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 5px;
}

.target-item {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 12px;
}

.target-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.target-label {
  font-weight: 500;
  color: #606266;
}
</style>
