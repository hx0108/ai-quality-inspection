import request from '../utils/request'

export function getAiMetricsOverview() {
  return request.get('/ai-metrics/overview').catch(() => ({}))
}

export function getAiMetricsTrend(days = 30) {
  return request.get(`/ai-metrics/trend?days=${days}`).catch(() => ({ trend: [] }))
}

export function getModuleStats() {
  return request.get('/ai-metrics/module-stats').catch(() => ({ modules: [] }))
}

export function getConfidenceCalibration() {
  return request.get('/ai-metrics/confidence-calibration').catch(() => ({ data: [] }))
}

export function getBiasAndEdges() {
  return request.get('/ai-metrics/bias-and-edges').catch(() => ({ data: [] }))
}

export function getDiagnosis() {
  return request.get('/ai-metrics/diagnosis').catch(() => ({ items: [] }))
}

export function runDiagnosis(days = 30) {
  return request.post(`/ai-metrics/diagnosis/run?days=${days}`).catch(() => ({ items: [] }))
}
