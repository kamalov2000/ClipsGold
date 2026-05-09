'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const email = searchParams.get('email') || ''
  const token = searchParams.get('token') || ''

  // ── Token verification mode ──────────────────────────────────
  const [verifyState, setVerifyState] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle')
  const [verifyError, setVerifyError] = useState('')

  useEffect(() => {
    if (!token) return
    setVerifyState('loading')
    api.post('/auth/verify-email', { token })
      .then(() => {
        setVerifyState('ok')
        setTimeout(() => router.replace('/login?verified=1'), 2500)
      })
      .catch((err: any) => {
        setVerifyError(err?.response?.data?.detail || 'Ссылка недействительна или истекла')
        setVerifyState('error')
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // ── Resend mode ──────────────────────────────────────────────
  const [resendTimer, setResendTimer] = useState(30)
  const [canResend, setCanResend] = useState(false)
  const [toastVisible, setToastVisible] = useState(false)
  const [resendError, setResendError] = useState('')

  useEffect(() => {
    if (token) return  // don't run timer in verify mode
    if (resendTimer <= 0) { setCanResend(true); return }
    const t = setTimeout(() => setResendTimer(s => s - 1), 1000)
    return () => clearTimeout(t)
  }, [resendTimer, token])

  async function handleResend() {
    if (!canResend) return
    setResendError('')
    try {
      await api.post('/auth/resend-verification', { email })
      setToastVisible(true)
      setTimeout(() => setToastVisible(false), 1800)
      setCanResend(false)
      setResendTimer(30)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Ошибка при повторной отправке'
      setResendError(msg)
    }
  }

  const timerStr = resendTimer < 10 ? `0:0${resendTimer}` : `0:${resendTimer}`

  // ── Token verification UI ─────────────────────────────────────
  if (token) {
    return (
      <>
        <style>{`
          .verify-body {
            font-family: "Patrick Hand", sans-serif; color: var(--ink); font-size: 18px;
            background: var(--cream);
            background-image: radial-gradient(circle at 8% 8%, rgba(255,209,102,.5) 0,transparent 30%),
              radial-gradient(circle at 96% 14%, rgba(255,143,163,.4) 0,transparent 28%),
              radial-gradient(circle at 96% 92%, rgba(125,211,192,.4) 0,transparent 30%),
              radial-gradient(circle at 4% 92%, rgba(201,182,228,.4) 0,transparent 30%);
            min-height: 100vh; display: flex; flex-direction: column;
          }
        `}</style>
        <div className="verify-body" style={{ alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            background: 'var(--paper)', border: '3px solid var(--ink)',
            borderRadius: '32px 28px 36px 24px / 26px 32px 24px 36px',
            boxShadow: '10px 12px 0 var(--ink)', padding: '44px 48px', maxWidth: 480, width: '100%',
            textAlign: 'center', transform: 'rotate(-1deg)',
          }}>
            {verifyState === 'loading' && (
              <>
                <div style={{ fontSize: 52, marginBottom: 12 }}>🦖</div>
                <h1 style={{ fontFamily: '"Caveat", cursive', fontSize: 40 }}>Проверяем ссылку…</h1>
              </>
            )}
            {verifyState === 'ok' && (
              <>
                <div style={{ fontSize: 52, marginBottom: 12 }}>✅</div>
                <h1 style={{ fontFamily: '"Caveat", cursive', fontSize: 40, color: 'var(--ink)' }}>Email подтверждён!</h1>
                <p style={{ color: 'var(--ink-soft)', marginTop: 10 }}>Переходим в студию… 🦖</p>
              </>
            )}
            {verifyState === 'error' && (
              <>
                <div style={{ fontSize: 52, marginBottom: 12 }}>😬</div>
                <h1 style={{ fontFamily: '"Caveat", cursive', fontSize: 36 }}>Ссылка не работает</h1>
                <p style={{ color: 'var(--ink-soft)', marginTop: 10, fontSize: 16 }}>{verifyError}</p>
                <Link href="/register" style={{
                  display: 'inline-block', marginTop: 20,
                  fontFamily: '"Caveat", cursive', fontSize: 22,
                  border: '3px solid var(--ink)', padding: '8px 20px 6px',
                  borderRadius: '16px 20px 14px 18px', boxShadow: '3px 4px 0 var(--ink)',
                  background: 'var(--yellow)', color: 'var(--ink)', textDecoration: 'none',
                }}>← Зарегистрироваться снова</Link>
              </>
            )}
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <style>{`
        .verify-body {
          font-family: "Patrick Hand", sans-serif;
          color: var(--ink);
          font-size: 18px;
          background: var(--cream);
          background-image:
            radial-gradient(circle at 8% 8%, rgba(255,209,102,.5) 0,transparent 30%),
            radial-gradient(circle at 96% 14%, rgba(255,143,163,.4) 0,transparent 28%),
            radial-gradient(circle at 96% 92%, rgba(125,211,192,.4) 0,transparent 30%),
            radial-gradient(circle at 4% 92%, rgba(201,182,228,.4) 0,transparent 30%);
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }
        .arm-wave {
          transform-origin: 70px 108px;
          animation: wave 2.2s ease-in-out infinite;
        }
        @keyframes wave { 0%,100%{ transform:rotate(-8deg) } 50%{ transform:rotate(10deg) } }
      `}</style>

      <div className="verify-body">
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
        <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: '20px 28px 60px' }}>
          <div style={{
            background: 'var(--paper)', border: '3px solid var(--ink)',
            borderRadius: '32px 28px 36px 24px / 26px 32px 24px 36px',
            boxShadow: '10px 12px 0 var(--ink)', padding: '44px 48px', maxWidth: 560, width: '100%',
            textAlign: 'center', transform: 'rotate(-1deg)', position: 'relative'
          }}>

            {/* Dino waving envelope scene */}
            <div style={{ width: 220, height: 180, margin: '-8px auto 4px', position: 'relative' }}>
              <svg viewBox="0 0 220 180" width="220" height="180">
                <ellipse cx="110" cy="168" rx="82" ry="6" fill="#3A2E2A" opacity=".15"/>
                <ellipse cx="86" cy="118" rx="50" ry="36" fill="#FFD166" stroke="#3A2E2A" strokeWidth="3"/>
                <ellipse cx="86" cy="128" rx="30" ry="19" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="2"/>
                <path d="M44 88 L50 76 L58 84 L66 72 L74 84 L84 70 L92 84" stroke="#3A2E2A" strokeWidth="2.5" fill="#FF8FA3" strokeLinejoin="round"/>
                <ellipse cx="60" cy="74" rx="30" ry="24" fill="#FFD166" stroke="#3A2E2A" strokeWidth="3"/>
                <circle cx="50" cy="70" r="5" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
                <circle cx="50" cy="71" r="2.2" fill="#3A2E2A"/>
                <path d="M64 78 q4 3 9 0" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round"/>
                <circle cx="36" cy="76" r="1.6" fill="#3A2E2A"/>
                <path d="M68 150 v12 h8 v-12 M96 150 v12 h8 v-12" stroke="#3A2E2A" strokeWidth="2.5" fill="#FFD166"/>
                <path d="M132 122 q26 4 30 -12" stroke="#3A2E2A" strokeWidth="3" fill="#FFD166"/>
                <g className="arm-wave">
                  <path d="M70 108 Q56 92 60 70" stroke="#3A2E2A" strokeWidth="3" fill="#FFD166" strokeLinecap="round"/>
                  <g transform="translate(60 50)">
                    <rect x="-22" y="-14" width="44" height="28" rx="3" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="2.5"/>
                    <path d="M -22 -14 L 0 4 L 22 -14" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinejoin="round"/>
                    <path d="M -22 14 L -4 0 M 22 14 L 4 0" stroke="#3A2E2A" strokeWidth="1.6" fill="none"/>
                    <circle cx="14" cy="-9" r="3.4" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="1.5"/>
                  </g>
                  <path d="M58 66 v6 M62 66 v6" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round"/>
                </g>
                <g transform="translate(180 96)">
                  <rect x="-3" y="6" width="6" height="50" fill="#3A2E2A"/>
                  <rect x="-22" y="-22" width="44" height="30" rx="6" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2.5"/>
                  <path d="M -22 -7 a22 14 0 0 1 44 0" fill="#5BB9A4" stroke="#3A2E2A" strokeWidth="2"/>
                  <circle cx="0" cy="3" r="2.5" fill="#FFD166" stroke="#3A2E2A" strokeWidth="1.6"/>
                  <path d="M22 -16 v-18" stroke="#3A2E2A" strokeWidth="2.5"/>
                  <path d="M22 -34 L36 -30 L22 -26 Z" fill="#E96A85" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
                </g>
                <path d="M30 50 h-8 M28 60 h-10 M32 40 h-6" stroke="#3A2E2A" strokeWidth="1.8" strokeLinecap="round" opacity=".55"/>
              </svg>
            </div>

            <div style={{ fontFamily: '"Patrick Hand SC", sans-serif', fontSize: 13, letterSpacing: 2, textTransform: 'uppercase', color: 'var(--ink-soft)' }}>
              шаг 2 / 2 · подтверждение почты
            </div>
            <h1 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 46, lineHeight: 1, marginTop: 6, letterSpacing: '.5px' }}>
              Глянь <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 2px 0 var(--ink)' }}>почту</span> 📬
            </h1>
            <p style={{ color: 'var(--ink-soft)', fontSize: 18, margin: '14px auto 0', maxWidth: 420, lineHeight: 1.45 }}>
              Отправил тебе письмо со ссылкой-подтверждением. Кликни — и попадёшь сразу в Студию.
            </p>

            {/* Email pill */}
            {email && (
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap',
                background: 'var(--mint)', border: '2.5px solid var(--ink)',
                padding: '8px 18px 6px', borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
                boxShadow: '2px 3px 0 var(--ink)', marginTop: 14,
                fontFamily: '"Caveat", cursive', fontSize: 26, lineHeight: 1.05,
                maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis'
              }}>
                <svg width="22" height="16" viewBox="0 0 24 18" fill="none">
                  <rect x="1.25" y="1.25" width="21.5" height="15.5" rx="2" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="2"/>
                  <path d="M2 3 L12 11 L22 3" stroke="#3A2E2A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {email}
              </div>
            )}

            {/* Speech bubble */}
            <div style={{
              display: 'inline-block', background: '#fff', border: '3px solid var(--ink)',
              borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
              boxShadow: '4px 5px 0 var(--ink)', padding: '10px 18px 8px',
              fontFamily: '"Caveat", cursive', fontSize: 22, lineHeight: 1.05,
              transform: 'rotate(-1.5deg)', margin: '18px 0 0', position: 'relative'
            }}>
              письмо несу как могу 🦖
              <span style={{
                position: 'absolute', left: 30, bottom: -12,
                width: 18, height: 18, background: '#fff',
                borderRight: '3px solid var(--ink)', borderBottom: '3px solid var(--ink)',
                transform: 'rotate(45deg)', display: 'block'
              }} />
            </div>

            {/* Mail buttons */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap', marginTop: 24 }}>
              <button
                onClick={() => window.open('https://mail.google.com', '_blank')}
                style={{
                  fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 22, lineHeight: 1,
                  border: '3px solid var(--ink)', padding: '9px 18px 7px',
                  borderRadius: '18px 14px 20px 16px / 14px 18px 16px 20px',
                  boxShadow: '4px 5px 0 var(--ink)',
                  background: 'var(--pink)', color: '#fff',
                  textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                  cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6
                }}
              >
                Открыть Gmail
              </button>
              <button
                onClick={() => window.open('https://outlook.com', '_blank')}
                style={{
                  fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 22, lineHeight: 1,
                  border: '3px solid var(--ink)', padding: '9px 18px 7px',
                  borderRadius: '18px 14px 20px 16px / 14px 18px 16px 20px',
                  boxShadow: '4px 5px 0 var(--ink)',
                  background: '#fff', color: 'var(--ink)',
                  cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6
                }}
              >
                Открыть Outlook
              </button>
            </div>

            {/* Resend section */}
            <div style={{ marginTop: 24, color: 'var(--ink-soft)', fontSize: 14, lineHeight: 1.6 }}>
              Не пришло за 2 минуты? Загляни в <strong>спам</strong> — динозаврик иногда теряется.<br/>
              <button
                onClick={handleResend}
                disabled={!canResend}
                style={{
                  fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 18, lineHeight: 1,
                  border: '3px solid var(--ink)', padding: '6px 14px 4px',
                  borderRadius: '18px 14px 20px 16px / 14px 18px 16px 20px',
                  boxShadow: '2px 3px 0 var(--ink)',
                  background: '#fff', color: 'var(--ink)',
                  cursor: canResend ? 'pointer' : 'default',
                  opacity: canResend ? 1 : 0.6,
                  marginTop: 10, display: 'inline-block'
                }}
              >
                ↻ Прислать ещё раз
              </button>
              <div style={{ fontSize: 14, color: 'var(--ink-soft)', marginTop: 6 }}>
                {canResend
                  ? 'Готово — можно жать кнопку'
                  : <>Можно повторно через <strong>{timerStr}</strong></>
                }
              </div>
              {resendError && (
                <div style={{ color: 'var(--pink-deep)', fontSize: 13, marginTop: 4 }}>{resendError}</div>
              )}
            </div>

            <div style={{ marginTop: 18, color: 'var(--ink-soft)', fontSize: 14 }}>
              Ошибся почтой?{' '}
              <Link href="/register" style={{ color: 'var(--pink-deep)', textDecoration: 'underline' }}>
                ← вернуться к регистрации
              </Link>
            </div>
          </div>
        </div>

        {/* Toast */}
        {toastVisible && (
          <div style={{
            position: 'fixed', left: '50%', bottom: 34,
            transform: 'translateX(-50%) rotate(-1deg)',
            background: 'var(--mint)', border: '3px solid var(--ink)',
            borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
            boxShadow: '5px 6px 0 var(--ink)', padding: '12px 22px 10px',
            fontFamily: '"Caveat", cursive', fontSize: 24, zIndex: 50
          }}>
            отправил ещё одно 🦖✉️
          </div>
        )}
      </div>
    </>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailContent />
    </Suspense>
  )
}
