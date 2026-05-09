'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api, saveToken } from '@/lib/api'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/auth/json-login', { email, password })
      saveToken(res.data.access_token, res.data.refresh_token)
      router.push('/app')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Неверный email или пароль'
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
          <Link href="/" style={{ fontSize: 18, color: 'var(--ink-soft)' }}>← На главную</Link>
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
              <ellipse cx="50" cy="62" rx="32" ry="28" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
              <path d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8" stroke="#3A2E2A" strokeWidth="3" fill="#7DD3C0" strokeLinejoin="round"/>
              <path d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round"/>
              <ellipse className="dino-eye" cx="38" cy="56" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
              <circle cx="40" cy="58" r="2.5" fill="#3A2E2A"/>
              <path d="M28 70 q 8 6 16 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
              <path d="M76 90 L86 100 M64 96 L70 106 M52 96 L52 106" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round"/>
            </svg>
            <div style={{
              background: 'var(--paper)', border: '3px solid var(--ink)',
              borderRadius: '18px 16px 6px 18px / 16px 18px 4px 16px',
              padding: '6px 12px 4px', fontFamily: '"Caveat", cursive', fontSize: 22,
              boxShadow: '3px 4px 0 var(--ink)', transform: 'rotate(-3deg)', marginBottom: 18, lineHeight: 1
            }}>
              с возвращением! 🦖
            </div>
          </div>

          {/* Card */}
          <div style={{
            background: 'var(--paper)', border: '3px solid var(--ink)',
            borderRadius: '32px 28px 34px 30px / 28px 32px 30px 34px',
            boxShadow: '8px 10px 0 var(--ink)', padding: '36px 36px 28px',
            transform: 'rotate(-.6deg)', position: 'relative'
          }}>
            {/* Doodles */}
            <svg style={{ position: 'absolute', top: -30, right: -10, transform: 'rotate(18deg)', pointerEvents: 'none' }} width="36" height="36" viewBox="0 0 24 24">
              <path d="M12 1 L14 9 L22 11 L14 13 L12 22 L10 13 L2 11 L10 9 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/>
            </svg>
            <svg style={{ position: 'absolute', bottom: -20, left: -30, pointerEvents: 'none' }} width="80" height="14" viewBox="0 0 80 14">
              <path d="M2 7 Q 12 1 22 7 T 42 7 T 62 7 T 78 7" stroke="#FF8FA3" strokeWidth="3" fill="none" strokeLinecap="round"/>
            </svg>

            <h1 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 48, lineHeight: 1, letterSpacing: '.5px', paddingBottom: 4 }}>
              Войти в Clips<span style={{ color: 'var(--yellow-deep)', textShadow: '2px 2px 0 var(--ink)' }}>Gold</span>
            </h1>
            <div style={{ color: 'var(--ink-soft)', marginBottom: 22, fontSize: 17 }}>Динозаврик уже наточил ножницы.</div>

            <form onSubmit={handleSubmit}>
              <label style={{ display: 'block', marginBottom: 14, marginTop: 6 }}>
                <span style={{
                  display: 'block', fontFamily: '"Patrick Hand SC", sans-serif',
                  letterSpacing: '1.2px', textTransform: 'uppercase', fontSize: 13,
                  color: 'var(--ink-soft)', marginBottom: 5, paddingLeft: 6
                }}>Email</span>
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

              <label style={{ display: 'block', marginBottom: 14, marginTop: 6 }}>
                <span style={{
                  display: 'block', fontFamily: '"Patrick Hand SC", sans-serif',
                  letterSpacing: '1.2px', textTransform: 'uppercase', fontSize: 13,
                  color: 'var(--ink-soft)', marginBottom: 5, paddingLeft: 6
                }}>Пароль</span>
                <input
                  type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••" autoComplete="current-password"
                  style={{
                    width: '100%', padding: '11px 16px 9px', fontSize: 18,
                    fontFamily: '"Patrick Hand", sans-serif', color: 'var(--ink)',
                    background: '#fff', border: '3px solid var(--ink)',
                    borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                    boxShadow: '3px 4px 0 var(--ink)', outline: 'none'
                  }}
                />
              </label>

              <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '4px 4px 14px', fontSize: 14 }}>
                <Link href="/forgot" style={{ color: 'var(--pink-deep)' }}>Забыл пароль?</Link>
              </div>

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
                  padding: '11px 22px 9px', boxShadow: '5px 6px 0 var(--ink)', cursor: loading ? 'default' : 'pointer',
                  textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                  transition: 'transform .12s ease, box-shadow .12s ease, background .15s ease'
                }}
              >
                {loading ? 'Входим...' : 'Войти →'}
              </button>
            </form>

            <div style={{ textAlign: 'center', marginTop: 22, fontSize: 17, color: 'var(--ink-soft)' }}>
              Нет аккаунта?{' '}
              <Link href="/register" style={{ color: 'var(--ink)', borderBottom: '2px wavy var(--pink-deep)' }}>
                Зарегистрироваться →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
