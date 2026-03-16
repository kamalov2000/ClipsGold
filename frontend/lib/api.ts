/**
 * Centralised axios instance for ClipsGold API.
 * Reads the JWT access token from localStorage and injects it
 * as a Bearer header on every request automatically.
 */
import axios from 'axios'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export const api = axios.create({ baseURL: API_BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cg_access_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

export function saveToken(token: string) {
  localStorage.setItem('cg_access_token', token)
}

export function clearToken() {
  localStorage.removeItem('cg_access_token')
}

export function getToken(): string | null {
  return localStorage.getItem('cg_access_token')
}
