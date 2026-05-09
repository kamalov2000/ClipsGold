import Link from 'next/link'

type LogoSize = 'sm' | 'md' | 'lg'

const fontSizes: Record<LogoSize, string> = {
  sm: '24px',
  md: '28px',
  lg: '32px',
}

const markSizes: Record<LogoSize, number> = {
  sm: 30,
  md: 34,
  lg: 36,
}

interface LogoProps {
  size?: LogoSize
  href?: string
}

export default function Logo({ size = 'md', href = '/app' }: LogoProps) {
  const fontSize = fontSizes[size]
  const markSize = markSizes[size]
  const svgSize = size === 'lg' ? 22 : 20

  return (
    <Link
      href={href}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontFamily: '"Caveat", cursive',
        fontWeight: 700,
        fontSize,
        textDecoration: 'none',
        color: 'var(--ink)',
      }}
    >
      <span
        style={{
          width: markSize,
          height: markSize,
          display: 'grid',
          placeItems: 'center',
          background: 'var(--yellow)',
          border: '3px solid var(--ink)',
          borderRadius: '14px 12px 16px 10px / 12px 14px 10px 16px',
          boxShadow: '2px 3px 0 var(--ink)',
          transform: 'rotate(-4deg)',
          flexShrink: 0,
        }}
      >
        <svg width={svgSize} height={svgSize} viewBox="0 0 26 26">
          <path
            d="M5 7 L13 13 L21 7 M13 13 V22"
            stroke="#3A2E2A"
            strokeWidth="3"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="13" cy="13" r="2.5" fill="#3A2E2A" />
        </svg>
      </span>
      Clips
      <span
        style={{
          color: 'var(--yellow-deep)',
          textShadow: '1px 2px 0 var(--ink)',
        }}
      >
        Gold
      </span>
    </Link>
  )
}
