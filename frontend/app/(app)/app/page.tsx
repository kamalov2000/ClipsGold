'use client'

import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Job {
  job_id: string
  file_id: string
  title?: string
  filename?: string
  status: 'queued' | 'running' | 'done' | 'error'
  progress?: number
  clip_index?: number
  clip_total?: number
}

interface Clip {
  file_id: string
  clip_id: string
  title?: string
  platform?: string
  caption_style?: string
  language?: string
  virality?: number
  duration?: number
  thumbnail_gradient?: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FRAME_GRADIENTS = [
  'linear-gradient(160deg, #FFB199 0%, #FF8FA3 60%, #E96A85 100%)',
  'linear-gradient(180deg, #2A2A40 0%, #4B3F6E 100%)',
  'linear-gradient(180deg, #FFD166 0%, #F4B829 100%)',
  'linear-gradient(160deg, #7DD3C0 0%, #4FB6A0 100%)',
  'linear-gradient(180deg, #C9B6E4 0%, #8E7BB8 100%)',
  'linear-gradient(160deg, #FFE9B8 0%, #FFB199 100%)',
]

function viralityIcon(v: number) {
  if (v >= 9) return '🔥'
  if (v >= 8) return '⚡'
  return '🌟'
}

function platformIcon(p?: string) {
  return '📱'
}

function formatDuration(sec?: number) {
  if (!sec) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ─── Onboarding ───────────────────────────────────────────────────────────────

const ONB_STEPS = [
  {
    sel: 'ytTab',
    side: 'down' as const,
    step: '1 / 4',
    title: 'Привет! 🦖',
    text: 'Я — динозаврик ClipsGold. Кидай мне ссылку с YouTube или mp4 — нарежу вирусные клипы за пару минут.',
  },
  {
    sel: 'settings',
    side: 'down' as const,
    step: '2 / 4',
    title: 'Подкрути по вкусу',
    text: 'Платформа, число клипов, стиль субтитров и язык. Можно ничего не трогать — у меня неплохой вкус.',
  },
  {
    sel: 'btnBig',
    side: 'left' as const,
    step: '3 / 4',
    title: 'И жми «Резать!»',
    text: 'Я найду самые цепляющие моменты, обрежу под 9:16 со Smart Crop и подпишу субтитрами. В бете — 3 клипа в день бесплатно.',
  },
  {
    sel: 'jobsCard',
    side: 'left' as const,
    step: '4 / 4',
    title: 'А я тут готовлю',
    text: 'Прогресс рендеров и готовые клипы появятся здесь. Кликнул — открыл редактор.',
  },
]

interface OnbState {
  step: number
  spot: { top: number; left: number; width: number; height: number } | null
  bubble: { top: number; left: number; tailClass: string } | null
}

// ─── Main component ───────────────────────────────────────────────────────────

function StudioPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // ── Tab state ──
  const [activeTab, setActiveTab] = useState<'yt' | 'file'>('yt')

  // ── YouTube input ──
  const [ytUrl, setYtUrl] = useState('')
  const [ytLoading, setYtLoading] = useState(false)
  const [ytError, setYtError] = useState<string | null>(null)

  // ── File upload ──
  const [dragover, setDragover] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Settings ──
  const [platform, setPlatform] = useState('tiktok')
  const [clipCount, setClipCount] = useState('5')
  const [captionStyle, setCaptionStyle] = useState('podcast')
  const [language, setLanguage] = useState('ru')

  // ── Jobs & clips ──
  const [jobs, setJobs] = useState<Job[]>([])
  const [clips, setClips] = useState<Clip[]>([])
  const [jobsLoaded, setJobsLoaded] = useState(false)
  const [clipsLoaded, setClipsLoaded] = useState(false)

  // ── Onboarding ──
  const [showOnb, setShowOnb] = useState(false)
  const [onbStep, setOnbStep] = useState(0)
  const [onbSpot, setOnbSpot] = useState<{ top: number; left: number; width: number; height: number } | null>(null)
  const [onbBubble, setOnbBubble] = useState<{ top: number; left: number; tailClass: string } | null>(null)

  // Refs for onboarding target elements
  const ytTabRef = useRef<HTMLButtonElement>(null)
  const settingsRef = useRef<HTMLDivElement>(null)
  const btnBigRef = useRef<HTMLButtonElement>(null)
  const jobsCardRef = useRef<HTMLDivElement>(null)

  function getOnbRef(sel: string) {
    switch (sel) {
      case 'ytTab': return ytTabRef
      case 'settings': return settingsRef
      case 'btnBig': return btnBigRef
      case 'jobsCard': return jobsCardRef
      default: return null
    }
  }

  // ─── Load jobs & clips on mount ───────────────────────────────────────────

  useEffect(() => {
    async function loadJobs() {
      try {
        const res = await api.get('/jobs')
        setJobs(res.data?.jobs || res.data || [])
      } catch {
        // 404 or other error → empty state
      } finally {
        setJobsLoaded(true)
      }
    }
    async function loadClips() {
      try {
        const res = await api.get('/history')
        setClips(res.data?.clips || res.data || [])
      } catch {
        // 404 or other error → empty state
      } finally {
        setClipsLoaded(true)
      }
    }
    loadJobs()
    loadClips()
  }, [])

  // ─── Auto-fill from ?url= ────────────────────────────────────────────────

  useEffect(() => {
    const urlParam = searchParams.get('url')
    if (urlParam) {
      setYtUrl(urlParam)
      setActiveTab('yt')
    }
  }, [searchParams])

  // ─── Onboarding init ─────────────────────────────────────────────────────

  useEffect(() => {
    const isNew = searchParams.get('new') === '1'
    const seen = (() => { try { return localStorage.getItem('cg_onboarded') === '1' } catch { return false } })()
    if (isNew || !seen) {
      setShowOnb(true)
      setOnbStep(0)
    }
  }, [searchParams])

  const positionOnb = useCallback((stepIdx: number) => {
    const step = ONB_STEPS[stepIdx]
    const ref = getOnbRef(step.sel)
    const el = ref?.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const pad = 8
    setOnbSpot({ top: r.top - pad, left: r.left - pad, width: r.width + pad * 2, height: r.height + pad * 2 })
    const bw = 300
    if (step.side === 'left') {
      setOnbBubble({
        left: Math.min(window.innerWidth - bw - 16, r.right + 22),
        top: r.top + 8,
        tailClass: 'tail-left',
      })
    } else {
      const left = Math.max(16, Math.min(window.innerWidth - bw - 16, r.left))
      setOnbBubble({ left, top: r.bottom + 22, tailClass: 'tail-up' })
    }
  }, [])

  useEffect(() => {
    if (!showOnb) return
    positionOnb(onbStep)
    const handler = () => positionOnb(onbStep)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [showOnb, onbStep, positionOnb])

  function closeOnb() {
    setShowOnb(false)
    try { localStorage.setItem('cg_onboarded', '1') } catch {}
  }

  function onbNext() {
    if (onbStep === ONB_STEPS.length - 1) {
      closeOnb()
    } else {
      setOnbStep(onbStep + 1)
    }
  }

  function onbPrev() {
    if (onbStep > 0) setOnbStep(onbStep - 1)
  }

  // ─── YouTube download ─────────────────────────────────────────────────────

  async function handleYtDownload() {
    const url = ytUrl.trim()
    if (!url) { setYtError('Вставьте ссылку на YouTube'); return }
    setYtLoading(true)
    setYtError(null)
    try {
      const res = await api.post('/download-youtube', { url }, { timeout: 25 * 60 * 1000 })
      const fileId = res.data.file_id
      router.push(`/process/${fileId}`)
    } catch (err: any) {
      setYtError(err.response?.data?.detail || 'Не удалось скачать видео. Проверьте ссылку.')
    } finally {
      setYtLoading(false)
    }
  }

  // ─── File upload ──────────────────────────────────────────────────────────

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragover(false)
    const f = e.dataTransfer.files[0]
    if (f) { setSelectedFile(f); setUploadError(null) }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) { setSelectedFile(f); setUploadError(null) }
  }

  async function handleFileUpload() {
    if (!selectedFile) return
    setUploading(true)
    setUploadProgress(0)
    setUploadError(null)
    const fd = new FormData()
    fd.append('file', selectedFile)
    try {
      const res = await api.post('/upload', fd, {
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded * 100) / e.total))
        },
      })
      const fileId = res.data.file_id
      router.push(`/process/${fileId}`)
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Ошибка загрузки. Попробуйте снова.')
    } finally {
      setUploading(false)
    }
  }

  // ─── Submit (main "Резать!" button) ──────────────────────────────────────

  async function handleSubmit() {
    if (activeTab === 'yt') {
      await handleYtDownload()
    } else {
      await handleFileUpload()
    }
  }

  // ─── Chip helper ──────────────────────────────────────────────────────────

  function chipStyle(active: boolean, color: '' | 'pink' | 'yellow' | 'lilac' | 'mint') {
    const base: React.CSSProperties = {
      fontFamily: '"Caveat", cursive',
      fontSize: 20,
      lineHeight: 1,
      border: '2.5px solid var(--ink)',
      padding: '6px 12px 4px',
      borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
      boxShadow: '2px 2px 0 var(--ink)',
      cursor: 'pointer',
      transition: 'transform .12s ease, background .15s ease',
    }
    if (!active) return { ...base, background: '#fff' }
    const bg = color === 'pink' ? 'var(--pink)' : color === 'yellow' ? 'var(--yellow)' : color === 'lilac' ? 'var(--lilac)' : 'var(--mint)'
    const textShadow = color === 'pink' ? '1px 1px 0 rgba(58,46,42,.35)' : undefined
    return { ...base, background: bg, color: color === 'pink' ? '#fff' : undefined, textShadow }
  }

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '8px 28px 64px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'clamp(340px, 1.05fr, 100%) clamp(340px, 1.4fr, 100%)',
            gap: 32,
            alignItems: 'start',
          }}
          className="studio-grid"
        >

          {/* ── LEFT: New Clip card ───────────────────────────────────────── */}
          <div
            style={{
              background: 'var(--paper)',
              border: '3px solid var(--ink)',
              boxShadow: '6px 8px 0 var(--ink)',
              padding: '24px 26px',
              borderRadius: '28px 24px 30px 22px / 24px 28px 22px 30px',
              transform: 'rotate(-.6deg)',
            }}
          >
            <h2 style={{ fontSize: 38, marginBottom: 4 }}>Новый клип</h2>
            <div style={{ color: 'var(--ink-soft)', marginBottom: 18, fontSize: 17 }}>
              Скорми динозаврику ссылку или файл — он порежет сам.
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
              <button
                ref={ytTabRef}
                type="button"
                onClick={() => setActiveTab('yt')}
                style={{
                  flex: 1,
                  textAlign: 'center',
                  padding: '9px 12px 7px',
                  fontFamily: '"Caveat", cursive',
                  fontSize: 22,
                  background: activeTab === 'yt' ? 'var(--yellow)' : '#fff',
                  border: '2.5px solid var(--ink)',
                  borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
                  boxShadow: '2px 3px 0 var(--ink)',
                  cursor: 'pointer',
                  transition: 'transform .12s ease, background .15s ease',
                }}
              >
                🎥 YouTube
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('file')}
                style={{
                  flex: 1,
                  textAlign: 'center',
                  padding: '9px 12px 7px',
                  fontFamily: '"Caveat", cursive',
                  fontSize: 22,
                  background: activeTab === 'file' ? 'var(--yellow)' : '#fff',
                  border: '2.5px solid var(--ink)',
                  borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
                  boxShadow: '2px 3px 0 var(--ink)',
                  cursor: 'pointer',
                  transition: 'transform .12s ease, background .15s ease',
                }}
              >
                📁 Файл
              </button>
            </div>

            {/* YouTube panel */}
            {activeTab === 'yt' && (
              <div>
                <div
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'stretch',
                    background: '#fff',
                    border: '3px solid var(--ink)',
                    borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                    boxShadow: '3px 4px 0 var(--ink)',
                    padding: '6px 6px 6px 16px',
                  }}
                >
                  <input
                    type="url"
                    value={ytUrl}
                    onChange={(e) => setYtUrl(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !ytLoading && handleYtDownload()}
                    placeholder="https://youtube.com/watch?v=..."
                    disabled={ytLoading}
                    style={{
                      flex: 1,
                      border: 0,
                      outline: 'none',
                      background: 'transparent',
                      fontFamily: '"Patrick Hand", sans-serif',
                      fontSize: 18,
                      color: 'var(--ink)',
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleYtDownload}
                    disabled={ytLoading}
                    style={{
                      fontFamily: '"Caveat", cursive',
                      fontWeight: 700,
                      fontSize: 22,
                      background: ytLoading ? 'var(--ink-soft)' : 'var(--pink)',
                      color: '#fff',
                      border: '2.5px solid var(--ink)',
                      borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
                      padding: '8px 18px 6px',
                      boxShadow: '2px 3px 0 var(--ink)',
                      cursor: ytLoading ? 'not-allowed' : 'pointer',
                      textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {ytLoading ? 'Скачиваем…' : 'Загрузить'}
                  </button>
                </div>
                {ytError && (
                  <div style={{ marginTop: 8, color: 'var(--pink-deep)', fontSize: 15 }}>{ytError}</div>
                )}
              </div>
            )}

            {/* File panel */}
            {activeTab === 'file' && (
              <div>
                <div
                  onClick={() => !selectedFile && fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragover(true) }}
                  onDragLeave={() => setDragover(false)}
                  onDrop={handleFileDrop}
                  style={{
                    border: '3px dashed var(--ink)',
                    borderRadius: '22px 26px 20px 24px / 20px 24px 26px 22px',
                    background: dragover ? 'var(--cream-2)' : '#fff',
                    padding: '34px 18px 28px',
                    textAlign: 'center',
                    cursor: selectedFile ? 'default' : 'pointer',
                    position: 'relative',
                    transition: 'background .15s ease',
                  }}
                >
                  <div
                    style={{
                      width: 54,
                      height: 54,
                      display: 'inline-grid',
                      placeItems: 'center',
                      background: 'var(--yellow)',
                      border: '3px solid var(--ink)',
                      borderRadius: 18,
                      boxShadow: '3px 3px 0 var(--ink)',
                      transform: 'rotate(-4deg)',
                      marginBottom: 8,
                    }}
                  >
                    <svg width="26" height="22" viewBox="0 0 30 26">
                      <path d="M15 18 V4 M9 10 L15 4 L21 10" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      <rect x="3" y="18" width="24" height="5" rx="2" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2"/>
                    </svg>
                  </div>
                  <div style={{ fontFamily: '"Caveat", cursive', fontSize: 26, lineHeight: 1 }}>
                    {selectedFile ? `✔ ${selectedFile.name}` : 'Перетащи MP4 или жми, чтобы выбрать'}
                  </div>
                  <div style={{ color: 'var(--ink-soft)', fontSize: 15, marginTop: 4 }}>
                    {selectedFile
                      ? `${(selectedFile.size / 1024 / 1024).toFixed(1)} МБ · готово к рендеру`
                      : 'До 2 ГБ · MP4, MOV'}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/mp4,video/quicktime,video/*"
                    hidden
                    onChange={handleFileSelect}
                  />
                </div>
                {uploading && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 15, marginBottom: 4 }}>
                      <span>Загружаем…</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div
                      style={{
                        height: 10,
                        background: '#fff',
                        border: '2px solid var(--ink)',
                        borderRadius: 6,
                        overflow: 'hidden',
                        boxShadow: '1px 2px 0 var(--ink)',
                      }}
                    >
                      <span
                        style={{
                          display: 'block',
                          height: '100%',
                          width: `${uploadProgress}%`,
                          background: 'var(--pink)',
                          borderRight: uploadProgress < 100 ? '2px solid var(--ink)' : undefined,
                          transition: 'width .2s ease',
                        }}
                      />
                    </div>
                  </div>
                )}
                {uploadError && (
                  <div style={{ marginTop: 8, color: 'var(--pink-deep)', fontSize: 15 }}>{uploadError}</div>
                )}
              </div>
            )}

            {/* Settings */}
            <div
              ref={settingsRef}
              style={{ marginTop: 18, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}
            >
              {/* Platform */}
              <div>
                <span
                  style={{
                    display: 'block',
                    fontFamily: '"Patrick Hand SC", sans-serif',
                    letterSpacing: '1.2px',
                    textTransform: 'uppercase',
                    fontSize: 13,
                    color: 'var(--ink-soft)',
                    marginBottom: 5,
                    paddingLeft: 4,
                  }}
                >
                  Платформа
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(['tiktok', 'shorts', 'reels'] as const).map((v) => (
                    <button key={v} type="button" onClick={() => setPlatform(v)} className="chip-btn" style={chipStyle(platform === v, 'pink')}>
                      {v === 'tiktok' ? 'TikTok' : v === 'shorts' ? 'Shorts' : 'Reels'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Count */}
              <div>
                <span
                  style={{
                    display: 'block',
                    fontFamily: '"Patrick Hand SC", sans-serif',
                    letterSpacing: '1.2px',
                    textTransform: 'uppercase',
                    fontSize: 13,
                    color: 'var(--ink-soft)',
                    marginBottom: 5,
                    paddingLeft: 4,
                  }}
                >
                  Сколько клипов
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(['3', '5', '10', '15'] as const).map((v) => (
                    <button key={v} type="button" onClick={() => setClipCount(v)} className="chip-btn" style={chipStyle(clipCount === v, 'yellow')}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {/* Caption style */}
              <div>
                <span
                  style={{
                    display: 'block',
                    fontFamily: '"Patrick Hand SC", sans-serif',
                    letterSpacing: '1.2px',
                    textTransform: 'uppercase',
                    fontSize: 13,
                    color: 'var(--ink-soft)',
                    marginBottom: 5,
                    paddingLeft: 4,
                  }}
                >
                  Стиль субтитров
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(['podcast', 'hormozi', 'minimal'] as const).map((v) => (
                    <button key={v} type="button" onClick={() => setCaptionStyle(v)} className="chip-btn" style={chipStyle(captionStyle === v, 'lilac')}>
                      {v.charAt(0).toUpperCase() + v.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Language */}
              <div>
                <span
                  style={{
                    display: 'block',
                    fontFamily: '"Patrick Hand SC", sans-serif',
                    letterSpacing: '1.2px',
                    textTransform: 'uppercase',
                    fontSize: 13,
                    color: 'var(--ink-soft)',
                    marginBottom: 5,
                    paddingLeft: 4,
                  }}
                >
                  Язык
                </span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(['ru', 'en', 'es'] as const).map((v) => (
                    <button key={v} type="button" onClick={() => setLanguage(v)} className="chip-btn" style={chipStyle(language === v, 'mint')}>
                      {v === 'ru' ? 'Русский' : v === 'en' ? 'English' : 'Español'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Submit row */}
            <div style={{ marginTop: 22, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14 }}>
              <div style={{ color: 'var(--ink-soft)', fontSize: 16 }}>
                Бета-доступ · бесплатно · ≈ 4 мин на ролик
              </div>
              <button
                ref={btnBigRef}
                type="button"
                onClick={handleSubmit}
                disabled={ytLoading || uploading}
                className="btn-cut"
                style={{
                  fontFamily: '"Caveat", cursive',
                  fontWeight: 700,
                  fontSize: 30,
                  background: ytLoading || uploading ? 'var(--ink-soft)' : 'var(--pink)',
                  color: '#fff',
                  border: '3px solid var(--ink)',
                  borderRadius: '20px 16px 22px 18px / 16px 20px 18px 22px',
                  padding: '10px 28px 8px',
                  boxShadow: '5px 6px 0 var(--ink)',
                  cursor: ytLoading || uploading ? 'not-allowed' : 'pointer',
                  textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                  transition: 'transform .12s ease, box-shadow .12s ease, background .15s ease',
                  whiteSpace: 'nowrap',
                }}
              >
                {ytLoading || uploading ? 'Обработка…' : 'Резать! 🦖'}
              </button>
            </div>
          </div>

          {/* ── RIGHT column ────────────────────────────────────────────────── */}
          <div>

            {/* Jobs card */}
            <div
              ref={jobsCardRef}
              style={{
                background: 'var(--paper)',
                border: '3px solid var(--ink)',
                boxShadow: '6px 8px 0 var(--ink)',
                padding: '24px 26px',
                borderRadius: '24px 30px 22px 28px / 28px 24px 30px 22px',
                transform: 'rotate(.4deg)',
                marginBottom: 24,
              }}
            >
              {(() => {
                const runningCount = jobs.filter(j => j.status === 'running').length
                return (
                  <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '0 4px 14px' }}>
                    <h3 style={{ fontSize: 32 }}>Сейчас в работе</h3>
                    {runningCount > 0 && (
                      <span style={{ color: 'var(--ink-soft)', fontSize: 15 }}>
                        {runningCount} рендер{runningCount > 1 ? 'а' : ''} в работе
                      </span>
                    )}
                  </div>
                )
              })()}

              {/* Empty state */}
              {jobsLoaded && jobs.length === 0 && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 18,
                    padding: '18px 20px',
                    background: 'var(--paper)',
                    border: '2.5px dashed var(--ink-soft)',
                    borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                    color: 'var(--ink-soft)',
                  }}
                >
                  <svg style={{ flex: 'none', width: 74, height: 74 }} viewBox="0 0 80 80">
                    <ellipse cx="40" cy="50" rx="24" ry="18" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2.5"/>
                    <ellipse cx="40" cy="55" rx="14" ry="9" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="1.6"/>
                    <ellipse cx="26" cy="34" rx="16" ry="13" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2.5"/>
                    <circle cx="22" cy="32" r="3.5" fill="#fff" stroke="#3A2E2A" strokeWidth="1.6"/>
                    <circle cx="22" cy="32" r="1.6" fill="#3A2E2A"/>
                    <path d="M14 38 q3 4 8 3" stroke="#3A2E2A" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
                    <path d="M64 50 q14 3 16 -8" stroke="#3A2E2A" strokeWidth="2.5" fill="none"/>
                    <path d="M22 48 v8 h6 v-8 M48 48 v8 h6 v-8" stroke="#3A2E2A" strokeWidth="2" fill="#7DD3C0"/>
                  </svg>
                  <div style={{ flex: 1 }}>
                    <b style={{ fontFamily: '"Caveat", cursive', fontSize: 24, color: 'var(--ink)', display: 'block', lineHeight: 1, marginBottom: 4 }}>
                      Очередь пуста — динозаврик дремлет 🦖💤
                    </b>
                    <small style={{ fontSize: 14 }}>Кинь видео слева, и здесь появится живой прогресс.</small>
                  </div>
                </div>
              )}

              {/* Job list */}
              {jobs.map((job, idx) => (
                <div
                  key={job.job_id}
                  onClick={() => router.push(`/process/${job.file_id}`)}
                  style={{
                    background: 'var(--paper)',
                    border: '3px solid var(--ink)',
                    borderRadius: '22px 26px 20px 24px / 20px 24px 26px 22px',
                    boxShadow: '5px 6px 0 var(--ink)',
                    padding: '16px 18px',
                    marginBottom: 16,
                    display: 'flex',
                    gap: 14,
                    alignItems: 'center',
                    transform: idx % 2 === 0 ? 'rotate(-.3deg)' : 'rotate(.4deg)',
                    cursor: 'pointer',
                  }}
                >
                  <div
                    style={{
                      width: 64,
                      height: 64,
                      flex: 'none',
                      border: '2.5px solid var(--ink)',
                      borderRadius: 14,
                      boxShadow: '2px 3px 0 var(--ink)',
                      display: 'grid',
                      placeItems: 'center',
                      background: FRAME_GRADIENTS[idx % FRAME_GRADIENTS.length],
                    }}
                  >
                    <svg width="22" height="22" viewBox="0 0 24 24">
                      <path d="M5 4 L20 12 L5 20 Z" fill="#fff" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
                    </svg>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontFamily: '"Caveat", cursive', fontSize: 24, lineHeight: 1 }}>
                      {job.title || job.filename || `Задача ${job.job_id}`}
                    </div>
                    <div style={{ color: 'var(--ink-soft)', fontSize: 15, marginTop: 4 }}>
                      {job.status === 'running' && job.clip_index != null && job.clip_total != null
                        ? `режу клип ${job.clip_index} / ${job.clip_total}`
                        : job.status === 'queued'
                        ? 'в очереди · ждёт свободный слот'
                        : job.status}
                    </div>
                    {job.status === 'running' && job.progress != null && (
                      <div
                        style={{
                          marginTop: 10,
                          height: 10,
                          background: '#fff',
                          border: '2px solid var(--ink)',
                          borderRadius: 6,
                          overflow: 'hidden',
                          boxShadow: '1px 2px 0 var(--ink)',
                        }}
                      >
                        <span
                          style={{
                            display: 'block',
                            height: '100%',
                            width: `${job.progress}%`,
                            background: 'var(--pink)',
                            borderRight: '2px solid var(--ink)',
                          }}
                        />
                      </div>
                    )}
                  </div>
                  <div
                    style={{
                      flex: 'none',
                      fontFamily: '"Caveat", cursive',
                      fontSize: 20,
                      padding: '3px 12px 1px',
                      border: '2.5px solid var(--ink)',
                      borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
                      boxShadow: '2px 2px 0 var(--ink)',
                      background:
                        job.status === 'done' ? 'var(--mint)' :
                        job.status === 'running' ? 'var(--yellow)' :
                        'var(--lilac)',
                    }}
                  >
                    {job.status === 'running' && job.progress != null
                      ? `${job.progress}%`
                      : job.status === 'done'
                      ? 'готово'
                      : 'в очереди'}
                  </div>
                </div>
              ))}
            </div>

            {/* Clips card */}
            <div
              style={{
                background: 'var(--paper)',
                border: '3px solid var(--ink)',
                boxShadow: '6px 8px 0 var(--ink)',
                padding: '24px 26px',
                borderRadius: '28px 24px 30px 22px / 24px 28px 22px 30px',
                transform: 'rotate(-.6deg)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '0 4px 14px' }}>
                <h3 style={{ fontSize: 32 }}>Готовые клипы</h3>
                {clips.length > 0 && (
                  <span style={{ color: 'var(--ink-soft)', fontSize: 15 }}>
                    {clips.length} клипов
                  </span>
                )}
              </div>

              {/* Empty state */}
              {clipsLoaded && clips.length === 0 && (
                <>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 18,
                      padding: '18px 20px',
                      marginBottom: 14,
                      background: 'var(--paper)',
                      border: '2.5px dashed var(--ink-soft)',
                      borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                      color: 'var(--ink-soft)',
                    }}
                  >
                    <div style={{ fontSize: 42, lineHeight: 1 }}>🥚</div>
                    <div style={{ flex: 1 }}>
                      <b style={{ fontFamily: '"Caveat", cursive', fontSize: 24, color: 'var(--ink)', display: 'block', lineHeight: 1, marginBottom: 4 }}>
                        Здесь вылупится твой первый клип
                      </b>
                      <small style={{ fontSize: 14 }}>
                        После первого видео — увидишь карточки с виральностью, длительностью и быстрым переходом в редактор.
                      </small>
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                    {['клип 1', 'клип 2', 'клип 3'].map((label) => (
                      <div
                        key={label}
                        style={{
                          aspectRatio: '9/16',
                          border: '2.5px dashed var(--ink-soft)',
                          background: 'var(--cream)',
                          borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
                          display: 'grid',
                          placeItems: 'center',
                          color: 'var(--ink-soft)',
                          fontFamily: '"Caveat", cursive',
                          fontSize: 22,
                          textAlign: 'center',
                          padding: 8,
                          lineHeight: 1.05,
                        }}
                      >
                        {label}
                        <br/>
                        <span style={{ fontSize: 32 }}>·</span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Clip grid */}
              {clips.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginTop: 8 }}>
                  {clips.map((clip, idx) => (
                    <div
                      key={`${clip.file_id}-${clip.clip_id}`}
                      onClick={() => router.push(`/render/${clip.file_id}/${clip.clip_id}`)}
                      className="clip-card"
                      style={{
                        background: 'var(--paper)',
                        border: '3px solid var(--ink)',
                        borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                        boxShadow: '4px 5px 0 var(--ink)',
                        overflow: 'hidden',
                        transition: 'transform .14s ease, box-shadow .14s ease',
                        cursor: 'pointer',
                        position: 'relative',
                      }}
                    >
                      <div
                        style={{
                          aspectRatio: '9 / 16',
                          borderBottom: '3px solid var(--ink)',
                          position: 'relative',
                          overflow: 'hidden',
                          display: 'grid',
                          placeItems: 'center',
                          background: clip.thumbnail_gradient || FRAME_GRADIENTS[idx % FRAME_GRADIENTS.length],
                        }}
                      >
                        {clip.virality != null && (
                          <div
                            style={{
                              position: 'absolute',
                              top: 8,
                              left: 8,
                              background: 'var(--yellow)',
                              border: '2.5px solid var(--ink)',
                              borderRadius: '10px 14px 8px 12px / 12px 8px 14px 10px',
                              padding: '2px 8px 0',
                              fontFamily: '"Caveat", cursive',
                              fontSize: 20,
                              lineHeight: 1.1,
                              boxShadow: '2px 2px 0 var(--ink)',
                            }}
                          >
                            {viralityIcon(clip.virality)} {clip.virality.toFixed(1)}
                          </div>
                        )}
                        <div
                          style={{
                            width: 42,
                            height: 42,
                            borderRadius: '50%',
                            background: '#fff',
                            border: '2.5px solid var(--ink)',
                            boxShadow: '2px 3px 0 var(--ink)',
                            display: 'grid',
                            placeItems: 'center',
                          }}
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" style={{ marginLeft: 3 }}>
                            <path d="M5 4 L20 12 L5 20 Z" fill="#3A2E2A"/>
                          </svg>
                        </div>
                        {clip.duration != null && (
                          <div
                            style={{
                              position: 'absolute',
                              bottom: 8,
                              right: 8,
                              background: 'rgba(58,46,42,.85)',
                              color: '#fff',
                              borderRadius: 8,
                              padding: '2px 8px 0',
                              fontFamily: '"Caveat", cursive',
                              fontSize: 18,
                              lineHeight: 1.2,
                            }}
                          >
                            {formatDuration(clip.duration)}
                          </div>
                        )}
                      </div>
                      <div style={{ padding: '10px 12px 12px' }}>
                        <div style={{ fontFamily: '"Caveat", cursive', fontSize: 22, lineHeight: 1.05 }}>
                          {clip.title || `Клип ${idx + 1}`}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, color: 'var(--ink-soft)', fontSize: 14 }}>
                          <span>
                            {platformIcon(clip.platform)} {clip.platform || 'TikTok'}
                          </span>
                          <span>
                            {[clip.caption_style, clip.language].filter(Boolean).join(' · ')}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── Onboarding overlay ─────────────────────────────────────────────── */}
      {showOnb && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(58,46,42,.45)',
            zIndex: 60,
          }}
        >
          {/* Skip button */}
          <button
            type="button"
            onClick={closeOnb}
            style={{
              position: 'absolute',
              top: 18,
              right: 18,
              fontFamily: '"Caveat", cursive',
              fontSize: 20,
              color: '#fff',
              background: 'transparent',
              border: 0,
              cursor: 'pointer',
              opacity: 0.85,
            }}
          >
            пропустить ↗
          </button>

          {/* Spotlight */}
          {onbSpot && (
            <div
              style={{
                position: 'absolute',
                top: onbSpot.top,
                left: onbSpot.left,
                width: onbSpot.width,
                height: onbSpot.height,
                border: '3px dashed #FFD166',
                borderRadius: 18,
                boxShadow: '0 0 0 9999px rgba(58,46,42,.55)',
                pointerEvents: 'none',
                transition: 'all .35s cubic-bezier(.4,1.4,.5,1)',
              }}
            />
          )}

          {/* Bubble */}
          {onbBubble && (
            <div
              style={{
                position: 'absolute',
                top: onbBubble.top,
                left: onbBubble.left,
                maxWidth: 300,
                background: 'var(--paper)',
                border: '3px solid var(--ink)',
                borderRadius: '20px 24px 18px 22px / 18px 22px 24px 20px',
                boxShadow: '5px 6px 0 var(--ink)',
                padding: '16px 18px',
                transform: 'rotate(-1deg)',
                transition: 'all .35s cubic-bezier(.4,1.4,.5,1)',
              }}
            >
              {/* Tail */}
              {onbBubble.tailClass === 'tail-up' && (
                <div
                  style={{
                    position: 'absolute',
                    top: -12,
                    left: 36,
                    width: 18,
                    height: 18,
                    background: 'var(--paper)',
                    borderRight: '3px solid var(--ink)',
                    borderBottom: '3px solid var(--ink)',
                    transform: 'rotate(-135deg)',
                  }}
                />
              )}
              {onbBubble.tailClass === 'tail-left' && (
                <div
                  style={{
                    position: 'absolute',
                    left: -12,
                    top: 36,
                    width: 18,
                    height: 18,
                    background: 'var(--paper)',
                    borderRight: '3px solid var(--ink)',
                    borderBottom: '3px solid var(--ink)',
                    transform: 'rotate(135deg)',
                  }}
                />
              )}

              <div
                style={{
                  fontFamily: '"Patrick Hand SC", sans-serif',
                  fontSize: 12,
                  letterSpacing: '1.5px',
                  textTransform: 'uppercase',
                  color: 'var(--ink-soft)',
                }}
              >
                {ONB_STEPS[onbStep].step}
              </div>
              <h4 style={{ fontSize: 28, lineHeight: 1.05, margin: '2px 0 6px' }}>
                {ONB_STEPS[onbStep].title}
              </h4>
              <p style={{ margin: 0, fontSize: 16, lineHeight: 1.4 }}>
                {ONB_STEPS[onbStep].text}
              </p>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, gap: 10 }}>
                {/* Dots */}
                <div style={{ display: 'flex', gap: 6 }}>
                  {ONB_STEPS.map((_, k) => (
                    <span
                      key={k}
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: k === onbStep ? 'var(--pink)' : 'var(--ink)',
                        opacity: k === onbStep ? 1 : 0.2,
                        display: 'inline-block',
                      }}
                    />
                  ))}
                </div>
                {/* Actions */}
                <div style={{ display: 'flex', gap: 8 }}>
                  {onbStep > 0 && (
                    <button
                      type="button"
                      onClick={onbPrev}
                      style={{
                        fontFamily: '"Caveat", cursive',
                        fontSize: 20,
                        lineHeight: 1,
                        border: '2.5px solid var(--ink)',
                        background: '#fff',
                        padding: '6px 14px 4px',
                        borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
                        boxShadow: '2px 3px 0 var(--ink)',
                        cursor: 'pointer',
                      }}
                    >
                      ← назад
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={onbNext}
                    style={{
                      fontFamily: '"Caveat", cursive',
                      fontSize: 20,
                      lineHeight: 1,
                      border: '2.5px solid var(--ink)',
                      background: 'var(--pink)',
                      color: '#fff',
                      padding: '6px 14px 4px',
                      borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
                      boxShadow: '2px 3px 0 var(--ink)',
                      cursor: 'pointer',
                      textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                    }}
                  >
                    {onbStep === ONB_STEPS.length - 1 ? 'Поехали! 🦖' : 'Дальше →'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        @media (max-width: 940px) {
          .studio-grid {
            grid-template-columns: 1fr !important;
          }
        }
        @media (max-width: 1100px) {
          .clips-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        @media (max-width: 680px) {
          .empty-clips-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        .clip-card:hover {
          transform: translate(-2px,-2px) rotate(-.5deg) !important;
          box-shadow: 6px 7px 0 var(--ink) !important;
        }
        .btn-cut:hover:not(:disabled) {
          transform: translate(-2px,-2px) rotate(-1deg) !important;
          box-shadow: 7px 8px 0 var(--ink) !important;
          background: var(--pink-deep) !important;
        }
        .chip-btn:hover {
          transform: translate(-1px,-1px) !important;
        }
      `}</style>
    </>
  )
}

export default function Page() {
  return (
    <Suspense fallback={<div />}>
      <StudioPage />
    </Suspense>
  )
}
