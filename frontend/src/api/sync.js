import request from '../utils/request'

/**
 * 批量同步离线数据
 * @param {string} recordId - 检查记录ID
 * @param {FormData} formData - 包含 metadata(JSON) + 照片文件
 * @returns {Promise<{results: Array, synced_count: number, conflict_count: number}>}
 */
export function batchSync(recordId, formData) {
  return request.post(`/records/${recordId}/batch-sync`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000  // 2分钟超时（批量照片上传）
  })
}
