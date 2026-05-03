'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

export default function LandingPage() {
  const router = useRouter()
  const urlInputRef = useRef<HTMLInputElement>(null)

  // Intersection observer for entrance animations
  useEffect(() => {
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target) }
      }),
      { threshold: 0.15 }
    )
    document.querySelectorAll('.anim').forEach(el => obs.observe(el))
    return () => obs.disconnect()
  }, [])

  const handleExtract = () => {
    const url = urlInputRef.current?.value
    if (url) {
      router.push(`/process?url=${encodeURIComponent(url)}`)
    } else {
      router.push('/process')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleExtract()
  }

  // Tweaks panel logic
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (e.data?.type === '__activate_edit_mode')   document.getElementById('tweaks-panel')?.classList.add('open')
      if (e.data?.type === '__deactivate_edit_mode') document.getElementById('tweaks-panel')?.classList.remove('open')
    }
    window.addEventListener('message', onMsg)
    window.parent.postMessage({ type: '__edit_mode_available' }, '*')
    return () => window.removeEventListener('message', onMsg)
  }, [])

  function clearActive(groupId: string) {
    document.querySelectorAll(`#${groupId} .tweak-opt`).forEach(b => b.classList.remove('active'))
  }

  function setHeadline(btn: HTMLElement, val: string) {
    clearActive('tw-headline'); btn.classList.add('active')
    const el = document.querySelector('.hero-h1 .gold-text') as HTMLElement | null
    if (!el) return
    if (val === 'gradient') {
      el.style.background = 'linear-gradient(100deg, var(--gold) 0%, oklch(0.88 0.12 68) 100%)'
      el.style.webkitBackgroundClip = 'text'; el.style.webkitTextFillColor = 'transparent'
      el.style.backgroundClip = 'text'
    } else if (val === 'outline') {
      el.style.background = 'none'; el.style.webkitTextFillColor = 'transparent'
      ;(el.style as any).webkitTextStroke = '1.5px var(--gold)'; el.style.backgroundClip = 'unset'
    } else {
      el.style.background = 'none'; el.style.webkitTextFillColor = 'var(--gold)'
      ;(el.style as any).webkitTextStroke = 'none'
    }
  }

  function setAccent(btn: HTMLElement, color: string) {
    clearActive('tw-color'); btn.classList.add('active')
    document.documentElement.style.setProperty('--gold', color)
    document.documentElement.style.setProperty('--gold-dim', color.replace(')', ' / 0.15)'))
    document.documentElement.style.setProperty('--gold-line', color.replace(')', ' / 0.35)'))
  }

  function setBg(btn: HTMLElement, color: string) {
    clearActive('tw-bg'); btn.classList.add('active')
    document.documentElement.style.setProperty('--bg', color)
    document.body.style.background = color
    const nav = document.querySelector('.cg-nav') as HTMLElement | null
    if (nav) nav.style.background = color.replace(')', ' / 0.85)')
  }

  return (
    <>
      {/* NAV */}
      <nav className="cg-nav">
        <div className="cg-nav-inner">
          <a className="cg-logo display" href="#">Clips<em>Gold</em></a>
          <div className="cg-nav-links">
            <a className="cg-nav-link" href="#how">How it works</a>
            <a className="cg-nav-link" href="#features">Features</a>
          </div>
          <div className="cg-nav-actions">
            <Link href="/process" className="btn btn-ghost btn-sm">Sign in</Link>
            <Link href="/process" className="btn btn-primary btn-sm">Start free</Link>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section>
        <div className="cg-container">
          <div className="hero">
            <div className="hero-left">
              <div className="hero-eyebrow anim anim-d1">
                <span className="badge">For YouTubers &amp; Podcasters</span>
              </div>
              <h1 className="hero-h1 display anim anim-d2">
                Your best moments,<br />
                <span className="gold-text">extracted by AI.</span>
              </h1>
              <p className="hero-body anim anim-d3">
                Paste any YouTube URL. ClipsGold detects the hooks, highlights, and punchlines — and delivers portrait-ready clips in minutes.
              </p>

              <div className="url-input-row anim anim-d4">
                <div className="url-input-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.97C18.88 4 12 4 12 4s-6.88 0-8.59.45A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.97C5.12 20 12 20 12 20s6.88 0 8.59-.45a2.78 2.78 0 0 0 1.95-1.97A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z" />
                    <polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02" fill="currentColor" />
                  </svg>
                </div>
                <input
                  ref={urlInputRef}
                  className="url-input-field"
                  type="text"
                  placeholder="Paste YouTube URL…"
                  onKeyDown={handleKeyDown}
                />
                <button className="url-input-btn" onClick={handleExtract}>Extract clips →</button>
              </div>

              <div className="hero-trust anim anim-d4">
                <span className="trust-item"><span className="trust-dot">✦</span> Free to start</span>
                <span className="trust-item"><span className="trust-dot">✦</span> No credit card</span>
                <span className="trust-item"><span className="trust-dot">✦</span> Ready in &lt; 3 min</span>
              </div>
            </div>

            {/* Hero right — clips column */}
            <div className="hero-right">
              <div className="clips-stack">
                <div className="clip-card" style={{ width: 118 }}>
                  <div className="clip-img" style={{ height: 210 }}>
                    <div className="sc-img-label" style={{ position: 'absolute', bottom: 10, left: 0, right: 0 }}>portrait clip 9:16</div>
                  </div>
                  <div className="sc-bar" style={{ width: '42%' }} />
                  <div className="clip-footer">
                    <span className="clip-score">AI 88</span>
                    <span className="clip-dur">0:47</span>
                  </div>
                  <div className="clip-caption-preview">&ldquo;The key insight nobody talks about&rdquo;</div>
                </div>

                <div className="clip-card" style={{ width: 118, boxShadow: '0 0 0 1.5px var(--gold-line), 0 16px 48px oklch(0.76 0.148 80 / 0.18)' }}>
                  <div className="clip-img" style={{ height: 252, background: 'repeating-linear-gradient(-45deg, oklch(0.19 0.015 70) 0px, oklch(0.19 0.015 70) 5px, oklch(0.22 0.015 70) 5px, oklch(0.22 0.015 70) 10px)' }}>
                    <div className="sc-img-label" style={{ position: 'absolute', bottom: 10, left: 0, right: 0 }}>portrait clip 9:16</div>
                  </div>
                  <div className="sc-bar" />
                  <div className="clip-footer">
                    <span className="clip-score" style={{ color: 'var(--gold)' }}>AI 97</span>
                    <span className="clip-dur">1:12</span>
                  </div>
                  <div className="clip-caption-preview">&ldquo;This changed everything for me&rdquo;</div>
                </div>

                <div className="clip-card" style={{ width: 118 }}>
                  <div className="clip-img" style={{ height: 210 }}>
                    <div className="sc-img-label" style={{ position: 'absolute', bottom: 10, left: 0, right: 0 }}>portrait clip 9:16</div>
                  </div>
                  <div className="sc-bar" style={{ width: '61%' }} />
                  <div className="clip-footer">
                    <span className="clip-score">AI 82</span>
                    <span className="clip-dur">0:55</span>
                  </div>
                  <div className="clip-caption-preview">&ldquo;Here&apos;s what actually works&rdquo;</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* STATS BAND — hidden until real data available */}
      <div className="stats-band" style={{ display: 'none' }}>
        <div className="stat-cell">
          <div className="stat-val display">500K+</div>
          <div className="stat-lbl">Clips generated</div>
        </div>
        <div className="stat-cell">
          <div className="stat-val display">10×</div>
          <div className="stat-lbl">Faster than manual editing</div>
        </div>
        <div className="stat-cell">
          <div className="stat-val display">&lt;3 min</div>
          <div className="stat-lbl">From URL to download</div>
        </div>
        <div className="stat-cell">
          <div className="stat-val display">97%</div>
          <div className="stat-lbl">Creator satisfaction</div>
        </div>
      </div>

      {/* HOW IT WORKS */}
      <section className="section" id="how">
        <div className="cg-container">
          <div className="section-head">
            <div className="section-eyebrow">How it works</div>
            <h2 className="section-title display">Three steps from video to viral</h2>
            <p className="section-sub">No editing experience. No timeline. Just a URL.</p>
          </div>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-num-large display">01</div>
              <div className="step-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                </svg>
              </div>
              <div className="step-title">Paste your URL</div>
              <p className="step-desc">Drop in any YouTube link or upload an MP4 directly. We fetch and process the full video automatically.</p>
            </div>
            <div className="step-card">
              <div className="step-num-large display">02</div>
              <div className="step-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" /><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
                </svg>
              </div>
              <div className="step-title">AI finds the moments</div>
              <p className="step-desc">Whisper transcribes every word. Claude scores each segment for virality, emotional impact, and shareability.</p>
            </div>
            <div className="step-card">
              <div className="step-num-large display">03</div>
              <div className="step-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              </div>
              <div className="step-title">Download &amp; post</div>
              <p className="step-desc">Get portrait-reframed 9:16 clips with animated captions, ready for TikTok, Instagram Reels, and YouTube Shorts.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CLIP SHOWCASE — hidden (placeholder cards) */}
      <section className="showcase-section" style={{ display: 'none' }}>
        <div className="cg-container" style={{ marginBottom: 32 }}>
          <div className="section-eyebrow" style={{ textAlign: 'center' }}>Example outputs</div>
        </div>
        <div className="showcase-track">
          {[
            { label: 'Hook clip',      score: '97 ✦', width: '100%', angle: 'default' },
            { label: 'Key insight',    score: '91 ✦', width: '88%',  angle: '30' },
            { label: 'Funny cut',      score: '88 ✦', width: '75%',  angle: '60' },
            { label: 'Emotional peak', score: '94 ✦', width: '94%',  angle: 'default' },
            { label: 'Best quote',     score: '85 ✦', width: '80%',  angle: '-30' },
            { label: 'CTA moment',     score: '79 ✦', width: '69%',  angle: 'default' },
            { label: 'Surprise',       score: '92 ✦', width: '91%',  angle: '15' },
          ].map((c, i) => (
            <div key={i} className="showcase-clip">
              <div className="sc-img" style={c.angle !== 'default' ? { background: `repeating-linear-gradient(${c.angle}deg,oklch(0.17 0.01 62) 0,oklch(0.17 0.01 62) 5px,oklch(0.20 0.01 62) 5px,oklch(0.20 0.01 62) 10px)` } : {}}>
                <div className="sc-img-label">{c.label.toLowerCase()}<br />9:16 portrait</div>
              </div>
              <div className="sc-bar" style={c.width !== '100%' ? { width: c.width } : {}} />
              <div className="sc-info">
                <div className="sc-label">{c.label}</div>
                <div className="sc-score">AI score {c.score}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES */}
      <section className="features-section" id="features">
        <div className="cg-container">
          <div className="section-head">
            <div className="section-eyebrow">Features</div>
            <h2 className="section-title display">Everything you need to go viral</h2>
          </div>
          <div className="features-grid">
            {[
              {
                icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" /><path d="M10 8l6 4-6 4V8z" fill="var(--gold)" /></svg>,
                title: 'AI Moment Detection',
                desc: 'Whisper transcription + Claude analysis identifies peaks in energy, emotion, and information density. No guessing.',
              },
              {
                icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2"><rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" /></svg>,
                title: 'Portrait Reframing',
                desc: 'Horizontal footage auto-converted to 9:16 with smart crop tracking. Every clip looks native to mobile feeds.',
              },
              {
                icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>,
                title: 'Animated Captions',
                desc: 'Word-by-word subtitle animation, perfectly timed to the audio. Proven to increase watch time by up to 40%.',
              },
              {
                icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>,
                title: 'YouTube URL Import',
                desc: 'No manual download needed. Paste a link — we handle fetching, processing, and rendering in the cloud.',
              },
              {
                icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></svg>,
                title: 'Batch Factory Mode',
                desc: 'Process entire playlists or channels at once. Ideal for agencies or creators with high-volume publishing schedules.',
              },
              {
                icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.07 4.93A10 10 0 1 0 4.93 19.07" /></svg>,
                title: 'Niche Optimization',
                desc: 'Configure scoring for podcasts, interviews, tutorials, or commentary. AI adapts its criteria to your content genre.',
              },
            ].map((f, i) => (
              <div key={i} className="feature-card">
                <div className="feature-icon-wrap">{f.icon}</div>
                <div className="feature-title">{f.title}</div>
                <p className="feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS — hidden (placeholder reviews) */}
      <section className="section" style={{ paddingBottom: 0, display: 'none' }}>
        <div className="cg-container">
          <div className="section-head">
            <div className="section-eyebrow">What creators say</div>
            <h2 className="section-title display">Built for real creators</h2>
          </div>
          <div className="testi-grid">
            {[
              { quote: 'Cut my editing time from 4 hours to 20 minutes. The AI actually finds better clips than I would have chosen myself.', name: 'Alex R.', role: 'Podcast host · 180K subscribers', bg: 'oklch(0.38 0.06 240)' },
              { quote: 'Finally a tool that understands what makes a clip go viral. My Reels engagement is up 3× since I started using ClipsGold.', name: 'Maria S.', role: 'YouTube creator · 450K subscribers', bg: 'oklch(0.42 0.06 30)' },
              { quote: 'The auto-captions are so accurate I barely touch them before posting. This is the first repurposing tool I\'ve stuck with.', name: 'James T.', role: 'Interview host · 95K subscribers', bg: 'oklch(0.40 0.05 160)' },
            ].map((t, i) => (
              <div key={i} className="testi-card">
                <div className="testi-stars">★★★★★</div>
                <p className="testi-quote">&ldquo;{t.quote}&rdquo;</p>
                <div className="testi-author">
                  <div className="testi-avatar" style={{ background: t.bg }} />
                  <div>
                    <div className="testi-name">{t.name}</div>
                    <div className="testi-role">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING — hidden */}
      <section className="pricing-section" id="pricing" style={{ display: 'none' }}>
        <div className="cg-container">
          <div className="section-head">
            <div className="section-eyebrow">Pricing</div>
            <h2 className="section-title display">Start free, scale when ready</h2>
            <p className="section-sub">No credit card required. Upgrade any time.</p>
          </div>
          <div className="pricing-grid">
            <div className="pricing-card">
              <div className="pricing-name display">Free</div>
              <div className="pricing-price display">$0<span>/mo</span></div>
              <p className="pricing-desc">Try ClipsGold with no commitment.</p>
              <div className="pricing-divider" />
              <div className="pricing-feats">
                <div className="pricing-feat"><span className="feat-check">✦</span>3 clips per month</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>YouTube URL import</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>Auto-captions</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>Portrait reframing</div>
              </div>
              <Link href="/process" className="btn btn-ghost" style={{ width: '100%', padding: 12 }}>Start free</Link>
            </div>

            <div className="pricing-card featured">
              <div className="pricing-badge">Most popular</div>
              <div className="pricing-name display">Pro</div>
              <div className="pricing-price display">$19<span>/mo</span></div>
              <p className="pricing-desc">For active creators publishing weekly.</p>
              <div className="pricing-divider" />
              <div className="pricing-feats">
                <div className="pricing-feat"><span className="feat-check">✦</span>Unlimited clips</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>Batch processing</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>Priority queue</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>Custom caption styles</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>Viral score dashboard</div>
              </div>
              <Link href="/process" className="btn btn-primary" style={{ width: '100%', padding: 12 }}>Go Pro →</Link>
            </div>

            <div className="pricing-card">
              <div className="pricing-name display">Studio</div>
              <div className="pricing-price display">$79<span>/mo</span></div>
              <p className="pricing-desc">For agencies and high-volume teams.</p>
              <div className="pricing-divider" />
              <div className="pricing-feats">
                <div className="pricing-feat"><span className="feat-check">✦</span>Everything in Pro</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>API access</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>5 team seats</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>White-label export</div>
                <div className="pricing-feat"><span className="feat-check">✦</span>SLA &amp; dedicated support</div>
              </div>
              <a href="mailto:kamalov.alb2000@yandex.ru" className="btn btn-ghost" style={{ width: '100%', padding: 12 }}>Contact us</a>
            </div>
          </div>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="footer-cta">
        <div className="cg-container" style={{ position: 'relative', zIndex: 1 }}>
          <div className="badge" style={{ marginBottom: 28 }}>Get started today</div>
          <h2 className="footer-cta-h2 display">
            Ready to grow your<br />short-form presence?
          </h2>
          <p className="footer-cta-sub">Paste a URL. Get clips. Post everywhere.</p>
          <div className="footer-cta-actions">
            <Link href="/process" className="btn btn-primary" style={{ padding: '16px 40px', fontSize: 16 }}>Start for free →</Link>
            <button className="btn btn-ghost" style={{ padding: '16px 28px', fontSize: 16 }}>Watch a demo</button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="cg-footer">
        <div className="cg-container">
          <div className="footer-inner">
            <a className="cg-logo display" href="#" style={{ fontSize: 16 }}>Clips<em>Gold</em></a>
            <div className="footer-copy">© 2025 ClipsGold. All rights reserved.</div>
            <div className="footer-links">
              <a className="footer-link" href="#">Privacy</a>
              <a className="footer-link" href="#">Terms</a>
              <a className="footer-link" href="mailto:kamalov.alb2000@yandex.ru">Contact</a>
            </div>
          </div>
        </div>
      </footer>

      {/* TWEAKS PANEL */}
      <div id="tweaks-panel">
        <h3 className="display">
          Tweaks{' '}
          <button id="tweaks-close" onClick={() => {
            document.getElementById('tweaks-panel')?.classList.remove('open')
            window.parent.postMessage({ type: '__edit_mode_dismissed' }, '*')
          }}>×</button>
        </h3>

        <div className="tweak-row">
          <div className="tweak-label">Hero headline style</div>
          <div className="tweak-options" id="tw-headline">
            <button className="tweak-opt active" onClick={e => setHeadline(e.currentTarget, 'gradient')}>Gradient</button>
            <button className="tweak-opt" onClick={e => setHeadline(e.currentTarget, 'outline')}>Outline</button>
            <button className="tweak-opt" onClick={e => setHeadline(e.currentTarget, 'solid')}>Solid gold</button>
          </div>
        </div>

        <div className="tweak-row">
          <div className="tweak-label">Accent color</div>
          <div className="tweak-options" id="tw-color">
            <button className="tweak-opt active" onClick={e => setAccent(e.currentTarget, 'oklch(0.76 0.148 80)')}>Gold</button>
            <button className="tweak-opt" onClick={e => setAccent(e.currentTarget, 'oklch(0.72 0.14 200)')}>Teal</button>
            <button className="tweak-opt" onClick={e => setAccent(e.currentTarget, 'oklch(0.72 0.14 310)')}>Violet</button>
          </div>
        </div>

        <div className="tweak-row">
          <div className="tweak-label">Background tone</div>
          <div className="tweak-options" id="tw-bg">
            <button className="tweak-opt active" onClick={e => setBg(e.currentTarget, 'oklch(0.11 0.01 62)')}>Warm dark</button>
            <button className="tweak-opt" onClick={e => setBg(e.currentTarget, 'oklch(0.10 0.005 240)')}>Cool dark</button>
            <button className="tweak-opt" onClick={e => setBg(e.currentTarget, 'oklch(0.09 0 0)')}>Pure black</button>
          </div>
        </div>
      </div>
    </>
  )
}
