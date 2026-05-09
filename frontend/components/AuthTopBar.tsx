import Link from 'next/link'
import Logo from './Logo'

interface AuthTopBarProps {
  backHref?: string
}

export default function AuthTopBar({ backHref = '/' }: AuthTopBarProps) {
  return (
    <div
      style={{
        maxWidth: 560,
        margin: '0 auto',
        padding: '22px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <Link
        href={backHref}
        style={{
          fontSize: 18,
          color: 'var(--ink-soft)',
          textDecoration: 'none',
          transition: 'color 0.15s ease',
        }}
        onMouseEnter={undefined}
      >
        ← На главную
      </Link>
      <Logo size="md" href="/" />
    </div>
  )
}
