'use client'

import { useEffect } from 'react'

export default function ProcessError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error('[ProcessPage error]', error)
  }, [error])

  return (
    <div style={{ height: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div style={{ maxWidth: 560, width: '100%', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 14, padding: 36 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'oklch(0.75 0.10 25)', marginBottom: 10 }}>Runtime error on /process</div>
        <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: 20, fontWeight: 700, color: 'var(--hi)', marginBottom: 16 }}>
          {error.message || 'Unknown error'}
        </div>
        {error.stack && (
          <pre style={{ fontSize: 11, color: 'var(--lo)', background: 'oklch(0.09 0.008 62)', border: '1px solid var(--border)', borderRadius: 8, padding: 14, overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', marginBottom: 20, lineHeight: 1.7 }}>
            {error.stack}
          </pre>
        )}
        <button onClick={reset} style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: 'var(--gold)', color: 'oklch(0.11 0.01 62)', fontFamily: "'DM Sans',sans-serif", fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
          Retry
        </button>
      </div>
    </div>
  )
}
