import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ClipsGold',
  description: 'AI-Powered Viral Clip Detection',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur border-b border-white/10">
          <div className="max-w-7xl mx-auto px-4 h-12 flex items-center gap-6">
            <Link href="/" className="text-white font-bold text-lg tracking-tight">✂️ ClipsGold</Link>
            <Link href="/" className="text-gray-400 hover:text-white text-sm transition-colors">Upload</Link>
            <Link href="/factory" className="text-gray-400 hover:text-white text-sm transition-colors flex items-center gap-1">
              <span className="text-yellow-400">⚡</span> Factory
            </Link>
          </div>
        </nav>
        <div className="pt-12">{children}</div>
      </body>
    </html>
  )
}
