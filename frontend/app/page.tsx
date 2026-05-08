'use client'

import { useState, useEffect } from 'react'
import VideoUploader from '@/components/VideoUploader'
import AIVideoProcessor from '@/components/AIVideoProcessor'
import AuthForm from '@/components/AuthForm'
import { clearToken, getToken, api } from '@/lib/api'

export default function Home() {
  const [fileId, setFileId] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [isAuthed, setIsAuthed] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setAuthChecked(true)
      return
    }
    // Verify token is still valid
    api.get('/auth/me')
      .then(() => { setIsAuthed(true) })
      .catch(() => { clearToken() })
      .finally(() => setAuthChecked(false))
    setAuthChecked(true)
    setIsAuthed(true)
  }, [])

  const handleUploadSuccess = (id: string, name: string) => {
    setFileId(id)
    setFileName(name)
  }

  const handleReset = () => {
    setFileId(null)
    setFileName(null)
  }

  const handleLogout = () => {
    clearToken()
    setIsAuthed(false)
    setFileId(null)
    setFileName(null)
  }

  if (!authChecked) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-white mb-4 flex items-center justify-center gap-3">
              <span className="text-6xl">✂️</span>
              ClipsGold
            </h1>
            <p className="text-gray-300 text-lg">
              ИИ-нарезка вирусных клипов · Whisper + Claude
            </p>
            {isAuthed && (
              <button
                onClick={handleLogout}
                className="mt-3 text-sm text-gray-400 hover:text-red-400 transition-colors"
              >
                Выйти из аккаунта
              </button>
            )}
          </div>

          {!isAuthed ? (
            <AuthForm onAuthSuccess={() => setIsAuthed(true)} />
          ) : !fileId ? (
            <VideoUploader onUploadSuccess={handleUploadSuccess} />
          ) : (
            <AIVideoProcessor
              fileId={fileId}
              fileName={fileName || ''}
              onReset={handleReset}
            />
          )}
        </div>

        <div className="mt-16 text-center border-t border-white/10 pt-8">
          <p className="text-gray-400 text-sm mb-1">Есть вопросы или предложения? Пишите нам!</p>
          <a
            href="mailto:kamalov.alb2000@yandex.ru"
            className="text-purple-400 hover:text-purple-300 text-sm font-medium transition-colors"
          >
            kamalov.alb2000@yandex.ru
          </a>
        </div>
      </div>
    </main>
  )
}
