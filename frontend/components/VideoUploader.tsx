'use client'

import { useState, useCallback } from 'react'
import { Upload, FileVideo, X, Youtube, Link } from 'lucide-react'
import { api } from '@/lib/api'

interface VideoUploaderProps {
  onUploadSuccess: (fileId: string, fileName: string) => void
}

export default function VideoUploader({ onUploadSuccess }: VideoUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [downloadStep, setDownloadStep] = useState('')

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    setError(null)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type === 'video/mp4') {
      setFile(droppedFile)
    } else {
      setError('Пожалуйста, загрузите MP4 файл')
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.type === 'video/mp4') {
      setFile(selectedFile)
    } else {
      setError('Пожалуйста, загрузите MP4 файл')
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setUploadProgress(0)
    setError(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const response = await api.post('/upload', formData, {
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded * 100) / e.total))
        },
      })
      onUploadSuccess(response.data.file_id, file.name)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки. Попробуйте снова.')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }

  const handleRemoveFile = () => {
    setFile(null)
    setError(null)
  }

  const handleYoutubeDownload = async () => {
    const url = youtubeUrl.trim()
    if (!url) {
      setError('Вставьте ссылку на YouTube видео')
      return
    }
    setDownloading(true)
    setDownloadStep('Подключаемся к YouTube...')
    setError(null)

    // Simulate step messages to show progress to user
    const steps = [
      { delay: 3000,  msg: 'Определяем качество видео...' },
      { delay: 8000,  msg: 'Скачиваем видео (это может занять несколько минут)...' },
      { delay: 30000, msg: 'Скачивание продолжается — большие видео требуют времени...' },
      { delay: 90000, msg: 'Почти готово, финальная обработка...' },
    ]
    const timers = steps.map(({ delay, msg }) => setTimeout(() => setDownloadStep(msg), delay))

    try {
      const response = await api.post('/download-youtube', { url }, {
        timeout: 25 * 60 * 1000,
      })
      onUploadSuccess(response.data.file_id, response.data.title || response.data.filename)
    } catch (err: any) {
      if (err.code === 'ECONNABORTED') {
        setError('Время ожидания истекло. Видео слишком большое или медленное соединение.')
      } else {
        setError(err.response?.data?.detail || 'Не удалось скачать видео. Проверьте ссылку.')
      }
    } finally {
      timers.forEach(clearTimeout)
      setDownloading(false)
      setDownloadStep('')
    }
  }

  const handleYoutubeKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !downloading) handleYoutubeDownload()
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8">
      {/* YouTube import — primary action */}
      <div className="mb-8 p-6 bg-gradient-to-r from-red-50 to-pink-50 border-2 border-red-200 rounded-xl">
        <div className="flex items-center gap-3 mb-4">
          <Youtube className="w-8 h-8 text-red-600" />
          <div>
            <h3 className="text-xl font-semibold text-gray-800">Скачать с YouTube</h3>
            <p className="text-sm text-gray-500">Вставьте ссылку — скачаем в лучшем качестве</p>
          </div>
        </div>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              onKeyDown={handleYoutubeKeyDown}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full pl-9 pr-4 py-3 border-2 border-gray-300 rounded-lg focus:border-red-500 focus:outline-none"
              disabled={downloading}
            />
          </div>
          <button
            onClick={handleYoutubeDownload}
            disabled={downloading || !youtubeUrl.trim()}
            className="px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-lg font-semibold hover:from-red-700 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {downloading ? 'Скачиваем...' : 'Скачать'}
          </button>
        </div>
        {downloading && downloadStep && (
          <div className="mt-3 flex items-center gap-2 text-sm text-amber-700">
            <div className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin" />
            {downloadStep}
          </div>
        )}
        {!downloading && (
          <p className="text-xs text-gray-500 mt-2">
            Поддерживаются видео до 1080p · YouTube, Shorts и плейлисты
          </p>
        )}
      </div>

      {/* Divider */}
      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-white text-gray-500 font-medium">ИЛИ ЗАГРУЗИТЕ ФАЙЛ</span>
        </div>
      </div>

      {/* File drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-4 border-dashed rounded-xl p-12 text-center transition-all
          ${isDragging ? 'border-purple-500 bg-purple-50' : 'border-gray-300 bg-gray-50'}
          ${file ? 'border-green-500 bg-green-50' : ''}
        `}
      >
        <input
          type="file"
          accept="video/mp4"
          onChange={handleFileSelect}
          className="hidden"
          id="file-input"
        />

        {!file ? (
          <>
            <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              Перетащите MP4 сюда
            </h3>
            <p className="text-gray-500 mb-4">или</p>
            <label
              htmlFor="file-input"
              className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg cursor-pointer hover:bg-purple-700 transition-colors"
            >
              Выбрать файл
            </label>
          </>
        ) : (
          <div className="flex items-center justify-between bg-white rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <FileVideo className="w-8 h-8 text-purple-600" />
              <div className="text-left">
                <p className="font-semibold text-gray-800">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / (1024 * 1024)).toFixed(2)} МБ
                </p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {file && (
        <div className="mt-6">
          {uploading && (
            <div className="mb-3">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Загружаем...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-purple-600 to-blue-600 h-2 rounded-full transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? `Загружаем ${uploadProgress}%` : 'Загрузить видео'}
          </button>
        </div>
      )}
    </div>
  )
}
