import request from '../utils/request'

// 生成报告
export function generateReport(taskId) {
  return request.post(`/reports/generate/${taskId}`)
}

// 查询报告生成进度
export function getReportStatus(taskId) {
  return request.get(`/reports/status/${taskId}`)
}

// 获取报告详情
export function getReport(taskId) {
  return request.get(`/reports/${taskId}`)
}

// 下载报告（兼容 PC + 移动端）
export async function downloadReportFile(taskId, format = 'word') {
  const token = localStorage.getItem('token')
  const ext = format === 'pdf' ? 'pdf' : 'docx'

  try {
    const resp = await fetch(`/api/v1/reports/${taskId}/download?format=${format}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({ detail: '下载失败' }))
      throw new Error(data.detail || `下载失败 (${resp.status})`)
    }

    const blob = await resp.blob()
    const blobUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `report_${taskId}.${ext}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(blobUrl)
  } catch (e) {
    // 移动端 fallback：直接导航到下载 URL（带 token 参数）
    const fallbackUrl = `/api/v1/reports/${taskId}/download?format=${format}&token=${encodeURIComponent(token)}`
    window.location.href = fallbackUrl
  }
}

// 获取报告列表
export function getReportList(params) {
  return request.get('/reports/list/all', { params })
}

// 获取报告版本列表
export function getReportVersions(taskId) {
  return request.get(`/reports/versions/${taskId}`)
}

// 获取指定版本报告详情
export function getReportById(reportId) {
  return request.get(`/reports/version/${reportId}`)
}
