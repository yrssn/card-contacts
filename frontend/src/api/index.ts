import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

export const http = axios.create({ baseURL: '/', timeout: 180000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: any) => d.msg).join('；') : err.message
    if (status === 401) {
      localStorage.removeItem('token')
      router.replace('/login')
    }
    ElMessage.error(msg || '请求失败')
    return Promise.reject(err)
  },
)

export interface User {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
}

export interface VisionModel {
  id: number
  name: string
  provider: string
  base_url: string
  api_key_masked: string
  model: string
  max_tokens: number
  temperature: number
  is_default: boolean
  vision_verified: boolean
  verify_message: string
}

export interface Category {
  id: number
  key: string
  label: string
  sheet_name: string
  description: string
  sort_order: number
  is_active: boolean
}

export interface KdocsConfig {
  file_id: string
  script_id: string
  token_masked: string
  doc_url: string
  configured: boolean
}

export interface SearchConfig {
  provider: string
  api_key_masked: string
  enabled: boolean
  max_results: number
  configured: boolean
  llm_base_url: string
  llm_api_key_masked: string
  llm_model: string
  llm_max_tokens: number
  llm_configured: boolean
}

export interface EnrichOut {
  website: string
  businessKeywords: string
  productServiceType: string
  summary: string
  sources: { title: string; url: string }[]
}

export interface Card {
  language: string
  name: string
  sex: string
  note: string
  department: string
  businessKeywords: string
  productServiceType: string
  company: string
  website: string
  email: string
  phone: string
}

export interface RecognizeOut {
  card: Card
  front_image: string
  back_image: string
  front_image_url: string
  back_image_url: string
  model_used: string
  company_summary: string
  search_error: string
  sources: { title: string; url: string }[]
}

export interface CardRecord {
  id: number
  importer: string
  category_key: string
  front_image_url: string
  back_image_url: string
  card: Card
  kdocs_row: number
  duplicate: boolean
  status: string
  error: string
  warning: string
  created_at: string
}

export const api = {
  login: (username: string, password: string) =>
    http.post<any, { access_token: string }>('/api/auth/login-json', { username, password }),
  me: () => http.get<any, User>('/api/auth/me'),
  changePassword: (old_password: string, new_password: string) =>
    http.post('/api/auth/change-password', { old_password, new_password }),

  users: () => http.get<any, User[]>('/api/users'),
  createUser: (data: Partial<User> & { password: string }) => http.post<any, User>('/api/users', data),
  updateUser: (id: number, data: Partial<User> & { password?: string }) => http.patch<any, User>(`/api/users/${id}`, data),
  deleteUser: (id: number) => http.delete(`/api/users/${id}`),

  models: () => http.get<any, VisionModel[]>('/api/vision-models'),
  createModel: (data: any) => http.post<any, VisionModel>('/api/vision-models', data),
  updateModel: (id: number, data: any) => http.put<any, VisionModel>(`/api/vision-models/${id}`, data),
  verifyModel: (id: number) => http.post<any, VisionModel>(`/api/vision-models/${id}/verify`),
  defaultModel: (id: number) => http.post<any, VisionModel>(`/api/vision-models/${id}/default`),
  deleteModel: (id: number) => http.delete(`/api/vision-models/${id}`),

  categories: (all = false) => http.get<any, Category[]>('/api/categories', { params: { all } }),
  createCategory: (data: any) => http.post<any, Category>('/api/categories', data),
  updateCategory: (id: number, data: Partial<Category>) => http.patch<any, Category>(`/api/categories/${id}`, data),
  ensureSheet: (id: number) => http.post(`/api/categories/${id}/ensure-sheet`),
  deleteCategory: (id: number) => http.delete(`/api/categories/${id}`),

  kdocsConfig: () => http.get<any, KdocsConfig>('/api/kdocs/config'),
  saveKdocsConfig: (data: any) => http.put<any, KdocsConfig>('/api/kdocs/config', data),
  testKdocs: () => http.post<any, { ok: boolean; version: string; sheets: string[] }>('/api/kdocs/test'),

  searchConfig: () => http.get<any, SearchConfig>('/api/search/config'),
  saveSearchConfig: (data: any) => http.put<any, SearchConfig>('/api/search/config', data),
  testSearch: (data: { company: string; website?: string; language?: string }) => http.post<any, EnrichOut>('/api/search/test', data),
  enrichCompany: (data: { company: string; website?: string; language?: string }) => http.post<any, EnrichOut>('/api/search/enrich', data),

  recognize: (front: File, back?: File | null) => {
    const fd = new FormData()
    fd.append('front', front)
    if (back) fd.append('back', back)
    return http.post<any, RecognizeOut>('/api/cards/recognize', fd)
  },
  confirm: (data: { category_key: string; card: Card; front_image: string; back_image: string }) =>
    http.post<any, CardRecord>('/api/cards/confirm', data),
  retry: (id: number) => http.post<any, CardRecord>(`/api/cards/${id}/retry`),
  records: (mine = false) => http.get<any, CardRecord[]>('/api/cards/records', { params: { mine } }),
}
