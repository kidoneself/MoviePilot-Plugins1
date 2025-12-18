import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.MODE === 'production' ? '/api' : '/api',
  timeout: 30000
})

export default {
  // 统计信息
  getStats() {
    return api.get('/stats')
  },

  // 映射管理
  getMappings(params) {
    return api.get('/mappings', { params })
  },
  
  createMapping(data) {
    return api.post('/mappings', data)
  },
  
  updateMapping(id, data) {
    return api.put(`/mappings/${id}`, data)
  },
  
  deleteMapping(id) {
    return api.delete(`/mappings/${id}`)
  },
  
  exportMappings(params) {
    return api.get('/export/mappings', { params, responseType: 'blob' })
  },

  // 网盘链接生成
  generateLinks(data) {
    return api.post('/cloudpan/generate-links', data)
  },
  
  // 上传网盘Cookie
  uploadCookie(panType, cookieData) {
    return api.post('/cloudpan/upload-cookie', null, {
      params: { pan_type: panType },
      data: cookieData
    })
  },

  // 链接记录
  getRecords(params) {
    return api.get('/records', { params })
  },
  
  deleteRecordsByShow(showName) {
    return api.delete('/records/by-show', { params: { show_name: showName } })
  },
  
  exportRecords(params) {
    return api.get('/export/records', { params, responseType: 'blob' })
  },

  // 目录树
  getTree(params) {
    return api.get('/tree', { params })
  },

  // 配置
  getConfig() {
    return api.get('/config')
  },
  
  updateConfig(data) {
    return api.post('/config', data)
  },

  // 全量同步
  syncAll() {
    return api.post('/sync-all')
  }
}
