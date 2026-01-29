/**
 * API客户端
 * 封装所有与后端API的交互
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

/**
 * 获取所有可用日期
 */
export const getDates = () => {
  return apiClient.get('/api/dates')
}

/**
 * 获取论文列表
 * @param {Object} params - 查询参数
 * @param {string} params.date - 日期 (YYYY-MM-DD)
 * @param {string} params.category - 分类
 * @param {string} params.keyword - 关键词
 * @param {string} params.author - 作者
 * @param {number} params.limit - 返回数量限制
 * @param {number} params.offset - 偏移量
 */
export const getPapers = (params = {}) => {
  return apiClient.get('/api/papers', { params })
}

/**
 * 获取所有日期的论文列表
 * @param {Object} params - 查询参数
 */
export const getAllPapers = (params = {}) => {
  return apiClient.get('/api/papers/all', { params })
}

/**
 * 获取单篇论文详情
 * @param {string} paperId - 论文ID (YYYY-MM-DD_Title)
 */
export const getPaperDetail = (paperId) => {
  return apiClient.get(`/api/paper/${paperId}`)
}

/**
 * 获取所有分类
 */
export const getCategories = () => {
  return apiClient.get('/api/categories')
}

/**
 * 获取统计数据
 */
export const getStats = () => {
  return apiClient.get('/api/stats')
}

/**
 * 获取每日统计数据
 */
export const getDailyStats = () => {
  return apiClient.get('/api/stats/daily')
}

// 导出API base URL，供其他模块使用
export { API_BASE_URL }

export default apiClient
