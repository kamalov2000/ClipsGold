'use client'

import { useState } from 'react'
import { FileVideo, Info, Image, Minimize2, Download, RotateCcw, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

interface VideoProcessorProps {
  fileId: string
  fileName: string
  onReset: () => void
}

export default function VideoProcessor({ fileId, fileName, onReset }: VideoProcessorProps) {
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const handleProcess = async (operation: string) => {
    setProcessing(true)
    setError(null)
    setResult(null)

    try {
      const response = await api.post(
        `/process/${fileId}?operation=${operation}`
      )
      setResult({ operation, data: response.data })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Processing failed')
    } finally {
      setProcessing(false)
    }
  }

  const handleDownload = async (fileType: string) => {
    try {
      const response = await api.get(
        `/download/${fileId}?file_type=${fileType}`,
        { responseType: 'blob' }
      )

      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${fileId}_${fileType}.${fileType === 'thumbnail' ? 'jpg' : 'mp4'}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err: any) {
      setError('Download failed')
    }
  }

  const handleCleanupAndReset = async () => {
    try {
      await api.delete(`/cleanup/${fileId}`)
    } catch (err) {
      console.error('Cleanup failed:', err)
    }
    onReset()
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8">
      <div className="flex items-center justify-between mb-6 pb-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <FileVideo className="w-8 h-8 text-purple-600" />
          <div>
            <h2 className="text-xl font-semibold text-gray-800">{fileName}</h2>
            <p className="text-sm text-gray-500">Ready to process</p>
          </div>
        </div>
        <button
          onClick={handleCleanupAndReset}
          className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          Upload New
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <button
          onClick={() => handleProcess('info')}
          disabled={processing}
          className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <Info className="w-8 h-8 mx-auto mb-3 text-gray-600 group-hover:text-purple-600" />
          <h3 className="font-semibold text-gray-800 mb-1">Get Info</h3>
          <p className="text-sm text-gray-500">Video metadata</p>
        </button>

        <button
          onClick={() => handleProcess('thumbnail')}
          disabled={processing}
          className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <Image className="w-8 h-8 mx-auto mb-3 text-gray-600 group-hover:text-purple-600" />
          <h3 className="font-semibold text-gray-800 mb-1">Thumbnail</h3>
          <p className="text-sm text-gray-500">Extract frame</p>
        </button>

        <button
          onClick={() => handleProcess('compress')}
          disabled={processing}
          className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
        >
          <Minimize2 className="w-8 h-8 mx-auto mb-3 text-gray-600 group-hover:text-purple-600" />
          <h3 className="font-semibold text-gray-800 mb-1">Compress</h3>
          <p className="text-sm text-gray-500">Reduce file size</p>
        </button>
      </div>

      {processing && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
          <span className="ml-3 text-gray-600">Processing...</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {result && (
        <div className="mt-6 p-6 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800 text-lg">
              {result.operation === 'info' && 'Video Information'}
              {result.operation === 'thumbnail' && 'Thumbnail Generated'}
              {result.operation === 'compress' && 'Video Compressed'}
            </h3>
            {result.operation !== 'info' && (
              <button
                onClick={() => handleDownload(result.operation === 'thumbnail' ? 'thumbnail' : 'compressed')}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </button>
            )}
          </div>
          <div className="bg-white rounded-lg p-4 max-h-64 overflow-auto">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap">
              {JSON.stringify(result.data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
