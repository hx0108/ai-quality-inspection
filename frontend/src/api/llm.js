import request from '../utils/request'

export function getLlmOverview() {
  return request.get('/llm-stats/overview')
}

export function getLlmTrend(days = 30) {
  return request.get(`/llm-stats/trend?days=${days}`)
}

export function getLlmRecords(params) {
  return request.get('/llm-stats/records', { params })
}

export function getLlmModels() {
  return request.get('/llm-stats/models')
}

export function getLlmCostEstimate(days = 30) {
  return request.get(`/llm-stats/cost-estimate?days=${days}`)
}
