import axios from 'axios'
import { showToast } from 'vant'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response) {
      const { status, data } = error.response
      const detail = data?.detail || '请求失败'

      if (status === 401) {
        const hasToken = !!localStorage.getItem('token')
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        // Only redirect to login if the user had a token — no-token 401 means
        // unauthenticated request on a public page (login/register), skip redirect
        if (hasToken) {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }

      // 429 速率限制 - 明确提示
      if (status === 429) {
        showToast(detail || '操作过于频繁，请稍后再试')
        error._toasted = true
        return Promise.reject(error)
      }

      // 413 请求体过大（通常是照片上传超限）
      if (status === 413) {
        showToast('上传数据过大，请减少照片数量或重试')
        error._toasted = true
        return Promise.reject(error)
      }

      // 500/502/503 服务器错误
      if (status >= 500) {
        showToast('服务器异常，请稍后重试')
        error._toasted = true
        return Promise.reject(error)
      }

      // 400/422 验证错误 - 显示后端返回的详情
      if (status === 400 || status === 422) {
        if (detail && detail !== '请求失败') {
          showToast(detail)
          error._toasted = true
        }
        return Promise.reject(error)
      }

      // 其他错误标记，由各组件自行处理
      error.response._detail = detail
    } else {
      // 网络错误（无响应）
      error._networkError = true
      showToast('网络连接失败，请检查网络')
      error._toasted = true
    }
    return Promise.reject(error)
  }
)

export default request
