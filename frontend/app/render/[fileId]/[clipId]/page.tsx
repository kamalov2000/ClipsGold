'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api, API_BASE, WS_BASE, getToken } from '@/lib/api'

// ── Types ──────────────────────────────────────────────────────────────────

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

interface Segment {
  start: number
  end: number
  text: string
  virality?: number
  vir?: number
  start_time?: number
  timestamp?: string
}

interface ClipMeta {
  title: string
  description: string
  hashtags: string[]
  cta: string
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmt(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ── Component ──────────────────────────────────────────────────────────────

export default function RenderPage() {
  const params = useParams()
  const router = useRouter()
  const fileId = params.fileId as string
  const clipId = parseInt(params.clipId as string, 10) // 1-based

  // ── Data state ──────────────────────────────────────────────────────────
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [segments, setSegments] = useState<Segment[]>([])
  const [clipMeta, setClipMeta] = useState<ClipMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  // ── Settings state ──────────────────────────────────────────────────────
  const [platform, setPlatform] = useState<'tiktok' | 'shorts' | 'reels'>('tiktok')
  const [cropPosition, setCropPosition] = useState(50)
  const [cropMode, setCropMode] = useState<'face' | 'group' | 'split'>('face')
  const [subtitleStyle, setSubtitleStyle] = useState<'podcast' | 'hormozi' | 'minimal'>('hormozi')
  const [language, setLanguage] = useState<'ru' | 'en' | 'es'>('ru')
  const [jumpCut, setJumpCut] = useState(false)

  // ── Editable post meta ──────────────────────────────────────────────────
  const [hook, setHook] = useState('')
  const [description, setDescription] = useState('')
  const [hashtags, setHashtags] = useState<string[]>([])
  const [cta, setCta] = useState('')

  // ── Transcript editing ──────────────────────────────────────────────────
  const [editingTranscript] = useState(true)
  const [editedSegments, setEditedSegments] = useState<Segment[]>([])

  // ── Render state ────────────────────────────────────────────────────────
  const [rendering, setRendering] = useState(false)
  const [renderProgress, setRenderProgress] = useState(0)
  const [renderStatus, setRenderStatus] = useState('')
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [downloadFilename, setDownloadFilename] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [renderError, setRenderError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)

  // ── Load data ────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    setLoading(true)

    Promise.all([
      api.get(`/clips/${fileId}/candidates`),
      api.get(`/transcription/${fileId}`).catch(() => ({ data: { segments: [] } })),
      api.get(`/clip-meta/${fileId}/${clipId}`).catch(() => ({ data: null })),
    ])
      .then(([candRes, trRes, metaRes]) => {
        if (cancelled) return
        const allCands: Candidate[] = Array.isArray(candRes.data.candidates)
          ? candRes.data.candidates
          : Array.isArray(candRes.data) ? candRes.data : []
        setCandidates(allCands)
        const found = allCands[clipId - 1] || null
        setCandidate(found)

        const segs: Segment[] = Array.isArray(trRes.data.segments) ? trRes.data.segments : []
        setSegments(segs)
        setEditedSegments(segs.map(s => ({ ...s })))

        const meta: ClipMeta | null = metaRes.data
        if (meta) {
          setClipMeta(meta)
          setHook(meta.title || found?.hook || '')
          setDescription(meta.description || found?.description || '')
          setHashtags(meta.hashtags || found?.hashtags || [])
          setCta(meta.cta || '')
        } else if (found) {
          setHook(found.hook || found.title || '')
          setDescription(found.description || '')
          setHashtags(found.hashtags || [])
          setCta('')
        }
      })
      .catch(err => {
        if (!cancelled) setLoadError(err.response?.data?.detail || 'Ошибка загрузки')
      })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [fileId, clipId])

  // ── Toast helper ────────────────────────────────────────────────────────
  const showToast = useCallback((msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 1800)
  }, [])

  const copyText = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      showToast('скопировано в буфер 🦖')
    } catch {}
  }, [showToast])

  // ── Render ───────────────────────────────────────────────────────────────
  const handleRender = async () => {
    if (!candidate) return
    setRendering(true)
    setRenderProgress(0)
    setRenderStatus('starting')
    setRenderError(null)

    try {
      const res = await api.post('/render-clip', {
        file_id: fileId,
        clip_index: clipId - 1,
        platform,
        subtitle_style: subtitleStyle,
        render_mode: cropMode === 'face' ? 'blur_background' : 'blur_background',
        enable_jump_cut: jumpCut,
        enable_filler_removal: false,
      })

      const taskId = res.data.task_id
      const token = getToken() ?? ''
      const ws = new WebSocket(`${WS_BASE}/ws/render-progress/${taskId}?token=${encodeURIComponent(token)}`)
      wsRef.current = ws

      ws.onopen = () => setRenderStatus('rendering')

      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data)
        if (data.status === 'queued') {
          setRenderStatus(`очередь: позиция ${data.position}`)
        } else if (data.status === 'rendering_started') {
          setRenderStatus('rendering')
        } else if (data.status === 'processing') {
          setRenderProgress(data.progress || 0)
          setRenderStatus(`${data.progress || 0}%`)
        } else if (data.status === 'complete' || data.status === 'success') {
          setRenderProgress(100)
          setRenderStatus('done')
          const url = data.download_url || `/download-clip/${data.file_id}/${data.clip_id}`
          const fn = data.filename || `clip_${clipId}.mp4`
          setDownloadUrl(url)
          setDownloadFilename(fn)
          setShowModal(true)

          if (data.meta) {
            setHook(data.meta.title || hook)
            setDescription(data.meta.description || description)
            setHashtags(data.meta.hashtags || hashtags)
            setCta(data.meta.cta || cta)
          } else {
            api.get(`/clip-meta/${fileId}/${clipId}`)
              .then(r => {
                if (r.data) {
                  setHook(r.data.title || hook)
                  setDescription(r.data.description || description)
                  setHashtags(r.data.hashtags || hashtags)
                  setCta(r.data.cta || cta)
                }
              }).catch(() => {})
          }

          setRendering(false)
          ws.close()
        } else if (data.status === 'error') {
          setRenderError(data.error || 'Ошибка рендера')
          setRenderStatus('error')
          setRendering(false)
          ws.close()
        }
      }

      ws.onerror = () => {
        setRenderError('Соединение с сервером потеряно')
        setRenderStatus('error')
        setRendering(false)
      }
    } catch (err: any) {
      setRenderError(err.response?.data?.detail || 'Ошибка запуска рендера')
      setRenderStatus('error')
      setRendering(false)
    }
  }

  const handleReset = () => {
    setPlatform('tiktok')
    setCropPosition(50)
    setCropMode('face')
    setSubtitleStyle('hormozi')
    setLanguage('ru')
    setJumpCut(false)
    setRenderProgress(0)
    setRenderStatus('')
    setDownloadUrl(null)
    setRenderError(null)
  }

  const handleDownload = async () => {
    if (!downloadUrl) return
    try {
      const resp = await api.get(downloadUrl, { responseType: 'blob' })
      const blobUrl = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = downloadFilename || 'clip.mp4'
      a.click()
      URL.revokeObjectURL(blobUrl)
    } catch {
      const full = downloadUrl.startsWith('http') ? downloadUrl : `${API_BASE}${downloadUrl}`
      window.open(full, '_blank')
    }
    setShowModal(false)
    showToast('качаем... 🦖')
  }

  // ── Segments in clip ─────────────────────────────────────────────────────
  const isInClip = (seg: Segment) => {
    if (!candidate) return false
    return seg.end > candidate.start_time && seg.start < candidate.end_time
  }

  // ── Render bar meta ──────────────────────────────────────────────────────
  const clipDuration = candidate ? Math.round(candidate.end_time - candidate.start_time) : 0
  const renderBarMeta = candidate
    ? `⏱ ~${fmt(clipDuration)} · ✂ обрезка ${fmt(candidate.start_time)}–${fmt(candidate.end_time)} · 🎯 ${cropMode} · ✏ ${subtitleStyle} · ${language}`
    : ''

  if (loading) {
    return (
      <>
        <FontLinks />
        <BaseStyles />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh', fontFamily: 'Caveat, cursive', fontSize: 28 }}>
          <span style={{ marginRight: 16, fontSize: 48, display: 'inline-block', animation: 'wob 1.4s ease-in-out infinite' }}>🦖</span>
          Загружаем клип...
        </div>
      </>
    )
  }

  if (loadError) {
    return (
      <>
        <FontLinks />
        <BaseStyles />
        <div style={{ padding: '48px 28px', fontFamily: 'Caveat, cursive', fontSize: 24, color: '#991B1B' }}>
          ❌ {loadError}
        </div>
      </>
    )
  }

  return (
    <>
      <FontLinks />
      <BaseStyles />

      {/* ── Navbar ────────────────────────────────────────────────────────── */}
      <nav style={S.navbar}>
        <a style={S.logo} href="/">
          <span style={S.mark}>
            <svg width="22" height="22" viewBox="0 0 26 26">
              <path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              <circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/>
            </svg>
          </span>
          Clips<span style={S.gold}>Gold</span>
        </a>
        <div style={S.navRight}>
          <div style={S.betaBadge}>🦖 <b>Beta · бесплатно</b></div>
        </div>
      </nav>

      {/* ── Breadcrumbs ───────────────────────────────────────────────────── */}
      <div style={S.crumbs}>
        <a href="/app" style={S.crumbLink}>← Студия</a>
        <span style={{ opacity: 0.5 }}>/</span>
        <span>{fileId}</span>
        <span style={{ opacity: 0.5 }}>/</span>
        <span style={{ color: 'var(--ink)' }}>Клип {clipId} из {candidates.length || '?'}</span>
      </div>

      <div style={S.wrap}>
        {/* ── Head ──────────────────────────────────────────────────────── */}
        <div style={S.head}>
          <div>
            <h1 style={S.h1}>
              {candidate?.hook
                ? <>«{candidate.hook.slice(0, 30)}<span style={{ color: 'var(--yellow-deep)', textShadow: '2px 2px 0 var(--ink)' }}>{candidate.hook.length > 30 ? '...' : ''}</span>»</>
                : candidate?.title || `Клип ${clipId}`}
            </h1>
            <div style={S.sub}>
              9:16 · {platform} · {candidate ? fmt(Math.round(candidate.end_time - candidate.start_time)) : '—'} · {subtitleStyle} · {language} · 🔥 виральность {candidate?.virality_score}
            </div>
          </div>
          <div style={S.headActions}>
            <button
              style={S.btn}
              onClick={() => downloadUrl ? handleDownload() : setShowModal(true)}
              type="button"
            >
              <svg width="14" height="14" viewBox="0 0 24 24"><path d="M12 4 v12 M6 10 l6 6 6-6 M4 20 h16" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
              Скачать MP4
            </button>
            <button
              style={{ ...S.btn, background: 'var(--yellow)' }}
              onClick={() => copyText(`${hook}\n\n${description}\n\n${hashtags.join(' ')}\n\n${cta}`)}
              type="button"
            >
              <svg width="14" height="14" viewBox="0 0 24 24"><rect x="6" y="3" width="14" height="16" rx="2" fill="none" stroke="#3A2E2A" strokeWidth="2.5"/><rect x="3" y="6" width="14" height="16" rx="2" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5"/></svg>
              Copy meta
            </button>
          </div>
        </div>

        {/* ── 2-column grid ─────────────────────────────────────────────── */}
        <div style={S.grid}>

          {/* ── LEFT: preview + scrubber ──────────────────────────────── */}
          <div>
            {/* Preview 9:16 */}
            <div style={S.preview}>
              <div style={S.previewVir}>
                {candidate?.virality_score && candidate.virality_score >= 9.2 ? '🔥' : '⚡'} {candidate?.virality_score}
              </div>
              <div style={S.previewDur}>
                {candidate ? fmt(Math.round(candidate.end_time - candidate.start_time)) : '—'}
              </div>
              {candidate?.hook && (
                <div style={S.previewHook}>
                  {candidate.hook}
                </div>
              )}
              <div style={S.playBig}>
                <svg width="22" height="22" viewBox="0 0 24 24" style={{ marginLeft: 5 }}>
                  <path d="M5 4 L20 12 L5 20 Z" fill="#3A2E2A" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
                </svg>
              </div>
              <div style={S.faceDot} title="Smart Crop · лицо" />
              <div style={S.caption}>
                {editedSegments.filter(isInClip).slice(-1)[0]?.text || candidate?.title || ''}
              </div>
            </div>

            {/* Scrubber */}
            <div style={S.scrub}>
              <div style={S.scrubRow}>
                <div style={S.playMini}>
                  <svg width="12" height="12" viewBox="0 0 24 24"><path d="M5 4 L20 12 L5 20 Z" fill="#fff"/></svg>
                </div>
                <div style={S.scrubTime}>
                  <b>0:00</b> / {candidate ? fmt(Math.round(candidate.end_time - candidate.start_time)) : '0:00'}
                </div>
                <div style={{ flex: 1 }} />
                {candidate && (
                  <div style={{ ...S.scrubTime, fontSize: 17 }}>🎯 {fmt(candidate.start_time)}–{fmt(candidate.end_time)}</div>
                )}
              </div>
              <div style={S.timeline}>
                <div style={S.timelineWave} />
                <div style={S.timelineClip} />
                <div style={{ ...S.timelineHandle, left: '18%', transform: 'translateX(-50%)' }} title="начало" />
                <div style={{ ...S.timelineHandle, left: '54%', transform: 'translateX(-50%)' }} title="конец" />
                <div style={S.timelineCursor} />
              </div>
              <div style={S.timelineMarks}>
                <span>0:00</span>
                <span>в исходнике</span>
                <span>{candidate ? fmt(Math.round(candidate.end_time)) : '0:00'}</span>
              </div>
            </div>
          </div>

          {/* ── RIGHT: settings + meta + transcript ───────────────────── */}
          <div style={{ display: 'grid', gap: 20 }}>

            {/* ── Render settings card ──────────────────────────────── */}
            <div style={S.cardTiltR}>
              <h2 style={S.cardH2}>Настройки рендера</h2>
              <div style={S.cardHint}>Двигай ползунки — динозаврик пересчитает.</div>

              {/* Platform */}
              <div style={S.field}>
                <span style={S.lbl}>Платформа</span>
                <div style={S.chips}>
                  {(['tiktok', 'shorts', 'reels'] as const).map(p => (
                    <button
                      key={p}
                      type="button"
                      style={{ ...S.chip, ...(platform === p ? { ...S.chipOn, ...S.chipOnPink } : {}) }}
                      onClick={() => setPlatform(p)}
                    >
                      {p === 'tiktok' ? 'TikTok' : p === 'shorts' ? 'Shorts' : 'Reels'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Smart Crop position */}
              <div style={S.field}>
                <span style={S.lbl}>Smart Crop · позиция</span>
                <div style={{ padding: '6px 4px 0' }}>
                  <input
                    type="range" min={0} max={100} value={cropPosition}
                    onChange={e => setCropPosition(parseInt(e.target.value))}
                    style={{ width: '100%' }}
                  />
                  <div style={S.sliderMarks}>
                    <span>← левее</span><span>лицо в кадре</span><span>правее →</span>
                  </div>
                </div>
              </div>

              {/* Crop mode */}
              <div style={S.field}>
                <span style={S.lbl}>Smart Crop · режим</span>
                <div style={S.chips}>
                  {(['face', 'group', 'split'] as const).map(m => (
                    <button
                      key={m}
                      type="button"
                      style={{ ...S.chip, ...(cropMode === m ? { ...S.chipOn, ...S.chipOnYellow } : {}) }}
                      onClick={() => setCropMode(m)}
                    >
                      {m === 'face' ? 'Face' : m === 'group' ? 'Group' : 'Split'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Subtitle style */}
              <div style={S.field}>
                <span style={S.lbl}>Стиль субтитров</span>
                <div style={S.chips}>
                  {(['podcast', 'hormozi', 'minimal'] as const).map(st => (
                    <button
                      key={st}
                      type="button"
                      style={{ ...S.chip, ...(subtitleStyle === st ? { ...S.chipOn, ...S.chipOnLilac } : {}) }}
                      onClick={() => setSubtitleStyle(st)}
                    >
                      {st === 'podcast' ? 'Podcast' : st === 'hormozi' ? 'Hormozi' : 'Minimal'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Language + jump-cut */}
              <div style={{ ...S.field, marginBottom: 0 }}>
                <span style={S.lbl}>Язык · jump-cut</span>
                <div style={S.chips}>
                  {(['ru', 'en', 'es'] as const).map(l => (
                    <button
                      key={l}
                      type="button"
                      style={{ ...S.chip, ...(language === l ? S.chipOn : {}) }}
                      onClick={() => setLanguage(l)}
                    >
                      {l === 'ru' ? 'Русский' : l === 'en' ? 'English' : 'Español'}
                    </button>
                  ))}
                  <span style={{ flex: 1 }} />
                  <button
                    type="button"
                    style={{ ...S.chip, ...(jumpCut ? { ...S.chipOn, ...S.chipOnPink } : {}) }}
                    onClick={() => setJumpCut(v => !v)}
                  >
                    ✂ Jump-cut
                  </button>
                </div>
              </div>
            </div>

            {/* ── Post meta card ────────────────────────────────────── */}
            <div style={S.cardTiltL}>
              <h2 style={S.cardH2}>Готовый пост</h2>
              <div style={S.cardHint}>AI собрал хук, эмодзи, хэштеги — правь под канал.</div>

              <div style={S.metaBlock}>
                <div style={S.metaBlockLbl}>
                  Хук
                  <span style={S.copyBtn} onClick={() => copyText(hook)}>копировать</span>
                </div>
                <input
                  type="text" value={hook} onChange={e => setHook(e.target.value)}
                  style={S.metaInput}
                />
              </div>

              <div style={S.metaBlock}>
                <div style={S.metaBlockLbl}>
                  Описание
                  <span style={S.copyBtn} onClick={() => copyText(description)}>копировать</span>
                </div>
                <textarea
                  rows={3} value={description} onChange={e => setDescription(e.target.value)}
                  style={S.metaTextarea}
                />
              </div>

              <div style={S.metaBlock}>
                <div style={S.metaBlockLbl}>
                  Хэштеги
                  <span style={S.copyBtn} onClick={() => copyText(hashtags.join(' '))}>копировать</span>
                </div>
                <div style={S.hashtagsBox}>
                  {hashtags.map((tag, i) => (
                    <span key={i} style={S.tag}>{tag}</span>
                  ))}
                  <span style={{ ...S.tag, background: 'var(--mint)', cursor: 'pointer' }}>+ добавить</span>
                </div>
              </div>

              <div style={{ ...S.metaBlock, marginBottom: 0 }}>
                <div style={S.metaBlockLbl}>CTA</div>
                <input
                  type="text" value={cta} onChange={e => setCta(e.target.value)}
                  style={S.metaInput}
                />
              </div>
            </div>

            {/* ── Transcript card ───────────────────────────────────── */}
            <div style={S.cardTiltR}>
              <h2 style={S.cardH2}>Транскрипт</h2>
              <div style={S.cardHint}>Жёлтое — попало в клип. Кликай по тексту, чтобы править.</div>

              {editedSegments.length === 0 && (
                <div style={{ color: 'var(--ink-soft)', fontSize: 16 }}>Транскрипция не загружена</div>
              )}

              {editedSegments.map((seg, i) => {
                const inClip = isInClip(seg)
                const virScore = seg.virality ?? seg.vir ?? null
                return (
                  <div key={i} style={{ ...S.seg, ...(inClip ? S.segInClip : {}) }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '2px 0', width: '100%' }}>
                      <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--pink)', flexShrink: 0, paddingTop: 2 }}>
                        {seg.start_time != null ? fmt(Math.round(seg.start_time)) : seg.timestamp ?? fmt(Math.round(seg.start))}
                      </span>
                      {virScore != null && (
                        <span style={{
                          flexShrink: 0, fontFamily: '"Caveat", cursive', fontSize: 14,
                          background: virScore >= 8 ? 'var(--pink)' : 'var(--yellow)',
                          color: virScore >= 8 ? '#fff' : 'var(--ink)',
                          padding: '0px 6px', borderRadius: '8px 10px 6px 8px',
                          border: '1.5px solid var(--ink)', boxShadow: '1px 1px 0 var(--ink)',
                          lineHeight: 1.4,
                        }}>
                          {virScore.toFixed(1)}
                        </span>
                      )}
                      <span
                        style={{ flex: 1 }}
                        contentEditable={editingTranscript}
                        suppressContentEditableWarning
                        onBlur={e => {
                          const text = e.currentTarget.textContent || ''
                          setEditedSegments(prev => {
                            const next = [...prev]
                            next[i] = { ...next[i], text }
                            return next
                          })
                        }}
                      >
                        {seg.text}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>

          </div>
        </div>

        {/* ── Render progress bar ────────────────────────────────────────── */}
        {rendering && (
          <div style={{ ...S.renderBar, marginTop: 16 }}>
            <div>
              <div style={{ fontFamily: 'Caveat, cursive', fontSize: 22 }}>
                🦖 Рендерим: {renderStatus}
              </div>
              <div style={{ height: 10, background: '#fff', border: '2px solid var(--ink)', borderRadius: 6, overflow: 'hidden', boxShadow: '1px 2px 0 var(--ink)', marginTop: 8, width: 320, maxWidth: '100%' }}>
                <span style={{ display: 'block', height: '100%', background: 'var(--pink)', borderRight: '2px solid var(--ink)', width: `${renderProgress}%`, transition: 'width .4s ease' }} />
              </div>
            </div>
          </div>
        )}

        {renderError && (
          <div style={{ background: '#FEF2F2', border: '3px solid #F87171', padding: '14px 20px', borderRadius: 16, marginTop: 16, fontFamily: 'Caveat, cursive', fontSize: 20, color: '#991B1B' }}>
            ❌ {renderError}
          </div>
        )}

        {/* ── Bottom re-render bar ───────────────────────────────────────── */}
        <div style={S.renderBar}>
          <div style={S.renderBarInfo}>
            Готов перерендерить с новыми настройками?
            <div style={S.renderBarMeta}>{renderBarMeta}</div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button style={S.btn} type="button" onClick={handleReset}>
              <svg width="14" height="14" viewBox="0 0 24 24"><path d="M4 12 a8 8 0 1 0 3-6 M4 4 v6 h6" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
              Сбросить
            </button>
            <button
              style={{ ...S.btnBig, ...(rendering ? { opacity: 0.6 } : {}) }}
              type="button"
              onClick={handleRender}
              disabled={rendering}
            >
              {rendering ? `Re-render ${renderProgress}%` : 'Re-render 🦖'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Toast ─────────────────────────────────────────────────────────── */}
      {toast && (
        <div style={S.toast}>
          {toast}
        </div>
      )}

      {/* ── Download modal ────────────────────────────────────────────────── */}
      {showModal && (
        <div style={S.modalOverlay} onClick={e => { if (e.target === e.currentTarget) setShowModal(false) }}>
          <div style={S.modalBox}>
            <div style={{ fontSize: 48 }}>🦖</div>
            <h2 style={{ fontFamily: 'Caveat, cursive', fontSize: 36, margin: '4px 0 6px' }}>Готово!</h2>
            <div style={{ color: 'var(--ink-soft)', fontSize: 16, marginBottom: 16 }}>
              {downloadFilename || 'clip.mp4'} · 9:16 · 1080p
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                style={{ ...S.btn, ...S.btnPink }}
                onClick={handleDownload}
                type="button"
              >
                Скачать сейчас
              </button>
              <button style={S.btn} onClick={() => setShowModal(false)} type="button">Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

// ── Inline style helpers ─────────────────────────────────────────────────────

function FontLinks() {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
      {/* eslint-disable-next-line @next/next/no-page-custom-font */}
      <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;600;700&family=Patrick+Hand&family=Patrick+Hand+SC&display=swap" rel="stylesheet" />
    </>
  )
}

function BaseStyles() {
  return (
    <style>{`
      :root {
        --cream:#FFF3D6;--cream-2:#FFE9B8;--paper:#FFFCF1;--ink:#3A2E2A;--ink-soft:#6B574F;
        --pink:#FF8FA3;--pink-deep:#E96A85;--yellow:#FFD166;--yellow-deep:#F4B829;
        --teal:#7DD3C0;--teal-deep:#4FB6A0;--lilac:#C9B6E4;--mint:#B8E6CC;
      }
      *,*::before,*::after{box-sizing:border-box}
      html,body{margin:0;padding:0}
      body{
        font-family:"Patrick Hand",sans-serif;color:var(--ink);font-size:18px;
        background:var(--cream);
        background-image:
          radial-gradient(circle at 8% 8%,rgba(255,209,102,.4) 0,transparent 28%),
          radial-gradient(circle at 96% 14%,rgba(255,143,163,.3) 0,transparent 26%),
          radial-gradient(circle at 96% 92%,rgba(125,211,192,.32) 0,transparent 28%),
          radial-gradient(circle at 4% 92%,rgba(201,182,228,.3) 0,transparent 28%);
        min-height:100vh;
      }
      h1,h2,h3{font-family:"Caveat",cursive;font-weight:700;margin:0;letter-spacing:.5px}
      a{color:inherit;text-decoration:none}
      button{font-family:inherit;color:inherit;cursor:pointer}
      input[type=range]{width:100%;-webkit-appearance:none;background:transparent;height:34px}
      input[type=range]::-webkit-slider-runnable-track{height:10px;background:#fff;border:2.5px solid var(--ink);border-radius:6px;box-shadow:2px 2px 0 rgba(58,46,42,.15) inset}
      input[type=range]::-moz-range-track{height:10px;background:#fff;border:2.5px solid var(--ink);border-radius:6px}
      input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:24px;height:24px;background:var(--pink);border:2.5px solid var(--ink);border-radius:50%;box-shadow:2px 2px 0 var(--ink);margin-top:-9px;cursor:grab}
      input[type=range]::-moz-range-thumb{width:22px;height:22px;background:var(--pink);border:2.5px solid var(--ink);border-radius:50%;cursor:grab}
      @keyframes wob{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(6deg)}}
      [contenteditable="true"]:focus{outline:2px dashed var(--pink-deep);outline-offset:2px;border-radius:6px}
    `}</style>
  )
}

// ── Styles object ────────────────────────────────────────────────────────────

const S: Record<string, React.CSSProperties> = {
  navbar: {
    maxWidth: 1280, margin: '0 auto', padding: '18px 28px',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 24,
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 8,
    fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 30,
  },
  mark: {
    width: 34, height: 34, display: 'grid', placeItems: 'center',
    background: 'var(--yellow)', border: '3px solid var(--ink)',
    borderRadius: '14px 12px 16px 10px / 12px 14px 10px 16px',
    boxShadow: '2px 3px 0 var(--ink)', transform: 'rotate(-4deg)',
  },
  gold: { color: 'var(--yellow-deep)', textShadow: '1px 2px 0 var(--ink)' },
  navRight: { display: 'flex', gap: 16, alignItems: 'center' },
  betaBadge: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    fontFamily: '"Caveat", cursive', fontSize: 20, lineHeight: '1',
    background: 'var(--mint)', border: '2.5px solid var(--ink)',
    borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
    padding: '4px 12px 2px', boxShadow: '2px 3px 0 var(--ink)', transform: 'rotate(-1.5deg)',
  },
  crumbs: {
    maxWidth: 1280, margin: '0 auto', padding: '0 28px 6px',
    display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink-soft)', fontSize: 16,
  },
  crumbLink: { color: 'var(--ink-soft)' },
  wrap: { maxWidth: 1280, margin: '0 auto', padding: '6px 28px 64px' },
  head: {
    display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between',
    gap: 24, marginBottom: 18, flexWrap: 'wrap',
  },
  h1: { fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 48, lineHeight: 1, margin: 0 },
  sub: { color: 'var(--ink-soft)', marginTop: 6, fontSize: 17 },
  headActions: { display: 'flex', gap: 10, flexWrap: 'wrap' },
  btn: {
    fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 22, lineHeight: '1',
    border: '2.5px solid var(--ink)', padding: '8px 18px 6px',
    borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
    boxShadow: '3px 4px 0 var(--ink)',
    background: '#fff', color: 'var(--ink)',
    display: 'inline-flex', alignItems: 'center', gap: 6,
    cursor: 'pointer',
    transition: 'transform .12s ease, box-shadow .12s ease',
  },
  btnPink: {
    background: 'var(--pink)', color: '#fff', textShadow: '1px 1px 0 rgba(58,46,42,.35)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'minmax(0,420px) 1fr',
    gap: 32, alignItems: 'start',
  },

  // Preview
  preview: {
    aspectRatio: '9/16', maxWidth: 380, margin: '0 auto',
    border: '3px solid var(--ink)', borderRadius: 24,
    boxShadow: '6px 8px 0 var(--ink)',
    background: 'linear-gradient(160deg,#FFB199 0%,#FF8FA3 55%,#E96A85 100%)',
    position: 'relative', overflow: 'hidden',
  },
  previewVir: {
    position: 'absolute', top: 10, left: 10,
    background: 'var(--yellow)', border: '2.5px solid var(--ink)',
    borderRadius: '10px 14px 8px 12px / 12px 8px 14px 10px',
    padding: '3px 10px 1px', fontFamily: '"Caveat", cursive', fontSize: 22, lineHeight: '1.1',
    boxShadow: '2px 2px 0 var(--ink)',
  },
  previewDur: {
    position: 'absolute', top: 10, right: 10,
    background: 'rgba(58,46,42,.85)', color: '#fff', borderRadius: 8,
    padding: '2px 10px 0', fontFamily: '"Caveat", cursive', fontSize: 18,
  },
  previewHook: {
    position: 'absolute', top: 54, left: '50%', transform: 'translateX(-50%) rotate(-2deg)',
    background: '#fff', border: '3px solid var(--ink)', padding: '6px 14px 4px',
    borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
    boxShadow: '3px 4px 0 var(--ink)',
    fontFamily: '"Caveat", cursive', fontSize: 22, maxWidth: '80%', textAlign: 'center', lineHeight: '1.05',
  },
  playBig: {
    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
    width: 78, height: 78, borderRadius: '50%', background: '#fff',
    border: '3px solid var(--ink)', boxShadow: '4px 5px 0 var(--ink)',
    display: 'grid', placeItems: 'center',
  },
  faceDot: {
    position: 'absolute', bottom: '30%', left: '50%', transform: 'translate(-50%,0)',
    width: 60, height: 60, borderRadius: '50%', border: '3px dashed #fff',
    boxShadow: '0 0 0 2px rgba(58,46,42,.4)',
  },
  caption: {
    position: 'absolute', left: '8%', right: '8%', bottom: '10%',
    background: 'rgba(0,0,0,.65)', color: '#fff', textAlign: 'center',
    padding: '8px 14px 6px', borderRadius: 8,
    fontFamily: '"Patrick Hand SC", sans-serif', fontSize: 16, letterSpacing: 1,
    textTransform: 'uppercase', lineHeight: '1.15',
  },

  // Scrubber
  scrub: {
    marginTop: 18, padding: '14px 16px',
    background: 'var(--paper)', border: '3px solid var(--ink)',
    borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
    boxShadow: '4px 5px 0 var(--ink)',
  },
  scrubRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 },
  playMini: {
    width: 34, height: 34, borderRadius: '50%', background: 'var(--pink)',
    border: '2.5px solid var(--ink)', boxShadow: '2px 3px 0 var(--ink)',
    display: 'grid', placeItems: 'center', flexShrink: 0,
  },
  scrubTime: { fontFamily: '"Caveat", cursive', fontSize: 22, lineHeight: '1', color: 'var(--ink-soft)' },
  timeline: {
    position: 'relative', height: 34, background: '#fff',
    border: '2.5px solid var(--ink)', borderRadius: 8, overflow: 'hidden', boxShadow: '2px 3px 0 var(--ink)',
  },
  timelineWave: {
    position: 'absolute', inset: 0,
    background: 'repeating-linear-gradient(90deg, transparent 0 6px, rgba(58,46,42,.2) 6px 7px)',
  },
  timelineClip: {
    position: 'absolute', top: 0, bottom: 0, left: '18%', width: '36%',
    background: 'rgba(255,209,102,.55)', borderLeft: '3px solid var(--ink)', borderRight: '3px solid var(--ink)',
  },
  timelineHandle: {
    position: 'absolute', top: -6, bottom: -6, width: 14,
    background: 'var(--yellow-deep)', border: '2.5px solid var(--ink)', borderRadius: 4,
    cursor: 'ew-resize',
  },
  timelineCursor: {
    position: 'absolute', top: -4, bottom: -4, width: 3,
    background: 'var(--pink-deep)', left: '32%', boxShadow: '0 0 0 1px rgba(58,46,42,.6)',
  },
  timelineMarks: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 13, color: 'var(--ink-soft)',
    fontFamily: '"Patrick Hand SC", sans-serif', letterSpacing: 1, textTransform: 'uppercase', marginTop: 8,
  },

  // Cards
  cardTiltR: {
    background: 'var(--paper)', border: '3px solid var(--ink)', boxShadow: '6px 8px 0 var(--ink)',
    padding: '22px 24px', borderRadius: '24px 30px 22px 28px / 28px 24px 30px 22px', transform: 'rotate(.3deg)',
  },
  cardTiltL: {
    background: 'var(--paper)', border: '3px solid var(--ink)', boxShadow: '6px 8px 0 var(--ink)',
    padding: '22px 24px', borderRadius: '28px 24px 30px 22px / 24px 28px 22px 30px', transform: 'rotate(-.4deg)',
  },
  cardH2: { fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 30, margin: 0 },
  cardHint: { color: 'var(--ink-soft)', fontSize: 15, marginBottom: 14 },

  // Settings fields
  field: { marginBottom: 16 },
  lbl: {
    display: 'block',
    fontFamily: '"Patrick Hand SC", sans-serif', letterSpacing: '1.2px', textTransform: 'uppercase',
    fontSize: 13, color: 'var(--ink-soft)', marginBottom: 6, paddingLeft: 4,
  },
  chips: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  chip: {
    fontFamily: '"Caveat", cursive', fontSize: 20, lineHeight: '1',
    background: '#fff', border: '2.5px solid var(--ink)', padding: '6px 12px 4px',
    borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
    boxShadow: '2px 2px 0 var(--ink)', cursor: 'pointer',
    transition: 'transform .12s ease, box-shadow .12s ease',
  },
  chipOn: { background: 'var(--mint)' },
  chipOnPink: { background: 'var(--pink)', color: '#fff', textShadow: '1px 1px 0 rgba(58,46,42,.35)' },
  chipOnYellow: { background: 'var(--yellow)' },
  chipOnLilac: { background: 'var(--lilac)' },
  sliderMarks: {
    display: 'flex', justifyContent: 'space-between', fontSize: 13,
    color: 'var(--ink-soft)', fontFamily: '"Patrick Hand SC", sans-serif',
    letterSpacing: 1, textTransform: 'uppercase', marginTop: 6,
  },

  // Post meta
  metaBlock: { marginBottom: 14 },
  metaBlockLbl: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    fontFamily: '"Patrick Hand SC", sans-serif', letterSpacing: '1.2px', textTransform: 'uppercase',
    fontSize: 13, color: 'var(--ink-soft)', marginBottom: 5, padding: '0 4px',
  },
  copyBtn: {
    fontFamily: '"Caveat", cursive', fontSize: 18, color: 'var(--pink-deep)',
    textTransform: 'none', letterSpacing: 0, cursor: 'pointer',
  },
  metaInput: {
    width: '100%', padding: '10px 14px 8px', fontSize: 17,
    fontFamily: '"Patrick Hand", sans-serif', color: 'var(--ink)',
    background: '#fff', border: '3px solid var(--ink)',
    borderRadius: '16px 20px 14px 18px / 18px 14px 20px 16px',
    boxShadow: '3px 3px 0 var(--ink)', outline: 'none',
  },
  metaTextarea: {
    width: '100%', padding: '10px 14px 8px', fontSize: 17,
    fontFamily: '"Patrick Hand", sans-serif', color: 'var(--ink)',
    background: '#fff', border: '3px solid var(--ink)',
    borderRadius: '16px 20px 14px 18px / 18px 14px 20px 16px',
    boxShadow: '3px 3px 0 var(--ink)', outline: 'none', resize: 'vertical',
  },
  hashtagsBox: {
    background: '#fff', border: '3px solid var(--ink)',
    borderRadius: '16px 20px 14px 18px / 18px 14px 20px 16px',
    boxShadow: '3px 3px 0 var(--ink)', padding: '10px 12px 6px',
    display: 'flex', flexWrap: 'wrap', gap: 6,
  },
  tag: {
    background: 'var(--lilac)', border: '2px solid var(--ink)',
    borderRadius: '10px 14px 8px 12px / 12px 8px 14px 10px',
    padding: '3px 10px 1px', fontFamily: '"Caveat", cursive', fontSize: 18, lineHeight: '1.1',
    boxShadow: '1px 2px 0 var(--ink)',
  },

  // Transcript
  seg: {
    display: 'flex', gap: 12, alignItems: 'flex-start',
    padding: '10px 12px', border: '2.5px solid var(--ink)',
    borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
    background: '#fff', boxShadow: '2px 3px 0 var(--ink)', marginBottom: 10,
  },
  segInClip: { background: 'var(--cream-2)' },
  segTs: { flexShrink: 0, fontFamily: '"Caveat", cursive', fontSize: 20, color: 'var(--pink-deep)', lineHeight: '1.1', minWidth: 64 },
  segText: { flex: 1, lineHeight: '1.3', fontSize: 17 },

  // Render bar
  renderBar: {
    marginTop: 24, padding: '18px 24px',
    background: 'var(--paper)', border: '3px solid var(--ink)',
    borderRadius: '22px 26px 20px 24px / 20px 24px 26px 22px',
    boxShadow: '6px 8px 0 var(--ink)',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, flexWrap: 'wrap',
  },
  renderBarInfo: { fontFamily: '"Caveat", cursive', fontSize: 22 },
  renderBarMeta: { fontFamily: '"Patrick Hand", sans-serif', fontSize: 15, color: 'var(--ink-soft)', marginTop: 2, lineHeight: '1.2' },
  btnBig: {
    fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 28,
    background: 'var(--pink)', color: '#fff',
    border: '3px solid var(--ink)',
    borderRadius: '20px 16px 22px 18px / 16px 20px 18px 22px',
    padding: '10px 26px 8px', boxShadow: '5px 6px 0 var(--ink)',
    textShadow: '1px 1px 0 rgba(58,46,42,.35)', cursor: 'pointer',
    transition: 'transform .12s ease, box-shadow .12s ease',
  },

  // Toast
  toast: {
    position: 'fixed', left: '50%', bottom: 34,
    transform: 'translateX(-50%) rotate(-1deg)',
    background: 'var(--mint)', border: '3px solid var(--ink)',
    borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
    boxShadow: '5px 6px 0 var(--ink)', padding: '12px 22px 10px',
    fontFamily: '"Caveat", cursive', fontSize: 24, zIndex: 50,
    pointerEvents: 'none',
  },

  // Modal
  modalOverlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(58,46,42,.45)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 60,
  },
  modalBox: {
    background: 'var(--paper)', border: '3px solid var(--ink)',
    borderRadius: '24px 28px 22px 26px / 22px 26px 28px 24px',
    boxShadow: '7px 9px 0 var(--ink)', padding: '24px 28px', maxWidth: 380,
    textAlign: 'center', transform: 'rotate(-.6deg)',
  },
}
