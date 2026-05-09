'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { api } from '@/lib/api'

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
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const CARD_COLORS = [
  'linear-gradient(160deg,#FFB199 0%,#FF8FA3 55%,#E96A85 100%)',
  'linear-gradient(160deg,#B8E6CC 0%,#7DD3C0 55%,#4FB6A0 100%)',
  'linear-gradient(160deg,#FFD166 0%,#F4B829 55%,#e8a000 100%)',
  'linear-gradient(160deg,#C9B6E4 0%,#9B7FCA 55%,#7B5DB0 100%)',
  'linear-gradient(160deg,#FFF3D6 0%,#FFE9B8 55%,#FFD166 100%)',
]

function viralEmoji(score: number): string {
  if (score >= 9.2) return '🔥'
  if (score >= 9.0) return '⚡'
  if (score >= 8.5) return '🌟'
  return ''
}

export default function CandidatesPage() {
  const params = useParams()
  const router = useRouter()
  const fileId = params.fileId as string

  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [renderingAll, setRenderingAll] = useState(false)
  const [renderingIdx, setRenderingIdx] = useState<Set<number>>(new Set())

  useEffect(() => {
    setLoading(true)
    api.get(`/clips/${fileId}/candidates`)
      .then(res => {
        const data = res.data
        setCandidates(Array.isArray(data.candidates) ? data.candidates : Array.isArray(data) ? data : [])
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Не удалось загрузить кандидатов')
      })
      .finally(() => setLoading(false))
  }, [fileId])

  const handleRenderOne = async (index: number) => {
    setRenderingIdx(prev => new Set(prev).add(index))
    try {
      await api.post(`/render-clip`, {
        file_id: fileId,
        clip_index: index,
        platform: 'tiktok',
        subtitle_style: 'podcast',
        render_mode: 'blur_background',
        enable_jump_cut: false,
        enable_filler_removal: false,
      })
    } catch (err: any) {
      alert(`Ошибка рендера: ${err.response?.data?.detail || err.message}`)
    } finally {
      setRenderingIdx(prev => {
        const s = new Set(prev); s.delete(index); return s
      })
    }
  }

  const handleRenderAll = async () => {
    setRenderingAll(true)
    for (let i = 0; i < candidates.length; i++) {
      try {
        await api.post(`/render-clip`, {
          file_id: fileId,
          clip_index: i,
          platform: 'tiktok',
          subtitle_style: 'podcast',
          render_mode: 'blur_background',
          enable_jump_cut: false,
          enable_filler_removal: false,
        })
      } catch {}
    }
    setRenderingAll(false)
  }

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
        h1,h2,h3 { font-family: "Caveat", cursive; font-weight: 700; margin: 0; letter-spacing: .5px; }
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
        .head {
          display: flex; align-items: flex-end; justify-content: space-between;
          gap: 24px; margin-bottom: 28px; flex-wrap: wrap;
        }
        .head h1 { font-size: 48px; line-height: 1; }
        .head .sub { color: var(--ink-soft); margin-top: 6px; font-size: 17px; }

        .action-bar {
          margin-bottom: 24px; padding: 14px 20px;
          background: var(--paper); border: 3px solid var(--ink);
          border-radius: 20px 24px 18px 22px / 18px 22px 24px 20px;
          box-shadow: 4px 5px 0 var(--ink);
          display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap;
        }
        .action-bar .info {
          font-family: "Caveat", cursive; font-size: 22px; color: var(--ink);
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
        .btn-big:disabled { opacity: .6; cursor: not-allowed; transform: none; }

        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 24px;
        }

        .clip-card {
          background: var(--paper); border: 3px solid var(--ink);
          border-radius: 24px 20px 26px 22px / 20px 24px 22px 26px;
          box-shadow: 5px 7px 0 var(--ink);
          overflow: hidden;
          transition: transform .15s, box-shadow .15s;
          display: flex; flex-direction: column;
        }
        .clip-card:hover { transform: translate(-2px,-3px); box-shadow: 7px 10px 0 var(--ink); }

        .preview-9-16 {
          aspect-ratio: 9/16; position: relative; overflow: hidden;
          display: flex; align-items: center; justify-content: center;
        }
        .preview-9-16 .vir-badge {
          position: absolute; top: 10px; left: 10px;
          background: var(--yellow); border: 2.5px solid var(--ink);
          border-radius: 10px 14px 8px 12px / 12px 8px 14px 10px;
          padding: 3px 10px 1px; font-family: "Caveat", cursive; font-size: 22px; line-height: 1.1;
          box-shadow: 2px 2px 0 var(--ink);
        }
        .preview-9-16 .vir-badge.top { background: var(--pink); color: #fff; text-shadow: 1px 1px 0 rgba(58,46,42,.35); }
        .preview-9-16 .dur-badge {
          position: absolute; top: 10px; right: 10px;
          background: rgba(58,46,42,.85); color: #fff; border-radius: 8px;
          padding: 2px 10px 0; font-family: "Caveat", cursive; font-size: 18px;
        }
        .preview-9-16 .hook-label {
          position: absolute; top: 54px; left: 50%; transform: translateX(-50%) rotate(-2deg);
          background: #fff; border: 3px solid var(--ink); padding: 6px 14px 4px;
          border-radius: 14px 18px 12px 16px / 16px 12px 18px 14px;
          box-shadow: 3px 4px 0 var(--ink);
          font-family: "Caveat", cursive; font-size: 20px; max-width: 80%; text-align: center; line-height: 1.05;
        }
        .preview-9-16 .play-btn {
          width: 64px; height: 64px; border-radius: 50%; background: #fff;
          border: 3px solid var(--ink); box-shadow: 4px 5px 0 var(--ink);
          display: grid; place-items: center;
        }

        .card-body { padding: 16px 18px; flex: 1; display: flex; flex-direction: column; }
        .card-body .clip-title {
          font-family: "Caveat", cursive; font-size: 22px; line-height: 1.1; margin-bottom: 4px;
        }
        .card-body .clip-meta {
          color: var(--ink-soft); font-size: 14px; margin-bottom: 12px; line-height: 1.3;
        }
        .card-body .btn-render {
          font-family: "Caveat", cursive; font-weight: 700; font-size: 20px;
          background: var(--pink); color: #fff; border: 2.5px solid var(--ink);
          border-radius: 14px 18px 12px 16px / 16px 12px 18px 14px;
          box-shadow: 3px 4px 0 var(--ink); padding: 8px 16px 6px; width: 100%;
          text-shadow: 1px 1px 0 rgba(58,46,42,.35);
          transition: transform .12s, box-shadow .12s, background .15s;
        }
        .card-body .btn-render:hover { transform: translate(-1px,-2px); box-shadow: 4px 6px 0 var(--ink); background: var(--pink-deep); }
        .card-body .btn-render:disabled { opacity: .6; cursor: not-allowed; transform: none; }

        .loading-state {
          display: flex; align-items: center; justify-content: center; min-height: 300px;
          font-family: "Caveat", cursive; font-size: 28px; color: var(--ink-soft);
        }
        .error-state {
          background: #FEF2F2; border: 3px solid #F87171; padding: 20px 24px;
          border-radius: 18px; box-shadow: 4px 5px 0 #F87171; color: #991B1B;
          font-family: "Caveat", cursive; font-size: 22px; margin: 24px 0;
        }
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
        <span style={{ color: 'var(--ink)' }}>Кандидаты</span>
      </div>

      <div className="wrap">
        <div className="head">
          <div>
            <h1>
              Кандидаты от <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 2px 0 var(--ink)' }}>ИИ</span> 🦖
            </h1>
            <div className="sub">Выбери клипы для рендера или рендери все сразу</div>
          </div>
        </div>

        {loading && (
          <div className="loading-state">
            <span style={{ animation: 'wob 1.4s ease-in-out infinite', display: 'inline-block', marginRight: 16, fontSize: 48 }}>🦖</span>
            Загружаем кандидатов...
          </div>
        )}

        {error && (
          <div className="error-state">❌ {error}</div>
        )}

        {!loading && !error && candidates.length > 0 && (
          <>
            <div className="action-bar">
              <div className="info">
                Найдено: <b>{candidates.length}</b> клипов · выбери интересные или рендери всё
              </div>
              <button
                className="btn-big"
                onClick={handleRenderAll}
                disabled={renderingAll}
              >
                {renderingAll ? '⏳ Рендерим...' : `Render all 🦖`}
              </button>
            </div>

            <div className="grid">
              {candidates.map((candidate, index) => {
                const duration = candidate.end_time - candidate.start_time
                const isTop = candidate.virality_score >= 9.0
                const colorBg = CARD_COLORS[index % CARD_COLORS.length]
                const isRendering = renderingIdx.has(index)

                return (
                  <div key={index} className="clip-card">
                    <div
                      className="preview-9-16"
                      style={{ background: colorBg }}
                    >
                      <div className={`vir-badge${isTop ? ' top' : ''}`}>
                        {viralEmoji(candidate.virality_score)} {candidate.virality_score}
                      </div>
                      <div className="dur-badge">{formatTime(Math.round(duration))}</div>
                      {candidate.hook && (
                        <div className="hook-label">{candidate.hook}</div>
                      )}
                      <div className="play-btn">
                        <svg width="22" height="22" viewBox="0 0 24 24" style={{ marginLeft: 4 }}>
                          <path d="M5 4 L20 12 L5 20 Z" fill="#3A2E2A" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
                        </svg>
                      </div>
                    </div>

                    <div className="card-body">
                      <div className="clip-title">
                        {candidate.emojis && candidate.emojis.length > 0 && candidate.emojis.slice(0,2).join('')}{' '}
                        {candidate.title}
                      </div>
                      <div className="clip-meta">
                        {formatTime(Math.round(candidate.start_time))} → {formatTime(Math.round(candidate.end_time))} · {formatTime(Math.round(duration))} · TikTok
                      </div>
                      <button
                        className="btn-render"
                        disabled={isRendering}
                        onClick={() => router.push(`/render/${fileId}/${index + 1}`)}
                      >
                        {isRendering ? '⏳ Рендерим...' : '✏ Редактировать + Рендерить'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}

        {!loading && !error && candidates.length === 0 && (
          <div className="loading-state" style={{ flexDirection: 'column', gap: 16 }}>
            <span style={{ fontSize: 64 }}>🦕</span>
            <div>Кандидатов пока нет — сначала обработайте видео</div>
            <button
              style={{
                fontFamily: 'Caveat, cursive', fontSize: 22, background: 'var(--pink)',
                color: '#fff', border: '3px solid var(--ink)', borderRadius: '16px 20px 14px 18px / 18px 14px 20px 16px',
                padding: '8px 24px 6px', boxShadow: '4px 5px 0 var(--ink)', cursor: 'pointer',
                textShadow: '1px 1px 0 rgba(58,46,42,.35)',
              }}
              onClick={() => router.push('/app')}
            >
              ← В студию
            </button>
          </div>
        )}
      </div>
    </>
  )
}
