import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ClipsGold — ИИ-нарезка вирусных клипов',
  description: 'Автоматическая нарезка вирусных клипов с помощью ИИ: Whisper + Claude. Загрузи видео — получи готовые шортсы.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  )
}
