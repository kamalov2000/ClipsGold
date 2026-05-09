'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

/* ─── shared SVG symbols (rendered once, hidden) ─── */
const SvgDefs = () => (
  <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true">
    <defs>
      <symbol id="lp-dino" viewBox="0 0 220 230">
        <path d="M48 138 Q 12 116 22 86 Q 34 96 50 110" fill="#FFD166" stroke="#3A2E2A" strokeWidth="4" strokeLinejoin="round" />
        <ellipse cx="108" cy="148" rx="70" ry="58" fill="#FFD166" stroke="#3A2E2A" strokeWidth="4" strokeLinejoin="round" />
        <ellipse cx="118" cy="166" rx="40" ry="28" fill="#FFF0C7" />
        <path d="M62 110 L72 86 L82 108 L96 80 L110 106 L126 78 L140 104 L156 82 L168 108" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3.5" strokeLinejoin="round" />
        <ellipse cx="86" cy="208" rx="18" ry="14" fill="#FFD166" stroke="#3A2E2A" strokeWidth="4" strokeLinejoin="round" />
        <ellipse cx="132" cy="208" rx="18" ry="14" fill="#FFD166" stroke="#3A2E2A" strokeWidth="4" strokeLinejoin="round" />
        <circle cx="76" cy="214" r="3" fill="#3A2E2A" />
        <circle cx="86" cy="217" r="3" fill="#3A2E2A" />
        <circle cx="96" cy="214" r="3" fill="#3A2E2A" />
        <circle cx="122" cy="214" r="3" fill="#3A2E2A" />
        <circle cx="132" cy="217" r="3" fill="#3A2E2A" />
        <circle cx="142" cy="214" r="3" fill="#3A2E2A" />
        <g style={{ transformBox: 'fill-box', transformOrigin: '95px 132px', animation: 'lp-wave 3.2s ease-in-out infinite' }}>
          <path d="M95 132 Q 78 116 70 96" fill="none" stroke="#3A2E2A" strokeWidth="6" strokeLinecap="round" />
          <circle cx="69" cy="93" r="6" fill="#FFD166" stroke="#3A2E2A" strokeWidth="3" />
        </g>
        <path d="M138 144 Q 152 152 156 162" fill="none" stroke="#3A2E2A" strokeWidth="5" strokeLinecap="round" />
        <ellipse cx="148" cy="84" rx="52" ry="46" fill="#FFD166" stroke="#3A2E2A" strokeWidth="4" strokeLinejoin="round" />
        <ellipse cx="125" cy="98" rx="9" ry="6" fill="#FF8FA3" opacity={0.8} />
        <path d="M118 100 Q 132 112 148 102" stroke="#3A2E2A" strokeWidth="3.5" fill="none" strokeLinecap="round" />
        <path d="M126 105 q 2 4 6 4" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round" />
        <circle cx="180" cy="86" r="2.5" fill="#3A2E2A" />
        <g style={{ transformBox: 'fill-box', transformOrigin: 'center', animation: 'lp-blink 5.4s infinite' }}>
          <circle cx="138" cy="76" r="13" fill="#fff" stroke="#3A2E2A" strokeWidth="3" />
          <circle cx="140" cy="78" r="6.5" fill="#3A2E2A" />
          <circle cx="142" cy="76" r="2" fill="#fff" />
        </g>
        <g style={{ transformBox: 'fill-box', transformOrigin: 'center', animation: 'lp-blink 5.4s 0.05s infinite' }}>
          <circle cx="170" cy="74" r="9" fill="#fff" stroke="#3A2E2A" strokeWidth="3" />
          <circle cx="172" cy="76" r="4.5" fill="#3A2E2A" />
          <circle cx="173" cy="74" r="1.5" fill="#fff" />
        </g>
        <path d="M118 50 L124 38 L130 50" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3" strokeLinejoin="round" />
        <path d="M138 44 L146 30 L154 44" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3" strokeLinejoin="round" />
      </symbol>

      <symbol id="lp-sparkle" viewBox="0 0 24 24">
        <path d="M12 1 L14 10 L23 12 L14 14 L12 23 L10 14 L1 12 L10 10 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="1.5" strokeLinejoin="round" />
      </symbol>

      <symbol id="lp-star" viewBox="0 0 30 30">
        <path d="M15 2 L18 12 L28 15 L18 18 L15 28 L12 18 L2 15 L12 12 Z" fill="none" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round" />
      </symbol>

      <symbol id="lp-cloud" viewBox="0 0 80 40">
        <path d="M14 32 Q 0 32 4 22 Q 0 12 14 14 Q 18 4 30 8 Q 36 0 48 6 Q 62 2 66 14 Q 80 14 76 26 Q 80 36 66 34 Z" fill="#fff" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round" />
      </symbol>

      <symbol id="lp-squiggle" viewBox="0 0 100 16">
        <path d="M2 8 Q 12 -2 24 8 T 48 8 T 72 8 T 98 8" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </symbol>

      <symbol id="lp-arrow" viewBox="0 0 140 60">
        <path d="M4 30 Q 50 -10 100 20 Q 120 30 130 50" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeDasharray="2 6" />
        <path d="M120 36 L 132 50 L 116 54" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </symbol>
    </defs>
  </svg>
)

/* ─── keyframes injected once ─── */
const GlobalKeyframes = () => (
  <style>{`
    @keyframes lp-blink {
      0%, 88%, 100% { transform: scaleY(1); }
      91%, 95% { transform: scaleY(0.08); }
    }
    @keyframes lp-wave {
      0%,100% { transform: rotate(0deg); }
      20% { transform: rotate(-22deg); }
      40% { transform: rotate(8deg); }
      60% { transform: rotate(-14deg); }
      80% { transform: rotate(0deg); }
    }
    @keyframes lp-bob {
      0%,100% { transform: translateY(0) rotate(-3deg); }
      50% { transform: translateY(-10px) rotate(-2deg); }
    }
    @keyframes lp-spin { to { transform: rotate(360deg); } }
    @keyframes lp-float {
      0%,100% { transform: translateY(0) rotate(var(--r, 0deg)); }
      50% { transform: translateY(-12px) rotate(var(--r, 0deg)); }
    }
    .lp-spin { animation: lp-spin 14s linear infinite; }
    .lp-float { animation: lp-float 6s ease-in-out infinite; }
    .lp-bob { animation: lp-bob 4.8s ease-in-out infinite; }

    .lp-step:hover { transform: translate(-3px,-4px) rotate(-1deg) !important; box-shadow: 9px 12px 0 #3A2E2A !important; }
    .lp-step:nth-child(2) { transform: rotate(1.2deg); background: #FFF7E0; }
    .lp-step:nth-child(2):hover { transform: translate(-3px,-4px) rotate(0) !important; }
    .lp-step:nth-child(3) { transform: rotate(-1deg); }

    .lp-feature:hover { transform: translate(-3px,-4px) rotate(-1.2deg); box-shadow: 9px 11px 0 #3A2E2A; }

    .lp-clip-card:nth-child(odd) { transform: rotate(-1.4deg); }
    .lp-clip-card:nth-child(even) { transform: rotate(1.2deg); }
    .lp-clip-card:hover { transform: translate(-3px,-4px) rotate(0) !important; box-shadow: 8px 10px 0 #3A2E2A !important; }

    .lp-faq-detail:hover { transform: rotate(-.3deg); }
    .lp-faq-detail[open] { background: #FFF7E0; }
    .lp-faq-detail[open] .lp-faq-toggle { transform: rotate(45deg); background: var(--pink); color:#fff; }

    .lp-navlink:hover { color: #E96A85; }
    .lp-btn { transition: transform .12s ease, box-shadow .12s ease, background .15s ease; }
    .lp-btn:hover { transform: translate(-2px,-2px) rotate(-1.5deg); box-shadow: 6px 7px 0 #3A2E2A !important; }
    .lp-btn:active { transform: translate(2px,2px); box-shadow: 1px 2px 0 #3A2E2A !important; }
    .lp-btn-yellow:hover { background: var(--yellow-deep) !important; }
    .lp-btn-pink:hover { background: var(--pink-deep) !important; }
    .lp-btn-ghost:hover { background: var(--paper) !important; }

    .lp-drop-card:hover { background: #FFF7E0; }
    .lp-drop-card.dragover { background: #FFE9B8; border-style: dashed; border-color: #E96A85; }
    .lp-drop-card.has-file .lp-drop-title { color: #4FB6A0; font-weight: 700; }

    .lp-tab-active { background: var(--yellow) !important; color: var(--ink) !important; transform: translateY(2px); }

    details.lp-faq-detail summary::-webkit-details-marker { display: none; }

    @media (max-width: 900px) {
      .lp-hero-grid { grid-template-columns: 1fr !important; }
      .lp-dino-stage { min-height: 380px; order: -1; }
      .lp-steps { grid-template-columns: 1fr !important; }
      .lp-features { grid-template-columns: 1fr 1fr !important; }
      .lp-arrows { display: none !important; }
    }
    @media (max-width: 700px) {
      .lp-footer-cols { grid-template-columns: 1fr 1fr !important; }
      .lp-clip-rail { grid-template-columns: repeat(2, 1fr) !important; }
    }
    @media (max-width: 560px) {
      .lp-features { grid-template-columns: 1fr !important; }
      .lp-nav-links { display: none !important; }
      .lp-url-card { flex-direction: column !important; align-items: stretch !important; }
      .lp-url-card .lp-btn { width: 100%; justify-content: center; }
      .lp-clip-rail { grid-template-columns: 1fr !important; }
      .lp-footer-cols { grid-template-columns: 1fr !important; }
    }
  `}</style>
)

/* ─── helpers ─── */
const S = {
  // layout
  wrap: { maxWidth: 1180, margin: '0 auto', padding: '0 28px' } as React.CSSProperties,
  // card base
  card: {
    background: 'var(--paper)',
    border: '3px solid var(--ink)',
    borderRadius: '28px 24px 30px 22px / 24px 28px 22px 30px',
    boxShadow: '6px 8px 0 var(--ink)',
  } as React.CSSProperties,
}

function Btn({
  href,
  onClick,
  variant = 'pink',
  size = 'md',
  className = '',
  children,
  type,
}: {
  href?: string
  onClick?: () => void
  variant?: 'pink' | 'yellow' | 'teal' | 'ghost'
  size?: 'md' | 'lg' | 'sm'
  className?: string
  children: React.ReactNode
  type?: 'button' | 'submit'
}) {
  const bg = variant === 'pink' ? 'var(--pink)' : variant === 'yellow' ? 'var(--yellow)' : variant === 'teal' ? 'var(--teal)' : 'var(--paper)'
  const color = variant === 'pink' ? '#fff' : 'var(--ink)'
  const textShadow = variant === 'pink' ? '1px 1px 0 rgba(58,46,42,.35)' : 'none'
  const fs = size === 'lg' ? 30 : size === 'sm' ? 22 : 26
  const pad = size === 'lg' ? '12px 28px 10px' : size === 'sm' ? '8px 18px 6px' : '10px 22px 8px'

  const hoverClass = variant === 'pink' ? 'lp-btn-pink' : variant === 'yellow' ? 'lp-btn-yellow' : 'lp-btn-ghost'

  const style: React.CSSProperties = {
    fontFamily: '"Caveat", cursive',
    fontWeight: 700,
    fontSize: fs,
    background: bg,
    color,
    border: '3px solid var(--ink)',
    borderRadius: '18px 14px 20px 12px / 14px 18px 12px 20px',
    padding: pad,
    boxShadow: '4px 5px 0 var(--ink)',
    cursor: 'pointer',
    textDecoration: 'none',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    textShadow,
  }

  if (href) return <a href={href} style={style} className={`lp-btn ${hoverClass} ${className}`}>{children}</a>
  return <button type={type || 'button'} onClick={onClick} style={style} className={`lp-btn ${hoverClass} ${className}`}>{children}</button>
}

/* ─── section eyebrow ─── */
function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 10,
      fontFamily: '"Patrick Hand SC", sans-serif', letterSpacing: 2, fontSize: 16,
      color: 'var(--ink-soft)',
    }}>
      <span style={{ height: 0, width: 28, borderTop: '3px dotted var(--ink-soft)' }} />
      {children}
      <span style={{ height: 0, width: 28, borderTop: '3px dotted var(--ink-soft)' }} />
    </div>
  )
}

/* ─── doodle floaters ─── */
function Doodle({ symbol, style }: { symbol: string; style: React.CSSProperties }) {
  return (
    <svg style={{ position: 'absolute', pointerEvents: 'none', ...style }}>
      <use href={symbol} />
    </svg>
  )
}

/* ─── main component ─── */
export default function HomePage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'yt' | 'file'>('yt')
  const [dropState, setDropState] = useState<{ dragging: boolean; fileName: string | null; fileSize: string | null }>({ dragging: false, fileName: null, fileSize: null })
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const token = localStorage.getItem('cg_access_token')
    if (token) router.replace('/app')
  }, [router])

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault()
    setDropState(d => ({ ...d, dragging: false }))
    const f = e.dataTransfer?.files?.[0]
    if (f) setFileInfo(f)
  }
  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) setFileInfo(f)
  }
  function setFileInfo(f: File) {
    setDropState({ dragging: false, fileName: f.name, fileSize: (f.size / 1024 / 1024).toFixed(1) + ' МБ · готово к рендеру' })
  }

  return (
    <>
      <GlobalKeyframes />
      <SvgDefs />

      {/* body bg */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: -1,
        background: 'var(--cream)',
        backgroundImage: `
          radial-gradient(circle at 12% 18%, rgba(255,209,102,.45) 0, transparent 35%),
          radial-gradient(circle at 88% 12%, rgba(255,143,163,.35) 0, transparent 32%),
          radial-gradient(circle at 90% 80%, rgba(125,211,192,.4) 0, transparent 36%),
          radial-gradient(circle at 8% 88%, rgba(201,182,228,.35) 0, transparent 36%)
        `,
      }} />

      {/* ─── NAV ─── */}
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '22px 28px', maxWidth: 1180, margin: '0 auto', position: 'relative', zIndex: 5 }}>
        <a href="#" style={{ display: 'flex', alignItems: 'center', gap: 10, fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 36, textDecoration: 'none', color: 'var(--ink)' }}>
          <span style={{
            width: 44, height: 44, display: 'grid', placeItems: 'center',
            background: 'var(--yellow)', border: '3px solid var(--ink)',
            borderRadius: '18px 14px 20px 12px / 14px 18px 12px 20px',
            boxShadow: '3px 4px 0 var(--ink)', transform: 'rotate(-4deg)', flexShrink: 0,
          }}>
            <svg width="26" height="26" viewBox="0 0 26 26">
              <path d="M5 7 L 13 13 L 21 7 M 13 13 V 22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="13" cy="13" r="3" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2" />
            </svg>
          </span>
          <span>Clips<span style={{ color: 'var(--yellow-deep)', textShadow: '1px 2px 0 var(--ink)' }}>Gold</span></span>
        </a>

        <div className="lp-nav-links" style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
          {(['#how', '#features', '#examples', '#faq'] as const).map((href, i) => (
            <a key={href} href={href} className="lp-navlink" style={{ fontFamily: '"Patrick Hand", sans-serif', fontSize: 20, color: 'var(--ink)', textDecoration: 'none', padding: '6px 4px' }}>
              {['Как работает', 'Фичи', 'Примеры', 'FAQ'][i]}
            </a>
          ))}
          <Link href="/login" className="lp-navlink" style={{ fontFamily: '"Caveat", cursive', fontSize: 20, color: 'var(--ink)', textDecoration: 'none' }}>Войти</Link>
          <a href="/register" className="lp-btn lp-btn-yellow" style={{
            fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 19,
            background: 'var(--yellow)', color: 'var(--ink)',
            border: '3px solid var(--ink)',
            borderRadius: '18px 14px 20px 12px / 14px 18px 12px 20px',
            padding: '5px 14px 3px',
            boxShadow: '4px 5px 0 var(--ink)',
            cursor: 'pointer', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 8,
          }}>Регистрация</a>
        </div>
      </nav>

      {/* ─── HERO ─── */}
      <section style={{ padding: '24px 0 80px', position: 'relative' }}>
        <Doodle symbol="#lp-star" style={{ top: 120, left: '6%', width: 48, height: 48 } as React.CSSProperties} />
        <Doodle symbol="#lp-sparkle" style={{ top: 60, right: '10%', width: 36, height: 36 } as React.CSSProperties} />
        <Doodle symbol="#lp-cloud" style={{ bottom: 60, left: '14%', width: 70, height: 36 } as React.CSSProperties} />

        <div style={S.wrap}>
          <div className="lp-hero-grid" style={{ display: 'grid', gridTemplateColumns: '1.05fr .95fr', gap: 40, alignItems: 'center' }}>

            {/* left col */}
            <div>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 8,
                background: 'var(--paper)', border: '3px solid var(--ink)', borderRadius: 999,
                padding: '6px 16px 4px', fontFamily: '"Patrick Hand", sans-serif', fontSize: 18,
                boxShadow: '3px 4px 0 var(--ink)', transform: 'rotate(-2deg)',
              }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--teal)', border: '2px solid var(--ink)' }} />
                AI режет видео, пока ты пьёшь чай
              </span>

              <h1 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(54px, 7.2vw, 110px)', lineHeight: 0.95, marginTop: 18, paddingBottom: 14 }}>
                Длинное<br />видео&nbsp;→&nbsp;
                <span style={{ color: 'var(--yellow-deep)', position: 'relative', display: 'inline-block', textShadow: '2px 3px 0 var(--ink)' }}>
                  золотые&nbsp;клипы
                  <span style={{
                    content: '""', position: 'absolute', left: -6, right: -6, bottom: 6, height: 16,
                    background: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 16'><path d='M2 12 Q 50 -2 100 8 T 198 6' stroke='%23FF8FA3' stroke-width='6' fill='none' stroke-linecap='round'/></svg>") no-repeat center / 100% 100%`,
                    zIndex: -1, opacity: 0.9, display: 'block',
                  }} />
                </span>
              </h1>

              <p style={{ fontSize: 22, color: 'var(--ink-soft)', marginTop: 40, maxWidth: 520 }}>
                Кидай YouTube-ссылку или MP4 — Whisper расшифрует речь, Claude найдёт самые вирусные моменты, а ClipsGold соберёт готовые шортсы для TikTok, Reels и YouTube Shorts. Три шага — пачка клипов.
              </p>

              {/* input tabs */}
              <div style={{ marginTop: 28, maxWidth: 540, display: 'flex', gap: 8, paddingLeft: 6 }} role="tablist">
                {([['yt', '🎥 YouTube ссылка'], ['file', '📁 Загрузить файл']] as const).map(([tab, label]) => (
                  <button key={tab} type="button" role="tab" aria-selected={activeTab === tab}
                    onClick={() => setActiveTab(tab)}
                    className={activeTab === tab ? 'lp-tab-active' : ''}
                    style={{
                      fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 22,
                      background: 'var(--paper)', color: activeTab === tab ? 'var(--ink)' : 'var(--ink-soft)',
                      border: '3px solid var(--ink)', borderBottom: 'none',
                      borderRadius: '16px 18px 0 0 / 14px 16px 0 0',
                      padding: '8px 16px 6px', cursor: 'pointer',
                      boxShadow: '3px -2px 0 var(--ink)',
                      display: 'inline-flex', alignItems: 'center', gap: 8,
                    }}>
                    {label}
                  </button>
                ))}
              </div>

              {/* YouTube panel */}
              {activeTab === 'yt' && (
                <form action="/register" method="get">
                  <div className="lp-url-card" style={{
                    maxWidth: 540, background: 'var(--paper)',
                    border: '3px solid var(--ink)',
                    borderRadius: '26px 22px 28px 24px / 22px 26px 24px 28px',
                    padding: '14px 14px 14px 18px',
                    boxShadow: '6px 8px 0 var(--ink)',
                    display: 'flex', alignItems: 'center', gap: 10,
                  }}>
                    <svg width="34" height="24" viewBox="0 0 34 24" style={{ flexShrink: 0 }}>
                      <rect x="1.5" y="1.5" width="31" height="21" rx="6" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2" />
                      <path d="M14 8 L22 12 L14 16 Z" fill="#fff" stroke="#3A2E2A" strokeWidth="1.5" strokeLinejoin="round" />
                    </svg>
                    <input type="text" name="url" placeholder="Вставь YouTube-ссылку или брось файл..."
                      style={{
                        flex: 1, border: 'none', outline: 'none', background: 'transparent',
                        fontFamily: '"Patrick Hand", sans-serif', fontSize: 20, color: 'var(--ink)', padding: '8px 4px',
                      }} />
                    <Btn type="submit" variant="pink" size="sm">Превратить в золото →</Btn>
                  </div>
                </form>
              )}

              {/* File upload panel */}
              {activeTab === 'file' && (
                <form action="/register" method="post" encType="multipart/form-data">
                  <input ref={fileInputRef} type="file" id="lp-fileInput" name="file" accept="video/mp4,video/quicktime,video/*" hidden onChange={handleFileChange} />
                  <div
                    className={`lp-drop-card${dropState.dragging ? ' dragover' : ''}${dropState.fileName ? ' has-file' : ''}`}
                    style={{
                      maxWidth: 540, background: 'var(--paper)',
                      border: '3px solid var(--ink)',
                      borderRadius: '26px 22px 28px 24px / 22px 26px 24px 28px',
                      padding: '14px 14px 14px 18px',
                      boxShadow: '6px 8px 0 var(--ink)',
                      display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
                    }}
                    onDragEnter={e => { e.preventDefault(); setDropState(d => ({ ...d, dragging: true })) }}
                    onDragOver={e => { e.preventDefault(); setDropState(d => ({ ...d, dragging: true })) }}
                    onDragLeave={e => { e.preventDefault(); setDropState(d => ({ ...d, dragging: false })) }}
                    onDrop={handleFileDrop}
                  >
                    <div style={{ flexShrink: 0, width: 38, display: 'grid', placeItems: 'center' }}>
                      <svg width="30" height="26" viewBox="0 0 30 26">
                        <path d="M15 18 V4 M9 10 L15 4 L21 10" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                        <rect x="3" y="18" width="24" height="5" rx="2" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" />
                      </svg>
                    </div>
                    <label htmlFor="lp-fileInput" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2, padding: '4px 4px', cursor: 'pointer' }}>
                      <span className="lp-drop-title" style={{ fontFamily: '"Patrick Hand", sans-serif', fontSize: 20, color: 'var(--ink)', lineHeight: 1.1 }}>
                        {dropState.fileName ? `✔ ${dropState.fileName}` : 'Перетащи MP4 или жми чтобы выбрать'}
                      </span>
                      <span style={{ fontFamily: '"Patrick Hand", sans-serif', fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1 }}>
                        {dropState.fileSize ?? 'До 2 ГБ · MP4, MOV'}
                      </span>
                    </label>
                    <Btn type="submit" variant="pink" size="sm">Превратить в золото →</Btn>
                  </div>
                </form>
              )}

              {/* trust line */}
              <div style={{ marginTop: 24, fontFamily: '"Patrick Hand", sans-serif', fontSize: 16, color: 'var(--ink-soft)', display: 'inline-flex', alignItems: 'center', gap: 8, opacity: 0.85 }}>
                <svg width="14" height="14" viewBox="0 0 14 14">
                  <path d="M7 1 L8.5 5.5 L13 6 L9.5 9 L10.5 13.5 L7 11 L3.5 13.5 L4.5 9 L1 6 L5.5 5.5 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="1.5" strokeLinejoin="round" />
                </svg>
                Первые 3 клипа — бесплатно <span style={{ opacity: 0.4 }}>·</span> Без карты <span style={{ opacity: 0.4 }}>·</span> Без подписки
              </div>

              {/* meta checks */}
              <div style={{ marginTop: 18, display: 'flex', gap: 22, flexWrap: 'wrap', alignItems: 'center', color: 'var(--ink-soft)' }}>
                {['До 1080p с YouTube', 'Smart Crop по лицам', 'Hooks · эмодзи · хэштеги'].map(text => (
                  <span key={text} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 18 }}>
                    <svg width="22" height="22" viewBox="0 0 22 22">
                      <path d="M4 12 L9 17 L18 6" stroke="#4FB6A0" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    {text}
                  </span>
                ))}
              </div>
            </div>

            {/* dino stage */}
            <div className="lp-dino-stage" style={{ position: 'relative', minHeight: 460, display: 'grid', placeItems: 'center' }}>
              <Doodle symbol="#lp-sparkle" style={{ top: '6%', left: '4%', width: 32, height: 32 } as React.CSSProperties} />
              <Doodle symbol="#lp-star" style={{ bottom: '14%', right: 0, width: 30, height: 30 } as React.CSSProperties} />
              <Doodle symbol="#lp-squiggle" style={{ bottom: '6%', left: '10%', width: 90, height: 14 } as React.CSSProperties} />
              <div className="lp-bob" style={{
                position: 'relative', width: 420, maxWidth: '100%',
                aspectRatio: '1 / 1.05',
                background: 'var(--paper)',
                border: '3px solid var(--ink)',
                borderRadius: '50% 48% 52% 50% / 50% 52% 48% 50%',
                boxShadow: '8px 10px 0 var(--ink)',
                display: 'grid', placeItems: 'center',
                transform: 'rotate(-3deg)',
              }}>
                {/* dashed inner ring */}
                <span style={{
                  position: 'absolute', inset: 8,
                  border: '2px dashed rgba(58,46,42,.25)',
                  borderRadius: 'inherit',
                  pointerEvents: 'none',
                }} />
                {/* speech bubble */}
                <div style={{
                  position: 'absolute', top: 18, right: -10,
                  background: 'var(--paper)', border: '3px solid var(--ink)',
                  borderRadius: '24px 22px 8px 22px / 22px 24px 6px 22px',
                  padding: '10px 16px 8px',
                  fontFamily: '"Caveat", cursive', fontSize: 28,
                  boxShadow: '4px 5px 0 var(--ink)',
                  transform: 'rotate(6deg)', lineHeight: 1,
                }}>
                  привет! 🦖
                  <span style={{
                    position: 'absolute', right: 24, bottom: -14,
                    width: 18, height: 18,
                    background: 'var(--paper)',
                    borderRight: '3px solid var(--ink)', borderBottom: '3px solid var(--ink)',
                    transform: 'rotate(45deg)', display: 'block',
                  }} />
                </div>
                <svg className="lp-dino" viewBox="0 0 220 230" style={{ width: '76%', height: 'auto', transform: 'rotate(3deg)' }}>
                  <use href="#lp-dino" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section id="how" style={{ padding: '100px 0', position: 'relative' }}>
        <div style={S.wrap}>
          <div style={{ textAlign: 'center', marginBottom: 56 }}>
            <Eyebrow>3 шага</Eyebrow>
            <h2 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(40px, 4.8vw, 72px)', lineHeight: 1 }}>
              Как это <span style={{ color: 'var(--pink-deep)' }}>работает</span>
            </h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 22, marginTop: 10 }}>Три клика — и у тебя пачка вирусных клипов. Динозаврик обещает.</p>
          </div>

          <div className="lp-steps" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 28, position: 'relative' }}>
            {/* connector arrows — desktop only */}
            <div className="lp-arrows" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
              <svg style={{ position: 'absolute', top: 80, left: '30%' }} width="120" height="50" viewBox="0 0 140 60"><use href="#lp-arrow" /></svg>
              <svg style={{ position: 'absolute', top: 80, left: '64%', transform: 'scaleY(-1)' }} width="120" height="50" viewBox="0 0 140 60"><use href="#lp-arrow" /></svg>
            </div>

            {[
              {
                n: 1, bg: 'var(--yellow)', title: 'Загружай и настраивай',
                text: 'YouTube-ссылка (до 1080p) или MP4 drag-and-drop. Выбираешь платформу — TikTok / Shorts / Reels — и сколько клипов искать: 3, 5, 10 или 15.',
                icon: (
                  <svg width="120" height="120" viewBox="0 0 120 120">
                    <rect x="14" y="38" width="92" height="58" rx="12" fill="#FFE9B8" stroke="#3A2E2A" strokeWidth="3.5" />
                    <path d="M14 50 H106" stroke="#3A2E2A" strokeWidth="3.5" />
                    <circle cx="22" cy="44" r="2.5" fill="#FF8FA3" /><circle cx="30" cy="44" r="2.5" fill="#FFD166" /><circle cx="38" cy="44" r="2.5" fill="#7DD3C0" />
                    <path d="M30 70 L60 70" stroke="#3A2E2A" strokeWidth="4" strokeLinecap="round" />
                    <rect x="62" y="64" width="32" height="14" rx="6" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="3" />
                    <path d="M30 84 L80 84" stroke="#3A2E2A" strokeWidth="3" strokeLinecap="round" strokeDasharray="3 5" />
                    <g transform="translate(72 16) rotate(10)">
                      <rect x="0" y="0" width="32" height="40" rx="5" fill="#fff" stroke="#3A2E2A" strokeWidth="3" />
                      <path d="M22 0 L32 10 H22 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="3" />
                      <path d="M8 22 L24 22 M8 28 L24 28" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round" />
                    </g>
                  </svg>
                ),
              },
              {
                n: 2, bg: 'var(--pink)', color: '#fff', title: 'Transcribe → Analyze',
                text: 'Whisper расшифровывает речь с пословным таймингом, Claude ищет хуки и эмоциональные пики, генерирует заголовки, эмодзи и оценивает виральность 1–10.',
                icon: (
                  <svg width="130" height="130" viewBox="0 0 130 130">
                    <path d="M14 70 q 6 -18 12 0 t 12 0 t 12 0 t 12 0 t 12 0 t 12 0" stroke="#7DD3C0" strokeWidth="4" fill="none" strokeLinecap="round" />
                    <circle cx="80" cy="58" r="28" fill="#FFF" stroke="#3A2E2A" strokeWidth="3.5" />
                    <path d="M101 79 L116 96" stroke="#3A2E2A" strokeWidth="6" strokeLinecap="round" />
                    <g transform="translate(58 38)">
                      <ellipse cx="22" cy="22" rx="20" ry="18" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" />
                      <circle cx="14" cy="18" r="5" fill="#fff" stroke="#3A2E2A" strokeWidth="2" />
                      <circle cx="15" cy="19" r="2.5" fill="#3A2E2A" />
                      <path d="M18 28 q 4 4 8 0" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round" />
                      <path d="M18 4 L22 -2 L26 4" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round" />
                    </g>
                    <path d="M30 110 L34 100 L38 110 L48 114 L38 118 L34 128 L30 118 L20 114 Z" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round" />
                  </svg>
                ),
              },
              {
                n: 3, bg: 'var(--teal)', title: 'Render Clips',
                text: 'Smart Crop по лицам, word-level субтитры в выбранном стиле, hook сверху. Очередь рендера в реальном времени — два клипа параллельно.',
                icon: (
                  <svg width="120" height="130" viewBox="0 0 120 130">
                    <rect x="32" y="6" width="60" height="118" rx="14" fill="#fff" stroke="#3A2E2A" strokeWidth="3.5" />
                    <rect x="38" y="14" width="48" height="98" rx="6" fill="#FFE9B8" stroke="#3A2E2A" strokeWidth="2.5" />
                    <rect x="40" y="20" width="44" height="14" rx="4" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2" />
                    <text x="62" y="31" textAnchor="middle" fontFamily="Patrick Hand SC, sans-serif" fontSize="9" fill="#fff" fontWeight="700">WAIT FOR IT</text>
                    <circle cx="62" cy="62" r="14" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" />
                    <circle cx="58" cy="60" r="2" fill="#3A2E2A" /><circle cx="66" cy="60" r="2" fill="#3A2E2A" />
                    <path d="M57 67 q 5 5 10 0" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round" />
                    <rect x="42" y="86" width="40" height="10" rx="2" fill="#3A2E2A" />
                    <rect x="44" y="88" width="14" height="6" fill="#FFD166" />
                    <rect x="60" y="88" width="20" height="6" fill="#fff" opacity={0.9} />
                    <circle cx="62" cy="118" r="4" fill="#3A2E2A" />
                    <path d="M100 24 L102 16 L106 24 L114 26 L106 28 L102 36 L100 28 L92 26 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round" />
                  </svg>
                ),
              },
            ].map(step => (
              <div key={step.n} className="lp-step" style={{
                background: 'var(--paper)', border: '3px solid var(--ink)',
                borderRadius: '28px 24px 30px 22px / 24px 28px 22px 30px',
                boxShadow: '6px 8px 0 var(--ink)',
                padding: '26px 24px 28px', position: 'relative',
                transition: 'transform .18s ease, box-shadow .18s ease',
              }}>
                <div style={{
                  position: 'absolute', top: -22, left: -22,
                  width: 56, height: 56, display: 'grid', placeItems: 'center',
                  border: '3px solid var(--ink)', borderRadius: '50%',
                  background: step.bg, color: step.color || 'var(--ink)',
                  fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 38,
                  boxShadow: '3px 4px 0 var(--ink)', transform: 'rotate(-6deg)',
                }}>{step.n}</div>
                <div style={{ height: 130, display: 'grid', placeItems: 'center', marginBottom: 12 }}>{step.icon}</div>
                <h3 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(28px,2.4vw,38px)', marginBottom: 6 }}>{step.title}</h3>
                <p style={{ color: 'var(--ink-soft)', fontSize: 19 }}>{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section id="features" style={{ padding: '60px 0 100px', position: 'relative' }}>
        <div style={S.wrap}>
          <div style={{ textAlign: 'center', marginBottom: 56 }}>
            <Eyebrow>Фичи</Eyebrow>
            <h2 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(40px,4.8vw,72px)', lineHeight: 1 }}>
              Маленький динозаврик, <span style={{ color: 'var(--pink-deep)' }}>большая магия</span>
            </h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 22, marginTop: 10 }}>Всё, что нужно, чтобы клипы выстреливали.</p>
          </div>

          <div className="lp-features" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 26 }}>
            {[
              {
                accent: 'var(--pink)', alt: false, chip: { text: 'face · group · split', bg: 'var(--pink)', color: '#fff' },
                title: 'Smart Crop по лицам',
                text: 'MediaPipe находит лица в кадре и выбирает режим: один спикер, группа или split-screen для интервью. Можно подправить слайдером.',
                icon: <svg width="32" height="32" viewBox="0 0 32 32"><circle cx="11" cy="12" r="4" fill="#fff" stroke="#3A2E2A" strokeWidth="2" /><circle cx="21" cy="12" r="4" fill="#fff" stroke="#3A2E2A" strokeWidth="2" /><rect x="4" y="4" width="24" height="24" rx="3" fill="none" stroke="#3A2E2A" strokeWidth="2.5" strokeDasharray="3 3" /></svg>,
              },
              {
                accent: 'var(--yellow)', alt: true, chip: { text: 'Podcast · Hormozi · Minimal', bg: 'var(--yellow)', color: 'var(--ink)' },
                title: '3 стиля субтитров',
                text: 'Word-level субтитры с pop-up анимацией. Языки: русский, English или авто. Если Whisper что-то недослышал — правь фразы вручную.',
                icon: <svg width="32" height="32" viewBox="0 0 32 32"><rect x="3" y="20" width="26" height="4" rx="1" fill="#3A2E2A" /><rect x="6" y="21" width="6" height="2" fill="#FFD166" /><rect x="14" y="21" width="10" height="2" fill="#fff" /><rect x="3" y="10" width="20" height="4" rx="1" fill="#3A2E2A" /><rect x="5" y="11" width="14" height="2" fill="#fff" /></svg>,
              },
              {
                accent: 'var(--teal)', alt: false, chip: { text: 'hook · emoji · хэштеги', bg: 'var(--teal)', color: 'var(--ink)' },
                title: 'Готовый пост к каждому клипу',
                text: 'Claude придумывает hook, подбирает эмодзи, генерирует название, описание, хэштеги и CTA. Одна кнопка «Copy Meta» — и пост готов.',
                icon: <svg width="32" height="32" viewBox="0 0 32 32"><path d="M6 12 L10 6 L20 4 L26 8 L24 16 L20 20 L10 22 L4 18 Z" fill="#fff" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round" /><circle cx="14" cy="13" r="2" fill="#3A2E2A" /><path d="M8 26 L12 22 M22 24 L18 20" stroke="#3A2E2A" strokeWidth="2" strokeLinecap="round" /></svg>,
              },
              {
                accent: 'var(--lilac)', alt: true, chip: { text: 'virality 1–10', bg: 'var(--lilac)', color: 'var(--ink)' },
                title: 'Оценка виральности',
                text: 'Каждый кандидат получает балл и причину. Можно править тайминг начало/конец вручную и перерендерить с новыми настройками.',
                icon: <svg width="32" height="32" viewBox="0 0 32 32"><path d="M16 4 L19 12 L28 13 L21 19 L23 28 L16 23 L9 28 L11 19 L4 13 L13 12 Z" fill="#fff" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round" /></svg>,
              },
              {
                accent: 'var(--yellow)', alt: false, chip: { text: 'jump-cut', bg: 'var(--paper)', color: 'var(--ink)' },
                title: 'Режет паузы автоматом',
                text: 'Один переключатель «✂ Jump-Cut» — и тишина из клипа вырезается. Ритм плотнее, внимание держится.',
                icon: <svg width="32" height="32" viewBox="0 0 32 32"><path d="M3 22 q 4 -10 8 0 t 8 0 t 8 0 t 8 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" /><path d="M11 12 L13 8 L15 12 M19 10 L21 6 L23 10" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>,
              },
              {
                accent: 'var(--pink)', alt: true, chip: { text: 'queue · batch', bg: 'var(--pink)', color: '#fff' },
                title: 'Пакетный рендер',
                text: 'Approve нужные клипы, жми «Render N Approved». Два рендера параллельно, остальные в очереди — WebSocket показывает прогресс в реальном времени.',
                icon: <svg width="32" height="32" viewBox="0 0 32 32"><rect x="4" y="8" width="22" height="16" rx="3" fill="#fff" stroke="#3A2E2A" strokeWidth="2.5" /><path d="M9 14 L9 18 M13 12 L13 20 M17 14 L17 18 M21 13 L21 19" stroke="#3A2E2A" strokeWidth="2" strokeLinecap="round" /></svg>,
              },
            ].map((f, i) => (
              <div key={i} className="lp-feature" style={{
                background: f.alt ? '#FFF7E0' : 'var(--paper)',
                border: '3px solid var(--ink)',
                borderRadius: '28px 24px 30px 22px / 24px 28px 22px 30px',
                boxShadow: '6px 7px 0 var(--ink)',
                padding: '22px 22px 24px',
                transition: 'transform .18s ease, box-shadow .18s ease',
              }}>
                <div style={{
                  width: 64, height: 64, border: '3px solid var(--ink)',
                  borderRadius: '18px 14px 20px 12px / 14px 18px 12px 20px',
                  background: f.accent, display: 'grid', placeItems: 'center',
                  boxShadow: '3px 4px 0 var(--ink)',
                }}>{f.icon}</div>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  border: '2px solid var(--ink)', background: f.chip.bg, color: f.chip.color,
                  borderRadius: 999, padding: '2px 10px 0', fontSize: 15,
                  fontFamily: '"Patrick Hand SC", sans-serif', letterSpacing: 1,
                  marginTop: 8,
                }}>{f.chip.text}</span>
                <h3 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(28px,2.4vw,38px)', margin: '8px 0 6px' }}>{f.title}</h3>
                <p style={{ color: 'var(--ink-soft)', fontSize: 18 }}>{f.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── EXAMPLES ─── */}
      <section id="examples" style={{ padding: '80px 0 40px', position: 'relative' }}>
        <div style={S.wrap}>
          <div style={{ textAlign: 'center', marginBottom: 30 }}>
            <Eyebrow>Примеры</Eyebrow>
            <h2 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(40px,4.8vw,72px)', lineHeight: 1 }}>
              Что получается <span style={{ color: 'var(--pink-deep)' }}>на выходе</span>
            </h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 22, marginTop: 10 }}>Реальные клипы, нарезанные динозавриком.</p>
          </div>

          <div className="lp-clip-rail" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20 }}>
            {/* clip 1 */}
            <div className="lp-clip-card" style={{ background: 'var(--paper)', border: '3px solid var(--ink)', borderRadius: '22px 18px 24px 20px / 18px 22px 20px 24px', padding: '12px 12px 14px', boxShadow: '5px 6px 0 var(--ink)', transition: 'transform .18s ease, box-shadow .18s ease' }}>
              <div style={{ aspectRatio: '9/16', border: '3px solid var(--ink)', borderRadius: '14px 12px 14px 12px', overflow: 'hidden', position: 'relative', background: 'linear-gradient(160deg,#FFE9B8,#FFD166)' }}>
                <div style={{ position: 'absolute', left: 8, right: 8, top: 10, background: 'var(--pink)', color: '#fff', border: '2.5px solid var(--ink)', borderRadius: '10px 8px 12px 9px', fontFamily: '"Patrick Hand SC",sans-serif', fontWeight: 700, fontSize: 11, padding: '4px 6px 3px', textAlign: 'center', boxShadow: '2px 2px 0 var(--ink)', transform: 'rotate(-2deg)' }}>WAIT FOR IT...</div>
                <svg viewBox="0 0 90 160" style={{ width: '100%', height: '100%' }} preserveAspectRatio="xMidYMid slice">
                  <g transform="translate(20 56)"><ellipse cx="28" cy="28" rx="26" ry="24" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2.5" /><circle cx="20" cy="22" r="6" fill="#fff" stroke="#3A2E2A" strokeWidth="2" /><circle cx="36" cy="22" r="6" fill="#fff" stroke="#3A2E2A" strokeWidth="2" /><circle cx="22" cy="24" r="2.5" fill="#3A2E2A" /><circle cx="38" cy="24" r="2.5" fill="#3A2E2A" /><path d="M22 36 q 6 6 12 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" /><path d="M16 4 L20 -4 L24 4 M32 6 L36 -2 L40 6" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2" /></g>
                  <g transform="translate(58 86) rotate(20)"><rect x="-6" y="0" width="12" height="22" rx="6" fill="#3A2E2A" /><rect x="-3" y="3" width="6" height="14" rx="3" fill="#FF8FA3" /><path d="M0 22 V32" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round" /><path d="M-7 32 H7" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round" /></g>
                </svg>
                <div style={{ position: 'absolute', left: 8, right: 8, bottom: 14, background: 'var(--ink)', color: '#fff', borderRadius: 6, fontFamily: '"Patrick Hand SC",sans-serif', fontSize: 10, padding: '4px 6px', lineHeight: 1.1, textAlign: 'center' }}>говорит <b style={{ background: 'var(--yellow)', color: 'var(--ink)', padding: '0 3px', borderRadius: 3 }}>важную</b> вещь</div>
              </div>
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontFamily: '"Caveat",cursive', fontWeight: 700, fontSize: 22, lineHeight: 1.1, color: 'var(--ink)' }}>Бизнес-подкаст</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--cream-2)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>15s</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--yellow)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>⚡ 9.2/10</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--ink)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: '#fff' }}>TikTok</span>
                  <span style={{ fontSize: 13 }}>🎙 Podcast · 🇷🇺</span>
                </div>
              </div>
            </div>

            {/* clip 2 */}
            <div className="lp-clip-card" style={{ background: 'var(--paper)', border: '3px solid var(--ink)', borderRadius: '22px 18px 24px 20px / 18px 22px 20px 24px', padding: '12px 12px 14px', boxShadow: '5px 6px 0 var(--ink)', transition: 'transform .18s ease, box-shadow .18s ease' }}>
              <div style={{ aspectRatio: '9/16', border: '3px solid var(--ink)', borderRadius: '14px 12px 14px 12px', overflow: 'hidden', position: 'relative', background: 'linear-gradient(160deg,#C9B6E4,#FF8FA3)' }}>
                <div style={{ position: 'absolute', left: 8, right: 8, top: 10, background: 'var(--yellow)', color: 'var(--ink)', border: '2.5px solid var(--ink)', borderRadius: '10px 8px 12px 9px', fontFamily: '"Patrick Hand SC",sans-serif', fontWeight: 700, fontSize: 11, padding: '4px 6px 3px', textAlign: 'center', boxShadow: '2px 2px 0 var(--ink)', transform: 'rotate(-2deg)' }}>3 ПРАВДЫ ОБ AI</div>
                <svg viewBox="0 0 90 160" style={{ width: '100%', height: '100%' }} preserveAspectRatio="xMidYMid slice">
                  <g transform="translate(8 60)"><ellipse cx="18" cy="20" rx="16" ry="18" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" /><circle cx="13" cy="18" r="2.2" fill="#3A2E2A" /><circle cx="23" cy="18" r="2.2" fill="#3A2E2A" /><path d="M13 26 q 5 4 10 0" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round" /></g>
                  <line x1="45" y1="42" x2="45" y2="118" stroke="#3A2E2A" strokeWidth="2" strokeDasharray="4 3" />
                  <g transform="translate(50 60)"><ellipse cx="18" cy="20" rx="16" ry="18" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2.5" /><circle cx="13" cy="18" r="2.2" fill="#3A2E2A" /><circle cx="23" cy="18" r="2.2" fill="#3A2E2A" /><path d="M13 24 L23 24" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round" /></g>
                </svg>
                <div style={{ position: 'absolute', left: 8, right: 8, bottom: 14, background: 'var(--ink)', color: '#fff', borderRadius: 6, fontFamily: '"Patrick Hand SC",sans-serif', fontSize: 10, padding: '4px 6px', lineHeight: 1.1, textAlign: 'center' }}><b style={{ background: 'var(--yellow)', color: 'var(--ink)', padding: '0 3px', borderRadius: 3 }}>интервью</b> с экспертом</div>
              </div>
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontFamily: '"Caveat",cursive', fontWeight: 700, fontSize: 22, lineHeight: 1.1, color: 'var(--ink)' }}>Интервью</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--cream-2)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>32s</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--yellow)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>⚡ 8.5/10</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--pink)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: '#fff' }}>Reels</span>
                  <span style={{ fontSize: 13 }}>🟡 Hormozi · 🇷🇺</span>
                </div>
              </div>
            </div>

            {/* clip 3 */}
            <div className="lp-clip-card" style={{ background: 'var(--paper)', border: '3px solid var(--ink)', borderRadius: '22px 18px 24px 20px / 18px 22px 20px 24px', padding: '12px 12px 14px', boxShadow: '5px 6px 0 var(--ink)', transition: 'transform .18s ease, box-shadow .18s ease' }}>
              <div style={{ aspectRatio: '9/16', border: '3px solid var(--ink)', borderRadius: '14px 12px 14px 12px', overflow: 'hidden', position: 'relative', background: 'linear-gradient(160deg,#7DD3C0,#4FB6A0)' }}>
                <div style={{ position: 'absolute', left: 8, right: 8, top: 10, background: 'var(--teal)', color: 'var(--ink)', border: '2.5px solid var(--ink)', borderRadius: '10px 8px 12px 9px', fontFamily: '"Patrick Hand SC",sans-serif', fontWeight: 700, fontSize: 11, padding: '4px 6px 3px', textAlign: 'center', boxShadow: '2px 2px 0 var(--ink)', transform: 'rotate(-2deg)' }}>СЕКРЕТ ЗА 47s</div>
                <svg viewBox="0 0 90 160" style={{ width: '100%', height: '100%' }} preserveAspectRatio="xMidYMid slice">
                  <g transform="translate(20 56)"><ellipse cx="28" cy="28" rx="26" ry="24" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2.5" /><path d="M16 22 q 4 4 8 0 M30 22 q 4 4 8 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" /><path d="M20 36 q 8 8 16 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" /><path d="M16 4 L20 -4 L24 4 M32 6 L36 -2 L40 6" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2" /></g>
                  <g transform="translate(54 92)"><rect x="-12" y="-8" width="24" height="18" rx="3" fill="#3A2E2A" /><circle cx="0" cy="1" r="6" fill="#FFD166" stroke="#fff" strokeWidth="1.5" /><circle cx="0" cy="1" r="2.5" fill="#3A2E2A" /><rect x="-4" y="-11" width="8" height="3" fill="#3A2E2A" /></g>
                </svg>
                <div style={{ position: 'absolute', left: 8, right: 8, bottom: 14, background: 'var(--ink)', color: '#fff', borderRadius: 6, fontFamily: '"Patrick Hand SC",sans-serif', fontSize: 10, padding: '4px 6px', lineHeight: 1.1, textAlign: 'center' }}>мотивация на <b style={{ background: 'var(--yellow)', color: 'var(--ink)', padding: '0 3px', borderRadius: 3 }}>миллион</b></div>
              </div>
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontFamily: '"Caveat",cursive', fontWeight: 700, fontSize: 22, lineHeight: 1.1, color: 'var(--ink)' }}>Мотивация</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--cream-2)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>47s</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--yellow)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>⚡ 9.7/10</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--pink-deep)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: '#fff' }}>Shorts</span>
                  <span style={{ fontSize: 13 }}>⚪ Minimal · 🇬🇧</span>
                </div>
              </div>
            </div>

            {/* clip 4 */}
            <div className="lp-clip-card" style={{ background: 'var(--paper)', border: '3px solid var(--ink)', borderRadius: '22px 18px 24px 20px / 18px 22px 20px 24px', padding: '12px 12px 14px', boxShadow: '5px 6px 0 var(--ink)', transition: 'transform .18s ease, box-shadow .18s ease' }}>
              <div style={{ aspectRatio: '9/16', border: '3px solid var(--ink)', borderRadius: '14px 12px 14px 12px', overflow: 'hidden', position: 'relative', background: 'linear-gradient(160deg,#FF8FA3,#E96A85)' }}>
                <div style={{ position: 'absolute', left: 8, right: 8, top: 10, background: 'var(--yellow)', color: 'var(--ink)', border: '2.5px solid var(--ink)', borderRadius: '10px 8px 12px 9px', fontFamily: '"Patrick Hand SC",sans-serif', fontWeight: 700, fontSize: 11, padding: '4px 6px 3px', textAlign: 'center', boxShadow: '2px 2px 0 var(--ink)', transform: 'rotate(-2deg)' }}>ОН ЭТО СКАЗАЛ?!</div>
                <svg viewBox="0 0 90 160" style={{ width: '100%', height: '100%' }} preserveAspectRatio="xMidYMid slice">
                  <g transform="translate(20 50)"><ellipse cx="28" cy="32" rx="26" ry="26" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" /><circle cx="20" cy="22" r="5" fill="#fff" stroke="#3A2E2A" strokeWidth="2" /><circle cx="36" cy="22" r="5" fill="#fff" stroke="#3A2E2A" strokeWidth="2" /><circle cx="20" cy="22" r="2" fill="#3A2E2A" /><circle cx="36" cy="22" r="2" fill="#3A2E2A" /><ellipse cx="28" cy="40" rx="6" ry="8" fill="#3A2E2A" /><path d="M16 4 L20 -4 L24 4" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" /></g>
                  <path d="M12 26 L4 22 M14 38 L4 38 M12 50 L4 56 M76 26 L84 22 M74 38 L84 38 M76 50 L84 56" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
                </svg>
                <div style={{ position: 'absolute', left: 8, right: 8, bottom: 14, background: 'var(--ink)', color: '#fff', borderRadius: 6, fontFamily: '"Patrick Hand SC",sans-serif', fontSize: 10, padding: '4px 6px', lineHeight: 1.1, textAlign: 'center' }}><b style={{ background: 'var(--yellow)', color: 'var(--ink)', padding: '0 3px', borderRadius: 3 }}>comedy</b> момент</div>
              </div>
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontFamily: '"Caveat",cursive', fontWeight: 700, fontSize: 22, lineHeight: 1.1, color: 'var(--ink)' }}>Comedy</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--cream-2)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>22s</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--yellow)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: 'var(--ink)' }}>⚡ 8.8/10</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: '"Patrick Hand",sans-serif', fontSize: 14, color: 'var(--ink-soft)' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px 1px', background: 'var(--ink)', border: '2px solid var(--ink)', borderRadius: 999, fontSize: 13, color: '#fff' }}>TikTok</span>
                  <span style={{ fontSize: 13 }}>🟡 Hormozi · 🌐</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── FAQ ─── */}
      <section id="faq" style={{ padding: '100px 0', position: 'relative' }}>
        <div style={S.wrap}>
          <div style={{ textAlign: 'center', marginBottom: 56 }}>
            <Eyebrow>FAQ</Eyebrow>
            <h2 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(40px,4.8vw,72px)', lineHeight: 1 }}>
              Часто <span style={{ color: 'var(--pink-deep)' }}>спрашивают</span>
            </h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 22, marginTop: 10 }}>Если динозаврик не ответил — пиши, добавим.</p>
          </div>

          <div style={{ maxWidth: 820, margin: '0 auto', display: 'grid', gap: 16 }}>
            {[
              {
                q: 'Как выглядит путь от видео до готовых клипов?',
                a: 'Войди по email/паролю → кинь YouTube-ссылку или MP4 → выбери платформу (TikTok / Shorts / Reels) и сколько клипов искать (3/5/10/15) → жми Transcribe, потом Analyze → правь субтитры и тайминг в карточках кандидатов → Render. Готовые MP4 скачиваешь и копируешь метаданные одной кнопкой.',
                leafBg: 'var(--teal)', leafIcon: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M3 9 L7 13 L15 5" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>,
                open: true,
              },
              {
                q: 'Сколько занимает обработка длинного видео?',
                a: 'Скачивание YouTube — 2–10 минут (показывается живой статус). Транскрипция режется на части и обрабатывается по 3/6 чанкам. AI-анализ — 5–15 секунд. Один клип со Smart Crop и word-level субтитрами — 10–20 секунд. Два рендера идут параллельно, остальные ждут в очереди.',
                leafBg: 'var(--pink)', leafIcon: <svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="6" fill="none" stroke="#3A2E2A" strokeWidth="2.5" /><path d="M9 5 V9 L12 11" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" /></svg>,
              },
              {
                q: 'Можно ли править результаты вручную?',
                a: 'Да. Тайминг начало/конец, текст субтитров по фразам, позиция Smart Crop слайдером, стиль субтитров и язык — всё меняется в карточке клипа. После рендера есть кнопка Re-render с другими настройками.',
                leafBg: 'var(--lilac)', leafIcon: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M6 4 H14 V14 H4 V6 Z" fill="none" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round" /><path d="M7 9 L9 11 L13 7" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" /></svg>,
              },
              {
                q: 'Можно ли обработать длинный подкаст?',
                a: 'Да. yt-dlp тянет до 1080p, а Whisper жуёт даже двухчасовые записи. Из всего видео AI выбирает топ-3 самых вирусных 30-секундных кусочка — но количество легко настраивается в коде.',
                leafBg: 'var(--teal)', leafIcon: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M3 9 H15 M9 3 V15" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round" /></svg>,
              },
              {
                q: 'В каком формате я получу клипы?',
                a: 'MP4, 9:16, H.264 CRF 23 — оптимально для TikTok, Reels и Shorts. Каждый клип идёт со встроенным хуком сверху и word-level субтитрами снизу.',
                leafBg: 'var(--pink)', leafIcon: <svg width="18" height="18" viewBox="0 0 18 18"><path d="M4 12 V14 H14 V12 M9 3 V11 M5 8 L9 11 L13 8" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>,
              },
              {
                q: 'Что такое Factory mode?',
                a: 'Автономная фабрика контента на /factory. Система сама ищет видео по нишам (business, comedy, motivation, psychology…), работает 24/7 без участия пользователя и показывает статистику: сколько найдено, обработано и в очереди.',
                leafBg: 'var(--lilac)', leafIcon: <svg width="18" height="18" viewBox="0 0 18 18"><rect x="4" y="4" width="10" height="10" rx="2" fill="none" stroke="#3A2E2A" strokeWidth="2.5" /><path d="M7 9 H11" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round" /></svg>,
              },
            ].map((item, i) => (
              <details key={i} className="lp-faq-detail" open={item.open || undefined}
                style={{
                  background: 'var(--paper)', border: '3px solid var(--ink)',
                  borderRadius: '22px 18px 24px 20px / 18px 22px 20px 24px',
                  boxShadow: '5px 6px 0 var(--ink)', padding: '14px 22px',
                  transition: 'transform .15s ease, box-shadow .15s ease',
                }}>
                <summary style={{ listStyle: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14, fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 30, lineHeight: 1.1 }}>
                  <span style={{
                    width: 36, height: 36, flexShrink: 0,
                    border: '3px solid var(--ink)', borderRadius: '12px 8px 14px 10px / 8px 12px 10px 14px',
                    display: 'grid', placeItems: 'center', boxShadow: '2px 3px 0 var(--ink)',
                    background: item.leafBg,
                  }}>{item.leafIcon}</span>
                  {item.q}
                  <span className="lp-faq-toggle" style={{
                    marginLeft: 'auto', width: 38, height: 38, flexShrink: 0, display: 'grid', placeItems: 'center',
                    border: '3px solid var(--ink)', borderRadius: '50%', background: 'var(--yellow)',
                    boxShadow: '2px 3px 0 var(--ink)', transition: 'transform .25s ease, background .15s',
                    fontFamily: '"Caveat", cursive', fontSize: 32, lineHeight: 1, fontWeight: 700,
                  }}>+</span>
                </summary>
                <div style={{ color: 'var(--ink-soft)', fontSize: 19, padding: '8px 4px 4px 56px', lineHeight: 1.5 }}>{item.a}</div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FINAL CTA ─── */}
      <section id="cta" style={{ padding: '100px 0', position: 'relative' }}>
        <div style={S.wrap}>
          <div style={{
            background: 'var(--paper)', border: '4px solid var(--ink)',
            borderRadius: '60px 50px 70px 55px / 50px 60px 55px 70px',
            boxShadow: '10px 14px 0 var(--ink)',
            padding: '60px 40px', textAlign: 'center', position: 'relative', overflow: 'hidden',
          }}>
            <Doodle symbol="#lp-sparkle" style={{ top: 20, left: 30, width: 42, height: 42 } as React.CSSProperties} />
            <Doodle symbol="#lp-star" style={{ top: 30, right: 40, width: 36, height: 36 } as React.CSSProperties} />
            <Doodle symbol="#lp-cloud" style={{ bottom: 30, left: '8%', width: 90, height: 46 } as React.CSSProperties} />
            <Doodle symbol="#lp-squiggle" style={{ bottom: 24, right: '10%', width: 120, height: 18 } as React.CSSProperties} />

            <svg width="170" height="180" viewBox="0 0 220 230" style={{ margin: '0 auto 8px', display: 'block' }}>
              <use href="#lp-dino" />
            </svg>
            <h2 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 'clamp(52px,6vw,88px)', paddingBottom: 16 }}>
              Готов превратить видео <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 3px 0 var(--ink)' }}>в&nbsp;золото?</span>
            </h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 22, margin: '26px auto', maxWidth: 520 }}>
              Динозаврик уже точит ножницы. Один клик — и шортсы готовы.
            </p>
            <div style={{ display: 'inline-flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
              <Btn href="/register" variant="pink" size="lg">Кинуть видео динозаврику 🦖</Btn>
              <Btn href="#how" variant="ghost" size="lg">Сначала посмотрю, как это</Btn>
            </div>
            <div style={{ marginTop: 18, fontFamily: '"Patrick Hand", sans-serif', fontSize: 16, color: 'var(--ink-soft)', display: 'inline-flex', alignItems: 'center', gap: 8, opacity: 0.85 }}>
              <svg width="14" height="14" viewBox="0 0 14 14">
                <path d="M7 1 L8.5 5.5 L13 6 L9.5 9 L10.5 13.5 L7 11 L3.5 13.5 L4.5 9 L1 6 L5.5 5.5 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="1.5" strokeLinejoin="round" />
              </svg>
              Бесплатно в бете <span style={{ opacity: 0.4 }}>·</span> Регистрация за 30 секунд
            </div>
          </div>
        </div>
      </section>

      {/* ─── FOOTER ─── */}
      <footer style={{ padding: '40px 0 60px', color: 'var(--ink-soft)' }}>
        <div style={S.wrap}>
          <div className="lp-footer-cols" style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1fr', gap: 32, alignItems: 'start', padding: '20px 0 30px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: '"Caveat",cursive', fontWeight: 700, fontSize: 30, color: 'var(--ink)', textDecoration: 'none' }}>
                <span style={{ width: 36, height: 36, display: 'grid', placeItems: 'center', background: 'var(--yellow)', border: '3px solid var(--ink)', borderRadius: '18px 14px 20px 12px / 14px 18px 12px 20px', boxShadow: '3px 4px 0 var(--ink)', transform: 'rotate(-4deg)', flexShrink: 0 }}>
                  <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L 13 13 L 21 7 M 13 13 V 22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" /><circle cx="13" cy="13" r="2.5" fill="#3A2E2A" /></svg>
                </span>
                Clips<span style={{ color: 'var(--yellow-deep)', textShadow: '1px 2px 0 var(--ink)' }}>Gold</span>
              </div>
              <p style={{ fontFamily: '"Patrick Hand",sans-serif', fontSize: 16, color: 'var(--ink-soft)', marginTop: 10, maxWidth: 240 }}>Длинное видео → вирусные клипы. Динозаврик режет за тебя.</p>
            </div>

            <div>
              <h4 style={{ fontFamily: '"Caveat",cursive', fontSize: 26, marginBottom: 10, color: 'var(--ink)' }}>Продукт</h4>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[['#how', 'Как работает'], ['#features', 'Фичи'], ['#examples', 'Примеры'], ['/factory', '⚡ Фабрика']].map(([href, label]) => (
                  <li key={href}><a href={href} className="lp-navlink" style={{ color: 'var(--ink-soft)', textDecoration: 'none', fontSize: 17 }}>{label}</a></li>
                ))}
              </ul>
            </div>

            <div>
              <h4 style={{ fontFamily: '"Caveat",cursive', fontSize: 26, marginBottom: 10, color: 'var(--ink)' }}>Поддержка</h4>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  ['https://t.me/clipsgold', '✈ Telegram-канал'],
                  ['https://t.me/clipsgold_help', '💬 Поддержка'],
                  ['mailto:hello@clipsgold.ru', '✉ hello@clipsgold.ru'],
                  ['#faq', 'FAQ'],
                ].map(([href, label]) => (
                  <li key={href}><a href={href} className="lp-navlink" style={{ color: 'var(--ink-soft)', textDecoration: 'none', fontSize: 17 }}>{label}</a></li>
                ))}
              </ul>
            </div>

            <div>
              <h4 style={{ fontFamily: '"Caveat",cursive', fontSize: 26, marginBottom: 10, color: 'var(--ink)' }}>Юридическое</h4>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  ['/privacy', 'Политика конфиденциальности'],
                  ['/terms', 'Условия использования'],
                  ['/offer', 'Публичная оферта'],
                ].map(([href, label]) => (
                  <li key={href}><a href={href} className="lp-navlink" style={{ color: 'var(--ink-soft)', textDecoration: 'none', fontSize: 17 }}>{label}</a></li>
                ))}
              </ul>
            </div>
          </div>

          <div style={{ borderTop: '2px dashed rgba(58,46,42,.25)', marginTop: 10, paddingTop: 18, display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, fontFamily: '"Patrick Hand",sans-serif', fontSize: 15, color: 'var(--ink-soft)' }}>
            <div>© 2026 ClipsGold · сделано с 🦖 и любовью</div>
            <div>Нарезали <b>---</b> вирусных клипов</div>
          </div>
        </div>
      </footer>
    </>
  )
}
