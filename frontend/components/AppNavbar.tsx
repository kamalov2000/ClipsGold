'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Logo from './Logo'
import { clearToken, getToken } from '@/lib/api'

interface AppNavbarProps {
  userEmail?: string
}

export default function AppNavbar({ userEmail }: AppNavbarProps) {
  const [open, setOpen] = useState(false)
  const router = useRouter()
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('click', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('click', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [])

  async function doLogout() {
    try {
      const token = getToken()
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
    } catch {
      // ignore network errors
    }
    clearToken()
    router.push('/login')
  }

  const avatarLetter = userEmail ? userEmail[0].toUpperCase() : '?'

  return (
    <nav
      style={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: '18px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 24,
      }}
    >
      <Logo size="lg" href="/app" />

      <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
        {/* Beta badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: '"Caveat", cursive',
            fontSize: 20,
            lineHeight: 1,
            background: 'var(--mint)',
            border: '2.5px solid var(--ink)',
            borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
            padding: '4px 12px 2px',
            boxShadow: '2px 3px 0 var(--ink)',
            transform: 'rotate(-1.5deg)',
          }}
        >
          🦖 <b style={{ color: 'var(--ink)' }}>Beta · бесплатно</b>
        </div>

        {/* Avatar + dropdown */}
        <div ref={menuRef} style={{ position: 'relative' }}>
          <div
            onClick={(e) => { e.stopPropagation(); setOpen((v) => !v) }}
            title="Профиль"
            style={{
              width: 42,
              height: 42,
              borderRadius: '50%',
              border: '3px solid var(--ink)',
              background: 'var(--lilac)',
              display: 'grid',
              placeItems: 'center',
              fontFamily: '"Caveat", cursive',
              fontSize: 24,
              fontWeight: 700,
              boxShadow: '2px 3px 0 var(--ink)',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            {avatarLetter}
          </div>

          {open && (
            <div
              style={{
                position: 'absolute',
                right: 0,
                top: 54,
                minWidth: 220,
                background: 'var(--paper)',
                border: '3px solid var(--ink)',
                borderRadius: '18px 22px 16px 20px / 18px 16px 22px 20px',
                boxShadow: '5px 6px 0 var(--ink)',
                padding: 6,
                zIndex: 50,
                transform: 'rotate(-1deg)',
              }}
            >
              {userEmail && (
                <>
                  <div
                    style={{
                      padding: '8px 12px 4px',
                      fontFamily: '"Patrick Hand SC", sans-serif',
                      fontSize: 13,
                      letterSpacing: 1,
                      textTransform: 'uppercase',
                      color: 'var(--ink-soft)',
                    }}
                  >
                    аккаунт
                    <b
                      style={{
                        display: 'block',
                        fontFamily: '"Patrick Hand", sans-serif',
                        fontSize: 16,
                        letterSpacing: 0,
                        textTransform: 'none',
                        color: 'var(--ink)',
                        marginTop: 2,
                      }}
                    >
                      {userEmail}
                    </b>
                  </div>
                  <hr style={{ border: 0, borderTop: '2px dashed var(--ink)', opacity: 0.3, margin: '8px 4px' }} />
                </>
              )}

              {[
                { href: '/factory', label: '🦖 Фабрика (24/7)' },
                { href: '/history', label: 'История проектов' },
                { href: '/settings', label: 'Настройки' },
              ].map(({ href, label }) => (
                <a
                  key={href}
                  href={href}
                  style={{
                    display: 'block',
                    padding: '8px 12px 6px',
                    fontFamily: '"Caveat", cursive',
                    fontSize: 22,
                    borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
                    textDecoration: 'none',
                    color: 'var(--ink)',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--cream-2)' }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                >
                  {label}
                </a>
              ))}

              <button
                type="button"
                onClick={doLogout}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 12px 6px',
                  fontFamily: '"Caveat", cursive',
                  fontSize: 22,
                  border: 0,
                  background: 'transparent',
                  cursor: 'pointer',
                  color: 'var(--pink-deep)',
                  borderRadius: '12px 16px 10px 14px / 14px 10px 16px 12px',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--cream-2)' }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
              >
                Выйти →
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
