import request from '../utils/request'

// 获取仪表盘数据（端点在 analysis 模块中）
export function getDashboardStats() {
  return request.get('/analysis/dashboard/stats')
}
