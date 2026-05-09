'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

const CONFETTI_COLORS = ['#FF8FA3', '#FFD166', '#7DD3C0', '#C9B6E4', '#B8E6CC']

export default function ResetSuccessPage() {
  const router = useRouter()
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    if (countdown <= 0) {
      router.push('/app')
      return
    }
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown, router])

  // Generate confetti pieces deterministically for SSR safety
  const confettiPieces = Array.from({ length: 28 }, (_, k) => ({
    left: (((k * 37 + 13) % 100)),
    top: -(30 + (k * 7) % 200),
    color: CONFETTI_COLORS[k % CONFETTI_COLORS.length],
    delay: ((k * 0.09) % 2.5),
    duration: 3.5 + (k * 0.07) % 2,
    shape: k % 3,
  }))

  return (
    <>
      <style>{`
        .success-body {
          font-family: "Patrick Hand", sans-serif;
          color: var(--ink);
          font-size: 18px;
          background: var(--cream);
          background-image:
            radial-gradient(circle at 8% 8%, rgba(184,230,204,.6) 0,transparent 30%),
            radial-gradient(circle at 96% 14%, rgba(255,209,102,.4) 0,transparent 28%),
            radial-gradient(circle at 96% 92%, rgba(255,143,163,.4) 0,transparent 30%),
            radial-gradient(circle at 4% 92%, rgba(201,182,228,.4) 0,transparent 30%);
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .arm-throw {
          transform-origin: 60px 110px;
          animation: throw 2.4s ease-in-out infinite;
        }
        @keyframes throw { 0%,100%{ transform:rotate(-10deg) } 50%{ transform:rotate(30deg) } }
        .star-spin {
          transform-origin: center;
          animation: spin 4s linear infinite;
        }
        @keyframes spin { to{ transform:rotate(360deg) } }
        @keyframes fall {
          0%{ transform:translateY(-50px) rotate(0) }
          100%{ transform:translateY(110vh) rotate(720deg) }
        }
      `}</style>

      <div className="success-body">
        {/* Navbar */}
        <nav style={{ maxWidth: 1180, width: '100%', margin: '0 auto', padding: '18px 28px' }}>
          <Link href="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 30, color: 'var(--ink)', textDecoration: 'none' }}>
            <span style={{
              width: 34, height: 34, display: 'grid', placeItems: 'center',
              background: 'var(--yellow)', border: '3px solid var(--ink)',
              borderRadius: '14px 12px 16px 10px / 12px 14px 10px 16px',
              boxShadow: '2px 3px 0 var(--ink)', transform: 'rotate(-4deg)'
            }}>
              <svg width="22" height="22" viewBox="0 0 26 26">
                <path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/>
              </svg>
            </span>
            Clips<span style={{ color: 'var(--yellow-deep)', textShadow: '1px 2px 0 var(--ink)' }}>Gold</span>
          </Link>
        </nav>

        {/* Stage */}
        <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: '20px 28px 60px', position: 'relative' }}>

          {/* Confetti */}
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 1, overflow: 'hidden' }}>
            {confettiPieces.map((p, k) => (
              <span key={k} style={{
                position: 'absolute', width: 14, height: 14,
                border: '2px solid var(--ink)', boxSizing: 'border-box',
                left: `${p.left}vw`, top: p.top,
                background: p.color,
                borderRadius: p.shape === 0 ? '50%' : p.shape === 2 ? 4 : 0,
                animation: `fall ${p.duration}s linear ${p.delay}s infinite`,
              }} />
            ))}
          </div>

          <div style={{
            background: 'var(--paper)', border: '3px solid var(--ink)',
            borderRadius: '32px 26px 36px 24px / 24px 32px 24px 36px',
            boxShadow: '10px 12px 0 var(--ink)',
            padding: '48px 52px', maxWidth: 560, width: '100%',
            textAlign: 'center', transform: 'rotate(-1.2deg)',
            position: 'relative', zIndex: 2
          }}>
            {/* Checkmark stamp */}
            <div style={{
              position: 'absolute', top: -22, right: -20,
              width: 90, height: 90, borderRadius: '50%',
              background: 'var(--mint)', border: '3.5px solid var(--ink)',
              boxShadow: '5px 6px 0 var(--ink)',
              display: 'grid', placeItems: 'center', transform: 'rotate(8deg)'
            }}>
              <svg width="44" height="44" viewBox="0 0 44 44">
                <path d="M10 22 L19 31 L36 14" stroke="#3A2E2A" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>

            {/* Dino scene */}
            <div style={{ width: 200, height: 170, margin: '-12px auto 8px', position: 'relative' }}>
              <svg viewBox="0 0 200 170" width="200" height="170">
                <g className="star-spin" transform="translate(160 30)">
                  <path d="M0 -16 L4 -4 L16 0 L4 4 L0 16 L-4 4 L-16 0 L-4 -4 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
                </g>
                <ellipse cx="80" cy="120" rx="48" ry="34" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
                <ellipse cx="80" cy="128" rx="28" ry="18" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="2"/>
                <path d="M40 90 L46 78 L54 86 L62 74 L70 86 L80 72 L88 86" stroke="#3A2E2A" strokeWidth="2.5" fill="#FFD166" strokeLinejoin="round"/>
                <ellipse cx="58" cy="76" rx="28" ry="22" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
                <path d="M44 70 q5 -6 10 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
                <path d="M62 72 q5 -6 10 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
                <path d="M44 84 q10 8 18 0" stroke="#3A2E2A" strokeWidth="2.5" fill="#FFFCF1" strokeLinecap="round"/>
                <circle cx="36" cy="76" r="1.4" fill="#3A2E2A"/>
                <path d="M62 152 v12 h8 v-12 M88 152 v12 h8 v-12" stroke="#3A2E2A" strokeWidth="2.5" fill="#7DD3C0"/>
                <path d="M120 122 q22 4 28 -10" stroke="#3A2E2A" strokeWidth="3" fill="#7DD3C0"/>
                <g className="arm-throw">
                  <path d="M60 110 q-12 -16 -2 -32" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round"/>
                  <circle cx="58" cy="78" r="6" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2"/>
                  <path d="M55 72 v-8" stroke="#3A2E2A" strokeWidth="3" strokeLinecap="round"/>
                </g>
              </svg>
            </div>

            <h1 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 50, lineHeight: 1, marginTop: 6, letterSpacing: '.5px' }}>
              Пароль <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 3px 0 var(--ink)' }}>обновлён!</span>
            </h1>
            <p style={{ color: 'var(--ink-soft)', fontSize: 18, margin: '14px auto 0', maxWidth: 420, lineHeight: 1.45 }}>
              Динозаврик зашифровал его в самой глубокой норке. Теперь можно входить с новым.
            </p>

            <div style={{
              display: 'inline-block', background: '#fff', border: '3px solid var(--ink)',
              borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
              boxShadow: '4px 5px 0 var(--ink)', padding: '10px 18px 8px',
              fontFamily: '"Caveat", cursive', fontSize: 24, lineHeight: 1.05,
              transform: 'rotate(-2deg)', margin: '18px 0 0', position: 'relative'
            }}>
              главное — не забудь снова 🦖
              <span style={{
                content: '""', position: 'absolute', left: 30, bottom: -12,
                width: 18, height: 18, background: '#fff',
                borderRight: '3px solid var(--ink)', borderBottom: '3px solid var(--ink)',
                transform: 'rotate(45deg)', display: 'block'
              }} />
            </div>

            <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap', marginTop: 24 }}>
              <button
                onClick={() => router.push('/app')}
                style={{
                  fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 24, lineHeight: 1,
                  border: '3px solid var(--ink)', padding: '10px 20px 8px',
                  borderRadius: '18px 14px 20px 16px / 14px 18px 16px 20px',
                  boxShadow: '4px 5px 0 var(--ink)',
                  background: 'var(--pink)', color: '#fff',
                  textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                  cursor: 'pointer',
                  display: 'inline-flex', alignItems: 'center', gap: 8
                }}
              >
                Войти и резать клипы →
              </button>
              <Link href="/login" style={{
                fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 24, lineHeight: 1,
                border: '3px solid var(--ink)', padding: '10px 20px 8px',
                borderRadius: '18px 14px 20px 16px / 14px 18px 16px 20px',
                boxShadow: '4px 5px 0 var(--ink)',
                background: '#fff', color: 'var(--ink)',
                display: 'inline-flex', alignItems: 'center', gap: 8
              }}>
                К форме входа
              </Link>
            </div>

            <div style={{
              marginTop: 18, fontFamily: '"Patrick Hand SC", sans-serif',
              letterSpacing: '1.5px', fontSize: 13, color: 'var(--ink-soft)', textTransform: 'uppercase'
            }}>
              через{' '}
              <span style={{ color: 'var(--pink-deep)', fontFamily: '"Caveat", cursive', fontSize: 22, letterSpacing: 0, textTransform: 'none' }}>
                {countdown}
              </span>
              {' '}сек откроется студия...
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
