'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import AppNavbar from '@/components/AppNavbar'
import { API_BASE } from '@/lib/api'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [userEmail, setUserEmail] = useState<string | undefined>(undefined)

  useEffect(() => {
    const token = localStorage.getItem('cg_access_token')
    if (!token) {
      router.replace('/login')
      return
    }

    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) return null
        return res.json()
      })
      .then((data: { email?: string } | null) => {
        if (data?.email) setUserEmail(data.email)
      })
      .catch(() => {
        // non-fatal: avatar will show '?' fallback
      })
  }, [router])

  return (
    <>
      <div
        style={{
          minHeight: '100vh',
          background: 'var(--cream)',
          backgroundImage: `
            radial-gradient(circle at 8% 8%, rgba(255,209,102,.4) 0, transparent 28%),
            radial-gradient(circle at 96% 14%, rgba(255,143,163,.3) 0, transparent 26%),
            radial-gradient(circle at 96% 92%, rgba(125,211,192,.32) 0, transparent 28%),
            radial-gradient(circle at 4% 92%, rgba(201,182,228,.3) 0, transparent 28%)
          `,
        }}
      >
        <AppNavbar userEmail={userEmail} />
        {children}
      </div>
    </>
  )
}
