import Link from 'next/link'
import FactoryDashboard from '@/components/FactoryDashboard'

export const metadata = {
  title: 'AI Factory | ClipsGold',
  description: 'Autonomous content production pipeline',
}

export default function FactoryPage() {
  return (
    <>
      <nav style={{ position: 'sticky', top: 0, zIndex: 100, background: 'oklch(0.11 0.01 62 / 0.92)', backdropFilter: 'blur(20px)', borderBottom: '1px solid oklch(0.24 0.01 62)' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 24px', height: 48, display: 'flex', alignItems: 'center', gap: 24 }}>
          <Link href="/" style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 18, color: 'oklch(0.96 0.004 60)', textDecoration: 'none', display: 'flex', gap: 2 }}>
            Clips<span style={{ color: 'oklch(0.76 0.148 80)' }}>Gold</span>
          </Link>
          <Link href="/process" style={{ fontSize: 13, color: 'oklch(0.44 0.005 60)', textDecoration: 'none' }}>Upload</Link>
          <Link href="/factory" style={{ fontSize: 13, color: 'oklch(0.44 0.005 60)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: '#facc15' }}>⚡</span> Factory
          </Link>
        </div>
      </nav>
      <FactoryDashboard />
    </>
  )
}
