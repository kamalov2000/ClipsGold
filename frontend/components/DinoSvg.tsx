interface DinoSvgProps {
  color: string
  size?: number
}

export default function DinoSvg({ color, size = 74 }: DinoSvgProps) {
  // Maintain the original viewBox aspect ratio: 100x110
  const height = Math.round(size * (110 / 100))

  return (
    <svg
      width={size}
      height={height}
      viewBox="0 0 100 110"
      style={{ transform: 'rotate(-4deg)', flexShrink: 0 }}
    >
      <style>{`
        @keyframes blink {
          0%, 88%, 100% { transform: scaleY(1); }
          92%, 95% { transform: scaleY(0.1); }
        }
        .dino-eye {
          animation: blink 5s infinite;
          transform-box: fill-box;
          transform-origin: center;
        }
      `}</style>

      {/* Body */}
      <ellipse cx="50" cy="62" rx="32" ry="28" fill={color} stroke="#3A2E2A" strokeWidth="3" />

      {/* Neck / head */}
      <path
        d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8"
        stroke="#3A2E2A"
        strokeWidth="3"
        fill={color}
        strokeLinejoin="round"
      />

      {/* Spikes */}
      <path
        d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36"
        fill="#FFD166"
        stroke="#3A2E2A"
        strokeWidth="2.5"
        strokeLinejoin="round"
      />

      {/* Eye white */}
      <ellipse
        className="dino-eye"
        cx="38"
        cy="56"
        rx="6"
        ry="7"
        fill="#fff"
        stroke="#3A2E2A"
        strokeWidth="2"
      />

      {/* Pupil */}
      <circle cx="40" cy="58" r="2.5" fill="#3A2E2A" />

      {/* Smile */}
      <path
        d="M28 70 q 8 6 16 0"
        stroke="#3A2E2A"
        strokeWidth="2.5"
        fill="none"
        strokeLinecap="round"
      />

      {/* Legs */}
      <path
        d="M76 90 L86 100 M64 96 L70 106 M52 96 L52 106"
        stroke="#3A2E2A"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
