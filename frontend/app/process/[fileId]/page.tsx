'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import { api, getToken } from '@/lib/api'

type StepState = 'queue' | 'run' | 'done' | 'error'

interface LogEntry {
  ts: string
  msg: string
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
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
  const [log, setLog] = useState<LogEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const analyzeBarRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

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

  const runAnalyze = useCallback(async () => {
    setAnalyzeState('run')
    setAnalyzeBarWidth(10)
    addLog('Клод изучает транскрипцию...')

    analyzeBarRef.current = setInterval(() => {
      setAnalyzeBarWidth(prev => Math.min(96, prev + Math.random() * 3))
    }, 700)

    try {
      await api.post(`/analyze/${fileId}?provider=claude&max_clips=${maxClips}&platform=${platform}`)
      clearAnalyzeBar()
      setAnalyzeBarWidth(100)
      setAnalyzeState('done')
      addLog(`Анализ завершён — найдены кандидаты`)
      router.push(`/candidates/${fileId}`)
    } catch (err: any) {
      clearAnalyzeBar()
      setAnalyzeState('error')
      const msg = err.response?.data?.detail || 'Ошибка анализа'
      setError(msg)
      addLog(`Ошибка: ${msg}`)
    }
  }, [fileId, maxClips, platform, addLog, router])

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
          addLog('Транскрипция готова!')
          clearPoll()
          await runAnalyze()
          return true
        }
        if (data.status === 'failed') {
          setTranscribeState('error')
          const msg = typeof data.error === 'string' ? data.error : 'Транскрипция упала'
          setError(msg)
          addLog(`Ошибка: ${msg}`)
          clearPoll()
          return true
        }
      } catch (e: any) {
        setTranscribeState('error')
        const msg = e.response?.data?.detail || 'Ошибка опроса статуса'
        setError(msg)
        addLog(`Ошибка: ${msg}`)
        clearPoll()
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
  }, [fileId, addLog, runAnalyze])

  useEffect(() => {
    void runTranscribe()
    return () => {
      clearPoll()
      clearAnalyzeBar()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [log])

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
    <svg className="step-check" viewBox="0 0 28 28" width="28" height="28">
      <circle cx="14" cy="14" r="12" fill="#B8E6CC" stroke="#3A2E2A" strokeWidth="2.5" />
      <path d="M8 14 L13 19 L21 10" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )

  const isProcessing = transcribeState === 'run' || analyzeState === 'run'
  const currentStepLabel =
    transcribeState === 'run'
      ? transcribeProgress
        ? `Транскрипция: ${transcribeProgress.progress}/${transcribeProgress.total} чанков`
        : 'Запуск транскрипции...'
      : analyzeState === 'run'
      ? 'Динозаврик смотрит видео... 🦖'
      : analyzeState === 'done'
      ? 'Готово!'
      : 'Обработка...'

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
        .step-check { position: absolute; top: -12px; right: 14px; width: 28px; height: 28px; }
        .bar {
          height: 10px; background: #fff; border: 2px solid var(--ink);
          border-radius: 6px; overflow: hidden; box-shadow: 1px 2px 0 var(--ink); margin-top: 8px;
        }
        .bar > span {
          display: block; height: 100%; background: var(--pink);
          border-right: 2px solid var(--ink); transition: width .4s ease;
        }
        .dino-area {
          display: flex; align-items: center; justify-content: center; gap: 24px;
          padding: 32px; background: var(--paper);
          border: 3px solid var(--ink);
          border-radius: 24px 28px 22px 26px / 22px 26px 28px 24px;
          box-shadow: 6px 8px 0 var(--ink); margin-bottom: 24px;
          flex-wrap: wrap;
        }
        .dino-emoji {
          font-size: 72px; animation: dino-bob 1.2s ease-in-out infinite;
          filter: drop-shadow(2px 4px 0 rgba(58,46,42,.2));
        }
        @keyframes dino-bob { 0%,100%{transform:translateY(0) rotate(-3deg)} 50%{transform:translateY(-12px) rotate(3deg)} }
        .dino-text { font-family: "Caveat", cursive; font-size: 28px; line-height: 1.2; }
        .dino-sub { color: var(--ink-soft); font-size: 16px; margin-top: 6px; }
        .log-box {
          background: #fff; border: 3px solid var(--ink);
          border-radius: 16px 20px 14px 18px / 18px 14px 20px 16px;
          box-shadow: 3px 4px 0 var(--ink);
          padding: 14px 16px; max-height: 220px; overflow-y: auto;
          font-size: 15px; line-height: 1.5;
        }
        .log-box .log-ts { color: var(--pink-deep); font-family: "Caveat", cursive; font-size: 17px; margin-right: 6px; }
        .log-box .log-new { background: #FFF3D6; padding: 0 4px; border-radius: 3px; }
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
            </div>
          ))}
        </div>

        {error && (
          <div className="error-box">
            ❌ {error}
          </div>
        )}

        {isProcessing && (
          <div className="dino-area">
            <div className="dino-emoji">🦖</div>
            <div>
              <div className="dino-text">{currentStepLabel}</div>
              {transcribeState === 'run' && transcribeProgress && transcribeProgress.total > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div className="bar" style={{ width: 320, maxWidth: '100%' }}>
                    <span style={{ width: `${Math.round(100 * transcribeProgress.progress / transcribeProgress.total)}%` }} />
                  </div>
                  <div className="dino-sub" style={{ marginTop: 6 }}>
                    {transcribeProgress.progress} из {transcribeProgress.total} чанков обработано
                  </div>
                </div>
              )}
              {analyzeState === 'run' && (
                <div className="dino-sub">Claude смотрит ваш контент и ищет вирусные моменты...</div>
              )}
            </div>
          </div>
        )}

        {analyzeState === 'done' && (
          <div className="dino-area">
            <div style={{ fontSize: 72 }}>✅</div>
            <div>
              <div className="dino-text">Готово! Переходим к кандидатам...</div>
            </div>
          </div>
        )}

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

        <button className="btn-cancel" onClick={() => router.push('/app')}>
          ← Отмена
        </button>
      </div>
    </>
  )
}
