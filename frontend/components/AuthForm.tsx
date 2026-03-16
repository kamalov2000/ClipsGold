'use client'

import { useState } from 'react'
import axios from 'axios'
import { saveToken, API_BASE } from '@/lib/api'

interface AuthFormProps {
  onAuthSuccess: () => void
}

export default function AuthForm({ onAuthSuccess }: AuthFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const resp = await axios.post(`${API_BASE}/auth/simple-login`, { email, password })
      saveToken(resp.data.access_token)
      onAuthSuccess()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto bg-white/10 backdrop-blur-sm rounded-2xl p-8 shadow-2xl border border-white/20">
      <h2 className="text-2xl font-bold text-white text-center mb-6">Sign In</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-300 mb-1">Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
        </div>

        {error && (
          <p className="text-red-400 text-sm bg-red-900/30 rounded-lg px-3 py-2">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-semibold transition-colors"
        >
          {loading ? 'Please wait…' : 'Sign In'}
        </button>
      </form>
    </div>
  )
}
