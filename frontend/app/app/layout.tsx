'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import AppNavbar from '@/components/AppNavbar'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem('cg_access_token')
    if (!token) {
      router.replace('/login')
    }
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
        <AppNavbar />
        {children}
      </div>
    </>
  )
}
