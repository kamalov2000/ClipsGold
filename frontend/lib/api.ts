/**
 * Centralised axios instance for ClipsGold API.
 * Injects Bearer token on every request and auto-refreshes on 401.
 */
import axios from 'axios'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export const api = axios.create({ baseURL: API_BASE })

// ── SSR-safe browser API helpers ──────────────────────────────────────────

function ls(key: string): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(key)
}

function lsSet(key: string, value: string) {
  if (typeof window === 'undefined') return
  localStorage.setItem(key, value)
}

function lsRemove(key: string) {
  if (typeof window === 'undefined') return
  localStorage.removeItem(key)
}

function redirect(path: string) {
  if (typeof window === 'undefined') return
  window.location.href = path
}

// ── Token helpers ──────────────────────────────────────────────────────────

export function saveToken(accessToken: string, refreshToken?: string) {
  lsSet('cg_access_token', accessToken)
  if (refreshToken) lsSet('cg_refresh_token', refreshToken)
}

export function clearToken() {
  lsRemove('cg_access_token')
  lsRemove('cg_refresh_token')
}

export function getToken(): string | null {
  return ls('cg_access_token')
}

// ── Request interceptor: inject auth header ────────────────────────────────

api.interceptors.request.use((config) => {
  const token = ls('cg_access_token')
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

    // Don't redirect for auth-check endpoints — 401 is expected for guests
    const url = original?.url || ''
    if (url.includes('/auth/me') || url.includes('/auth/refresh')) {
      return Promise.reject(error)
    }

    const refreshToken = ls('cg_refresh_token')
    if (!refreshToken) {
      clearToken()
      redirect('/')
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
      redirect('/')
      return Promise.reject(error)
    } finally {
      _refreshing = false
    }
  }
)
