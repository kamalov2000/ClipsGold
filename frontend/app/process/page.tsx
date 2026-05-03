'use client'

import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { api, API_BASE, getToken, saveToken, clearToken } from '@/lib/api'

/* ─── helpers ─── */
function formatDur(secs: number) {
  if (!secs || isNaN(secs)) return '0:00'
  const m = Math.floor(secs / 60)
  const s = Math.round(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

/* ─── types ─── */
type View = 'upload' | 'processing' | 'results'

interface Clip {
  id: number
  label: string
  score: number
  dur: string
  tags: string[]
  start_time: number
  end_time: number
  file_id: string
  reason?: string
  hook?: string
  rendered?: boolean
}

interface InputInfo {
  type: 'url' | 'file'
  url?: string
  name?: string
  file?: File
}

/* ─── icon ─── */
function Icon({ d, size = 16, stroke = 'currentColor', fill = 'none', sw = 2 }: {
  d: string | string[]; size?: number; stroke?: string; fill?: string; sw?: number
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      {Array.isArray(d) ? d.map((p, i) => <path key={i} d={p} />) : <path d={d} />}
    </svg>
  )
}

function YTIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.97C18.88 4 12 4 12 4s-6.88 0-8.59.45A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.97C5.12 20 12 20 12 20s6.88 0 8.59-.45a2.78 2.78 0 0 0 1.95-1.97A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z" />
      <polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02" fill="currentColor" stroke="none" />
    </svg>
  )
}

/* ─── nav ─── */
const navS: React.CSSProperties = {
  height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '0 28px', borderBottom: '1px solid var(--border)',
  background: 'oklch(0.11 0.01 62 / 0.92)', backdropFilter: 'blur(12px)',
  flexShrink: 0,
}

function Nav({ onBack, userEmail, onLogout }: { onBack?: () => void; userEmail?: string; onLogout?: () => void }) {
  return (
    <div style={navS}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {onBack && (
          <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--lo)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, padding: 0 }}>
            <Icon d="M19 12H5M12 5l-7 7 7 7" size={14} /> Back
          </button>
        )}
        <Link href="/" style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 700, fontSize: 18, color: 'var(--hi)', textDecoration: 'none', display: 'flex', gap: 2 }}>
          Clips<span style={{ color: 'var(--gold)' }}>Gold</span>
        </Link>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {userEmail ? (
          <>
            <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'oklch(0.38 0.06 240)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, color: '#fff' }}>
              {userEmail[0].toUpperCase()}
            </div>
            <button onClick={onLogout} style={{ background: 'none', border: 'none', color: 'var(--lo)', cursor: 'pointer', fontSize: 12 }}>
              Sign out
            </button>
          </>
        ) : (
          <span style={{ fontSize: 12, color: 'var(--lo)' }}>Not signed in</span>
        )}
      </div>
    </div>
  )
}

/* ─── auth overlay ─── */
function AuthOverlay({ onAuth }: { onAuth: (email: string) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setLoading(true); setError(''); setSuccess('')
    try {
      if (mode === 'login') {
        const res = await api.post('/auth/json-login', { email, password })
        const token = res.data.access_token
        if (token) { saveToken(token); onAuth(email) }
        else setError('Login failed')
      } else {
        await api.post('/auth/register', { email, password })
        setSuccess('Account created! Sign in to continue.')
        setMode('login')
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Authentication failed')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div style={{ width: '100%', maxWidth: 400, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: 36 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 22, fontWeight: 700, color: 'var(--hi)', marginBottom: 6 }}>
            {mode === 'login' ? 'Sign in to ClipsGold' : 'Create your account'}
          </div>
          <p style={{ fontSize: 13, color: 'var(--lo)' }}>
            {mode === 'login' ? 'Welcome back' : 'Start clipping for free'}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input
            value={email} onChange={e => setEmail(e.target.value)}
            type="email" placeholder="Email address"
            style={{ background: 'oklch(0.14 0.01 62)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 14px', fontSize: 14, color: 'var(--hi)', fontFamily: "'DM Sans',sans-serif", outline: 'none' }}
          />
          <input
            value={password} onChange={e => setPassword(e.target.value)}
            type="password" placeholder="Password"
            onKeyDown={e => e.key === 'Enter' && submit()}
            style={{ background: 'oklch(0.14 0.01 62)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 14px', fontSize: 14, color: 'var(--hi)', fontFamily: "'DM Sans',sans-serif", outline: 'none' }}
          />
          {error && <div style={{ fontSize: 12, color: 'oklch(0.65 0.14 25)', textAlign: 'center' }}>{error}</div>}
          {success && <div style={{ fontSize: 12, color: 'oklch(0.65 0.14 130)', textAlign: 'center' }}>{success}</div>}
          <button
            onClick={submit} disabled={loading || !email || !password}
            style={{ padding: '13px', borderRadius: 8, border: 'none', cursor: email && password && !loading ? 'pointer' : 'not-allowed', background: email && password ? 'var(--gold)' : 'oklch(0.20 0.01 62)', color: email && password ? 'oklch(0.11 0.01 62)' : 'var(--lo)', fontFamily: "'DM Sans',sans-serif", fontWeight: 600, fontSize: 15, transition: 'all 0.2s' }}>
            {loading ? 'Loading…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </div>

        <div style={{ textAlign: 'center', marginTop: 20, fontSize: 12, color: 'var(--lo)' }}>
          {mode === 'login' ? (
            <>No account? <button onClick={() => { setMode('register'); setError(''); setSuccess('') }} style={{ background: 'none', border: 'none', color: 'var(--gold)', cursor: 'pointer', fontSize: 12 }}>Register →</button></>
          ) : (
            <>Have an account? <button onClick={() => { setMode('login'); setError(''); setSuccess('') }} style={{ background: 'none', border: 'none', color: 'var(--gold)', cursor: 'pointer', fontSize: 12 }}>Sign in →</button></>
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── chip style ─── */
const chip: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 5,
  padding: '3px 10px', borderRadius: 99,
  fontSize: 10, fontWeight: 500, letterSpacing: '0.08em', textTransform: 'uppercase',
  background: 'var(--gold-dim12)', color: 'var(--gold)', border: '1px solid var(--gold-line)',
}

/* ══════════════════════════════
   STATE 1 — UPLOAD
══════════════════════════════ */
function UploadState({ onSubmit, initialUrl }: { onSubmit: (inp: InputInfo) => void; initialUrl?: string }) {
  const [tab, setTab] = useState<'url' | 'file'>('url')
  const [url, setUrl] = useState(initialUrl || '')
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onSubmit({ type: 'file', name: f.name, file: f })
  }, [onSubmit])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) onSubmit({ type: 'file', name: f.name, file: f })
  }

  const handleUrlSubmit = () => {
    const trimmed = url.trim()
    if (!trimmed) return
    onSubmit({ type: 'url', url: trimmed })
  }

  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, overflow: 'auto' }}>
      <div style={{ width: '100%', maxWidth: 620 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ ...chip, margin: '0 auto 20px', display: 'inline-flex' }}>New clip extraction</div>
          <h1 style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 36, fontWeight: 700, letterSpacing: '-0.025em', color: 'var(--hi)', marginBottom: 10 }}>
            What are we clipping today?
          </h1>
          <p style={{ fontSize: 15, color: 'var(--mid)', lineHeight: 1.6 }}>Paste a YouTube link or upload a video file.</p>
        </div>

        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, overflow: 'hidden' }}>
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
            {([{ id: 'url', label: 'YouTube URL' }, { id: 'file', label: 'Upload file' }] as const).map(t => (
              <button key={t.id} onClick={() => setTab(t.id)} style={{
                flex: 1, padding: '14px 0', background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 13, fontWeight: 500,
                color: tab === t.id ? 'var(--hi)' : 'var(--lo)',
                borderBottom: tab === t.id ? '2px solid var(--gold)' : '2px solid transparent',
                marginBottom: -1, transition: 'all 0.15s',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}>
                {t.id === 'url' ? <YTIcon /> : <Icon d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" size={15} />}
                {t.label}
              </button>
            ))}
          </div>

          <div style={{ padding: 28 }}>
            {tab === 'url' ? (
              <div>
                <div style={{
                  display: 'flex', alignItems: 'center',
                  background: 'oklch(0.14 0.01 62)',
                  border: '1.5px solid var(--gold-line)',
                  borderRadius: 10, overflow: 'hidden', marginBottom: 16,
                  boxShadow: '0 0 0 4px oklch(0.76 0.148 80 / 0.05)',
                }}>
                  <div style={{ padding: '0 16px', color: 'var(--lo)', display: 'flex', alignItems: 'center', flexShrink: 0 }}><YTIcon /></div>
                  <input
                    value={url} onChange={e => setUrl(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleUrlSubmit()}
                    placeholder="https://youtube.com/watch?v=…"
                    style={{ flex: 1, background: 'none', border: 'none', outline: 'none', padding: '16px 0', fontSize: 14, color: 'var(--hi)', fontFamily: "'DM Sans',sans-serif" }}
                  />
                  {url && <button onClick={() => setUrl('')} style={{ padding: '0 14px', background: 'none', border: 'none', color: 'var(--lo)', cursor: 'pointer', fontSize: 18 }}>×</button>}
                </div>
                <button
                  onClick={handleUrlSubmit} disabled={!url.trim()}
                  style={{
                    width: '100%', padding: 14, borderRadius: 8, border: 'none',
                    cursor: url.trim() ? 'pointer' : 'not-allowed',
                    background: url.trim() ? 'var(--gold)' : 'oklch(0.20 0.01 62)',
                    color: url.trim() ? 'oklch(0.11 0.01 62)' : 'var(--lo)',
                    fontFamily: "'DM Sans',sans-serif", fontWeight: 600, fontSize: 15, transition: 'all 0.2s',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  }}>
                  Extract clips →
                </button>
              </div>
            ) : (
              <div
                onDragOver={e => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                style={{
                  border: `2px dashed ${dragging ? 'var(--gold)' : 'var(--border)'}`,
                  borderRadius: 10, padding: '56px 32px', textAlign: 'center', cursor: 'pointer',
                  background: dragging ? 'var(--gold-dim12)' : 'oklch(0.14 0.01 62)', transition: 'all 0.15s',
                }}>
                <input ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }} onChange={handleFileChange} />
                <div style={{ width: 52, height: 52, borderRadius: 12, background: 'var(--gold-dim12)', border: '1px solid var(--gold-line)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 18px', color: 'var(--gold)' }}>
                  <Icon d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" size={22} stroke="var(--gold)" />
                </div>
                <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontWeight: 600, fontSize: 16, color: 'var(--hi)', marginBottom: 6 }}>Drop your video here</div>
                <div style={{ fontSize: 13, color: 'var(--lo)', marginBottom: 20 }}>MP4, MOV, MKV — up to 4GB</div>
                <span style={{ fontSize: 12, color: 'var(--gold)', border: '1px solid var(--gold-line)', padding: '6px 18px', borderRadius: 99 }}>Browse files</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════
   STATE 2 — PROCESSING (real API)
══════════════════════════════ */
function getSteps(isFile: boolean) {
  return [
    { id: 'fetch',   label: isFile ? 'Uploading video'  : 'Fetching video',    sub: isFile ? 'Sending file to server…' : 'Downloading from YouTube…' },
    { id: 'whisper', label: 'Transcribing audio', sub: 'Whisper speech recognition…' },
    { id: 'claude',  label: 'Analysing moments',  sub: 'Claude scoring each segment…' },
  ]
}

function ProcessingState({ input, onDone }: { input: InputInfo | null; onDone: (clips: Clip[]) => void }) {
  const [step, setStep] = useState(0)
  const [stepsDone, setStepsDone] = useState([false, false, false])
  const [pct, setPct] = useState(0)
  const [log, setLog] = useState<string[]>(['Starting job…'])
  const [error, setError] = useState('')
  const [videoDuration, setVideoDuration] = useState(0)

  const STEPS = getSteps(input?.type === 'file')

  const addLog = useCallback((msg: string) => {
    setLog(prev => [...prev.slice(-14), msg])
  }, [])

  useEffect(() => {
    if (!input) return

    let cancelled = false

    const run = async () => {
      try {
        // ── Step 1: Download or Upload ───────────────────────────────────
        setStep(0); setPct(5)
        let fileId: string
        let sizeMb = 0

        if (input.type === 'file') {
          if (!input.file) { setError('No file selected'); return }
          addLog(`Uploading "${input.name?.slice(0, 50)}"…`)

          const formData = new FormData()
          formData.append('file', input.file)

          const upRes = await api.post('/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (e) => {
              if (e.total) {
                const p = Math.round((e.loaded / e.total) * 100)
                setPct(Math.round(p * 0.25))
                if (p % 20 === 0) addLog(`Uploading… ${p}%`)
              }
            },
          })
          if (cancelled) return

          fileId = upRes.data.file_id
          sizeMb = Math.round((upRes.data.size || 0) / 1024 / 1024)
          addLog(`Upload complete — ${sizeMb} MB`)
        } else {
          if (!input.url) { setError('No URL provided'); return }
          addLog('Connecting to YouTube…')

          const dlRes = await api.post('/download-youtube', { url: input.url })
          if (cancelled) return

          fileId = dlRes.data.file_id
          const title: string = dlRes.data.title || 'Video'
          const duration: number = dlRes.data.duration || 0
          sizeMb = Math.round((dlRes.data.size || 0) / 1024 / 1024)

          setVideoDuration(duration)
          addLog(`Downloaded: "${title.slice(0, 55)}"`)
          addLog(`Duration: ${formatDur(duration)} · ${sizeMb} MB`)
        }

        setPct(25)
        setStepsDone(prev => { const n = [...prev]; n[0] = true; return n })

        // ── Step 2: Transcribe ───────────────────────────────────────────
        setStep(1)
        addLog('Starting Whisper transcription…')

        await api.post(`/transcribe/${fileId}`)
        if (cancelled) return
        addLog('Transcription job queued…')

        while (true) {
          if (cancelled) return
          await new Promise(r => setTimeout(r, 3500))

          const sRes = await api.get(`/transcribe/${fileId}/status`)
          if (cancelled) return
          const s = sRes.data

          if (s.status === 'done') { addLog('Transcription complete ✓'); break }
          if (s.status === 'failed') throw new Error(s.error || 'Transcription failed')
          if (s.status === 'processing' && s.total_chunks > 0) {
            const p = Math.round((s.progress / s.total_chunks) * 100)
            addLog(`Transcribing… ${p}%`)
            setPct(25 + Math.round(p * 0.35))
          }
        }

        setPct(62)
        setStepsDone(prev => { const n = [...prev]; n[1] = true; return n })

        // ── Step 3: Analyze with Claude ──────────────────────────────────
        setStep(2)
        addLog('Sending transcript to Claude…')

        const analyzeRes = await api.post(`/analyze/${fileId}?max_clips=6`)
        if (cancelled) return

        const rawClips: any[] = analyzeRes.data.viral_clips || []
        addLog(`Claude found ${rawClips.length} viral moments`)
        setPct(100)
        setStepsDone(prev => { const n = [...prev]; n[2] = true; return n })

        await new Promise(r => setTimeout(r, 500))

        const clips: Clip[] = rawClips.map((c, i) => {
          const raw = c.virality_score ?? 0.5
          const score = raw <= 1 ? Math.round(raw * 100) : Math.round(raw)
          return {
            id: i + 1,
            label: c.title || `Clip ${i + 1}`,
            score,
            dur: formatDur((c.end_time || 0) - (c.start_time || 0)),
            tags: c.tags || [],
            start_time: c.start_time || 0,
            end_time: c.end_time || 0,
            file_id: fileId,
            reason: c.reason,
            hook: c.hook,
            rendered: false,
          }
        })

        onDone(clips)
      } catch (e: any) {
        if (!cancelled) {
          const msg = e?.response?.data?.detail || e?.message || 'Processing failed'
          setError(typeof msg === 'string' ? msg.slice(0, 400) : 'Processing failed')
        }
      }
    }

    run()
    return () => { cancelled = true }
  }, [input, onDone, addLog])

  const pctFmt = Math.round(pct)

  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{ maxWidth: 500, textAlign: 'center' }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>⚠️</div>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 18, fontWeight: 600, color: 'var(--hi)', marginBottom: 12 }}>Processing failed</div>
          <div style={{ fontSize: 13, color: 'var(--lo)', lineHeight: 1.7, marginBottom: 24, whiteSpace: 'pre-wrap', wordBreak: 'break-word', textAlign: 'left', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>{error}</div>
          <button onClick={() => window.location.reload()} style={{ padding: '10px 24px', borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--mid)', cursor: 'pointer', fontFamily: "'DM Sans',sans-serif", fontSize: 14 }}>
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '340px 1fr', overflow: 'hidden' }}>
      {/* Left panel — steps */}
      <div style={{ borderRight: '1px solid var(--border)', padding: '40px 32px', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 12, color: 'var(--lo)', marginBottom: 6 }}>Processing</div>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 17, fontWeight: 600, color: 'var(--hi)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {input?.url ? 'YouTube video' : input?.name ?? 'Video file'}
          </div>
          {input?.url && <div style={{ fontSize: 11, color: 'var(--lo)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{input.url}</div>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 36 }}>
          <svg width={64} height={64} viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="26" fill="none" stroke="var(--border)" strokeWidth="4" />
            <circle cx="32" cy="32" r="26" fill="none" stroke="var(--gold)" strokeWidth="4"
              strokeDasharray={`${2 * Math.PI * 26}`}
              strokeDashoffset={`${2 * Math.PI * 26 * (1 - pct / 100)}`}
              strokeLinecap="round"
              style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%', transition: 'stroke-dashoffset 0.3s ease' }}
            />
            <text x="32" y="37" textAnchor="middle" fill="var(--gold)" fontSize="13" fontFamily="Space Grotesk" fontWeight="700">{pctFmt}%</text>
          </svg>
          <div>
            <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 15, fontWeight: 600, color: 'var(--hi)', marginBottom: 3 }}>{STEPS[step].label}</div>
            <div style={{ fontSize: 12, color: 'var(--lo)' }}>{STEPS[step].sub}</div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {STEPS.map((st, i) => {
            const done = stepsDone[i]; const active = i === step && !done
            return (
              <div key={st.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, paddingBottom: i < STEPS.length - 1 ? 20 : 0, position: 'relative' }}>
                {i < STEPS.length - 1 && (
                  <div style={{ position: 'absolute', left: 11, top: 24, width: 1, bottom: 0, background: done ? 'var(--gold-line)' : 'var(--border)' }} />
                )}
                <div style={{
                  width: 23, height: 23, borderRadius: '50%', flexShrink: 0, marginTop: 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: done ? 'var(--gold)' : active ? 'var(--gold-dim12)' : 'var(--bg-lift)',
                  border: active ? '1.5px solid var(--gold)' : done ? 'none' : '1.5px solid var(--border)',
                  transition: 'all 0.3s',
                }}>
                  {done
                    ? <Icon d="M20 6L9 17l-5-5" size={12} stroke="oklch(0.11 0.01 62)" sw={2.5} />
                    : active
                      ? <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--gold)', animation: 'pulse 1s infinite' }} />
                      : <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--border)' }} />
                  }
                </div>
                <div style={{ paddingTop: 2 }}>
                  <div style={{ fontSize: 13, fontWeight: active || done ? 500 : 400, color: done ? 'var(--mid)' : active ? 'var(--hi)' : 'var(--lo)', transition: 'color 0.3s' }}>{st.label}</div>
                  {active && <div style={{ fontSize: 11, color: 'var(--lo)', marginTop: 2 }}>{st.sub}</div>}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Right — live log */}
      <div style={{ padding: '40px 36px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--gold)', animation: 'pulse 1.2s infinite' }} />
          <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--mid)' }}>Live log</span>
        </div>
        <div style={{
          flex: 1, background: 'oklch(0.09 0.008 62)', borderRadius: 10,
          border: '1px solid var(--border)', padding: '20px 22px',
          fontFamily: "'Courier New',monospace", fontSize: 12,
          color: 'oklch(0.60 0.01 62)', lineHeight: 1.8,
          overflow: 'hidden', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end',
        }}>
          {log.map((l, i) => (
            <div key={i} style={{ color: i === log.length - 1 ? 'oklch(0.80 0.01 62)' : 'oklch(0.50 0.008 62)' }}>
              <span style={{ color: 'oklch(0.76 0.148 80 / 0.6)', marginRight: 8 }}>
                {new Date().toLocaleTimeString('en-US', { hour12: false }).slice(0, 5)}
              </span>
              {l}
              {i === log.length - 1 && <span style={{ animation: 'blink 1s step-start infinite' }}>█</span>}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 20, display: 'flex', gap: 16 }}>
          {[
            { label: 'Step', val: STEPS[step].label },
            { label: 'Video length', val: videoDuration ? formatDur(videoDuration) : '—' },
            { label: 'Progress', val: `${stepsDone.filter(Boolean).length} / ${STEPS.length} steps` },
          ].map(s => (
            <div key={s.label} style={{ flex: 1, padding: '14px 16px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }}>
              <div style={{ fontSize: 10, color: 'var(--lo)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 4 }}>{s.label}</div>
              <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 14, fontWeight: 600, color: 'var(--hi)' }}>{s.val}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════
   STATE 3 — RESULTS
══════════════════════════════ */
function ClipCard({ clip, selected, active, onSelect, onPlay }: {
  clip: Clip; selected: boolean; active: boolean
  onSelect: (id: number) => void; onPlay: (clip: Clip) => void
}) {
  const hue = clip.score > 90 ? 'var(--gold)' : clip.score > 80 ? 'oklch(0.70 0.10 150)' : 'oklch(0.65 0.08 200)'
  const stripeAngle = (clip.id * 37) % 90
  const stripeFg = `oklch(${0.17 + (clip.id % 3) * 0.01} 0.01 62)`
  const stripeBg = `oklch(${0.20 + (clip.id % 3) * 0.01} 0.01 62)`

  return (
    <div onClick={() => onSelect(clip.id)} style={{
      background: 'var(--bg-card)',
      border: `1.5px solid ${active ? 'var(--gold-line)' : 'var(--border)'}`,
      borderRadius: 10, overflow: 'hidden', cursor: 'pointer',
      transition: 'all 0.15s',
      boxShadow: active ? '0 0 0 3px oklch(0.76 0.148 80 / 0.12)' : 'none',
    }}>
      <div style={{ position: 'relative' }}>
        <div style={{
          height: 160,
          background: `repeating-linear-gradient(${stripeAngle}deg,${stripeBg} 0,${stripeBg} 5px,${stripeFg} 5px,${stripeFg} 10px)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <button onClick={e => { e.stopPropagation(); onPlay(clip) }}
            style={{
              width: 40, height: 40, borderRadius: '50%',
              background: 'oklch(0 0 0 / 0.55)', border: '1.5px solid oklch(1 0 0 / 0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', backdropFilter: 'blur(4px)', color: 'white', paddingLeft: 2,
            }}>
            <Icon d="M5 3l14 9-14 9V3z" size={14} fill="white" stroke="none" />
          </button>
        </div>
        <div style={{ position: 'absolute', bottom: 8, right: 8, background: 'oklch(0 0 0 / 0.65)', borderRadius: 4, padding: '2px 6px', fontSize: 11, fontWeight: 600, color: '#fff', backdropFilter: 'blur(4px)' }}>
          {clip.dur}
        </div>
        {clip.score >= 90 && (
          <div style={{ position: 'absolute', top: 8, left: 8, ...chip, fontSize: 9 }}>✦ Top pick</div>
        )}
        <div onClick={e => { e.stopPropagation(); onSelect(clip.id) }}
          style={{
            position: 'absolute', top: 8, right: 8, zIndex: 2,
            width: 20, height: 20, borderRadius: 5, cursor: 'pointer',
            background: selected ? 'var(--gold)' : 'oklch(0 0 0 / 0.5)',
            border: `1.5px solid ${selected ? 'var(--gold)' : 'oklch(1 0 0 / 0.3)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            backdropFilter: 'blur(4px)',
          }}>
          {selected && <Icon d="M20 6L9 17l-5-5" size={11} stroke="oklch(0.11 0.01 62)" sw={2.5} />}
        </div>
      </div>

      <div style={{ padding: '12px 14px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 13, fontWeight: 600, color: 'var(--hi)', lineHeight: 1.3 }}>{clip.label}</div>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 13, fontWeight: 700, color: hue, flexShrink: 0 }}>{clip.score}</div>
        </div>
        <div style={{ height: 3, background: 'var(--bg-lift)', borderRadius: 99, marginBottom: 10, overflow: 'hidden' }}>
          <div style={{ width: `${clip.score}%`, height: '100%', background: `linear-gradient(90deg, ${hue}, oklch(0.88 0.12 68))`, borderRadius: 99, transition: 'width 0.8s ease' }} />
        </div>
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          {clip.tags.map(t => (
            <span key={t} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 99, background: 'var(--bg-lift)', color: 'var(--lo)', border: '1px solid var(--border)' }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

function ResultsState({ clips, onNew }: { clips: Clip[]; onNew: () => void }) {
  const [clipsData, setClipsData] = useState<Clip[]>(clips)
  const [selected, setSelected] = useState(new Set(clips.slice(0, 3).map(c => c.id)))
  const [sort, setSort] = useState<'score' | 'recent'>('score')
  const [activeClip, setActiveClip] = useState<Clip>(clips[0])
  const [rendering, setRendering] = useState(new Set<number>())
  const [renderError, setRenderError] = useState('')

  const activeData = clipsData.find(c => c.id === activeClip?.id) ?? clipsData[0]
  const sorted = [...clipsData].sort((a, b) => sort === 'score' ? b.score - a.score : a.id - b.id)

  const toggleSel = (id: number) => setSelected(s => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n
  })

  const downloadClip = async (clip: Clip) => {
    setRenderError('')
    const c = clipsData.find(x => x.id === clip.id) ?? clip
    if (!c.file_id) return

    if (!c.rendered) {
      setRendering(prev => new Set(prev).add(c.id))
      try {
        await api.post(`/extract-clips/${c.file_id}`, {
          clip_indices: [c.id - 1],
          enable_reframe: true,
          enable_subtitles: true,
        })
        setClipsData(prev => prev.map(x => x.id === c.id ? { ...x, rendered: true } : x))
      } catch (e: any) {
        const msg = e?.response?.data?.detail || e?.message || 'Render failed'
        setRenderError(typeof msg === 'string' ? msg.slice(0, 200) : 'Render failed')
        setRendering(prev => { const n = new Set(prev); n.delete(c.id); return n })
        return
      }
      setRendering(prev => { const n = new Set(prev); n.delete(c.id); return n })
    }

    const a = document.createElement('a')
    a.href = `${API_BASE}/download-clip/${c.file_id}/${c.id}`
    a.download = `${c.label}.mp4`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const isRendering = (id: number) => rendering.has(id)
  const isRendered = (id: number) => clipsData.find(c => c.id === id)?.rendered ?? false

  return (
    <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 340px', overflow: 'hidden' }}>
      {/* Left — clips grid */}
      <div style={{ padding: '28px', overflow: 'auto', borderRight: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 16, fontWeight: 600, color: 'var(--hi)' }}>{clipsData.length} clips found</div>
            <div style={{ fontSize: 12, color: 'var(--lo)', marginTop: 2 }}>Select a clip → Render &amp; Download</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: 'var(--lo)' }}>Sort:</span>
            {(['score', 'recent'] as const).map(v => (
              <button key={v} onClick={() => setSort(v)} style={{
                fontSize: 11, padding: '5px 10px', borderRadius: 5, cursor: 'pointer',
                background: sort === v ? 'var(--gold-dim12)' : 'var(--bg-lift)',
                border: `1px solid ${sort === v ? 'var(--gold-line)' : 'var(--border)'}`,
                color: sort === v ? 'var(--gold)' : 'var(--lo)',
              }}>{v === 'score' ? 'AI Score' : 'Timestamp'}</button>
            ))}
          </div>
          <button onClick={onNew} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', borderRadius: 7, border: 'none', background: 'var(--gold)', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: 'oklch(0.11 0.01 62)', fontFamily: "'DM Sans',sans-serif" }}>
            + New video
          </button>
        </div>

        {renderError && (
          <div style={{ marginBottom: 16, padding: '10px 14px', background: 'oklch(0.18 0.04 25)', border: '1px solid oklch(0.35 0.10 25)', borderRadius: 8, fontSize: 12, color: 'oklch(0.75 0.10 25)' }}>
            ⚠️ {renderError}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 14 }}>
          {sorted.map(clip => (
            <ClipCard key={clip.id} clip={clip}
              selected={selected.has(clip.id)}
              active={activeData?.id === clip.id}
              onSelect={id => { toggleSel(id); setActiveClip(clipsData.find(c => c.id === id) ?? clipsData[0]) }}
              onPlay={c => setActiveClip(c)}
            />
          ))}
        </div>
      </div>

      {/* Right — detail panel */}
      <div style={{ padding: '28px 24px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
        {activeData && <>
          {/* Preview */}
          <div style={{
            aspectRatio: '9/16', maxHeight: 280,
            background: `repeating-linear-gradient(${activeData.id * 30}deg,oklch(0.17 0.01 62) 0,oklch(0.17 0.01 62) 5px,oklch(0.21 0.015 70) 5px,oklch(0.21 0.015 70) 10px)`,
            borderRadius: 10, border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            position: 'relative', overflow: 'hidden', width: '100%', flexShrink: 0,
          }}>
            <div style={{ position: 'absolute', bottom: 20, left: 16, right: 16, textAlign: 'center', fontFamily: "'Space Grotesk',sans-serif", fontSize: 13, fontWeight: 700, color: '#fff', textShadow: '0 2px 8px oklch(0 0 0 / 0.8)', lineHeight: 1.4 }}>
              &ldquo;{activeData.hook || activeData.label}&rdquo;
            </div>
          </div>

          {/* Meta */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
            <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 15, fontWeight: 600, color: 'var(--hi)', marginBottom: 8 }}>{activeData.label}</div>
            {activeData.reason && (
              <div style={{ fontSize: 12, color: 'var(--lo)', marginBottom: 12, lineHeight: 1.6 }}>{activeData.reason}</div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[
                { label: 'AI Score', val: `${activeData.score}/100` },
                { label: 'Duration', val: activeData.dur },
                { label: 'Start', val: formatDur(activeData.start_time) },
                { label: 'End', val: formatDur(activeData.end_time) },
              ].map(m => (
                <div key={m.label}>
                  <div style={{ fontSize: 10, color: 'var(--lo)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 2 }}>{m.label}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--hi)' }}>{m.val}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Download action */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              onClick={() => downloadClip(activeData)}
              disabled={isRendering(activeData.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '12px 16px', borderRadius: 7, border: 'none',
                background: isRendering(activeData.id) ? 'oklch(0.20 0.01 62)' : 'var(--gold)',
                cursor: isRendering(activeData.id) ? 'wait' : 'pointer',
                fontFamily: "'DM Sans',sans-serif", fontWeight: 600, fontSize: 13,
                color: isRendering(activeData.id) ? 'var(--lo)' : 'oklch(0.11 0.01 62)',
                transition: 'all 0.2s',
              }}>
              <Icon d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" size={14}
                stroke={isRendering(activeData.id) ? 'var(--lo)' : 'oklch(0.11 0.01 62)'} />
              {isRendering(activeData.id)
                ? (isRendered(activeData.id) ? 'Downloading…' : 'Rendering… (1–3 min)')
                : isRendered(activeData.id) ? 'Download clip' : 'Render & Download'
              }
            </button>
            <div style={{ fontSize: 11, color: 'var(--lo)', textAlign: 'center' }}>
              {isRendered(activeData.id) ? '✓ Ready to download' : 'First render encodes captions + reframe'}
            </div>
          </div>

          {/* Score + tags */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--mid)' }}>Virality score</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--gold)' }}>{activeData.score}/100</span>
            </div>
            <div style={{ height: 6, background: 'var(--bg-lift)', borderRadius: 99, overflow: 'hidden', marginBottom: 12 }}>
              <div style={{ width: `${activeData.score}%`, height: '100%', background: 'linear-gradient(90deg,var(--gold),oklch(0.88 0.12 68))', borderRadius: 99, transition: 'width 0.8s ease' }} />
            </div>
            {activeData.tags.length > 0 && (
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                {activeData.tags.map(t => (
                  <span key={t} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 99, background: 'var(--gold-dim12)', color: 'var(--gold)', border: '1px solid var(--gold-line)' }}>{t}</span>
                ))}
              </div>
            )}
          </div>
        </>}
      </div>
    </div>
  )
}

/* ══════════════════════════════
   ROOT
══════════════════════════════ */
function ProcessPageInner() {
  const searchParams = useSearchParams()
  const initialUrl = searchParams.get('url') ?? undefined

  const [view, setView] = useState<View>('upload')
  const [input, setInput] = useState<InputInfo | null>(null)
  const [clips, setClips] = useState<Clip[]>([])
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [authed, setAuthed] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (token) {
      api.get('/auth/me')
        .then(res => { setUserEmail(res.data.email); setAuthed(true) })
        .catch(() => { clearToken() })
    }
  }, [])

  const handleSubmit = (inp: InputInfo) => { setInput(inp); setView('processing') }
  const handleDone = (c: Clip[]) => { setClips(c); setView('results') }
  const handleNew = () => { setInput(null); setClips([]); setView('upload') }
  const handleLogout = () => { clearToken(); setAuthed(false); setUserEmail(null); setView('upload') }

  const stepOrder = ['upload', 'processing', 'results'] as const
  const stepLabel = { upload: 'Upload', processing: 'Processing…', results: 'Results' }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)', overflow: 'hidden' }}>
      <Nav onBack={view !== 'upload' ? handleNew : undefined} userEmail={userEmail ?? undefined} onLogout={handleLogout} />

      {/* Step indicator */}
      <div style={{ height: 36, borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', padding: '0 28px', flexShrink: 0, background: 'oklch(0.12 0.01 62)' }}>
        {stepOrder.map((v, i) => {
          const curIdx = stepOrder.indexOf(view)
          return (
            <div key={v} style={{ display: 'flex', alignItems: 'center' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 7, fontSize: 12,
                color: v === view ? 'var(--hi)' : i < curIdx ? 'var(--gold)' : 'var(--lo)',
                fontWeight: v === view ? 500 : 400,
              }}>
                <div style={{
                  width: 18, height: 18, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 600,
                  background: i < curIdx ? 'var(--gold)' : v === view ? 'var(--gold-dim12)' : 'var(--bg-lift)',
                  border: v === view ? '1.5px solid var(--gold)' : 'none',
                  color: i < curIdx ? 'oklch(0.11 0.01 62)' : v === view ? 'var(--gold)' : 'var(--lo)',
                }}>
                  {i < curIdx ? '✓' : i + 1}
                </div>
                {stepLabel[v]}
              </div>
              {i < 2 && <div style={{ width: 40, height: 1, background: 'var(--border)', margin: '0 10px' }} />}
            </div>
          )
        })}
      </div>

      {!authed
        ? <AuthOverlay onAuth={e => { setUserEmail(e); setAuthed(true) }} />
        : view === 'upload'     ? <UploadState onSubmit={handleSubmit} initialUrl={initialUrl} />
        : view === 'processing' ? <ProcessingState input={input} onDone={handleDone} />
        : <ResultsState clips={clips} onNew={handleNew} />
      }
    </div>
  )
}

export default function ProcessPage() {
  return (
    <Suspense fallback={
      <div style={{ height: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--lo)', fontSize: 14 }}>Loading…</div>
      </div>
    }>
      <ProcessPageInner />
    </Suspense>
  )
}
