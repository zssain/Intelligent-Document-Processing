import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { auth } from '@/shared/lib/firebase'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Create shared Axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to attach Firebase ID token
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const currentUser = auth.currentUser
      if (currentUser) {
        const idToken = await currentUser.getIdToken()
        config.headers.Authorization = `Bearer ${idToken}`
      }
    } catch (error) {
      console.error('Error attaching auth token:', error)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling auth errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Optionally trigger sign out or token refresh
      console.error('Unauthorized request - token may be invalid')
    }
    return Promise.reject(error)
  }
)

export default api
