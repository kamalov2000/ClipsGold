'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'

const FILTERS = [
  { key: 'all', label: 'Все' },
  { key: 'done', label: 'Готовые' },
  { key: 'running', label: 'В работе' },
  { key: 'factory', label: 'Из Фабрики' },
  { key: 'viral', label: '🔥 9+' },
]

interface Clip {
  id: string
  file_id: string
  title: string
  virality: number
  duration: number
  platform?: string
  created_at: string
}

interface HistoryProject {
  id: string
  title: string
  platform: string
  duration_seconds: number
  created_at: string
  clips: Clip[]
  clips_count: number
  avg_virality: number
  published_count?: number
}

interface HistoryData {
  projects: HistoryProject[]
  total_projects: number
  total_videos: number
  total_clips: number
  hours_saved: number
}

const CLIP_COLORS = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6']

function fmtDuration(secs: number) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function fmtClipDuration(secs: number) {
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

function groupByDay(projects: HistoryProject[]) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const weekAgo = new Date(today)
  weekAgo.setDate(weekAgo.getDate() - 7)

  const groups: { label: string; projects: HistoryProject[] }[] = []
  const todayGroup: HistoryProject[] = []
  const weekGroup: HistoryProject[] = []
  const earlierGroup: HistoryProject[] = []

  for (const p of projects) {
    const d = new Date(p.created_at)
    d.setHours(0, 0, 0, 0)
    if (d.getTime() === today.getTime()) {
      todayGroup.push(p)
    } else if (d > weekAgo) {
      weekGroup.push(p)
    } else {
      earlierGroup.push(p)
    }
  }

  if (todayGroup.length) groups.push({ label: 'Сегодня', projects: todayGroup })
  if (weekGroup.length) groups.push({ label: 'На этой неделе', projects: weekGroup })
  if (earlierGroup.length) groups.push({ label: 'Раньше', projects: earlierGroup })
  return groups
}

export default function HistoryPage() {
  const router = useRouter()
  const [data, setData] = useState<HistoryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get('/history')
        setData(res.data)
      } catch {
        setData({ projects: [], total_projects: 0, total_videos: 0, total_clips: 0, hours_saved: 0 })
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const allProjects = data?.projects ?? []

  const filtered = allProjects.filter((p) => {
    const matchSearch = !search || p.title.toLowerCase().includes(search.toLowerCase())
    if (!matchSearch) return false
    if (filter === 'done') return (p.published_count ?? 0) > 0
    if (filter === 'running') return (p as any).status === 'running'
    if (filter === 'factory') return p.platform === 'factory'
    if (filter === 'viral') return p.avg_virality >= 9
    return true
  })

  const groups = groupByDay(filtered)

  return (
    <>
      <style>{`
        .clip-f1{background:linear-gradient(160deg,#FF8FA3,#E96A85)}
        .clip-f2{background:linear-gradient(160deg,#7DD3C0,#5BB9A4)}
        .clip-f3{background:linear-gradient(160deg,#FFD166,#F4B829)}
        .clip-f4{background:linear-gradient(160deg,#C9B6E4,#9d7fd1)}
        .clip-f5{background:linear-gradient(160deg,#B8E6CC,#7CC8A0)}
        .clip-f6{background:linear-gradient(160deg,#FF8FA3,#FFD166)}
        .clip-card{aspect-ratio:9/16;border:2.5px solid var(--ink);border-radius:12px 16px 10px 14px / 14px 10px 16px 12px;box-shadow:3px 3px 0 var(--ink);overflow:hidden;position:relative;color:#fff;display:block;cursor:pointer;text-decoration:none;}
        .clip-card:hover{transform:translate(-2px,-2px);box-shadow:5px 5px 0 var(--ink)}
        @keyframes histPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.3)}}
      `}</style>
      <nav style={{maxWidth:1280,margin:'0 auto',padding:'18px 28px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:24}}>
        <Link href="/" style={{display:'flex',alignItems:'center',gap:8,fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:30,color:'var(--ink)',textDecoration:'none'}}>
          <span style={{width:34,height:34,display:'grid',placeItems:'center',background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'14px 12px 16px 10px / 12px 14px 10px 16px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-4deg)'}}>
            <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/></svg>
          </span>
          Clips<span style={{color:'var(--yellow-deep)',textShadow:'1px 2px 0 var(--ink)'}}>Gold</span>
        </Link>
        <div style={{display:'flex',gap:16,alignItems:'center'}}>
          <div style={{display:'inline-flex',alignItems:'center',gap:6,fontFamily:'"Caveat",cursive',fontSize:20,lineHeight:1,background:'var(--mint)',border:'2.5px solid var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',padding:'4px 12px 2px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-1.5deg)'}}>
            🦖 <b>Beta · бесплатно</b>
          </div>
        </div>
      </nav>

      <div style={{maxWidth:1280,margin:'0 auto',padding:'0 28px 6px',display:'flex',alignItems:'center',gap:10,color:'var(--ink-soft)',fontSize:16}}>
        <Link href="/app" style={{color:'var(--ink-soft)',textDecoration:'none'}}>← Студия</Link>
        <span style={{opacity:.5}}>/</span>
        <span style={{color:'var(--ink)'}}>История</span>
      </div>

      <div style={{maxWidth:1280,margin:'0 auto',padding:'6px 28px 80px'}}>
        <div style={{marginBottom:8}}>
          <h1 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:60,lineHeight:1,margin:0}}>
            История <span style={{color:'var(--yellow-deep)',textShadow:'2px 3px 0 var(--ink)'}}>подвигов</span> 🦖
          </h1>
          <div style={{color:'var(--ink-soft)',fontSize:18,marginTop:4}}>Все видео, которые ты приносил динозаврику. Кликни проект — увидишь все клипы из него.</div>
        </div>

        {/* Stats */}
        <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:14,margin:'18px 0 22px'}}>
          {[
            {bg:'var(--mint)',num: data?.total_projects ?? 0,lbl:'проектов'},
            {bg:'var(--yellow)',num: data?.total_videos ?? 0,lbl:'видео обработано'},
            {bg:'var(--pink)',num: data?.total_clips ?? 0,lbl:'клипов вырезано',white:true},
            {bg:'var(--lilac)',num: data ? `${data.hours_saved} ч` : '—',lbl:'сэкономлено вручную'},
          ].map((s,i) => (
            <div key={i} style={{background:s.bg,border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 18px 16px 22px 20px',boxShadow:'4px 5px 0 var(--ink)',padding:'14px 18px'}}>
              <div style={{fontFamily:'"Caveat",cursive',fontSize:42,lineHeight:1,color:s.white?'#fff':'inherit',textShadow:s.white?'1px 1px 0 rgba(58,46,42,.35)':'none'}}>{loading ? '…' : s.num}</div>
              <div style={{fontFamily:'"Patrick Hand SC",sans-serif',fontSize:13,letterSpacing:'1.5px',textTransform:'uppercase',marginTop:4,color:s.white?'rgba(255,255,255,.85)':'inherit'}}>{s.lbl}</div>
            </div>
          ))}
        </div>

        {/* Toolbar */}
        <div style={{background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'20px 24px 18px 22px / 18px 22px 24px 20px',boxShadow:'4px 5px 0 var(--ink)',padding:'12px 16px',display:'flex',gap:14,alignItems:'center',flexWrap:'wrap',marginBottom:18}}>
          <div style={{flex:1,minWidth:240,display:'flex',alignItems:'center',gap:8,background:'#fff',border:'2.5px solid var(--ink)',borderRadius:'14px 18px 12px 16px / 16px 12px 18px 14px',padding:'6px 12px 4px',boxShadow:'2px 3px 0 var(--ink)'}}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="7" stroke="#3A2E2A" strokeWidth="2.5"/><path d="m17 17 4 4" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round"/></svg>
            <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="найти видео или клип..." style={{border:0,outline:0,background:'transparent',flex:1,fontSize:18,fontFamily:'"Patrick Hand",sans-serif',color:'var(--ink)'}} />
          </div>
          <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
            {FILTERS.map(f => {
              const isActive = filter === f.key
              const isRunning = f.key === 'running'
              return (
                <button key={f.key} onClick={() => setFilter(f.key)} style={{fontFamily:'"Caveat",cursive',fontSize:18,lineHeight:1,border:'2.5px solid var(--ink)',background:isActive?(isRunning?'var(--yellow)':'var(--pink)'):'#fff',color:isActive&&!isRunning?'#fff':'inherit',textShadow:isActive&&!isRunning?'1px 1px 0 rgba(58,46,42,.35)':'none',padding:'6px 12px 4px',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',boxShadow:'2px 2px 0 var(--ink)',cursor:'pointer'}}>{f.label}</button>
              )
            })}
          </div>
          <div style={{marginLeft:'auto',display:'flex',border:'2.5px solid var(--ink)',borderRadius:'14px 18px 12px 16px',overflow:'hidden',boxShadow:'2px 3px 0 var(--ink)'}}>
            {(['grid','list'] as const).map(m => (
              <button key={m} onClick={() => setViewMode(m)} style={{fontFamily:'"Caveat",cursive',fontSize:18,padding:'4px 14px 2px',background:viewMode===m?'var(--yellow)':'#fff',border:0,cursor:'pointer',borderRight:m==='grid'?'2.5px solid var(--ink)':'none'}}>
                {m === 'grid' ? '⊞ Сетка' : '☰ Список'}
              </button>
            ))}
          </div>
        </div>

        {/* Empty state */}
        {!loading && filtered.length === 0 && (
          <div style={{textAlign:'center',padding:'60px 0'}}>
            <svg viewBox="0 0 200 180" width="160" height="144" style={{margin:'0 auto',display:'block'}}>
              <ellipse cx="100" cy="115" rx="56" ry="42" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
              <ellipse cx="100" cy="125" rx="36" ry="22" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="2"/>
              <path d="M58 96 L62 84 L72 92 L78 80 L86 92 L94 78 L102 92" stroke="#3A2E2A" strokeWidth="2.5" fill="#FFD166" strokeLinejoin="round"/>
              <ellipse cx="60" cy="72" rx="34" ry="28" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
              <ellipse cx="50" cy="68" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
              <circle cx="52" cy="70" r="2.5" fill="#3A2E2A"/>
              <path d="M38 84 q4 3 10 0" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round"/>
              <path d="M84 152 v14 h12 v-14 M116 152 v14 h12 v-14" stroke="#3A2E2A" strokeWidth="2.5" fill="#7DD3C0"/>
            </svg>
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:36,margin:'18px 0 8px'}}>Тут пусто 🦖</h2>
            <p style={{color:'var(--ink-soft)'}}>Загрузи первое видео, и динозаврик нарежет вирусные клипы!</p>
            <Link href="/app" style={{display:'inline-flex',marginTop:18,fontFamily:'"Caveat",cursive',fontSize:22,background:'var(--pink)',color:'#fff',border:'2.5px solid var(--ink)',padding:'8px 20px 6px',borderRadius:'18px 14px 20px 16px / 14px 18px 16px 20px',boxShadow:'3px 4px 0 var(--ink)',textDecoration:'none',textShadow:'1px 1px 0 rgba(58,46,42,.35)'}}>
              В Студию 🦖
            </Link>
          </div>
        )}

        {/* Groups */}
        {groups.map(group => (
          <div key={group.label} style={{marginBottom:32}}>
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:30,lineHeight:1,marginBottom:14,display:'flex',alignItems:'baseline',gap:12}}>
              {group.label} <small style={{fontFamily:'"Patrick Hand",sans-serif',color:'var(--ink-soft)',fontSize:15,fontWeight:'normal'}}>· {group.projects.length} проект{group.projects.length>1?'а':''} · {group.projects.reduce((a,p)=>a+p.clips_count,0)} клипов</small>
            </h2>

            {group.projects.map(proj => (
              <div key={proj.id} style={{background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'22px 26px 20px 24px / 20px 24px 26px 22px',boxShadow:'6px 7px 0 var(--ink)',padding:'18px 20px',marginBottom:16}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:14,flexWrap:'wrap'}}>
                  <div>
                    <div style={{fontFamily:'"Caveat",cursive',fontSize:28,lineHeight:1.05,maxWidth:560}}>{proj.title}</div>
                    <div style={{color:'var(--ink-soft)',fontSize:14,marginTop:4,display:'flex',gap:14,flexWrap:'wrap'}}>
                      <span>{proj.platform} · <b style={{color:'var(--ink)'}}>{fmtDuration(proj.duration_seconds)}</b></span>
                      <span>{proj.clips_count} клипов · средняя 🔥 <b style={{color:'var(--ink)'}}>{proj.avg_virality?.toFixed(1)}</b></span>
                      {proj.published_count !== undefined && <span>опубликовано <b style={{color:'var(--ink)'}}>{proj.published_count} / {proj.clips_count}</b></span>}
                    </div>
                  </div>
                  <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                    <Link href="/app" style={{fontFamily:'"Caveat",cursive',fontSize:18,lineHeight:1,background:'#fff',border:'2.5px solid var(--ink)',padding:'6px 12px 4px',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',boxShadow:'2px 2px 0 var(--ink)',textDecoration:'none',color:'var(--ink)'}}>Студия</Link>
                  </div>
                </div>

                {viewMode === 'grid' ? (
                  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(140px,1fr))',gap:10,marginTop:14}}>
                    {proj.clips.slice(0, 6).map((clip, idx) => (
                      <div key={clip.id} onClick={() => router.push(`/render/${clip.file_id}/${clip.id}`)} className={`clip-card clip-${CLIP_COLORS[idx % CLIP_COLORS.length]}`}>
                        <div style={{position:'absolute',top:6,left:6,background:'#fff',color:'var(--ink)',fontFamily:'"Caveat",cursive',fontSize:14,lineHeight:1,padding:'2px 7px 1px',border:'2px solid var(--ink)',borderRadius:'8px 12px 8px 12px',boxShadow:'1px 1px 0 var(--ink)'}}>
                          {virEmoji(clip.virality)} {clip.virality?.toFixed(1)}
                        </div>
                        <div style={{position:'absolute',top:6,right:6,background:'rgba(0,0,0,.5)',fontSize:11,padding:'1px 6px',borderRadius:6}}>{fmtClipDuration(clip.duration)}</div>
                        <div style={{position:'absolute',left:6,right:6,bottom:6,fontFamily:'"Caveat",cursive',fontSize:15,lineHeight:1.05,textShadow:'1px 1px 0 rgba(58,46,42,.5)'}}>{clip.title}</div>
                      </div>
                    ))}
                    {proj.clips_count > 6 && (
                      <div style={{aspectRatio:'9/16',border:'2.5px solid var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',boxShadow:'3px 3px 0 var(--ink)',background:'var(--cream-2)',borderStyle:'dashed',display:'grid',placeItems:'center',cursor:'pointer',textAlign:'center'}} onClick={() => router.push(`/app`)}>
                        <div style={{fontFamily:'"Caveat",cursive',fontSize:32,lineHeight:1}}>+{proj.clips_count - 6}</div>
                        <div style={{fontFamily:'"Patrick Hand",sans-serif',fontSize:13,color:'var(--ink-soft)',padding:'0 4px'}}>показать ещё клипы</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{marginTop:14,display:'flex',flexDirection:'column',gap:6}}>
                    {proj.clips.map((clip, idx) => (
                      <div key={clip.id} onClick={() => router.push(`/render/${clip.file_id}/${clip.id}`)} style={{display:'flex',alignItems:'center',gap:10,padding:'6px 10px',background:'#fff',border:'2px solid var(--ink)',borderRadius:'10px 14px 8px 12px / 12px 8px 14px 10px',boxShadow:'2px 2px 0 var(--ink)',cursor:'pointer'}}>
                        <div className={`clip-${CLIP_COLORS[idx % CLIP_COLORS.length]}`} style={{width:48,height:85,flex:'none',borderRadius:'6px 10px 6px 8px',border:'2px solid var(--ink)',position:'relative',overflow:'hidden'}}>
                          <div style={{position:'absolute',inset:0}}/>
                        </div>
                        <div style={{flex:1,minWidth:0}}>
                          <div style={{fontFamily:'"Caveat",cursive',fontSize:18,lineHeight:1.1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{clip.title}</div>
                        </div>
                        <div style={{fontFamily:'"Caveat",cursive',fontSize:16,color:'var(--ink-soft)',whiteSpace:'nowrap'}}>{fmtClipDuration(clip.duration)}</div>
                        <div style={{fontFamily:'"Caveat",cursive',fontSize:16,whiteSpace:'nowrap'}}>{virEmoji(clip.virality)} {clip.virality?.toFixed(1)}</div>
                        <div style={{fontSize:13,color:'var(--ink-soft)',whiteSpace:'nowrap'}}>{new Date(clip.created_at).toLocaleDateString('ru-RU',{day:'numeric',month:'short'})}</div>
                        <div style={{display:'flex',gap:6}}>
                          <button onClick={e=>{e.stopPropagation();router.push(`/render/${clip.file_id}/${clip.id}`)}} style={{fontFamily:'"Caveat",cursive',fontSize:16,background:'var(--pink)',color:'#fff',border:'2px solid var(--ink)',borderRadius:'8px 12px 6px 10px',padding:'3px 10px 1px',boxShadow:'2px 2px 0 var(--ink)',cursor:'pointer',textShadow:'1px 1px 0 rgba(58,46,42,.35)'}}>Открыть</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}

        <div style={{marginTop:30,padding:'16px 18px',background:'#fff',border:'2.5px dashed var(--ink-soft)',borderRadius:'16px 20px 14px 18px / 18px 14px 20px 16px',color:'var(--ink-soft)',textAlign:'center',fontSize:15}}>
          🗑️ Удалённые проекты хранятся 30 дней — найти их можно в <Link href="/settings#danger" style={{textDecoration:'underline',color:'inherit'}}>настройках</Link>.
        </div>
      </div>
    </>
  )
}
