'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { API_BASE } from '@/lib/api'

interface ShareClip {
  id: string
  title: string
  hook?: string
  post_text?: string
  hashtags?: string[]
  virality: number
  duration: number
  filename: string
  created_at: string
  author_name?: string
  author_initial?: string
  source_title?: string
  source_platform?: string
  source_duration?: number
}

function fmtDuration(secs: number) {
  const m = Math.floor(secs / 60)
  const s = Math.round(secs % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function virEmoji(v: number) {
  if (v >= 9) return '🔥'
  if (v >= 8.5) return '⚡'
  if (v >= 8) return '🌟'
  return ''
}

export default function SharePage({ params }: { params: { clipId: string } }) {
  const { clipId } = params
  const [clip, setClip] = useState<ShareClip | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState('')
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/share/${clipId}`)
        if (!res.ok) throw new Error('not found')
        const data = await res.json()
        setClip(data)
      } catch {
        setError('Клип не найден или ссылка устарела')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [clipId])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 2000)
  }

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href).then(() => {
      showToast('скопировано в буфер 🦖')
    }).catch(() => {
      showToast('не удалось скопировать')
    })
  }

  const copyPost = () => {
    if (!clip) return
    const text = [clip.hook, clip.post_text, (clip.hashtags ?? []).map(h => `#${h}`).join(' ')].filter(Boolean).join('\n\n')
    navigator.clipboard.writeText(text).then(() => showToast('пост скопирован 🦖'))
  }

  return (
    <>
      <style>{`
        @keyframes shareWob{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-12px) rotate(5deg)}}
      `}</style>

      <nav style={{maxWidth:1180,margin:'0 auto',padding:'18px 28px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:24}}>
        <Link href="/" style={{display:'flex',alignItems:'center',gap:8,fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:30,color:'var(--ink)',textDecoration:'none'}}>
          <span style={{width:34,height:34,display:'grid',placeItems:'center',background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'14px 12px 16px 10px / 12px 14px 10px 16px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-4deg)'}}>
            <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/></svg>
          </span>
          Clips<span style={{color:'var(--yellow-deep)',textShadow:'1px 2px 0 var(--ink)'}}>Gold</span>
        </Link>
        <Link href="/register" style={{fontFamily:'"Caveat",cursive',fontSize:22,background:'var(--pink)',color:'#fff',border:'2.5px solid var(--ink)',padding:'6px 16px 4px',borderRadius:'18px 14px 20px 16px / 14px 18px 16px 20px',boxShadow:'3px 4px 0 var(--ink)',textShadow:'1px 1px 0 rgba(58,46,42,.35)',textDecoration:'none'}}>
          Сделать свой клип 🦖
        </Link>
      </nav>

      {loading && (
        <div style={{textAlign:'center',padding:'80px 0',fontFamily:'"Caveat",cursive',fontSize:28,color:'var(--ink-soft)'}}>
          Загружаем клип…
        </div>
      )}

      {error && (
        <div style={{maxWidth:600,margin:'60px auto',padding:'0 28px',textAlign:'center'}}>
          <div style={{fontFamily:'"Caveat",cursive',fontSize:48,marginBottom:12}}>🦖</div>
          <h2 style={{fontFamily:'"Caveat",cursive',fontSize:42,margin:'0 0 12px'}}>Клип не найден</h2>
          <p style={{color:'var(--ink-soft)',fontSize:18}}>{error}</p>
          <Link href="/" style={{display:'inline-flex',marginTop:20,fontFamily:'"Caveat",cursive',fontSize:22,background:'var(--pink)',color:'#fff',border:'2.5px solid var(--ink)',padding:'8px 20px 6px',borderRadius:'18px 14px 20px 16px / 14px 18px 16px 20px',boxShadow:'3px 4px 0 var(--ink)',textDecoration:'none',textShadow:'1px 1px 0 rgba(58,46,42,.35)'}}>
            ← На главную
          </Link>
        </div>
      )}

      {clip && (
        <div style={{maxWidth:1180,margin:'0 auto',padding:'6px 28px 80px',display:'grid',gridTemplateColumns:'1fr 1.05fr',gap:40,alignItems:'start'}}>

          {/* Player */}
          <div style={{position:'sticky',top:18,alignSelf:'start'}}>
            <div style={{aspectRatio:'9/16',maxWidth:380,margin:'0 auto',border:'3px solid var(--ink)',borderRadius:24,boxShadow:'8px 10px 0 var(--ink)',overflow:'hidden',position:'relative',background:'linear-gradient(160deg,#2A2A40 0%,#4B3F6E 100%)',color:'#fff',transform:'rotate(-1.5deg)'}}>
              {clip.filename && (
                <video
                  src={`${API_BASE}/clips/${clip.filename}`}
                  style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}}
                  controls={playing}
                  playsInline
                  onClick={() => setPlaying(true)}
                />
              )}
              <div style={{position:'absolute',top:14,left:14,fontFamily:'"Caveat",cursive',fontSize:24,lineHeight:1,background:'#fff',color:'var(--ink)',border:'2.5px solid var(--ink)',padding:'5px 12px 3px',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',boxShadow:'2px 2px 0 var(--ink)',transform:'rotate(-3deg)'}}>
                {virEmoji(clip.virality)} {clip.virality?.toFixed(1)}
              </div>
              <div style={{position:'absolute',top:14,right:14,background:'rgba(0,0,0,.6)',fontSize:14,padding:'3px 10px',borderRadius:8,border:'2px solid #fff'}}>
                {fmtDuration(clip.duration)}
              </div>
              {!playing && (
                <div style={{position:'absolute',left:'50%',top:'50%',transform:'translate(-50%,-50%)',width:74,height:74,borderRadius:'50%',background:'#fff',border:'3px solid var(--ink)',boxShadow:'4px 5px 0 var(--ink)',display:'grid',placeItems:'center',cursor:'pointer'}} onClick={() => setPlaying(true)}>
                  <svg width="22" height="22" viewBox="0 0 24 24"><path d="M5 4 L20 12 L5 20 Z" fill="#3A2E2A"/></svg>
                </div>
              )}
              {clip.hook && (
                <div style={{position:'absolute',left:14,right:14,bottom:24,background:'var(--yellow)',color:'var(--ink)',fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:24,lineHeight:1.1,border:'2.5px solid var(--ink)',padding:'6px 12px 4px',borderRadius:'14px 18px 12px 16px / 16px 12px 18px 14px',boxShadow:'3px 3px 0 var(--ink)',textAlign:'center'}}>
                  {clip.hook}
                </div>
              )}
            </div>
            <div style={{textAlign:'center',marginTop:14,color:'var(--ink-soft)',fontSize:14}}>
              ↑ нажми, чтобы посмотреть
            </div>
          </div>

          {/* Right */}
          <div>
            <h1 style={{fontFamily:'"Caveat",cursive',fontSize:54,lineHeight:1.05,margin:0}}>
              «<span style={{color:'var(--yellow-deep)',textShadow:'2px 2px 0 var(--ink)'}}>{clip.title}</span>»
            </h1>

            <div style={{display:'flex',alignItems:'center',gap:12,marginTop:14}}>
              <div style={{width:46,height:46,borderRadius:'50%',border:'3px solid var(--ink)',background:'var(--lilac)',display:'grid',placeItems:'center',fontFamily:'"Caveat",cursive',fontSize:22,fontWeight:700,boxShadow:'2px 3px 0 var(--ink)',flexShrink:0}}>
                {clip.author_initial ?? '?'}
              </div>
              <div>
                <div style={{fontFamily:'"Caveat",cursive',fontSize:22,lineHeight:1.05}}>{clip.author_name ?? 'Пользователь'}</div>
                <div style={{fontFamily:'"Patrick Hand SC",sans-serif',fontSize:13,color:'var(--ink-soft)',letterSpacing:'1.5px',textTransform:'uppercase'}}>создал клип</div>
              </div>
              <div style={{marginLeft:'auto',color:'var(--ink-soft)',fontSize:14}}>
                {new Date(clip.created_at).toLocaleDateString('ru-RU',{day:'numeric',month:'long',year:'numeric'})}
              </div>
            </div>

            {clip.source_title && (
              <div style={{marginTop:16,color:'var(--ink-soft)',fontSize:15}}>
                Из эпизода «{clip.source_title}» · {clip.source_platform}
              </div>
            )}

            {/* Share */}
            <div style={{marginTop:22,background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'20px 24px 18px 22px / 18px 22px 24px 20px',boxShadow:'5px 6px 0 var(--ink)',padding:'16px 18px'}}>
              <div style={{display:'flex',gap:10,alignItems:'center',background:'#fff',border:'2.5px solid var(--ink)',padding:'8px 14px 6px',borderRadius:'14px 18px 12px 16px / 16px 12px 18px 14px',boxShadow:'2px 3px 0 var(--ink)',fontSize:16,color:'var(--ink-soft)',overflow:'hidden'}}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M9 15 L15 9 M10 6 L13 3 a4.2 4.2 0 0 1 6 6 L16 12 M14 18 L11 21 a4.2 4.2 0 0 1-6-6 L8 12" stroke="#3A2E2A" strokeWidth="2" strokeLinecap="round"/></svg>
                <input readOnly value={typeof window !== 'undefined' ? window.location.href : ''} style={{border:0,outline:0,background:'transparent',flex:1,fontFamily:'"Patrick Hand",sans-serif',fontSize:16,color:'var(--ink)',minWidth:0}} />
                <button onClick={copyLink} style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:18,lineHeight:1,border:'2.5px solid var(--ink)',padding:'5px 12px 3px',borderRadius:'14px 10px 16px 12px',boxShadow:'2px 2px 0 var(--ink)',background:'#fff',cursor:'pointer',flexShrink:0,color:'var(--ink)'}}>
                  Copy
                </button>
              </div>
              <div style={{display:'flex',gap:10,flexWrap:'wrap',marginTop:12}}>
                {[
                  {label:'TikTok',bg:'#000',color:'#fff'},
                  {label:'Shorts',bg:'var(--yellow)',color:'var(--ink)'},
                  {label:'Reels',bg:'var(--mint)',color:'var(--ink)'},
                  {label:'X',bg:'var(--lilac)',color:'var(--ink)'},
                ].map(b => (
                  <button key={b.label} disabled title="Скоро" style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:20,lineHeight:1,border:'2.5px solid var(--ink)',padding:'7px 14px 5px',borderRadius:'18px 14px 20px 16px / 14px 18px 16px 20px',boxShadow:'3px 4px 0 var(--ink)',background:b.bg,color:b.color,cursor:'not-allowed',opacity:.6,display:'inline-flex',alignItems:'center',gap:5}}>
                    {b.label} <span style={{fontFamily:'"Patrick Hand SC",sans-serif',fontSize:11,letterSpacing:'1px',opacity:.8}}>скоро</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Post */}
            {(clip.hook || clip.post_text || (clip.hashtags && clip.hashtags.length > 0)) && (
              <div style={{marginTop:22,background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'24px 22px 26px 20px / 22px 26px 20px 24px',boxShadow:'6px 7px 0 var(--ink)',padding:'20px 22px',transform:'rotate(.3deg)'}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
                  <h3 style={{fontFamily:'"Caveat",cursive',fontSize:26,margin:0}}>Готовый пост</h3>
                  <button onClick={copyPost} style={{fontFamily:'"Caveat",cursive',fontSize:18,background:'var(--yellow)',border:'2.5px solid var(--ink)',padding:'5px 12px 3px',borderRadius:'12px 16px 10px 14px',boxShadow:'2px 2px 0 var(--ink)',cursor:'pointer',color:'var(--ink)'}}>
                    Копировать
                  </button>
                </div>
                <div style={{background:'#fff',border:'2.5px dashed var(--ink-soft)',borderRadius:'14px 18px 12px 16px / 16px 12px 18px 14px',padding:'12px 14px',fontSize:16,lineHeight:1.5}}>
                  {clip.hook && <span style={{fontFamily:'"Caveat",cursive',fontSize:22,lineHeight:1.05,color:'var(--pink-deep)',display:'block',marginBottom:6}}>{clip.hook}</span>}
                  {clip.post_text && <p style={{margin:'0 0 8px'}}>{clip.post_text}</p>}
                  {clip.hashtags && clip.hashtags.length > 0 && (
                    <div style={{display:'flex',flexWrap:'wrap',gap:6,marginTop:8}}>
                      {clip.hashtags.map(h => (
                        <span key={h} style={{background:'var(--mint)',border:'2px solid var(--ink)',padding:'1px 8px 0',borderRadius:6,fontSize:14,fontFamily:'"Caveat",cursive'}}>#{h}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* CTA */}
            <div style={{marginTop:28,background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'24px 28px 22px 26px / 22px 26px 28px 24px',boxShadow:'7px 8px 0 var(--ink)',padding:'22px 24px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:20,flexWrap:'wrap',transform:'rotate(-.6deg)'}}>
              <div>
                <h2 style={{fontFamily:'"Caveat",cursive',fontSize:34,lineHeight:1,margin:0}}>Хочешь так же?</h2>
                <div style={{color:'var(--ink)',fontSize:16,marginTop:4,maxWidth:380}}>Кинь своё видео — динозаврик нарежет вирусные клипы за 4 минуты. Бесплатно в бете.</div>
              </div>
              <div style={{display:'flex',alignItems:'center',gap:14}}>
                <span style={{fontSize:54,lineHeight:1}}>🦖</span>
                <Link href="/register" style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:24,lineHeight:1,border:'2.5px solid var(--ink)',padding:'10px 20px 8px',borderRadius:'18px 14px 20px 16px / 14px 18px 16px 20px',boxShadow:'3px 4px 0 var(--ink)',background:'var(--pink)',color:'#fff',textShadow:'1px 1px 0 rgba(58,46,42,.35)',textDecoration:'none'}}>
                  Создать клип →
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      <footer style={{maxWidth:1180,margin:'30px auto 0',padding:'18px 28px',borderTop:'2px dashed var(--ink-soft)',color:'var(--ink-soft)',fontSize:14,display:'flex',justifyContent:'space-between',flexWrap:'wrap',gap:10}}>
        <div>сделано в <Link href="/" style={{color:'var(--pink-deep)'}}>ClipsGold</Link> · видеоредактор для подкастов и лекций</div>
        <div>
          <Link href="/terms" style={{color:'var(--pink-deep)'}}>условия</Link> · <Link href="/privacy" style={{color:'var(--pink-deep)'}}>политика</Link>
        </div>
      </footer>

      {toast && (
        <div style={{position:'fixed',left:'50%',bottom:34,transform:'translateX(-50%) rotate(-1deg)',background:'var(--mint)',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 18px 16px 22px 20px',boxShadow:'5px 6px 0 var(--ink)',padding:'12px 22px 10px',fontFamily:'"Caveat",cursive',fontSize:24,zIndex:50,whiteSpace:'nowrap'}}>
          {toast}
        </div>
      )}
    </>
  )
}
