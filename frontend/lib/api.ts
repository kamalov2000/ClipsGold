/**
 * Centralised axios instance for ClipsGold API.
 * Injects Bearer token on every request and auto-refreshes on 401.
 */
import axios from 'axios'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export const api = axios.create({ baseURL: API_BASE })

// ── Token helpers ──────────────────────────────────────────────────────────

export function saveToken(accessToken: string, refreshToken?: string) {
  localStorage.setItem('cg_access_token', accessToken)
  if (refreshToken) localStorage.setItem('cg_refresh_token', refreshToken)
}

export function clearToken() {
  localStorage.removeItem('cg_access_token')
  localStorage.removeItem('cg_refresh_token')
}

export function getToken(): string | null {
  return localStorage.getItem('cg_access_token')
}

// ── Request interceptor: inject auth header ────────────────────────────────

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cg_access_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: auto-refresh on 401 ─────────────────────────────

let _refreshing = false
let _refreshQueue: Array<(token: string | null) => void> = []

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem('cg_refresh_token')
    if (!refreshToken) {
      clearToken()
      window.location.href = '/'
      return Promise.reject(error)
    }

    if (_refreshing) {
      // Queue requests that arrive while a refresh is in progress
      return new Promise((resolve, reject) => {
        _refreshQueue.push((newToken) => {
          if (newToken) {
            original.headers['Authorization'] = `Bearer ${newToken}`
            resolve(api(original))
          } else {
            reject(error)
          }
        })
      })
    }

    _refreshing = true
    original._retry = true

    try {
      const resp = await axios.post(`${API_BASE}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      const { access_token, refresh_token: newRefresh } = resp.data
      saveToken(access_token, newRefresh)
      original.headers['Authorization'] = `Bearer ${access_token}`
      _refreshQueue.forEach((cb) => cb(access_token))
      _refreshQueue = []
      return api(original)
    } catch {
      clearToken()
      _refreshQueue.forEach((cb) => cb(null))
      _refreshQueue = []
      window.location.href = '/'
      return Promise.reject(error)
    } finally {
      _refreshing = false
    }
  }
)
