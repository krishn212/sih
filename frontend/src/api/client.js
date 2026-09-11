import axios from 'axios'

const defaultHost = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost'
export const API_BASE = import.meta.env.VITE_API_URL || `http://${defaultHost}:8000`

const client = axios.create({ baseURL: API_BASE })

// Attach JWT token to every request automatically
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client
