'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'

type StepState = 'queue' | 'run' | 'done' | 'error'

interface LogEntry {
  ts: string
  msg: string
}

interface TranscriptSegment {
  start: number
  end: number
  text: string
}

interface Candidate {
  start_time: number
  end_time: number
  title: string
  reason: string
  virality_score: number
  hook?: string
  emojis?: string[]
  description?: string
  hashtags?: string[]
}

function formatTime(sec: number): string {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.floor(sec % 60)
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }
  return `${m}:${s.toString().padStart(2, '0')}`
}

function viralEmoji(score: number): string {
  if (score >= 9.2) return '🔥'
  if (score >= 9.0) return '⚡'
  if (score >= 8.5) return '🌟'
  return ''
}

function virPillColor(score: number): string {
  if (score >= 9) return 'var(--pink)'
  if (score >= 8) return 'var(--yellow)'
  return 'var(--lilac)'
}

export default function ProcessPage() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const fileId = params.fileId as string

  const platform = searchParams.get('platform') || 'tiktok'
  const maxClips = parseInt(searchParams.get('max_clips') || '5', 10)

  const [uploadState] = useState<StepState>('done')
  const [transcribeState, setTranscribeState] = useState<StepState>('run')
  const [analyzeState, setAnalyzeState] = useState<StepState>('queue')
  const [renderState] = useState<StepState>('queue')

  const [transcribeProgress, setTranscribeProgress] = useState<{ progress: number; total: number } | null>(null)
  const [analyzeBarWidth, setAnalyzeBarWidth] = useState(0)

  // Transcript stream state
  const [transcriptSegments, setTranscriptSegments] = useState<TranscriptSegment[]>([])
  const [transcriptDone, setTranscriptDone] = useState(false)

  // Candidates state
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  const [log, setLog] = useState<LogEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const analyzeBarRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const transcriptPollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const streamRef = useRef<HTMLDivElement>(null)

  const addLog = useCallback((msg: string) => {
    const now = new Date()
    const ts = `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
    setLog(prev => [...prev.slice(-49), { ts, msg }])
  }, [])

  const clearPoll = () => {
    if (pollRef.current != null) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const clearAnalyzeBar = () => {
    if (analyzeBarRef.current != null) {
      clearInterval(analyzeBarRef.current)
      analyzeBarRef.current = null
    }
  }

  const clearTranscriptPoll = () => {
    if (transcriptPollRef.current != null) {
      clearInterval(transcriptPollRef.current)
      transcriptPollRef.current = null
    }
  }

  // Poll partial transcript for the stream panel
  const startTranscriptStream = useCallback(() => {
    const fetchTranscript = async () => {
      try {
        const { data } = await api.get(`/transcription/${fileId}`)
        const segs: TranscriptSegment[] = (data.segments || []).filter((s: TranscriptSegment) => s.text && s.text.trim())
        if (segs.length > 0) {
          setTranscriptSegments(segs)
        }
      } catch {
        // transcription not ready yet — silent fail
      }
    }
    void fetchTranscript()
    transcriptPollRef.current = setInterval(() => void fetchTranscript(), 3000)
  }, [fileId])

  const runAnalyze = useCallback(async () => {
    setAnalyzeState('run')
    setAnalyzeBarWidth(10)
    addLog('Клод изучает транскрипцию...')

    analyzeBarRef.current = setInterval(() => {
      setAnalyzeBarWidth(prev => Math.min(96, prev + Math.random() * 3))
    }, 700)

    try {
      const res = await api.post(`/analyze/${fileId}?provider=claude&max_clips=${maxClips}&platform=${platform}`)
      clearAnalyzeBar()
      setAnalyzeBarWidth(100)
      setAnalyzeState('done')

      // Load candidates from result or from API
      let rawCandidates: Candidate[] = []
      if (res.data && Array.isArray(res.data.candidates)) {
        rawCandidates = res.data.candidates
      } else if (Array.isArray(res.data)) {
        rawCandidates = res.data
      } else {
        // Fetch separately
        try {
          const candRes = await api.get(`/clips/${fileId}/candidates`)
          rawCandidates = Array.isArray(candRes.data.candidates) ? candRes.data.candidates : []
        } catch {
          rawCandidates = []
        }
      }

      setCandidates(rawCandidates)
      // Select top 3 by default
      const top3 = new Set<number>()
      const sorted = [...rawCandidates].map((c, i) => ({ c, i })).sort((a, b) => b.c.virality_score - a.c.virality_score)
      sorted.slice(0, 3).forEach(({ i }) => top3.add(i))
      setSelectedIds(top3)

      addLog(`Анализ завершён — найдено ${rawCandidates.length} кандидатов`)
    } catch (err: any) {
      clearAnalyzeBar()
      setAnalyzeState('error')
      const msg = err.response?.data?.detail || 'Ошибка анализа'
      setError(msg)
      addLog(`Ошибка: ${msg}`)
    }
  }, [fileId, maxClips, platform, addLog])

  const runTranscribe = useCallback(async () => {
    setTranscribeState('run')
    addLog('Запуск транскрипции...')

    try {
      await api.post(`/transcribe/${fileId}`)
    } catch (err: any) {
      setTranscribeState('error')
      const msg = err.response?.data?.detail || 'Ошибка запуска транскрипции'
      setError(msg)
      addLog(`Ошибка: ${msg}`)
      return
    }

    startTranscriptStream()

    const pollOnce = async (): Promise<boolean> => {
      try {
        const { data } = await api.get(`/transcribe/${fileId}/status`)
        if (data.status === 'processing') {
          const tot = Number(data.total_chunks) || 0
          const prog = Number(data.progress) || 0
          if (tot > 0) {
            setTranscribeProgress({ progress: prog, total: tot })
            addLog(`Транскрипция: ${prog}/${tot} чанков`)
          }
          return false
        }
        if (data.status === 'done') {
          setTranscribeProgress(null)
          setTranscribeState('done')
          setTranscriptDone(true)
          addLog('Транскрипция готова!')
          clearPoll()
          clearTranscriptPoll()
          // Final transcript fetch
          try {
            const { data: td } = await api.get(`/transcription/${fileId}`)
            const segs: TranscriptSegment[] = (td.segments || []).filter((s: TranscriptSegment) => s.text && s.text.trim())
            if (segs.length > 0) setTranscriptSegments(segs)
          } catch {}
          await runAnalyze()
          return true
        }
        if (data.status === 'failed') {
          setTranscribeState('error')
          const msg = typeof data.error === 'string' ? data.error : 'Транскрипция упала'
          setError(msg)
          addLog(`Ошибка: ${msg}`)
          clearPoll()
          clearTranscriptPoll()
          return true
        }
      } catch (e: any) {
        setTranscribeState('error')
        const msg = e.response?.data?.detail || 'Ошибка опроса статуса'
        setError(msg)
        addLog(`Ошибка: ${msg}`)
        clearPoll()
        clearTranscriptPoll()
        return true
      }
      return false
    }

    const stop = await pollOnce()
    if (stop) return

    pollRef.current = setInterval(() => {
      void (async () => {
        try {
          if (await pollOnce()) clearPoll()
        } catch {
          clearPoll()
        }
      })()
    }, 2000)
  }, [fileId, addLog, runAnalyze, startTranscriptStream])

  useEffect(() => {
    void runTranscribe()
    return () => {
      clearPoll()
      clearAnalyzeBar()
      clearTranscriptPoll()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [log])

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight
    }
  }, [transcriptSegments])

  const steps: { label: string; meta: string; state: StepState }[] = [
    {
      label: 'Загрузка',
      meta: 'Видео принято сервером',
      state: uploadState,
    },
    {
      label: 'Транскрипция',
      meta: transcribeProgress
        ? `Whisper · ${transcribeProgress.progress}/${transcribeProgress.total} чанков`
        : transcribeState === 'done'
        ? 'Whisper · готово'
        : 'Whisper расшифровывает...',
      state: transcribeState,
    },
    {
      label: 'Анализ ✨',
      meta:
        analyzeState === 'run'
          ? 'Claude ищет вирусные моменты · ~12 сек'
          : analyzeState === 'done'
          ? 'Кандидаты найдены'
          : 'ждём транскрипцию',
      state: analyzeState,
    },
    {
      label: 'Рендер',
      meta: 'ждём твоего выбора кандидатов',
      state: renderState,
    },
  ]

  const checkSvg = (
    <svg style={{ position: 'absolute', top: -12, right: 14, width: 28, height: 28 }} viewBox="0 0 28 28">
      <circle cx="14" cy="14" r="12" fill="#B8E6CC" stroke="#3A2E2A" strokeWidth="2.5" />
      <path d="M8 14 L13 19 L21 10" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )

  const toggleCandidate = (idx: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const handleRenderSelected = async () => {
    if (selectedIds.size === 0) return
    const indices = Array.from(selectedIds)
    for (const idx of indices) {
      try {
        await api.post(`/render-clip`, {
          file_id: fileId,
          clip_index: idx,
          platform,
          subtitle_style: 'podcast',
          render_mode: 'blur_background',
          enable_jump_cut: false,
          enable_filler_removal: false,
        })
      } catch {}
    }
    router.push(`/render/${fileId}/${indices[0] + 1}`)
  }

  const selectedCount = selectedIds.size
  const totalCount = candidates.length

  const isProcessing = transcribeState === 'run' || analyzeState === 'run'

  return (
    <>
      <style>{`
        :root {
          --cream: #FFF3D6; --cream-2: #FFE9B8; --paper: #FFFCF1; --ink: #3A2E2A;
          --ink-soft: #6B574F; --pink: #FF8FA3; --pink-deep: #E96A85;
          --yellow: #FFD166; --yellow-deep: #F4B829; --teal: #7DD3C0;
          --lilac: #C9B6E4; --mint: #B8E6CC;
        }
        *, *::before, *::after { box-sizing: border-box; }
        html, body { margin: 0; padding: 0; }
        body {
          font-family: "Patrick Hand", sans-serif; color: var(--ink); font-size: 18px;
          background: var(--cream);
          background-image:
            radial-gradient(circle at 8% 8%, rgba(255,209,102,.4) 0, transparent 28%),
            radial-gradient(circle at 96% 14%, rgba(255,143,163,.3) 0, transparent 26%),
            radial-gradient(circle at 96% 92%, rgba(125,211,192,.32) 0, transparent 28%),
            radial-gradient(circle at 4% 92%, rgba(201,182,228,.3) 0, transparent 28%);
          min-height: 100vh;
        }
        h1, h2, h3 { font-family: "Caveat", cursive; font-weight: 700; margin: 0; letter-spacing: .5px; }
        a { color: inherit; text-decoration: none; }
        button { font-family: inherit; color: inherit; cursor: pointer; }

        .navbar {
          max-width: 1280px; margin: 0 auto; padding: 18px 28px;
          display: flex; justify-content: space-between; align-items: center; gap: 24px;
        }
        .logo {
          display: flex; align-items: center; gap: 8px;
          font-family: "Caveat", cursive; font-weight: 700; font-size: 30px;
        }
        .logo .mark {
          width: 34px; height: 34px; display: grid; place-items: center;
          background: var(--yellow); border: 3px solid var(--ink);
          border-radius: 14px 12px 16px 10px / 12px 14px 10px 16px;
          box-shadow: 2px 3px 0 var(--ink); transform: rotate(-4deg);
        }
        .logo .gold { color: var(--yellow-deep); text-shadow: 1px 2px 0 var(--ink); }
        .nav-right { display: flex; gap: 16px; align-items: center; }
        .beta-badge {
          display: inline-flex; align-items: center; gap: 6px;
          font-family: "Caveat", cursive; font-size: 20px; line-height: 1;
          background: var(--mint); border: 2.5px solid var(--ink);
          border-radius: 12px 16px 10px 14px / 14px 10px 16px 12px;
          padding: 4px 12px 2px; box-shadow: 2px 3px 0 var(--ink); transform: rotate(-1.5deg);
        }
        .crumbs {
          max-width: 1280px; margin: 0 auto; padding: 0 28px 6px;
          display: flex; align-items: center; gap: 10px; color: var(--ink-soft); font-size: 16px;
        }
        .crumbs a:hover { color: var(--pink-deep); }
        .wrap { max-width: 1280px; margin: 0 auto; padding: 6px 28px 64px; }
        .head h1 { font-size: 54px; line-height: 1; }
        .head .sub { color: var(--ink-soft); margin-top: 6px; font-size: 17px; }

        /* Pipeline steps */
        .pipe {
          display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin: 22px 0 26px;
        }
        @media (max-width: 880px) { .pipe { grid-template-columns: repeat(2,1fr); } }
        .step {
          background: var(--paper); border: 3px solid var(--ink);
          border-radius: 18px 22px 16px 20px / 18px 16px 22px 20px;
          box-shadow: 4px 5px 0 var(--ink); padding: 14px 16px; position: relative;
        }
        .step.done { background: var(--mint); }
        .step.run { background: var(--yellow); }
        .step.queue { background: #fff; opacity: .7; }
        .step.error { background: #FECDD3; }
        .step .n {
          position: absolute; top: -14px; left: 14px;
          width: 30px; height: 30px; border-radius: 50%; border: 2.5px solid var(--ink);
          background: #fff; display: grid; place-items: center;
          font-family: "Caveat", cursive; font-size: 20px; line-height: 1;
          box-shadow: 2px 2px 0 var(--ink);
        }
        .step.done .n { background: var(--mint); }
        .step.run .n { background: var(--yellow); animation: wob 1.4s ease-in-out infinite; }
        @keyframes wob { 0%,100%{transform:rotate(-6deg)} 50%{transform:rotate(6deg)} }
        .step .ttl { font-family: "Caveat", cursive; font-size: 24px; line-height: 1; margin-top: 6px; }
        .step .meta { color: var(--ink-soft); font-size: 14px; margin-top: 4px; line-height: 1.2; }
        .step.done .meta, .step.run .meta { color: var(--ink); }
        .bar {
          height: 10px; background: #fff; border: 2px solid var(--ink);
          border-radius: 6px; overflow: hidden; box-shadow: 1px 2px 0 var(--ink); margin-top: 8px;
        }
        .bar > span {
          display: block; height: 100%; background: var(--pink);
          border-right: 2px solid var(--ink); transition: width .4s ease;
        }

        /* 2-col grid */
        .main-grid {
          display: grid; grid-template-columns: 1fr 1.6fr; gap: 32px; align-items: start;
        }
        @media (max-width: 860px) { .main-grid { grid-template-columns: 1fr; } }

        /* Cards */
        .card {
          background: var(--paper); border: 3px solid var(--ink);
          box-shadow: 6px 8px 0 var(--ink); padding: 22px 24px;
        }
        .card.tilt-l {
          border-radius: 28px 24px 30px 22px / 24px 28px 22px 30px;
          transform: rotate(-.6deg);
        }
        .card.tilt-r {
          border-radius: 24px 30px 22px 28px / 28px 24px 30px 22px;
          transform: rotate(.4deg);
        }
        .card h2 { font-size: 30px; }
        .card .hint { color: var(--ink-soft); font-size: 15px; margin-bottom: 12px; }

        /* Source video preview */
        .source-preview {
          aspect-ratio: 16/9;
          border: 3px solid var(--ink);
          border-radius: 18px;
          box-shadow: 5px 6px 0 var(--ink);
          background: linear-gradient(180deg, #2A2A40 0%, #4B3F6E 100%);
          position: relative; overflow: hidden;
          display: grid; place-items: center;
        }
        .source-preview .play-btn {
          width: 62px; height: 62px; border-radius: 50%;
          background: #fff; border: 3px solid var(--ink);
          box-shadow: 3px 4px 0 var(--ink);
          display: grid; place-items: center;
        }
        .source-preview .meta-row {
          position: absolute; left: 10px; right: 10px; bottom: 10px;
          display: flex; justify-content: space-between;
          font-family: "Caveat", cursive; color: #fff; font-size: 18px;
        }
        .source-preview .pill {
          background: rgba(0,0,0,.6); border: 2px solid #fff;
          padding: 1px 10px 0; border-radius: 10px;
        }
        .video-info {
          margin-top: 14px; font-size: 16px; color: var(--ink-soft); line-height: 1.4;
        }
        .video-info b { color: var(--ink); }

        /* Transcript stream */
        .stream {
          background: #fff; border: 3px solid var(--ink);
          border-radius: 16px 20px 14px 18px / 18px 14px 20px 16px;
          box-shadow: 3px 4px 0 var(--ink);
          padding: 14px 16px; max-height: 240px; overflow-y: auto;
          font-family: "Patrick Hand", sans-serif; font-size: 16px; line-height: 1.45;
        }
        .stream .ts {
          color: var(--pink-deep); font-family: "Caveat", cursive;
          font-size: 18px; margin-right: 6px;
        }
        .stream .new { background: var(--cream-2); padding: 0 4px; border-radius: 3px; }
        .cursor {
          display: inline-block; width: 8px; height: 18px;
          background: var(--ink); vertical-align: -3px;
          animation: blink 1s steps(2) infinite;
        }
        @keyframes blink { 50% { opacity: 0; } }

        /* Candidate rows */
        .cand-list { margin-top: 4px; }
        .cand-row {
          display: flex; align-items: center; gap: 14px;
          background: #fff; border: 2.5px solid var(--ink);
          border-radius: 16px 20px 14px 18px / 18px 14px 20px 16px;
          box-shadow: 3px 4px 0 var(--ink);
          padding: 12px 14px; margin-bottom: 10px;
        }
        .cand-row.top { background: var(--cream-2); }
        .cand-row .vir-pill {
          flex: none; font-family: "Caveat", cursive; font-size: 24px; line-height: 1;
          padding: 6px 12px 4px; border: 2.5px solid var(--ink);
          border-radius: 12px 16px 10px 14px / 14px 10px 16px 12px;
          box-shadow: 2px 2px 0 var(--ink);
          min-width: 64px; text-align: center;
        }
        .cand-row .body { flex: 1; min-width: 0; }
        .cand-row .ttl { font-family: "Caveat", cursive; font-size: 22px; line-height: 1.05; }
        .cand-row .sub { color: var(--ink-soft); font-size: 14px; margin-top: 3px; line-height: 1.2; }
        .cand-row .actions { flex: none; display: flex; gap: 8px; align-items: center; }
        .btn-s {
          font-family: "Caveat", cursive; font-size: 18px; line-height: 1;
          background: #fff; border: 2.5px solid var(--ink);
          padding: 6px 12px 4px;
          border-radius: 12px 16px 10px 14px / 14px 10px 16px 12px;
          box-shadow: 2px 2px 0 var(--ink);
          transition: transform .1s, box-shadow .1s;
        }
        .btn-s:hover { transform: translate(-1px,-1px); box-shadow: 3px 3px 0 var(--ink); }
        .cand-checkbox {
          width: 22px; height: 22px; border: 2.5px solid var(--ink);
          border-radius: 6px; cursor: pointer; accent-color: var(--pink);
        }

        /* Pick bar */
        .pick-bar {
          margin-top: 18px; padding: 14px 18px;
          background: var(--paper); border: 3px solid var(--ink);
          border-radius: 20px 24px 18px 22px / 18px 22px 24px 20px;
          box-shadow: 4px 5px 0 var(--ink);
          display: flex; justify-content: space-between; align-items: center;
          gap: 14px; flex-wrap: wrap;
        }
        .pick-bar .pick-info {
          font-family: "Caveat", cursive; font-size: 22px; color: var(--ink); margin: 0;
        }
        .btn-big {
          font-family: "Caveat", cursive; font-weight: 700; font-size: 26px;
          background: var(--pink); color: #fff; border: 3px solid var(--ink);
          border-radius: 20px 16px 22px 18px / 16px 20px 18px 22px;
          padding: 9px 22px 7px; box-shadow: 5px 6px 0 var(--ink);
          text-shadow: 1px 1px 0 rgba(58,46,42,.35);
          transition: transform .12s, box-shadow .12s, background .15s;
        }
        .btn-big:hover { transform: translate(-2px,-2px) rotate(-1deg); box-shadow: 7px 8px 0 var(--ink); background: var(--pink-deep); }
        .btn-big:disabled { opacity: .5; cursor: not-allowed; transform: none; box-shadow: 5px 6px 0 var(--ink); }

        /* Waiting/analyzing state for right panel */
        .analyzing-placeholder {
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          gap: 14px; padding: 40px 20px; text-align: center;
        }
        .analyzing-dino { font-size: 64px; animation: dino-bob 1.2s ease-in-out infinite; }
        @keyframes dino-bob { 0%,100%{transform:translateY(0) rotate(-3deg)} 50%{transform:translateY(-12px) rotate(3deg)} }
        .analyzing-text { font-family: "Caveat", cursive; font-size: 26px; }
        .analyzing-sub { color: var(--ink-soft); font-size: 15px; }

        /* Log box */
        .log-box {
          background: #fff; border: 3px solid var(--ink);
          border-radius: 16px 20px 14px 18px / 18px 14px 20px 16px;
          box-shadow: 3px 4px 0 var(--ink);
          padding: 14px 16px; max-height: 220px; overflow-y: auto;
          font-size: 15px; line-height: 1.5;
        }
        .log-box .log-ts { color: var(--pink-deep); font-family: "Caveat", cursive; font-size: 17px; margin-right: 6px; }
        .log-box .log-new { background: var(--cream-2); padding: 0 4px; border-radius: 3px; }

        /* Error */
        .error-box {
          background: #FEF2F2; border: 3px solid #F87171; padding: 16px 20px;
          border-radius: 18px; box-shadow: 4px 5px 0 #F87171; color: #991B1B; margin-bottom: 20px;
          font-family: "Caveat", cursive; font-size: 22px;
        }
        .btn-cancel {
          font-family: "Caveat", cursive; font-size: 22px; line-height: 1;
          background: #fff; border: 2.5px solid var(--ink);
          border-radius: 14px 18px 12px 16px / 16px 12px 18px 14px;
          box-shadow: 3px 4px 0 var(--ink); padding: 8px 20px 6px; margin-top: 20px;
          transition: transform .12s, box-shadow .12s;
        }
        .btn-cancel:hover { transform: translate(-1px,-1px); box-shadow: 4px 5px 0 var(--ink); }
      `}</style>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;600;700&family=Patrick+Hand&display=swap" rel="stylesheet" />

      <nav className="navbar">
        <a className="logo" href="/">
          <span className="mark">
            <svg width="22" height="22" viewBox="0 0 26 26">
              <path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/>
            </svg>
          </span>
          Clips<span className="gold">Gold</span>
        </a>
        <div className="nav-right">
          <div className="beta-badge">🦖 <b>Beta · бесплатно</b></div>
        </div>
      </nav>

      <div className="crumbs">
        <a href="/app">← Студия</a>
        <span style={{ opacity: 0.5 }}>/</span>
        <span>{fileId}</span>
        <span style={{ opacity: 0.5 }}>/</span>
        <span style={{ color: 'var(--ink)' }}>Обработка</span>
      </div>

      <div className="wrap">
        <div className="head">
          <h1>
            Динозаврик <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 3px 0 var(--ink)' }}>работает</span> 🦖
          </h1>
          <div className="sub">Транскрипция → анализ → кандидаты → рендер. Можно закрыть вкладку, мы пришлём уведомление.</div>
        </div>

        {/* Pipeline steps */}
        <div className="pipe">
          {steps.map((step, i) => (
            <div key={i} className={`step ${step.state}`}>
              <div className="n">{i + 1}</div>
              {step.state === 'done' && checkSvg}
              <div className="ttl">{step.label}</div>
              <div className="meta">{step.meta}</div>
              {step.state === 'run' && i === 2 && (
                <div className="bar">
                  <span style={{ width: `${analyzeBarWidth}%` }} />
                </div>
              )}
              {step.state === 'run' && i === 1 && transcribeProgress && transcribeProgress.total > 0 && (
                <div className="bar">
                  <span style={{ width: `${Math.round(100 * transcribeProgress.progress / transcribeProgress.total)}%` }} />
                </div>
              )}
            </div>
          ))}
        </div>

        {error && (
          <div className="error-box">
            ❌ {error}
          </div>
        )}

        {/* Main 2-column layout */}
        <div className="main-grid">

          {/* LEFT COLUMN: source card + transcript stream */}
          <div style={{ display: 'grid', gap: 18 }}>

            {/* Source video card */}
            <div className="card tilt-l">
              <h2>Исходник</h2>
              <div className="hint">Видео принято и готово к обработке.</div>
              <div className="source-preview">
                <div className="play-btn">
                  <svg width="22" height="22" viewBox="0 0 24 24">
                    <path d="M5 4 L20 12 L5 20 Z" fill="#3A2E2A" />
                  </svg>
                </div>
                <div className="meta-row">
                  <span className="pill">
                    {transcribeProgress
                      ? `${transcribeProgress.progress}/${transcribeProgress.total} чанков`
                      : transcribeState === 'done'
                      ? '✓ транскрипция'
                      : '⏳ транскрипция'}
                  </span>
                  <span className="pill">
                    {analyzeState === 'done'
                      ? `${candidates.length} клипов`
                      : platform === 'tiktok'
                      ? 'TikTok'
                      : platform === 'youtube'
                      ? 'YouTube'
                      : platform}
                  </span>
                </div>
              </div>
              <div className="video-info">
                <b style={{ fontFamily: 'Caveat, cursive', fontSize: 22 }}>{fileId}</b><br />
                {transcribeState === 'done' && transcriptSegments.length > 0 && (
                  <>
                    {transcriptSegments.length} сегментов · ~{transcriptSegments.reduce((a, s) => a + s.text.split(' ').length, 0).toLocaleString()} слов
                  </>
                )}
                {transcribeState === 'run' && (
                  <span style={{ color: 'var(--pink-deep)' }}>Whisper расшифровывает...</span>
                )}
                {analyzeState === 'run' && (
                  <span style={{ color: 'var(--yellow-deep)' }}> · Claude анализирует...</span>
                )}
              </div>
            </div>

            {/* Live transcript stream card */}
            <div className="card tilt-r">
              <h2>Поток транскрипции</h2>
              <div className="hint">То, что Whisper уже распознал.</div>
              <div className="stream" ref={streamRef}>
                {transcriptSegments.length === 0 && (
                  <div style={{ color: 'var(--ink-soft)' }}>
                    {transcribeState === 'run'
                      ? 'Ожидаем первые слова...'
                      : 'Транскрипция начнётся скоро...'}
                  </div>
                )}
                {transcriptSegments.map((seg, i) => {
                  const isLast = i === transcriptSegments.length - 1
                  const isNew = i >= transcriptSegments.length - 3
                  return (
                    <div key={i}>
                      <span className="ts">{formatTime(seg.start)}</span>
                      {isNew && !transcriptDone
                        ? <span className="new">{seg.text}</span>
                        : seg.text}
                      {isLast && !transcriptDone && (
                        <span className="cursor" />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Log panel (below the two left cards) */}
            <div>
              <h2 style={{ fontFamily: 'Caveat, cursive', fontSize: 24, marginBottom: 10 }}>Лог обработки</h2>
              <div className="log-box" ref={logRef}>
                {log.length === 0 && (
                  <div style={{ color: 'var(--ink-soft)' }}>Ожидаем события...</div>
                )}
                {log.map((entry, i) => (
                  <div key={i} className={i === log.length - 1 ? 'log-new' : ''}>
                    <span className="log-ts">{entry.ts}</span>{entry.msg}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: candidates panel */}
          <div className="card tilt-l">
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
              <h2>Вирусные моменты 🦖</h2>
              {candidates.length > 0 && (
                <span style={{ color: 'var(--ink-soft)', fontSize: 15 }}>
                  найдено {candidates.length} моментов
                </span>
              )}
            </div>
            <div className="hint">
              {analyzeState === 'done'
                ? 'Чем горячее — тем выше шанс залететь. Ставь галочки и жми Рендерить.'
                : 'Кандидаты появятся после анализа.'}
            </div>

            {/* Waiting states */}
            {(transcribeState === 'run' || analyzeState === 'run') && candidates.length === 0 && (
              <div className="analyzing-placeholder">
                <div className="analyzing-dino">🦖</div>
                <div className="analyzing-text">
                  {transcribeState === 'run'
                    ? 'Расшифровываю речь...'
                    : 'Ищу вирусные моменты...'}
                </div>
                <div className="analyzing-sub">
                  {transcribeState === 'run'
                    ? 'Whisper слушает аудио'
                    : 'Claude изучает транскрипцию'}
                </div>
                {analyzeState === 'run' && (
                  <div className="bar" style={{ width: '100%', maxWidth: 280 }}>
                    <span style={{ width: `${analyzeBarWidth}%` }} />
                  </div>
                )}
              </div>
            )}

            {/* Candidate list */}
            {candidates.length > 0 && (
              <div className="cand-list">
                {candidates.map((cand, idx) => {
                  const isTop = cand.virality_score >= 9
                  const isSelected = selectedIds.has(idx)
                  const dur = cand.end_time - cand.start_time
                  return (
                    <div key={idx} className={`cand-row${isTop ? ' top' : ''}`}>
                      <div
                        className="vir-pill"
                        style={{
                          background: virPillColor(cand.virality_score),
                          color: cand.virality_score >= 9 ? '#fff' : 'var(--ink)',
                          textShadow: cand.virality_score >= 9 ? '1px 1px 0 rgba(58,46,42,.35)' : 'none',
                        }}
                      >
                        {viralEmoji(cand.virality_score)} {cand.virality_score.toFixed(1)}
                      </div>
                      <div className="body">
                        <div className="ttl">{cand.title}</div>
                        <div className="sub">
                          {formatTime(Math.round(cand.start_time))} → {formatTime(Math.round(cand.end_time))} · {formatTime(Math.round(dur))}
                          {cand.hook ? ` · «${cand.hook}»` : ''}
                        </div>
                      </div>
                      <div className="actions">
                        <button
                          className="btn-s"
                          onClick={() => router.push(`/render/${fileId}/${idx + 1}`)}
                          title="Редактировать и рендерить"
                        >
                          ▶ превью
                        </button>
                        <input
                          type="checkbox"
                          className="cand-checkbox"
                          checked={isSelected}
                          onChange={() => toggleCandidate(idx)}
                          title={isSelected ? 'Снять выбор' : 'Выбрать для рендера'}
                        />
                      </div>
                    </div>
                  )
                })}

                {/* Pick bar */}
                <div className="pick-bar">
                  <div className="pick-info">
                    Выбрано: <b>{selectedCount} из {totalCount}</b>
                  </div>
                  <button
                    className="btn-big"
                    disabled={selectedCount === 0}
                    onClick={handleRenderSelected}
                  >
                    Рендерить {selectedCount > 0 ? `${selectedCount} клип${selectedCount === 1 ? '' : selectedCount < 5 ? 'а' : 'ов'}` : 'клипы'} 🦖
                  </button>
                </div>
              </div>
            )}

            {/* Error state in right panel */}
            {analyzeState === 'error' && candidates.length === 0 && (
              <div style={{
                textAlign: 'center', padding: '24px 12px',
                color: 'var(--ink-soft)', fontFamily: 'Caveat, cursive', fontSize: 22,
              }}>
                ❌ Ошибка анализа. Попробуйте ещё раз.
              </div>
            )}
          </div>

        </div>

        <button className="btn-cancel" onClick={() => router.push('/app')}>
          ← Отмена
        </button>
      </div>
    </>
  )
}
