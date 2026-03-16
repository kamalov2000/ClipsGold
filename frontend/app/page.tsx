'use client'

import { useState, useEffect } from 'react'
import VideoUploader from '@/components/VideoUploader'
import AIVideoProcessor from '@/components/AIVideoProcessor'
import AuthForm from '@/components/AuthForm'
import { clearToken } from '@/lib/api'

export default function Home() {
  const [fileId, setFileId] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const [isAuthed, setIsAuthed] = useState(true)  // TODO: Re-enable auth - set to true for dev

  useEffect(() => {
    // setIsAuthed(!!getToken())  // TODO: Re-enable auth
    setIsAuthed(true)  // Skip auth for development
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
              AI-Powered Viral Clip Detection with Whisper & GPT-4o
            </p>
            {isAuthed && (
              <button
                onClick={handleLogout}
                className="mt-3 text-sm text-gray-400 hover:text-red-400 transition-colors"
              >
                Sign out
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
      </div>
    </main>
  )
}
