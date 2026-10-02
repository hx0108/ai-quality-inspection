import request from '../utils/request'

// 检查标准列表（内置 + 自定义导入）
export function getStandardList() {
  return request.get('/standards/list')
}

// 导入检查标准（Word/Excel，AI 自动识别结构）
// formData: { file, label, scoring_model: 'auto'|'point_cap'|'weighted_5pt' }
export function importStandard(formData) {
  return request.post('/standards/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
}

// 删除自定义标准
export function deleteStandard(standardType) {
  return request.delete(`/standards/${standardType}`)
}
