'use client'

import { useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function ForgotPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/forgot-password', { email })
      setSuccess(true)
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Ошибка при отправке письма'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        .auth-body {
          font-family: "Patrick Hand", sans-serif;
          color: var(--ink);
          font-size: 18px;
          background: var(--cream);
          background-image:
            radial-gradient(circle at 12% 18%, rgba(255,209,102,.45) 0, transparent 35%),
            radial-gradient(circle at 88% 12%, rgba(255,143,163,.35) 0, transparent 32%),
            radial-gradient(circle at 90% 80%, rgba(125,211,192,.4) 0, transparent 36%),
            radial-gradient(circle at 8% 88%, rgba(201,182,228,.35) 0, transparent 36%);
          min-height: 100vh;
        }
        .dino-eye { animation: blink 5s infinite; transform-box: fill-box; transform-origin: center; }
        @keyframes blink { 0%,88%,100%{ transform:scaleY(1) } 92%,95%{ transform:scaleY(.1) } }
      `}</style>

      <div className="auth-body">
        {/* Top nav */}
        <div style={{
          maxWidth: 560, margin: '0 auto', padding: '22px 24px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center'
        }}>
          <Link href="/login" style={{ fontSize: 18, color: 'var(--ink-soft)' }}>← Назад ко входу</Link>
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 28 }}>
            <span style={{
              width: 34, height: 34, display: 'grid', placeItems: 'center',
              background: 'var(--yellow)', border: '3px solid var(--ink)',
              borderRadius: '14px 12px 16px 10px / 12px 14px 10px 16px',
              boxShadow: '2px 3px 0 var(--ink)', transform: 'rotate(-4deg)'
            }}>
              <svg width="20" height="20" viewBox="0 0 26 26">
                <path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/>
              </svg>
            </span>
            Clips<span style={{ color: 'var(--yellow-deep)', textShadow: '1px 2px 0 var(--ink)' }}>Gold</span>
          </Link>
        </div>

        {/* Stage */}
        <div style={{ maxWidth: 520, margin: '14px auto 60px', padding: '0 24px', position: 'relative' }}>

          {/* Dino + bubble */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', marginBottom: -22, position: 'relative', zIndex: 2, paddingLeft: 24 }}>
            <svg style={{ width: 74, height: 78, transform: 'rotate(-4deg)', flex: 'none' }} viewBox="0 0 100 110">
              <ellipse cx="50" cy="62" rx="32" ry="28" fill="#C9B6E4" stroke="#3A2E2A" strokeWidth="3"/>
              <path d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8" stroke="#3A2E2A" strokeWidth="3" fill="#C9B6E4" strokeLinejoin="round"/>
              <path d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round"/>
              <ellipse className="dino-eye" cx="38" cy="56" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
              <circle cx="40" cy="58" r="2.5" fill="#3A2E2A"/>
              <path d="M28 70 q 6 -2 14 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
              <path d="M76 90 L86 100 M64 96 L70 106 M52 96 L52 106" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round"/>
            </svg>
            <div style={{
              background: 'var(--paper)', border: '3px solid var(--ink)',
              borderRadius: '18px 16px 6px 18px / 16px 18px 4px 16px',
              padding: '6px 12px 4px', fontFamily: '"Caveat", cursive', fontSize: 22,
              boxShadow: '3px 4px 0 var(--ink)', transform: 'rotate(-3deg)', marginBottom: 18, lineHeight: 1
            }}>
              бывает! 🦖
            </div>
          </div>

          {/* Card */}
          <div style={{
            background: 'var(--paper)', border: '3px solid var(--ink)',
            borderRadius: '32px 28px 34px 30px / 28px 32px 30px 34px',
            boxShadow: '8px 10px 0 var(--ink)', padding: '36px 36px 28px',
            transform: 'rotate(-.6deg)', position: 'relative'
          }}>
            {/* Doodle */}
            <svg style={{ position: 'absolute', top: -30, right: -10, transform: 'rotate(18deg)', pointerEvents: 'none' }} width="36" height="36" viewBox="0 0 24 24">
              <path d="M12 1 L14 9 L22 11 L14 13 L12 22 L10 13 L2 11 L10 9 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
            </svg>

            <h1 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 48, lineHeight: 1, letterSpacing: '.5px' }}>
              Восстановить <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 2px 0 var(--ink)' }}>пароль</span>
            </h1>
            <div style={{ color: 'var(--ink-soft)', margin: '6px 0 22px', fontSize: 17, lineHeight: 1.3 }}>
              Кинь email — пришлём ссылку, по которой можно задать новый. Письмо обычно прилетает за минуту.
            </div>

            {success ? (
              <div style={{
                background: '#edfff5', border: '3px solid #0a8a4f',
                borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                padding: '16px 20px', fontFamily: '"Caveat", cursive', fontSize: 24,
                color: '#0a8a4f', textAlign: 'center', lineHeight: 1.3
              }}>
                Проверь почту — письмо уже летит 🦖
              </div>
            ) : (
              <form onSubmit={handleSubmit}>
                <label style={{ display: 'block', marginBottom: 14 }}>
                  <span style={{
                    display: 'block', fontFamily: '"Patrick Hand SC", sans-serif',
                    letterSpacing: '1.2px', textTransform: 'uppercase', fontSize: 13,
                    color: 'var(--ink-soft)', marginBottom: 5, paddingLeft: 6
                  }}>Email от аккаунта</span>
                  <input
                    type="email" required value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="ты@example.com" autoComplete="email"
                    style={{
                      width: '100%', padding: '11px 16px 9px', fontSize: 18,
                      fontFamily: '"Patrick Hand", sans-serif', color: 'var(--ink)',
                      background: '#fff', border: '3px solid var(--ink)',
                      borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                      boxShadow: '3px 4px 0 var(--ink)', outline: 'none'
                    }}
                  />
                </label>

                {error && (
                  <div style={{
                    background: '#fff0f2', border: '2px solid var(--pink-deep)',
                    borderRadius: 12, padding: '8px 14px', color: 'var(--pink-deep)',
                    fontSize: 15, marginBottom: 14
                  }}>{error}</div>
                )}

                <button
                  type="submit" disabled={loading}
                  style={{
                    width: '100%', fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 26,
                    background: loading ? 'var(--ink-soft)' : 'var(--pink)', color: '#fff',
                    border: '3px solid var(--ink)',
                    borderRadius: '20px 16px 22px 18px / 16px 20px 18px 22px',
                    padding: '11px 22px 9px', boxShadow: '5px 6px 0 var(--ink)',
                    cursor: loading ? 'default' : 'pointer',
                    textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                    transition: 'transform .12s ease, box-shadow .12s ease, background .15s ease'
                  }}
                >
                  {loading ? 'Отправляем...' : 'Прислать ссылку →'}
                </button>
              </form>
            )}

            <div style={{ textAlign: 'center', marginTop: 22, fontSize: 17, color: 'var(--ink-soft)' }}>
              Вспомнил пароль?{' '}
              <Link href="/login" style={{ color: 'var(--ink)', borderBottom: '2px wavy var(--pink-deep)' }}>
                Войти →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
