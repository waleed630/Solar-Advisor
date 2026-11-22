import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('adminToken')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export const errorText = (e) => e.response?.data?.error || e.message

export default api
