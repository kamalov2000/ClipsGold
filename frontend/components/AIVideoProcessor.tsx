'use client'

import { useState, useEffect, useRef } from 'react'
import { FileVideo, Sparkles, Scissors, Download, RotateCcw, Loader2, MessageSquare, Zap } from 'lucide-react'
import { api, API_BASE, WS_BASE } from '@/lib/api'

interface VideoProcessorProps {
  fileId: string
  fileName: string
  onReset: () => void
}

interface Candidate {
  start_time: number
  end_time: number
  title: string
  description?: string
  hashtags?: string[]
  reason: string
  virality_score: number
  hook: string
  emojis?: string[]
  thumbnail_url?: string
  crop_preview?: {
    mode?: string
    crop_x?: number
    crop_y?: number
    crop_width?: number
    crop_height?: number
    left_face?: {
      x: number
      y: number
      w: number
      h: number
    }
    right_face?: {
      x: number
      y: number
      w: number
      h: number
    }
    distance_percent?: number
  }
}

interface ViralClip {
  clip_id: number
  filename: string
  title: string
  start_time: number
  end_time: number
  virality_score: number
  reason: string
  hook?: string
  enhanced?: {
    reframed: boolean
    subtitles: boolean
  }
  candidateIndex?: number
  downloadUrl?: string
}

export default function AIVideoProcessor({ fileId, fileName, onReset }: VideoProcessorProps) {
  const [transcribing, setTranscribing] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [transcription, setTranscription] = useState<string | null>(null)
  const [segments, setSegments] = useState<Array<{ start: number; end: number; text: string; words?: Array<{ word: string; start?: number; end?: number }> }>>([])
  const [savingSubtitles, setSavingSubtitles] = useState(false)
  const [subtitleEditDirty, setSubtitleEditDirty] = useState(false)
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [renderingClips, setRenderingClips] = useState<Set<number>>(new Set())
  const [renderedClips, setRenderedClips] = useState<ViralClip[]>([])
  const [downloadingClips, setDownloadingClips] = useState<Set<number>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const provider = 'openai'
  const [targetPlatform, setTargetPlatform] = useState<'tiktok' | 'youtube' | 'instagram'>('tiktok')
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)
  
  // Manual crop control state
  const [manualCropX, setManualCropX] = useState<{[key: number]: number | null}>({})
  const [originalCropX, setOriginalCropX] = useState<{[key: number]: number}>({})

  // Batch render: approved checkboxes
  const [approvedClips, setApprovedClips] = useState<Set<number>>(new Set())
  const [batchRendering, setBatchRendering] = useState(false)

  // Subtitle style per clip
  const [subtitleStyles, setSubtitleStyles] = useState<{[key: number]: string}>({})

  // Jump-cut toggle (global)
  const [enableJumpCut, setEnableJumpCut] = useState(false)

  // Editable timecodes per candidate (overrides GPT values when rendering)
  const [clipTimecodes, setClipTimecodes] = useState<{[key: number]: { start: string; end: string } }>({})

  // Clip social metadata
  const [clipMeta, setClipMeta] = useState<{[key: number]: { title: string; description: string; hashtags: string[]; cta: string }}>({})
  const [copiedMeta, setCopiedMeta] = useState<number | null>(null)

  // Render progress tracking
  const [renderProgress, setRenderProgress] = useState<{[key: number]: number}>({})
  const [renderStatus, setRenderStatus] = useState<{[key: number]: string}>({})
  const [successResult, setSuccessResult] = useState<{ clipIndex: number; downloadUrl: string; filename: string; title: string } | null>(null)
  const wsConnections = useRef<{[key: string]: WebSocket}>({})
  const [safeZoneOverlayVisible, setSafeZoneOverlayVisible] = useState(true)
  // Cleanup WebSocket connections on unmount
  useEffect(() => {
    return () => {
      Object.values(wsConnections.current).forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close()
        }
      })
    }
  }, [])

  // Load segments for editing when we have transcription but segments empty (e.g. after refresh)
  useEffect(() => {
    if (!transcription || segments.length > 0 || !fileId) return
    api.get(`/transcription/${fileId}`)
      .then(res => {
        if (Array.isArray(res.data.segments) && res.data.segments.length > 0) {
          setSegments(res.data.segments)
        }
      })
      .catch(() => {})
  }, [transcription, fileId, segments.length])

  const handleTranscribe = async () => {
    setTranscribing(true)
    setError(null)

    try {
      const response = await api.post(`/transcribe/${fileId}`)
      setTranscription(response.data.transcription)
      setSegments(Array.isArray(response.data.segments) ? response.data.segments : [])
      setSubtitleEditDirty(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Transcription failed')
    } finally {
      setTranscribing(false)
    }
  }

  const handleAnalyze = async () => {
    if (!transcription) {
      setError('Please transcribe the video first')
      return
    }

    setAnalyzing(true)
    setError(null)

    try {
      const response = await api.post(
        `/analyze/${fileId}?provider=${provider}`
      )
      // Store candidates, don't auto-render
      setCandidates(response.data.viral_clips)
      
      // Initialize manual crop state with AI-detected values
      const initialCropX: {[key: number]: number} = {}
      response.data.viral_clips.forEach((candidate: Candidate, index: number) => {
        if (candidate.crop_preview?.crop_x !== undefined) {
          initialCropX[index] = candidate.crop_preview.crop_x
        }
      })
      setOriginalCropX(initialCropX)
      setManualCropX({})
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleResetCrop = (index: number) => {
    setManualCropX(prev => ({
      ...prev,
      [index]: null
    }))
  }

  const handleSegmentTextChange = (index: number, text: string) => {
    setSegments(prev => {
      const next = [...prev]
      if (next[index]) {
        next[index] = { ...next[index], text }
      }
      return next
    })
    setSubtitleEditDirty(true)
  }

  const formatSegmentTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const handleSaveSubtitles = async () => {
    if (!fileId || segments.length === 0) return
    setSavingSubtitles(true)
    setError(null)
    try {
      const response = await api.patch(`/transcription/${fileId}`, {
        segments: segments.map((seg, index) => ({ index, text: (seg.text || '').trim() }))
      })
      setTranscription(response.data.text)
      setSegments(response.data.segments || segments)
      setSubtitleEditDirty(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save subtitles')
    } finally {
      setSavingSubtitles(false)
    }
  }

  const handleRenderClip = async (clipIndex: number) => {
    setRenderingClips(prev => new Set(prev).add(clipIndex))
    setRenderProgress(prev => ({ ...prev, [clipIndex]: 0 }))
    setRenderStatus(prev => ({ ...prev, [clipIndex]: 'starting' }))
    setError(null)

    // Auto-save subtitle edits before rendering so the server uses current text
    if (subtitleEditDirty && segments.length > 0) {
      try {
        setRenderStatus(prev => ({ ...prev, [clipIndex]: 'saving subtitles…' }))
        const resp = await api.patch(`/transcription/${fileId}`, {
          segments: segments.map((seg, i) => ({ index: i, text: (seg.text || '').trim() }))
        })
        setTranscription(resp.data.text)
        setSegments(resp.data.segments || segments)
        setSubtitleEditDirty(false)
      } catch {
        // Non-fatal: proceed with render even if subtitle save fails
      }
    }

    const tc = clipTimecodes[clipIndex]
    const candidate = candidates[clipIndex]
    const startOverride = tc ? parseTime(tc.start) : null
    const endOverride = tc ? parseTime(tc.end) : null
    const effectiveStart = startOverride !== null ? startOverride : candidate?.start_time
    const effectiveEnd = endOverride !== null ? endOverride : candidate?.end_time

    try {
      const response = await api.post(
        `/render-clip`,
        {
          file_id: fileId,
          clip_index: clipIndex,
          start_time: effectiveStart,
          end_time: effectiveEnd,
          platform: targetPlatform,
          manual_crop_x: manualCropX[clipIndex] !== null && manualCropX[clipIndex] !== undefined
            ? manualCropX[clipIndex]
            : null,
          subtitle_style: subtitleStyles[clipIndex] || 'hormozi',
          enable_jump_cut: enableJumpCut,
          enable_sfx: false,
        }
      )
      
      const taskId = response.data.task_id
      const queuePosition = response.data.queue_position
      console.log('Render queued, task_id:', taskId, 'queue_position:', queuePosition)
      if (queuePosition > 1) {
        setRenderStatus(prev => ({ ...prev, [clipIndex]: `queued:${queuePosition}` }))
      }
      
      // Connect to WebSocket for progress updates
      const ws = new WebSocket(`${WS_BASE}/ws/render-progress/${taskId}`)
      wsConnections.current[taskId] = ws
      
      ws.onopen = () => {
        console.log('WebSocket connected for task:', taskId)
        setRenderStatus(prev => ({ ...prev, [clipIndex]: queuePosition > 1 ? `queued:${queuePosition}` : 'rendering' }))
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        console.log('Progress update:', data)
        
        if (data.status === 'processing') {
          setRenderProgress(prev => ({ ...prev, [clipIndex]: data.progress }))
          setRenderStatus(prev => ({ ...prev, [clipIndex]: `rendering (${data.progress}%)` }))
        } else if (data.status === 'complete') {
          setRenderProgress(prev => ({ ...prev, [clipIndex]: 100 }))
          setRenderStatus(prev => ({ ...prev, [clipIndex]: 'complete' }))
        } else if (data.status === 'success') {
          setRenderProgress(prev => ({ ...prev, [clipIndex]: 100 }))
          setRenderStatus(prev => ({ ...prev, [clipIndex]: 'complete' }))
          setSuccessResult({
            clipIndex,
            downloadUrl: data.download_url || `/download-clip/${data.file_id}/${data.clip_id}`,
            filename: data.filename || `${fileId}_clip_${clipIndex + 1}_VIRAL_GOLD.mp4`,
            title: data.title || candidates[clipIndex]?.title || 'Clip'
          })
          setRenderedClips(prev => [...prev, {
            clip_id: clipIndex + 1,
            filename: data.filename || `${fileId}_clip_${clipIndex + 1}_VIRAL_GOLD.mp4`,
            title: data.title || candidates[clipIndex]?.title || '',
            start_time: candidates[clipIndex]?.start_time ?? 0,
            end_time: candidates[clipIndex]?.end_time ?? 0,
            virality_score: candidates[clipIndex]?.virality_score ?? 0,
            reason: candidates[clipIndex]?.reason ?? '',
            hook: candidates[clipIndex]?.hook,
            enhanced: { reframed: true, subtitles: true },
            candidateIndex: clipIndex,
            downloadUrl: data.download_url || `/download-clip/${data.file_id}/${data.clip_id}`
          }])
          // Store social metadata if returned
          if (data.meta && typeof data.meta === 'object') {
            setClipMeta(prev => ({ ...prev, [clipIndex]: data.meta }))
          } else {
            // Fetch from backend as fallback
            api.get(`/clip-meta/${fileId}/${clipIndex + 1}`)
              .then(r => setClipMeta(prev => ({ ...prev, [clipIndex]: r.data })))
              .catch(() => {})
          }
          setRenderingClips(prev => {
            const updated = new Set(prev)
            updated.delete(clipIndex)
            return updated
          })
          // Keep WebSocket open for re-render / further commands; do not close
        } else if (data.status === 'error') {
          setError(`Render failed: ${data.error}`)
          setRenderStatus(prev => ({ ...prev, [clipIndex]: 'error' }))
          ws.close()
          delete wsConnections.current[taskId]
          setRenderingClips(prev => {
            const updated = new Set(prev)
            updated.delete(clipIndex)
            return updated
          })
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setError('WebSocket connection failed')
        setRenderStatus(prev => ({ ...prev, [clipIndex]: 'error' }))
        
        setRenderingClips(prev => {
          const updated = new Set(prev)
          updated.delete(clipIndex)
          return updated
        })
      }
      
      ws.onclose = () => {
        console.log('WebSocket closed for task:', taskId)
      }
      
    } catch (err: any) {
      console.error('Render error:', err)
      setError(err.response?.data?.detail || `Failed to render clip ${clipIndex + 1}`)
      setRenderStatus(prev => ({ ...prev, [clipIndex]: 'error' }))
      
      setRenderingClips(prev => {
        const updated = new Set(prev)
        updated.delete(clipIndex)
        return updated
      })
    }
  }

  const handleDownloadClip = async (clipId: number, downloadUrl?: string, candidateIndex?: number) => {
    const idx = candidateIndex ?? clipId
    setDownloadingClips(prev => new Set(prev).add(idx))
    try {
      const url = downloadUrl
        ? `${API_BASE}${downloadUrl}`
        : `${API_BASE}/clips/${fileId}_clip_${clipId}_VIRAL_GOLD.mp4`
      const response = await api.get(url, { responseType: 'blob' })
      const filename = response.headers['content-disposition']?.split('filename=')?.[1]?.replace(/"/g, '') || `${fileId}_clip_${clipId}_VIRAL_GOLD.mp4`
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (err: any) {
      setError('Download failed - clip may still be rendering')
    } finally {
      setDownloadingClips(prev => { const s = new Set(prev); s.delete(idx); return s })
    }
  }

  const handleRerender = (index: number) => {
    setRenderedClips(prev => prev.filter((c: any) => c.candidateIndex !== index))
    setRenderingClips(prev => { const s = new Set(prev); s.delete(index); return s })
    setRenderProgress(prev => { const n = { ...prev }; delete n[index]; return n })
    setRenderStatus(prev => { const n = { ...prev }; delete n[index]; return n })
  }

  const handleBackToEditor = () => {
    setSuccessResult(null)
  }

  const handleBatchRender = async () => {
    const toRender = approvedClips.size > 0
      ? Array.from(approvedClips)
      : candidates.map((_, i) => i)
    if (toRender.length === 0) return
    setBatchRendering(true)
    for (const idx of toRender) {
      await handleRenderClip(idx)
    }
    setBatchRendering(false)
  }

  const handleCopyMeta = async (index: number) => {
    const meta = clipMeta[index]
    if (!meta) return
    const text = `${meta.title}\n\n${meta.description}\n\n${meta.hashtags?.join(' ')}\n\n${meta.cta}`
    try {
      await navigator.clipboard.writeText(text)
      setCopiedMeta(index)
      setTimeout(() => setCopiedMeta(null), 2000)
    } catch {}
  }

  const handleCleanupAndReset = async () => {
    try {
      await api.delete(`/cleanup/${fileId}`)
    } catch (err) {
      console.error('Cleanup failed:', err)
    }
    onReset()
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const parseTime = (value: string): number | null => {
    const parts = value.trim().split(':')
    if (parts.length === 2) {
      const m = parseInt(parts[0])
      const s = parseInt(parts[1])
      if (!isNaN(m) && !isNaN(s) && s >= 0 && s < 60) return m * 60 + s
    } else if (parts.length === 1) {
      const s = parseInt(parts[0])
      if (!isNaN(s)) return s
    }
    return null
  }

  const getCandidateText = (candidate: Candidate, index: number): string => {
    const tc = clipTimecodes[index]
    const start = (tc ? parseTime(tc.start) : null) ?? candidate.start_time
    const end = (tc ? parseTime(tc.end) : null) ?? candidate.end_time
    return segments
      .filter(seg => seg.end > start && seg.start < end)
      .map(seg => (seg.text || '').trim())
      .filter(Boolean)
      .join(' ')
  }

  const copyDescription = async (candidate: Candidate, index: number) => {
    const description = candidate.description || candidate.title
    const hashtags = candidate.hashtags?.join(' ') || ''
    const fullText = `${description}\n\n${hashtags}`
    
    try {
      await navigator.clipboard.writeText(fullText)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="bg-white rounded-2xl shadow-2xl p-8">
      <div className="flex items-center justify-between mb-6 pb-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <FileVideo className="w-8 h-8 text-purple-600" />
          <div>
            <h2 className="text-xl font-semibold text-gray-800">{fileName}</h2>
            <p className="text-sm text-gray-500">AI-Powered Viral Clip Detection</p>
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

      <div className="grid grid-cols-1 gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target Platform
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setTargetPlatform('tiktok')}
              className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all ${
                targetPlatform === 'tiktok'
                  ? 'border-pink-600 bg-pink-50 text-pink-700'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              TikTok
            </button>
            <button
              onClick={() => setTargetPlatform('youtube')}
              className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all ${
                targetPlatform === 'youtube'
                  ? 'border-red-600 bg-red-50 text-red-700'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              YouTube
            </button>
            <button
              onClick={() => setTargetPlatform('instagram')}
              className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all ${
                targetPlatform === 'instagram'
                  ? 'border-purple-600 bg-purple-50 text-purple-700'
                  : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              Instagram
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <button
          onClick={handleTranscribe}
          disabled={transcribing || !!transcription}
          className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed group relative"
        >
          {transcription && (
            <div className="absolute top-2 right-2 w-3 h-3 bg-green-500 rounded-full"></div>
          )}
          <MessageSquare className="w-8 h-8 mx-auto mb-3 text-gray-600 group-hover:text-purple-600" />
          <h3 className="font-semibold text-gray-800 mb-1">
            {transcribing ? 'Transcribing...' : transcription ? 'Transcribed ✓' : 'Transcribe'}
          </h3>
          <p className="text-sm text-gray-500">Extract audio text</p>
        </button>

        <button
          onClick={handleAnalyze}
          disabled={!transcription || analyzing}
          className="p-6 border-2 border-gray-200 rounded-xl hover:border-purple-500 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed group relative"
        >
          {candidates.length > 0 && (
            <div className="absolute top-2 right-2 w-3 h-3 bg-green-500 rounded-full"></div>
          )}
          <Sparkles className="w-8 h-8 mx-auto mb-3 text-gray-600 group-hover:text-purple-600" />
          <h3 className="font-semibold text-gray-800 mb-1">
            {analyzing ? 'Analyzing...' : candidates.length > 0 ? 'Re-analyze' : 'Analyze'}
          </h3>
          <p className="text-sm text-gray-500">Find viral moments</p>
        </button>

        <div className="p-6 border-2 border-gray-200 rounded-xl bg-gray-50">
          <Scissors className="w-8 h-8 mx-auto mb-3 text-gray-400" />
          <h3 className="font-semibold text-gray-600 mb-1">Render Clips</h3>
          <p className="text-sm text-gray-500">Select clips below</p>
        </div>
      </div>

      {(transcribing || analyzing || renderingClips.size > 0) && (
        <div className="flex items-center justify-center py-8 bg-purple-50 rounded-xl mb-6">
          <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
          <span className="ml-3 text-gray-700 font-medium">
            {transcribing && 'Transcribing video with Whisper...'}
            {analyzing && 'Analyzing with GPT-4o...'}
            {renderingClips.size > 0 && `Rendering ${renderingClips.size} clip(s)...`}
          </span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-6">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {successResult && (
        <div className="p-4 mb-6 rounded-xl bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-green-500 flex items-center justify-center text-white text-xl">✓</div>
            <div>
              <p className="font-semibold text-gray-800">Clip ready: {successResult.title}</p>
              <p className="text-sm text-gray-600">Connection kept open for re-render or more edits.</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => handleDownloadClip(successResult.clipIndex + 1, successResult.downloadUrl)}
              className="px-5 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition-colors flex items-center gap-2 shadow-lg"
            >
              <Download className="w-5 h-5" />
              Download Clip
            </button>
            <button
              onClick={handleBackToEditor}
              className="px-5 py-2.5 bg-white border-2 border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              Back to Editor
            </button>
          </div>
        </div>
      )}

      {transcription && (
        <div className="mb-6 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-gray-800 text-lg">Transcription</h3>
          </div>
          <div className="bg-white rounded-lg p-4 max-h-48 overflow-auto">
            <p className="text-sm text-gray-700 leading-relaxed">{transcription}</p>
          </div>

          {segments.length > 0 && (
            <div className="mt-4 pt-4 border-t border-blue-200">
              <h4 className="font-medium text-gray-800 mb-2">Edit subtitles (phrases)</h4>
              <p className="text-sm text-gray-500 mb-3">Change text per phrase; it will be used when rendering clips.</p>
              <div className="space-y-2 max-h-64 overflow-auto bg-white rounded-lg p-3">
                {segments.map((seg, index) => (
                  <div key={index} className="flex gap-2 items-start">
                    <span className="text-xs text-gray-400 whitespace-nowrap mt-2 shrink-0">
                      {formatSegmentTime(seg.start)}–{formatSegmentTime(seg.end)}
                    </span>
                    <input
                      type="text"
                      value={seg.text || ''}
                      onChange={e => handleSegmentTextChange(index, e.target.value)}
                      className="flex-1 min-w-0 text-sm border border-gray-200 rounded px-2 py-1.5 focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                      placeholder="Phrase text"
                    />
                  </div>
                ))}
              </div>
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={handleSaveSubtitles}
                  disabled={!subtitleEditDirty || savingSubtitles}
                  className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {savingSubtitles ? 'Saving...' : 'Save subtitle edits'}
                </button>
                {subtitleEditDirty && <span className="text-xs text-amber-600">Unsaved changes</span>}
              </div>
            </div>
          )}
        </div>
      )}

      {candidates.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Zap className="w-6 h-6 text-yellow-500" />
              <h3 className="font-semibold text-gray-800 text-xl">
                Clip Candidates ({candidates.length})
              </h3>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer shrink-0">
                <input type="checkbox" checked={safeZoneOverlayVisible}
                  onChange={(e) => setSafeZoneOverlayVisible(e.target.checked)}
                  className="rounded border-gray-300 text-purple-600 focus:ring-purple-500" />
                <span className="text-sm font-medium text-gray-600">Platform UI</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer shrink-0">
                <input type="checkbox" checked={enableJumpCut}
                  onChange={(e) => setEnableJumpCut(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                <span className="text-sm font-medium text-gray-600">✂ Jump-Cut</span>
              </label>
              <button
                onClick={handleBatchRender}
                disabled={batchRendering || renderingClips.size > 0}
                className="px-4 py-2 bg-gradient-to-r from-yellow-500 to-orange-500 text-white text-sm font-bold rounded-lg hover:from-yellow-600 hover:to-orange-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow"
              >
                {batchRendering ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scissors className="w-4 h-4" />}
                {approvedClips.size > 0 ? `Render ${approvedClips.size} Approved` : 'Render All'}
              </button>
            </div>
          </div>

          {candidates.map((candidate, index) => {
            const isRendering = renderingClips.has(index)
            // Match by candidate index, not clip_id
            const renderedClip = renderedClips.find((c: any) => c.candidateIndex === index)
            
            return (
              <div
                key={index}
                className={`p-6 bg-gradient-to-r from-purple-50 to-pink-50 border-2 rounded-xl hover:shadow-lg transition-all ${approvedClips.has(index) ? 'border-green-400' : 'border-purple-200'}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      {/* Approve checkbox */}
                      <label className="flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={approvedClips.has(index)}
                          onChange={(e) => {
                            setApprovedClips(prev => {
                              const next = new Set(prev)
                              e.target.checked ? next.add(index) : next.delete(index)
                              return next
                            })
                          }}
                          className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
                        />
                        <span className="text-xs font-semibold text-gray-600">Approve</span>
                      </label>
                      <span className="px-3 py-1 bg-purple-600 text-white text-xs font-bold rounded-full">
                        #{index + 1}
                      </span>
                      <span className="px-3 py-1 bg-yellow-400 text-yellow-900 text-xs font-bold rounded-full flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {candidate.virality_score}/10
                      </span>
                      <div className="flex items-center gap-1">
                        <input
                          type="text"
                          value={clipTimecodes[index]?.start ?? formatTime(candidate.start_time)}
                          onChange={(e) => setClipTimecodes(prev => ({
                            ...prev,
                            [index]: { start: e.target.value, end: prev[index]?.end ?? formatTime(candidate.end_time) }
                          }))}
                          className="w-14 text-xs text-center border border-gray-300 rounded px-1 py-0.5 font-mono focus:border-purple-400 focus:ring-1 focus:ring-purple-300 bg-white"
                          placeholder="0:00"
                          title="Start time (M:SS)"
                        />
                        <span className="text-gray-400 text-xs">–</span>
                        <input
                          type="text"
                          value={clipTimecodes[index]?.end ?? formatTime(candidate.end_time)}
                          onChange={(e) => setClipTimecodes(prev => ({
                            ...prev,
                            [index]: { start: prev[index]?.start ?? formatTime(candidate.start_time), end: e.target.value }
                          }))}
                          className="w-14 text-xs text-center border border-gray-300 rounded px-1 py-0.5 font-mono focus:border-purple-400 focus:ring-1 focus:ring-purple-300 bg-white"
                          placeholder="0:00"
                          title="End time (M:SS)"
                        />
                        <span className="text-xs text-gray-400">
                          ({Math.round(
                            (clipTimecodes[index]
                              ? (parseTime(clipTimecodes[index].end) ?? candidate.end_time) - (parseTime(clipTimecodes[index].start) ?? candidate.start_time)
                              : candidate.end_time - candidate.start_time)
                          )}s)
                        </span>
                      </div>
                      {/* Subtitle style selector */}
                      <select
                        value={subtitleStyles[index] || 'hormozi'}
                        onChange={(e) => setSubtitleStyles(prev => ({ ...prev, [index]: e.target.value }))}
                        className="text-xs border border-purple-300 rounded-lg px-2 py-1 bg-white text-purple-700 font-semibold focus:ring-2 focus:ring-purple-400 cursor-pointer"
                      >
                        <option value="hormozi">🟡 Hormozi</option>
                        <option value="beast">🔵 Beast</option>
                        <option value="minimal">⚪ Minimal</option>
                      </select>
                      {renderedClip && (
                        <span className="px-2 py-1 bg-green-500 text-white text-xs font-bold rounded">
                          RENDERED ✓
                        </span>
                      )}
                    </div>
                    {candidate.hook && (
                      <div className="mb-2 px-3 py-2 bg-gradient-to-r from-yellow-100 to-orange-100 border-2 border-yellow-400 rounded-lg inline-block">
                        <p className="text-sm font-black text-gray-800 tracking-wide">
                          🔥 HOOK: {candidate.hook}
                        </p>
                      </div>
                    )}
                    {candidate.emojis && candidate.emojis.length > 0 && (
                      <div className="mb-2 flex gap-1">
                        {candidate.emojis.map((emoji, i) => (
                          <span key={i} className="text-2xl">{emoji}</span>
                        ))}
                      </div>
                    )}
                    <h4 className="text-lg font-bold text-gray-800 mb-2">{candidate.title}</h4>
                    
                    {/* Metadata Section */}
                    {candidate.description && (
                      <div className="mb-3 p-3 bg-white rounded-lg border border-gray-200">
                        <div className="flex items-start justify-between mb-2">
                          <p className="text-xs font-semibold text-gray-500">📱 Post Description:</p>
                          <button
                            onClick={() => copyDescription(candidate, index)}
                            className="px-2 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
                          >
                            {copiedIndex === index ? '✓ Copied!' : 'Copy'}
                          </button>
                        </div>
                        <p className="text-sm text-gray-700 mb-2">{candidate.description}</p>
                        {candidate.hashtags && candidate.hashtags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {candidate.hashtags.map((tag, i) => (
                              <span key={i} className="text-xs text-blue-600 font-medium">{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Smart Crop Visualization - Full 16:9 frame with crop overlay */}
                    <div className="mb-3 p-3 bg-gradient-to-b from-gray-50 to-gray-100 rounded-lg border border-gray-300">
                      <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                        <p className="text-xs font-semibold text-gray-600">
                          🎬 Smart Crop Preview ({targetPlatform.toUpperCase()})
                        </p>
                        {candidate.crop_preview?.mode === 'split_screen' && (
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs font-bold rounded-full flex items-center gap-1">
                            👥 Split Screen Mode
                          </span>
                        )}
                        {candidate.crop_preview?.mode === 'single_face' && (
                          <span className={`px-2 py-1 text-xs font-bold rounded-full ${
                            manualCropX[index] !== null && manualCropX[index] !== undefined
                              ? 'bg-orange-100 text-orange-700'
                              : 'bg-green-100 text-green-700'
                          }`}>
                            {manualCropX[index] !== null && manualCropX[index] !== undefined
                              ? '✋ Manual Fix'
                              : '👤 Face-Centered'}
                          </span>
                        )}
                        {candidate.crop_preview?.mode === 'group_face' && (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded-full">
                            👥 Group Centered
                          </span>
                        )}
                      </div>
                      <div className="relative w-full aspect-video bg-gray-900 rounded overflow-hidden">
                        {/* Full 16:9 video thumbnail */}
                        {candidate.thumbnail_url ? (
                          <>
                            {(() => {
                              const sourceWidth = 1920
                              const cropXDefault = candidate.crop_preview?.crop_x ?? 0
                              const currentX = manualCropX[index] !== null && manualCropX[index] !== undefined
                                ? manualCropX[index]!
                                : cropXDefault
                              const offsetPx = currentX - cropXDefault
                              const shiftPct = -(offsetPx / sourceWidth) * 100
                              return (
                                <img
                                  src={`${API_BASE}${candidate.thumbnail_url}`}
                                  alt="Video frame"
                                  className="absolute inset-0 w-full h-full object-contain transition-transform duration-75"
                                  style={{ transform: `translateX(${shiftPct.toFixed(2)}%)` }}
                                />
                              )
                            })()}
                            {/* Live offset badge */}
                            {manualCropX[index] !== null && manualCropX[index] !== undefined && candidate.crop_preview?.crop_x !== undefined && manualCropX[index] !== candidate.crop_preview.crop_x && (
                              <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-orange-500/90 text-white text-[9px] font-bold rounded pointer-events-none">
                                ✋ {manualCropX[index]! > (candidate.crop_preview.crop_x ?? 0) ? '→' : '←'} {Math.abs(manualCropX[index]! - (candidate.crop_preview.crop_x ?? 0))}px
                              </div>
                            )}
                            
                            {/* Crop visualization overlay */}
                            {candidate.crop_preview && candidate.crop_preview.mode !== 'split_screen' && (
                              <>
                                {/* Semi-transparent black masks for cropped-out areas */}
                                <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                                  {/* Calculate percentages for crop area */}
                                  {(() => {
                                    // Assume 16:9 source video for percentage calculation
                                    const sourceWidth = 1920  // Standard 16:9 width
                                    const sourceHeight = 1080 // Standard 16:9 height
                                    
                                    // Use manual crop X if set, otherwise use AI-detected
                                    const cropX = manualCropX[index] !== null && manualCropX[index] !== undefined
                                      ? manualCropX[index]!
                                      : candidate.crop_preview.crop_x
                                    const cropY = candidate.crop_preview.crop_y
                                    const cropW = candidate.crop_preview.crop_width
                                    const cropH = candidate.crop_preview.crop_height
                                    
                                    // Convert to percentages
                                    const leftPercent = (cropX / sourceWidth) * 100
                                    const topPercent = (cropY / sourceHeight) * 100
                                    const widthPercent = (cropW / sourceWidth) * 100
                                    const heightPercent = (cropH / sourceHeight) * 100
                                    
                                    return (
                                      <>
                                        {/* Left mask */}
                                        {leftPercent > 0 && (
                                          <rect 
                                            x="0" 
                                            y="0" 
                                            width={leftPercent} 
                                            height="100" 
                                            fill="black" 
                                            opacity="0.7"
                                          />
                                        )}
                                        
                                        {/* Right mask */}
                                        {(leftPercent + widthPercent) < 100 && (
                                          <rect 
                                            x={leftPercent + widthPercent} 
                                            y="0" 
                                            width={100 - (leftPercent + widthPercent)} 
                                            height="100" 
                                            fill="black" 
                                            opacity="0.7"
                                          />
                                        )}
                                        
                                        {/* Top mask */}
                                        {topPercent > 0 && (
                                          <rect 
                                            x={leftPercent} 
                                            y="0" 
                                            width={widthPercent} 
                                            height={topPercent} 
                                            fill="black" 
                                            opacity="0.7"
                                          />
                                        )}
                                        
                                        {/* Bottom mask */}
                                        {(topPercent + heightPercent) < 100 && (
                                          <rect 
                                            x={leftPercent} 
                                            y={topPercent + heightPercent} 
                                            width={widthPercent} 
                                            height={100 - (topPercent + heightPercent)} 
                                            fill="black" 
                                            opacity="0.7"
                                          />
                                        )}
                                        
                                        {/* Crop area border (green dashed) */}
                                        <rect 
                                          x={leftPercent} 
                                          y={topPercent} 
                                          width={widthPercent} 
                                          height={heightPercent} 
                                          fill="none" 
                                          stroke="#4ade80" 
                                          strokeWidth="0.5" 
                                          strokeDasharray="2,2"
                                        />
                                      </>
                                    )
                                  })()}
                                </svg>
                              </>
                            )}
                          </>
                        ) : (
                          <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
                            <p className="text-gray-400 text-sm">Loading preview...</p>
                          </div>
                        )}
                        
                        {/* Split Screen Mode Visualization */}
                        {candidate.crop_preview?.mode === 'split_screen' && candidate.crop_preview.left_face && candidate.crop_preview.right_face && (
                          <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                            {(() => {
                              const sourceWidth = 1920
                              const sourceHeight = 1080
                              
                              const leftFace = candidate.crop_preview.left_face
                              const rightFace = candidate.crop_preview.right_face
                              
                              // Calculate 1:1 crop areas for each face
                              const cropSize = sourceHeight / 2
                              
                              const leftCenterX = leftFace.x + leftFace.w / 2
                              const leftCenterY = leftFace.y + leftFace.h / 2
                              const rightCenterX = rightFace.x + rightFace.w / 2
                              const rightCenterY = rightFace.y + rightFace.h / 2
                              
                              // Convert to percentages
                              const leftX = ((leftCenterX - cropSize / 2) / sourceWidth) * 100
                              const leftY = ((leftCenterY - cropSize / 2) / sourceHeight) * 100
                              const rightX = ((rightCenterX - cropSize / 2) / sourceWidth) * 100
                              const rightY = ((rightCenterY - cropSize / 2) / sourceHeight) * 100
                              const size = (cropSize / sourceWidth) * 100
                              const sizeH = (cropSize / sourceHeight) * 100
                              
                              return (
                                <>
                                  {/* Darken everything */}
                                  <rect x="0" y="0" width="100" height="100" fill="black" opacity="0.7" />
                                  
                                  {/* Left face crop area (top half of final video) */}
                                  <rect 
                                    x={leftX} 
                                    y={leftY} 
                                    width={size} 
                                    height={sizeH} 
                                    fill="rgba(139, 92, 246, 0.3)" 
                                    stroke="#8b5cf6" 
                                    strokeWidth="0.5" 
                                    strokeDasharray="2,2"
                                  />
                                  
                                  {/* Right face crop area (bottom half of final video) */}
                                  <rect 
                                    x={rightX} 
                                    y={rightY} 
                                    width={size} 
                                    height={sizeH} 
                                    fill="rgba(139, 92, 246, 0.3)" 
                                    stroke="#8b5cf6" 
                                    strokeWidth="0.5" 
                                    strokeDasharray="2,2"
                                  />
                                  
                                  {/* Labels */}
                                  <text 
                                    x={leftX + size / 2} 
                                    y={leftY + 5} 
                                    fontSize="3" 
                                    fill="white" 
                                    textAnchor="middle" 
                                    fontWeight="bold"
                                  >
                                    TOP (Person 1)
                                  </text>
                                  <text 
                                    x={rightX + size / 2} 
                                    y={rightY + 5} 
                                    fontSize="3" 
                                    fill="white" 
                                    textAnchor="middle" 
                                    fontWeight="bold"
                                  >
                                    BOTTOM (Person 2)
                                  </text>
                                </>
                              )
                            })()}
                          </svg>
                        )}
                        
                        {/* Platform-specific UI overlay - aligned to current crop (manual or AI) */}
                            {safeZoneOverlayVisible && candidate.crop_preview && candidate.crop_preview.mode !== 'split_screen' && (
                              <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                                {(() => {
                                  const sourceWidth = 1920
                                  const sourceHeight = 1080
                                  const effectiveCropX = manualCropX[index] !== null && manualCropX[index] !== undefined
                                ? manualCropX[index]!
                                : candidate.crop_preview.crop_x
                              const cropX = effectiveCropX
                              const cropY = candidate.crop_preview.crop_y
                              const cropW = candidate.crop_preview.crop_width
                              const cropH = candidate.crop_preview.crop_height
                              
                              const leftPercent = (cropX / sourceWidth) * 100
                              const topPercent = (cropY / sourceHeight) * 100
                              const widthPercent = (cropW / sourceWidth) * 100
                              const heightPercent = (cropH / sourceHeight) * 100
                              
                              // Calculate platform UI zone height within crop
                              const uiZoneHeight = targetPlatform === 'tiktok' ? 35 : 
                                                  targetPlatform === 'youtube' ? 25 : 30
                              const uiZoneHeightPercent = (heightPercent * uiZoneHeight) / 100
                              
                              return (
                                <>
                                  {/* Bottom UI zone (red gradient) - within crop only */}
                                  <defs>
                                    <linearGradient id="uiGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                      <stop offset="0%" style={{stopColor: 'transparent', stopOpacity: 0}} />
                                      <stop offset="50%" style={{stopColor: 'rgba(0,0,0,0.8)', stopOpacity: 1}} />
                                      <stop offset="100%" style={{stopColor: 'rgba(0,0,0,0.9)', stopOpacity: 1}} />
                                    </linearGradient>
                                  </defs>
                                  
                                  <rect 
                                    x={leftPercent} 
                                    y={topPercent + heightPercent - uiZoneHeightPercent} 
                                    width={widthPercent} 
                                    height={uiZoneHeightPercent} 
                                    fill="url(#uiGradient)"
                                  />
                                  
                                  {/* Red tint for UI zone */}
                                  <rect 
                                    x={leftPercent} 
                                    y={topPercent + heightPercent - uiZoneHeightPercent} 
                                    width={widthPercent} 
                                    height={uiZoneHeightPercent} 
                                    fill="rgba(239, 68, 68, 0.15)"
                                  />
                                  
                                  {/* Subtitle safe zone line */}
                                  <line 
                                    x1={leftPercent} 
                                    y1={topPercent + heightPercent - uiZoneHeightPercent} 
                                    x2={leftPercent + widthPercent} 
                                    y2={topPercent + heightPercent - uiZoneHeightPercent} 
                                    stroke="#4ade80" 
                                    strokeWidth="0.3" 
                                    strokeDasharray="1,1"
                                  />
                                  {/* Right 15% of crop = Like/Comment buttons danger zone */}
                                  {(() => {
                                    const right15Width = widthPercent * 0.15
                                    const zoneLeft = leftPercent + widthPercent - right15Width
                                    return (
                                      <>
                                        <rect 
                                          x={zoneLeft} 
                                          y={topPercent} 
                                          width={right15Width} 
                                          height={heightPercent} 
                                          fill="rgba(239, 68, 68, 0.35)"
                                        />
                                        <line 
                                          x1={zoneLeft} 
                                          y1={topPercent} 
                                          x2={zoneLeft} 
                                          y2={topPercent + heightPercent} 
                                          stroke="#dc2626" 
                                          strokeWidth="0.5" 
                                          strokeDasharray="2,1"
                                        />
                                      </>
                                    )
                                  })()}
                                </>
                              )
                            })()}
                          </svg>
                        )}
                        
                        {/* Platform UI mockup - sidebar buttons (right 15%) + bottom; same position as crop */}
                        {safeZoneOverlayVisible && candidate.crop_preview && (
                          <div className="absolute inset-0 pointer-events-none">
                            {(() => {
                              const sourceWidth = 1920
                              const sourceHeight = 1080
                              const effectiveCropX = manualCropX[index] !== null && manualCropX[index] !== undefined
                                ? manualCropX[index]!
                                : candidate.crop_preview.crop_x
                              const cropX = effectiveCropX
                              const cropY = candidate.crop_preview.crop_y
                              const cropW = candidate.crop_preview.crop_width
                              const cropH = candidate.crop_preview.crop_height
                              
                              const leftPercent = (cropX / sourceWidth) * 100
                              const topPercent = (cropY / sourceHeight) * 100
                              const widthPercent = (cropW / sourceWidth) * 100
                              const heightPercent = (cropH / sourceHeight) * 100
                              
                              return (
                                <div 
                                  className="absolute"
                                  style={{
                                    left: `${leftPercent}%`,
                                    top: `${topPercent}%`,
                                    width: `${widthPercent}%`,
                                    height: `${heightPercent}%`
                                  }}
                                >
                                  {/* Right sidebar: Like / Comment / Share - show for ALL short-form (TikTok, YouTube Shorts, Reels) */}
                                  <div className="absolute top-1/4 right-2 space-y-2">
                                    <div className="w-8 h-8 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/30">
                                      <span className="text-white text-sm">❤️</span>
                                    </div>
                                    <div className="w-8 h-8 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/30">
                                      <span className="text-white text-sm">💬</span>
                                    </div>
                                    <div className="w-8 h-8 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/30">
                                      <span className="text-white text-sm">↗️</span>
                                    </div>
                                    {targetPlatform === 'tiktok' && (
                                      <div className="w-8 h-8 bg-black/40 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/30">
                                        <span className="text-white text-sm">🎵</span>
                                      </div>
                                    )}
                                  </div>
                                  
                                  {/* Platform label - bottom left */}
                                  <div className="absolute bottom-12 left-2">
                                    <span className="text-[10px] text-white/90 font-bold drop-shadow-lg">
                                      {targetPlatform === 'tiktok' && '🎵 TikTok'}
                                      {targetPlatform === 'youtube' && '▶️ YouTube Shorts'}
                                      {targetPlatform === 'instagram' && '📷 Reels'}
                                    </span>
                                  </div>
                                  
                                  {/* Subtitle safe zone label - above bottom UI */}
                                  <div 
                                    className="absolute left-0 right-0 flex justify-center"
                                    style={{
                                      bottom: targetPlatform === 'tiktok' ? '38%' : 
                                             targetPlatform === 'youtube' ? '28%' : '33%'
                                    }}
                                  >
                                    <span className="px-2 py-1 bg-green-500/90 text-white text-[9px] font-bold rounded shadow-lg">
                                      ✓ Subtitle safe zone
                                    </span>
                                  </div>
                                </div>
                              )
                            })()}
                          </div>
                        )}
                      </div>
                      <div className="mt-2 space-y-1">
                        {candidate.crop_preview?.mode === 'split_screen' ? (
                          <>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="inline-block w-2 h-2 bg-purple-400 rounded-full"></span>
                              <span className="font-semibold">Purple areas:</span> Two 1:1 crops stacked vertically
                            </p>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="inline-block w-2 h-2 bg-gray-700 rounded-full"></span>
                              <span className="font-semibold">Dark areas:</span> Cropped out
                            </p>
                            <p className="text-xs text-purple-600 font-semibold flex items-center gap-1">
                              ⚡ Detected: 2 People ({candidate.crop_preview.distance_percent?.toFixed(0)}% apart) - Split Screen Mode
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="inline-block w-2 h-2 bg-green-400 rounded-full"></span>
                              <span className="font-semibold">Green area:</span> Final 9:16 video
                            </p>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="inline-block w-2 h-2 bg-gray-700 rounded-full"></span>
                              <span className="font-semibold">Dark areas:</span> Cropped out
                            </p>
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="inline-block w-2 h-2 bg-red-400 rounded-full"></span>
                              {targetPlatform === 'tiktok' && 'Subtitles 280px from bottom - Clear of TikTok UI'}
                              {targetPlatform === 'youtube' && 'Subtitles 200px from bottom - Clear of YouTube UI'}
                              {targetPlatform === 'instagram' && 'Subtitles 250px from bottom - Clear of Instagram UI'}
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                    
                    {/* Manual Crop Control Slider - constrained to Safe Zone (face not in right 15%) */}
                    {candidate.crop_preview && candidate.crop_preview.mode !== 'split_screen' && candidate.crop_preview.crop_x !== undefined && (
                      <div className="mb-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-xs font-semibold text-blue-700">
                            🎯 Fine-tune Position (Safe Zone: face stays left of Like/Comment buttons)
                          </label>
                          <button
                            onClick={() => handleResetCrop(index)}
                            className="px-2 py-1 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors flex items-center gap-1"
                          >
                            <RotateCcw className="w-3 h-3" />
                            Reset
                          </button>
                        </div>
                        {(() => {
                          const cropW = candidate.crop_preview.crop_width ?? 608
                          const cropXDefault = candidate.crop_preview.crop_x
                          const faceCenterX = cropXDefault + cropW / 2
                          // Face must stay in left 75% of frame (well clear of right 15% Like/Comment buttons)
                          const faceMaxPositionInFrame = 0.75
                          const minCropX = Math.max(0, Math.floor(faceCenterX - faceMaxPositionInFrame * cropW))
                          const maxCropX = 1920 - cropW
                          const currentX = manualCropX[index] !== null && manualCropX[index] !== undefined
                            ? manualCropX[index]!
                            : cropXDefault
                          const clampedX = Math.min(maxCropX, Math.max(minCropX, currentX))
                          return (
                            <>
                              <input
                                type="range"
                                min={minCropX}
                                max={maxCropX}
                                step={2}
                                value={clampedX}
                                onChange={(e) => {
                                  const newValue = parseInt(e.target.value)
                                  setManualCropX(prev => ({ ...prev, [index]: newValue }))
                                }}
                                className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                              />
                              <div className="flex justify-between mt-1">
                                <span className="text-xs text-gray-500">Left (safe)</span>
                                <span className="text-xs text-blue-600 font-semibold">
                                  X: {clampedX}px
                                </span>
                                <span className="text-xs text-amber-600 font-medium">Right 15% = UI zone</span>
                              </div>
                            </>
                          )
                        })()}
                      </div>
                    )}
                    
                    <div className="mb-3">
                      <p className="text-xs font-semibold text-gray-500 mb-1">Why This Will Go Viral:</p>
                      <p className="text-sm text-gray-700 leading-relaxed">{candidate.reason}</p>
                    </div>
                    {segments.length > 0 && (() => {
                      const text = getCandidateText(candidate, index)
                      return text ? (
                        <div className="mb-3 p-2 bg-white border border-gray-200 rounded-lg">
                          <p className="text-xs font-semibold text-gray-400 mb-1">📝 Transcript:</p>
                          <p className="text-xs text-gray-600 leading-relaxed">{text}</p>
                        </div>
                      ) : null
                    })()}
                  </div>
                  <div className="ml-4 flex flex-col gap-2 min-w-[200px]">
                    {!renderedClip ? (
                      <>
                        <button
                          onClick={() => handleRenderClip(index)}
                          disabled={isRendering}
                          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition-colors flex items-center gap-2 whitespace-nowrap shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isRendering ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Rendering...
                            </>
                          ) : (
                            <>
                              <Scissors className="w-4 h-4" />
                              Render This Clip
                            </>
                          )}
                        </button>
                        
                        {/* Progress Bar / Queue Indicator */}
                        {isRendering && (
                          <div className="w-full">
                            {renderStatus[index]?.startsWith('queued:') ? (
                              <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-center">
                                <span className="text-xs font-semibold text-amber-700">
                                  ⏳ Ожидание в очереди... Перед вами {parseInt(renderStatus[index].split(':')[1]) - 1} видео
                                </span>
                              </div>
                            ) : renderProgress[index] !== undefined ? (
                              <>
                                <div className="flex justify-between items-center mb-1">
                                  <span className="text-xs font-medium text-gray-700">
                                    {renderStatus[index] || 'Processing...'}
                                  </span>
                                  <span className="text-xs font-bold text-purple-600">
                                    {renderProgress[index]}%
                                  </span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                                  <div
                                    className="bg-gradient-to-r from-purple-600 to-pink-600 h-2.5 rounded-full transition-all duration-300 ease-out"
                                    style={{ width: `${renderProgress[index]}%` }}
                                  />
                                </div>
                              </>
                            ) : null}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex flex-col gap-2">
                        <button
                          onClick={() => handleDownloadClip(renderedClip.clip_id, renderedClip.downloadUrl, index)}
                          disabled={downloadingClips.has(index)}
                          className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-colors flex items-center gap-2 whitespace-nowrap shadow-lg disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                          {downloadingClips.has(index) ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Скачивается...
                            </>
                          ) : (
                            <>
                              <Download className="w-4 h-4" />
                              Download
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => handleRerender(index)}
                          className="px-4 py-2 bg-white border border-purple-300 text-purple-700 text-xs font-semibold rounded-lg hover:bg-purple-50 transition-colors flex items-center gap-1.5 whitespace-nowrap"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Re-render
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Step 7: Ready Clips Section ─────────────────────────────── */}
      {renderedClips.length > 0 && (
        <div className="mt-8 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-green-200">
            <Download className="w-6 h-6 text-green-600" />
            <h3 className="font-bold text-gray-800 text-xl">Готовые ролики ({renderedClips.length})</h3>
          </div>
          {renderedClips.map((clip) => {
            const cidx = clip.candidateIndex ?? (clip.clip_id - 1)
            const meta = clipMeta[cidx]
            return (
              <div key={clip.clip_id} className="p-5 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-gray-800 text-lg truncate">{clip.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{clip.filename}</p>
                    {meta && (
                      <div className="mt-3 space-y-2">
                        <div className="p-3 bg-white rounded-lg border border-green-200">
                          <p className="text-xs font-semibold text-gray-500 mb-1">📱 Title</p>
                          <p className="text-sm font-bold text-gray-800">{meta.title}</p>
                        </div>
                        {meta.description && (
                          <div className="p-3 bg-white rounded-lg border border-green-200">
                            <p className="text-xs font-semibold text-gray-500 mb-1">📝 Caption</p>
                            <p className="text-sm text-gray-700">{meta.description}</p>
                          </div>
                        )}
                        {meta.hashtags && meta.hashtags.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {meta.hashtags.map((tag: string, i: number) => (
                              <span key={i} className="text-xs text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded-full">{tag}</span>
                            ))}
                          </div>
                        )}
                        {meta.cta && (
                          <p className="text-xs text-emerald-700 font-semibold">{meta.cta}</p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => handleDownloadClip(clip.clip_id, clip.downloadUrl)}
                      className="px-5 py-2.5 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition-colors flex items-center gap-2 shadow"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                    {meta && (
                      <button
                        onClick={() => handleCopyMeta(cidx)}
                        className="px-5 py-2.5 bg-white border-2 border-green-400 text-green-700 font-semibold rounded-lg hover:bg-green-50 transition-colors flex items-center gap-2"
                      >
                        {copiedMeta === cidx ? '✓ Copied!' : '📋 Copy Meta'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
