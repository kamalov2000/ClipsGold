'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'

function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [showPw2, setShowPw2] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Password strength: 4 levels by length
  function getStrength(pw: string): number {
    if (!pw) return 0
    if (pw.length < 6) return 1
    if (pw.length < 10) return 2
    if (pw.length < 14) return 3
    return 4
  }

  function getStrengthLabel(s: number): string {
    return ['введи пароль...', 'слабый 🦖', 'нормально', 'хороший', 'отличный!'][s]
  }

  function getStrengthColor(s: number): string {
    return ['#e8dcc8', 'var(--pink-deep)', 'var(--yellow-deep)', 'var(--mint)', '#0a8a4f'][s]
  }

  const strengthLevel = getStrength(password)

  const rules = {
    len: password.length >= 8,
    num: /[0-9]/.test(password),
    case: /[a-zа-яё]/.test(password) && /[A-ZА-ЯЁ]/.test(password),
  }

  const passwordsMatch = password.length > 0 && password === password2
  const canSubmit = rules.len && rules.num && rules.case && passwordsMatch

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/reset-password', { token, password })
      router.push('/reset-success')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Ошибка при сбросе пароля'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const pwrapStyle: React.CSSProperties = {
    background: '#fff', border: '2.5px solid var(--ink)',
    borderRadius: '14px 18px 12px 16px / 16px 12px 18px 14px',
    boxShadow: '3px 4px 0 var(--ink)',
    display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px 6px'
  }

  const inputInnerStyle: React.CSSProperties = {
    border: 0, outline: 0, background: 'transparent', flex: 1, fontSize: 18,
    fontFamily: '"Patrick Hand", sans-serif', color: 'var(--ink)'
  }

  return (
    <>
      <style>{`
        .reset-body {
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
        .key-shake {
          transform-origin: 14px 14px;
          animation: shake 1.6s ease-in-out infinite;
        }
        @keyframes shake { 0%,100%{ transform:rotate(-6deg) } 50%{ transform:rotate(10deg) } }
      `}</style>

      <div className="reset-body">
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
            borderRadius: '30px 26px 34px 24px / 24px 32px 24px 34px',
            boxShadow: '10px 12px 0 var(--ink)', padding: '40px 44px 36px',
            maxWidth: 520, width: '100%', transform: 'rotate(-1deg)', position: 'relative'
          }}>
            {/* Key-holding dino */}
            <svg style={{ display: 'block', margin: '0 auto', width: 96, height: 80 }} viewBox="0 0 96 80">
              <ellipse cx="48" cy="56" rx="28" ry="20" fill="#C9B6E4" stroke="#3A2E2A" strokeWidth="2.5"/>
              <ellipse cx="48" cy="60" rx="16" ry="11" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="1.6"/>
              <ellipse cx="32" cy="36" rx="18" ry="15" fill="#C9B6E4" stroke="#3A2E2A" strokeWidth="2.5"/>
              <circle cx="26" cy="34" r="3.5" fill="#fff" stroke="#3A2E2A" strokeWidth="1.6"/>
              <circle cx="26" cy="35" r="1.6" fill="#3A2E2A"/>
              <path d="M16 40 q3 3 8 2" stroke="#3A2E2A" strokeWidth="1.6" fill="none" strokeLinecap="round"/>
              <path d="M76 56 q14 3 16 -8" stroke="#3A2E2A" strokeWidth="2.5" fill="#C9B6E4"/>
              <path d="M28 70 v8 h6 v-8 M58 70 v8 h6 v-8" stroke="#3A2E2A" strokeWidth="2" fill="#C9B6E4"/>
              <g className="key-shake" transform="translate(64 30)">
                <circle cx="6" cy="6" r="6" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2"/>
                <circle cx="6" cy="6" r="2" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="1.4"/>
                <path d="M12 6 H24 L24 10 M20 10 V8" stroke="#3A2E2A" strokeWidth="2" fill="#FFD166" strokeLinejoin="round"/>
              </g>
              <path d="M50 36 q10 -8 14 -8" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
            </svg>

            <div style={{ fontFamily: '"Patrick Hand SC", sans-serif', fontSize: 13, letterSpacing: 2, textTransform: 'uppercase', color: 'var(--ink-soft)', textAlign: 'center', marginTop: 6 }}>
              шаг 2 / 2 · сброс пароля
            </div>
            <h1 style={{ fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 44, lineHeight: 1, marginTop: 6, textAlign: 'center', letterSpacing: '.5px' }}>
              Придумай <span style={{ color: 'var(--yellow-deep)', textShadow: '2px 2px 0 var(--ink)' }}>новый</span>
            </h1>
            <p style={{ color: 'var(--ink-soft)', fontSize: 17, margin: '10px auto 18px', maxWidth: 420, lineHeight: 1.45, textAlign: 'center' }}>
              Только не «12345678» — динозаврик расстроится. Минимум 8 символов, букв и цифр.
            </p>

            <form onSubmit={handleSubmit} noValidate>
              {/* New password */}
              <label style={{ display: 'block', margin: '14px 0' }}>
                <span style={{ fontFamily: '"Patrick Hand SC", sans-serif', fontSize: 13, letterSpacing: '1.2px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: 4 }}>
                  Новый пароль
                </span>
                <div style={pwrapStyle}>
                  <input
                    type={showPw ? 'text' : 'password'} value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="Минимум 8 символов" autoComplete="new-password"
                    style={inputInnerStyle}
                  />
                  <button type="button" onClick={() => setShowPw(v => !v)}
                    style={{ background: 'none', border: 0, color: 'var(--ink-soft)', fontFamily: '"Caveat", cursive', fontSize: 18, lineHeight: 1, padding: '0 4px', cursor: 'pointer' }}>
                    {showPw ? 'скрыть' : 'показать'}
                  </button>
                </div>
              </label>

              {/* Strength bars */}
              <div style={{ marginTop: 8 }}>
                <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                  {[1, 2, 3, 4].map(i => (
                    <span key={i} style={{
                      flex: 1, height: 6, border: '1.5px solid var(--ink)', borderRadius: 3,
                      background: i <= strengthLevel ? getStrengthColor(strengthLevel) : '#e8dcc8',
                      transition: 'background .2s'
                    }} />
                  ))}
                </div>
                <div style={{
                  fontSize: 13,
                  color: strengthLevel === 4 ? '#0a8a4f' : strengthLevel === 1 ? 'var(--pink-deep)' : 'var(--ink-soft)'
                }}>
                  {getStrengthLabel(strengthLevel)}
                </div>
              </div>

              {/* Rules checklist */}
              <ul style={{ margin: '6px 0', padding: 0, fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6 }}>
                {[
                  { rule: rules.len, label: '8+ символов' },
                  { rule: rules.num, label: 'хотя бы одна цифра' },
                  { rule: rules.case, label: 'буквы разного регистра' },
                ].map(({ rule, label }) => (
                  <li key={label} style={{ listStyle: 'none', paddingLeft: 22, position: 'relative', color: rule ? 'var(--ink)' : 'var(--ink-soft)' }}>
                    <span style={{ position: 'absolute', left: 4, color: rule ? '#0a8a4f' : 'var(--ink-soft)' }}>
                      {rule ? '✓' : '○'}
                    </span>
                    {label}
                  </li>
                ))}
              </ul>

              {/* Confirm password */}
              <label style={{ display: 'block', margin: '14px 0' }}>
                <span style={{ fontFamily: '"Patrick Hand SC", sans-serif', fontSize: 13, letterSpacing: '1.2px', textTransform: 'uppercase', color: 'var(--ink-soft)', display: 'block', marginBottom: 4 }}>
                  Повтори пароль
                </span>
                <div style={pwrapStyle}>
                  <input
                    type={showPw2 ? 'text' : 'password'} value={password2}
                    onChange={e => setPassword2(e.target.value)}
                    placeholder="Введи ещё раз" autoComplete="new-password"
                    style={inputInnerStyle}
                  />
                  <button type="button" onClick={() => setShowPw2(v => !v)}
                    style={{ background: 'none', border: 0, color: 'var(--ink-soft)', fontFamily: '"Caveat", cursive', fontSize: 18, lineHeight: 1, padding: '0 4px', cursor: 'pointer' }}>
                    {showPw2 ? 'скрыть' : 'показать'}
                  </button>
                </div>
                <div style={{
                  fontSize: 13, marginTop: 4,
                  color: password2
                    ? (passwordsMatch ? '#0a8a4f' : 'var(--pink-deep)')
                    : 'var(--ink-soft)'
                }}>
                  {password2
                    ? (passwordsMatch ? '✓ совпадают' : '✗ пароли не совпадают')
                    : ' '}
                </div>
              </label>

              {error && (
                <div style={{
                  background: '#fff0f2', border: '2px solid var(--pink-deep)',
                  borderRadius: 12, padding: '8px 14px', color: 'var(--pink-deep)',
                  fontSize: 15, marginBottom: 10
                }}>{error}</div>
              )}

              <button
                type="submit" disabled={!canSubmit || loading}
                style={{
                  width: '100%', display: 'block', marginTop: 18,
                  fontFamily: '"Caveat", cursive', fontWeight: 700, fontSize: 26, lineHeight: 1,
                  background: 'var(--pink)', color: '#fff', textShadow: '1px 1px 0 rgba(58,46,42,.35)',
                  border: '3px solid var(--ink)', padding: '12px 18px 10px',
                  borderRadius: '20px 16px 22px 18px / 16px 20px 18px 22px',
                  boxShadow: '5px 6px 0 var(--ink)',
                  opacity: (!canSubmit || loading) ? 0.55 : 1,
                  cursor: (!canSubmit || loading) ? 'not-allowed' : 'pointer',
                  transition: 'transform .12s, box-shadow .12s, background .15s'
                }}
              >
                {loading ? 'Сохраняем...' : 'Сохранить и войти 🦖'}
              </button>
            </form>

            <div style={{ marginTop: 18, textAlign: 'center', color: 'var(--ink-soft)', fontSize: 14 }}>
              Вспомнил старый?{' '}
              <Link href="/login" style={{ color: 'var(--pink-deep)', textDecoration: 'underline' }}>← обратно ко входу</Link>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  )
}
