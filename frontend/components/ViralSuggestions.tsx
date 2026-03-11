'use client'

import { useState } from 'react'
import { Zap, Sparkles, Clock, TrendingUp, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'

interface ViralMoment {
  start_time: number
  end_time: number
  title: string
  viral_score: number
  hook: string
  duration: number
  clip_index: number
  thumbnail_url?: string
  crop_preview?: {
    mode?: string
    crop_x?: number
    crop_y?: number
    crop_width?: number
    crop_height?: number
  }
}

interface ViralSuggestionsProps {
  fileId: string
  onMomentsDiscovered: (moments: ViralMoment[]) => void
}

export default function ViralSuggestions({ fileId, onMomentsDiscovered }: ViralSuggestionsProps) {
  const [discovering, setDiscovering] = useState(false)
  const [viralMoments, setViralMoments] = useState<ViralMoment[]>([])
  const [error, setError] = useState<string | null>(null)
  const discoverViralMoments = async () => {
    setDiscovering(true)
    setError(null)
    
    try {
      const response = await api.post(`/analyze-video?file_id=${fileId}`)
      const moments = response.data.viral_moments || []
      
      setViralMoments(moments)
      onMomentsDiscovered(moments)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to discover viral moments')
    } finally {
      setDiscovering(false)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getScoreColor = (score: number) => {
    if (score >= 8) return 'text-red-600 bg-red-50'
    if (score >= 6) return 'text-orange-600 bg-orange-50'
    if (score >= 4) return 'text-yellow-600 bg-yellow-50'
    return 'text-gray-600 bg-gray-50'
  }

  const getScoreEmoji = (score: number) => {
    if (score >= 9) return '🔥'
    if (score >= 7) return '⚡'
    if (score >= 5) return '✨'
    return '💫'
  }

  return (
    <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-6 border-2 border-purple-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-600 rounded-lg">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-gray-800 text-xl">AI Viral Scout</h3>
            <p className="text-sm text-gray-600">Autonomous moment discovery powered by GPT-4o</p>
          </div>
        </div>
        
        <button
          onClick={discoverViralMoments}
          disabled={discovering}
          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg hover:shadow-xl flex items-center gap-2"
        >
          {discovering ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              Discover Viral Moments
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {viralMoments.length > 0 && (
        <div className="space-y-3 mt-6">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-5 h-5 text-purple-600" />
            <h4 className="font-semibold text-gray-800">
              {viralMoments.length} Viral Moments Discovered
            </h4>
          </div>

          <div className="grid gap-3">
            {viralMoments.map((moment, index) => (
              <div
                key={index}
                className="bg-white rounded-lg p-4 border-2 border-gray-200 hover:border-purple-400 transition-all cursor-pointer group"
              >
                <div className="flex items-start gap-4">
                  {/* Thumbnail */}
                  {moment.thumbnail_url && (
                    <div className="relative w-24 h-32 rounded-lg overflow-hidden flex-shrink-0 bg-gray-100">
                      <img
                        src={`http://localhost:8000${moment.thumbnail_url}`}
                        alt={moment.title}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                      <div className="absolute bottom-1 left-1 right-1 text-center">
                        <span className="text-xs font-bold text-white">
                          {formatTime(moment.start_time)} - {formatTime(moment.end_time)}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h5 className="font-bold text-gray-800 text-lg group-hover:text-purple-600 transition-colors">
                        {moment.title}
                      </h5>
                      
                      <div className={`flex items-center gap-1 px-3 py-1 rounded-full font-bold text-sm ${getScoreColor(moment.viral_score)}`}>
                        <span>{getScoreEmoji(moment.viral_score)}</span>
                        <span>{moment.viral_score}/10</span>
                      </div>
                    </div>

                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                      {moment.hook}
                    </p>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{Math.floor(moment.duration)}s</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        <span>Clip #{index + 1}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Hover action hint */}
                <div className="mt-3 pt-3 border-t border-gray-100 opacity-0 group-hover:opacity-100 transition-opacity">
                  <p className="text-xs text-purple-600 font-medium text-center">
                    ✨ This moment is ready to render below
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!discovering && viralMoments.length === 0 && (
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-100 rounded-full mb-4">
            <Sparkles className="w-8 h-8 text-purple-600" />
          </div>
          <p className="text-gray-600 font-medium mb-2">
            Ready to discover viral moments
          </p>
          <p className="text-sm text-gray-500">
            AI will analyze your transcript and find 3-5 high-impact segments
          </p>
        </div>
      )}
    </div>
  )
}
