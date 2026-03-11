'use client'

import { useState, useCallback } from 'react'
import { Upload, FileVideo, X, Youtube } from 'lucide-react'
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
      setError('Please upload an MP4 file')
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.type === 'video/mp4') {
      setFile(selectedFile)
    } else {
      setError('Please upload an MP4 file')
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
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (e) => {
          if (e.total) {
            setUploadProgress(Math.round((e.loaded * 100) / e.total))
          }
        },
      })

      onUploadSuccess(response.data.file_id, file.name)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed')
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
    if (!youtubeUrl.trim()) {
      setError('Please enter a YouTube URL')
      return
    }

    setDownloading(true)
    setError(null)

    try {
      const response = await api.post('/download-youtube', {
        url: youtubeUrl
      }, {
        timeout: 25 * 60 * 1000, // 25 minutes — yt-dlp can take long
      })

      onUploadSuccess(response.data.file_id, response.data.title || response.data.filename)
    } catch (err: any) {
      if (err.code === 'ECONNABORTED') {
        setError('Download timed out. The video may be too large or the connection is slow.')
      } else {
        setError(err.response?.data?.detail || 'YouTube download failed')
      }
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8">
      <div className="mb-8 p-6 bg-gradient-to-r from-red-50 to-pink-50 border-2 border-red-200 rounded-xl">
        <div className="flex items-center gap-3 mb-4">
          <Youtube className="w-8 h-8 text-red-600" />
          <h3 className="text-xl font-semibold text-gray-800">Download from YouTube</h3>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={youtubeUrl}
            onChange={(e) => setYoutubeUrl(e.target.value)}
            placeholder="Paste YouTube URL here..."
            className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-red-500 focus:outline-none"
            disabled={downloading}
          />
          <button
            onClick={handleYoutubeDownload}
            disabled={downloading || !youtubeUrl.trim()}
            className="px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-lg font-semibold hover:from-red-700 hover:to-pink-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {downloading ? 'Downloading...' : 'Download'}
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-3">
          💡 Best quality up to 1080p will be downloaded automatically
        </p>
        {downloading && (
          <p className="text-sm text-amber-600 mt-2 font-medium">
            ⏳ Downloading video from YouTube — this may take several minutes for long videos...
          </p>
        )}
      </div>

      <div className="relative mb-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-white text-gray-500 font-medium">OR UPLOAD FILE</span>
        </div>
      </div>

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
              Drop your MP4 file here
            </h3>
            <p className="text-gray-500 mb-4">or</p>
            <label
              htmlFor="file-input"
              className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg cursor-pointer hover:bg-purple-700 transition-colors"
            >
              Browse Files
            </label>
          </>
        ) : (
          <div className="flex items-center justify-between bg-white rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <FileVideo className="w-8 h-8 text-purple-600" />
              <div className="text-left">
                <p className="font-semibold text-gray-800">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
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
                <span>Uploading...</span>
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
            {uploading ? `Uploading ${uploadProgress}%` : 'Upload Video'}
          </button>
        </div>
      )}
    </div>
  )
}
