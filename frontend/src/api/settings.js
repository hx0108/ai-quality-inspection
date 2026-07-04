import request from '../utils/request'

/**
 * 系统设置 API
 */

// 获取 API KEY 列表（脱敏）
export function getApiKeys() {
  return request.get('/admin/api-keys')
}

// 更新 API KEY
export function updateApiKey(data) {
  return request.put('/admin/api-keys', data)
}
