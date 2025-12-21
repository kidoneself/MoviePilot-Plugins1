import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.MODE === 'production' ? '/api' : '/api',
  timeout: 30000
})

export default {
  // 通用方法
  get(url, config) {
    return api.get(url, config)
  },
  
  post(url, data, config) {
    return api.post(url, data, config)
  },
  
  put(url, data, config) {
    return api.put(url, data, config)
  },
  
  delete(url, config) {
    return api.delete(url, config)
  },

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
  
  resyncToTarget(data) {
    return api.post('/mappings/resync', data)
  },
  
  exportMappings(params) {
    return api.get('/export/mappings', { params, responseType: 'blob' })
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
  },

  // 触发TaoSync
  triggerTaoSync() {
    return api.post('/trigger-taosync')
  },

  // 批量补充模板文件
  batchLinkTemplates() {
    return api.post('/batch-link-templates')
  },

  // 今日同步统计
  getTodaySync() {
    return api.get('/today-sync')
  },

  // 分享链接管理
  updateCookie(panType, cookie) {
    return api.post('/cookie', { pan_type: panType, cookie })
  },

  generateShareLink(panType, originalName) {
    return api.post('/generate-link', { pan_type: panType, original_name: originalName })
  },

  // 获取所有分享链接
  getShareLinks() {
    return api.get('/share-links')
  },

  // 获取今日更新分享文案
  getTodayShareText() {
    return api.get('/today-share-text')
  },

  // PanSou 搜索
  pansouSearch(keyword) {
    return api.post('/pansou-search', { keyword })
  }
}
