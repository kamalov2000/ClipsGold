'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface DiscoveryItem {
  id: string
  youtube_url: string
  youtube_video_id: string
  niche: string
  status: string
  view_count: number
  duration_seconds: number
  discovered_at: string
  processed_at: string | null
  error_message: string | null
}

interface FactoryStats {
  total_discovered: number
  total_processed: number
  total_clips: number
  pending_count: number
  processing_count: number
  failed_count: number
  niches: { [key: string]: number }
}

interface SchedulerStatus {
  running: boolean
  jobs: Array<{
    id: string
    name: string
    next_run: string | null
  }>
}

const NICHE_CONFIG: { [key: string]: { ico: string; label: string } } = {
  business: { ico: '💼', label: 'Бизнес' },
  startup: { ico: '🚀', label: 'Стартапы' },
  psychology: { ico: '🧠', label: 'Психология' },
  motivation: { ico: '💪', label: 'Мотивация' },
  comedy: { ico: '😂', label: 'Comedy' },
  sport: { ico: '⚽', label: 'Спорт' },
  cinema: { ico: '🎬', label: 'Кино' },
  education: { ico: '📚', label: 'Образование' },
  gamedev: { ico: '🎮', label: 'Геймдев' },
  cooking: { ico: '🍳', label: 'Готовка' },
  travel: { ico: '✈', label: 'Путешествия' },
  finance: { ico: '💰', label: 'Финансы' },
}

// 7-day static data (no backend endpoint yet)
const perfData = [
  { day: 'Пн', clips: 12, isWeekend: false },
  { day: 'Вт', clips: 8, isWeekend: false },
  { day: 'Ср', clips: 15, isWeekend: false },
  { day: 'Чт', clips: 10, isWeekend: false },
  { day: 'Пт', clips: 18, isWeekend: false },
  { day: 'Сб', clips: 6, isWeekend: true },
  { day: 'Вс', clips: 4, isWeekend: true },
]
const maxClips = Math.max(...perfData.map(d => d.clips))

const HOUR_STATES: Record<number, 'idle' | 'busy' | 'peak' | 'plan'> = {
  0: 'idle', 1: 'idle', 2: 'idle', 3: 'idle', 4: 'idle', 5: 'idle',
  6: 'busy', 7: 'busy', 8: 'peak', 9: 'peak', 10: 'peak', 11: 'busy',
  12: 'busy', 13: 'peak', 14: 'peak', 15: 'busy', 16: 'busy', 17: 'peak',
  18: 'busy', 19: 'busy', 20: 'idle', 21: 'idle', 22: 'idle', 23: 'idle',
}

const hourStateStyle: Record<'idle' | 'busy' | 'peak' | 'plan', { background: string; color: string }> = {
  idle: { background: '#fff', color: 'var(--ink-soft)' },
  busy: { background: 'var(--yellow)', color: 'var(--ink)' },
  peak: { background: 'var(--pink)', color: '#fff' },
  plan: { background: 'var(--lilac)', color: 'var(--ink)' },
}

const hourEmoji: Record<'idle' | 'busy' | 'peak' | 'plan', string> = {
  idle: '💤',
  busy: '⚡',
  peak: '🔥',
  plan: '📋',
}

function fmtDuration(secs: number) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${m}:${String(s).padStart(2, '0')}`
}

function statusDot(status: string): { bg: string; label: string; type: string } {
  switch (status) {
    case 'complete': return { bg: 'var(--mint)', label: 'done', type: 'done' }
    case 'pending': return { bg: 'var(--lilac)', label: 'queue', type: 'queue' }
    case 'failed':
    case 'skipped': return { bg: 'var(--pink)', label: 'ошибка', type: 'find' }
    default: return { bg: 'var(--yellow)', label: 'processing', type: 'run' }
  }
}

export default function FactoryPage() {
  const [discoveries, setDiscoveries] = useState<DiscoveryItem[]>([])
  const [stats, setStats] = useState<FactoryStats | null>(null)
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [factoryOn, setFactoryOn] = useState(true)
  const [activeNiches, setActiveNiches] = useState<Set<string>>(new Set())

  const fetchData = async () => {
    try {
      const [dRes, sRes, schRes] = await Promise.all([
        api.get('/factory/discoveries?limit=20'),
        api.get('/factory/stats'),
        api.get('/factory/scheduler-status'),
      ])
      setDiscoveries(dRes.data.discoveries || [])
      const s = sRes.data as FactoryStats
      setStats(s)
      setScheduler(schRes.data)
      setFactoryOn(schRes.data.running)
      if (s.niches) setActiveNiches(new Set(Object.keys(s.niches).filter(k => s.niches[k] > 0)))
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    if (autoRefresh) {
      const iv = setInterval(fetchData, 10000)
      return () => clearInterval(iv)
    }
  }, [autoRefresh])

  const toggleNiche = (key: string) => {
    setActiveNiches(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const niche_display_list = Object.entries(NICHE_CONFIG).map(([key, cfg]) => ({
    key,
    ...cfg,
    cnt: stats?.niches[key] ?? 0,
    on: activeNiches.has(key),
  }))

  // SVG bar chart calculations
  const barWidth = 28
  const barGap = 8
  const chartPaddingLeft = 24
  const chartPaddingRight = 16
  const chartPaddingTop = 22  // room for count labels above bars
  const chartPaddingBottom = 24  // room for day labels
  const barAreaHeight = 160
  const svgWidth = chartPaddingLeft + perfData.length * (barWidth + barGap) - barGap + chartPaddingRight
  const svgHeight = chartPaddingTop + barAreaHeight + chartPaddingBottom

  const barX = (i: number) => chartPaddingLeft + i * (barWidth + barGap)
  const barH = (clips: number) => (clips / maxClips) * barAreaHeight
  const barY = (clips: number) => chartPaddingTop + barAreaHeight - barH(clips)

  // Dashed trend line points (connecting tops of bars)
  const trendPoints = perfData.map((d, i) => {
    const cx = barX(i) + barWidth / 2
    const cy = barY(d.clips)
    return `${cx},${cy}`
  }).join(' ')

  return (
    <>
      <style>{`
        @keyframes factPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.3)}}
        @keyframes factBlink{0%,88%,100%{transform:scaleY(1)}92%,95%{transform:scaleY(.1)}}
        .fact-eye{animation:factBlink 5s infinite;transform-box:fill-box;transform-origin:center}
        .fact-dot-run{background:var(--yellow);animation:factPulse 1.4s infinite}
        .fact-dot-done{background:var(--mint)}
        .fact-dot-queue{background:var(--lilac)}
        .fact-dot-find{background:var(--pink)}
        .fact-feed::-webkit-scrollbar{width:8px}
        .fact-feed::-webkit-scrollbar-thumb{background:var(--ink);border-radius:4px}
      `}</style>

      <nav style={{maxWidth:1280,margin:'0 auto',padding:'18px 28px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:24}}>
        <Link href="/" style={{display:'flex',alignItems:'center',gap:8,fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:30,color:'var(--ink)',textDecoration:'none'}}>
          <span style={{width:34,height:34,display:'grid',placeItems:'center',background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'14px 12px 16px 10px / 12px 14px 10px 16px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-4deg)'}}>
            <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/></svg>
          </span>
          Clips<span style={{color:'var(--yellow-deep)',textShadow:'1px 2px 0 var(--ink)'}}>Gold</span>
        </Link>
        <div style={{display:'flex',gap:12,alignItems:'center'}}>
          <button onClick={fetchData} style={{fontFamily:'"Caveat",cursive',fontSize:18,background:'var(--paper)',border:'2.5px solid var(--ink)',padding:'5px 14px 3px',borderRadius:'12px 16px 10px 14px',boxShadow:'2px 3px 0 var(--ink)',cursor:'pointer',color:'var(--ink)'}}>
            ↻ Обновить
          </button>
          <label style={{display:'flex',alignItems:'center',gap:6,fontFamily:'"Caveat",cursive',fontSize:18,cursor:'pointer'}}>
            <input type="checkbox" checked={autoRefresh} onChange={e=>setAutoRefresh(e.target.checked)} style={{accentColor:'var(--yellow)'}}/>
            Авто
          </label>
          <div style={{display:'inline-flex',alignItems:'center',gap:6,fontFamily:'"Caveat",cursive',fontSize:20,lineHeight:1,background:'var(--mint)',border:'2.5px solid var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',padding:'4px 12px 2px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-1.5deg)'}}>
            🦖 <b>Beta · бесплатно</b>
          </div>
        </div>
      </nav>

      <div style={{maxWidth:1280,margin:'0 auto',padding:'6px 28px 64px'}}>

        {/* Hero row */}
        <div style={{display:'grid',gridTemplateColumns:'1.4fr 1fr',gap:24,alignItems:'end',margin:'8px 0 24px'}}>
          <div>
            <h1 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:64,lineHeight:.95,margin:0}}>
              ⚡ <span style={{color:'var(--yellow-deep)',textShadow:'2px 3px 0 var(--ink)'}}>Фабрика</span> контента
            </h1>
            <div style={{color:'var(--ink-soft)',marginTop:8,fontSize:18,maxWidth:540}}>
              Автономный режим. Динозаврик сам ищет свежие видео по нишам, режет, оценивает виральность и складывает в очередь — пока ты пьёшь кофе.
            </div>
          </div>

          <div style={{background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'24px 28px 22px 26px / 26px 22px 28px 24px',boxShadow:'6px 8px 0 var(--ink)',padding:'18px 22px',transform:'rotate(.5deg)',display:'flex',gap:14,alignItems:'center',justifyContent:'space-between',position:'relative'}}>
            {/* Mini dino */}
            <svg style={{position:'absolute',right:-12,top:-22,width:60,height:64,transform:'rotate(8deg)'}} viewBox="0 0 100 110">
              <ellipse cx="50" cy="62" rx="32" ry="28" fill="#FFD166" stroke="#3A2E2A" strokeWidth="3"/>
              <path d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8" stroke="#3A2E2A" strokeWidth="3" fill="#FFD166" strokeLinejoin="round"/>
              <path d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round"/>
              <ellipse className="fact-eye" cx="38" cy="56" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
              <circle cx="40" cy="58" r="2.5" fill="#3A2E2A"/>
              <path d="M28 70 q 8 6 16 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
            </svg>
            <div>
              <div style={{fontFamily:'"Caveat",cursive',fontSize:28,lineHeight:1}}>{factoryOn ? 'Фабрика работает' : 'Фабрика остановлена'}</div>
              <div style={{color:'var(--ink-soft)',fontSize:15,marginTop:2}}>
                {scheduler?.jobs?.[0]?.next_run ? `следующий запуск: ${new Date(scheduler.jobs[0].next_run).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}` : 'статус неизвестен'}
              </div>
            </div>
            <div onClick={() => setFactoryOn(x=>!x)} style={{width:88,height:46,borderRadius:30,background:factoryOn?'var(--mint)':'#fff',border:'3px solid var(--ink)',boxShadow:'3px 4px 0 var(--ink)',position:'relative',cursor:'pointer',flexShrink:0}}>
              <div style={{position:'absolute',top:3,left:factoryOn?43:3,width:34,height:34,borderRadius:'50%',background:'#fff',border:'2.5px solid var(--ink)',boxShadow:'1px 2px 0 var(--ink)',transition:'left .18s ease'}}></div>
              <span style={{position:'absolute',top:'50%',transform:'translateY(-50%)',left:10,fontFamily:'"Caveat",cursive',fontSize:18,lineHeight:1,display:factoryOn?'block':'none'}}>ON</span>
              <span style={{position:'absolute',top:'50%',transform:'translateY(-50%)',right:10,fontFamily:'"Caveat",cursive',fontSize:18,lineHeight:1,color:'var(--ink-soft)',display:factoryOn?'none':'block'}}>OFF</span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:18,marginBottom:28}}>
          {[
            {lbl:'Найдено видео',num:stats?.total_discovered??0,extra:`за 24ч +${stats?.total_discovered??0}`,bg:'var(--cream-2)',rot:'-.6deg'},
            {lbl:'Готовых клипов',num:stats?.total_clips??0,extra:`за 24ч +${stats?.total_clips??0}`,bg:'#FFE0E6',rot:'.4deg'},
            {lbl:'В очереди',num:stats?.pending_count??0,extra:'~ ожидает обработки',bg:'#E5F5EE',rot:'-.3deg'},
            {lbl:'🔥 На обработке',num:stats?.processing_count??0,extra:`ошибок: ${stats?.failed_count??0}`,bg:'#EEE5F5',rot:'.5deg'},
          ].map((s,i) => (
            <div key={i} style={{background:s.bg,border:'3px solid var(--ink)',borderRadius:'22px 26px 20px 24px / 20px 24px 26px 22px',boxShadow:'5px 6px 0 var(--ink)',padding:'18px 20px 16px',transform:`rotate(${s.rot})`}}>
              <div style={{fontFamily:'"Patrick Hand SC",sans-serif',letterSpacing:'1.2px',textTransform:'uppercase',fontSize:13,color:'var(--ink-soft)'}}>{s.lbl}</div>
              <div style={{fontFamily:'"Caveat",cursive',fontSize:60,lineHeight:1,marginTop:4}}>{loading?'…':s.num}</div>
              <div style={{fontSize:15,color:'var(--ink-soft)',marginTop:2}}>{s.extra}</div>
            </div>
          ))}
        </div>

        {/* Performance chart — 7 days */}
        <div style={{border:'3px solid var(--ink)',boxShadow:'4px 5px 0 var(--ink)',borderRadius:'22px 26px 20px 24px / 20px 24px 26px 22px',padding:'20px 22px',marginBottom:24,background:'var(--paper)'}}>
          <h2 style={{fontFamily:'"Caveat",cursive',fontSize:32,margin:'0 0 4px'}}>Производительность · 7 дней</h2>
          <div style={{color:'var(--ink-soft)',fontSize:15,marginBottom:14}}>Сколько клипов в день успеваем сделать.</div>

          <div style={{overflowX:'auto'}}>
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              width={svgWidth}
              height={svgHeight}
              style={{display:'block',fontFamily:'"Patrick Hand",sans-serif'}}
            >
              {/* Bars */}
              {perfData.map((d, i) => {
                const x = barX(i)
                const h = barH(d.clips)
                const y = barY(d.clips)
                const fill = d.isWeekend ? '#FF8FA3' : '#FFD166'
                return (
                  <g key={d.day}>
                    <rect
                      x={x} y={y} width={barWidth} height={h}
                      fill={fill} stroke="#3A2E2A" strokeWidth="2"
                      rx="4" ry="4"
                    />
                    {/* Count label above bar */}
                    <text
                      x={x + barWidth / 2} y={y - 5}
                      textAnchor="middle"
                      fontSize="13"
                      fill="#3A2E2A"
                      fontFamily='"Patrick Hand",sans-serif'
                    >
                      {d.clips}
                    </text>
                    {/* Day label below bar */}
                    <text
                      x={x + barWidth / 2}
                      y={svgHeight - 4}
                      textAnchor="middle"
                      fontSize="13"
                      fill="#6B574F"
                      fontFamily='"Patrick Hand",sans-serif'
                    >
                      {d.day}
                    </text>
                  </g>
                )
              })}

              {/* Dashed trend line connecting bar tops */}
              <polyline
                points={trendPoints}
                fill="none"
                stroke="#3A2E2A"
                strokeWidth="2"
                strokeDasharray="4 5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>

          {/* Legend */}
          <div style={{display:'flex',gap:18,marginTop:12,fontSize:15,color:'var(--ink-soft)',flexWrap:'wrap',alignItems:'center'}}>
            <span>
              <span style={{display:'inline-block',width:12,height:12,background:'#FFD166',border:'2px solid var(--ink)',verticalAlign:'middle',marginRight:4}}></span>
              будни
            </span>
            <span>
              <span style={{display:'inline-block',width:12,height:12,background:'#FF8FA3',border:'2px solid var(--ink)',verticalAlign:'middle',marginRight:4}}></span>
              выходные
            </span>
            <span style={{marginLeft:'auto'}}>
              Всего: <b style={{color:'var(--ink)'}}>73</b> клипа
            </span>
          </div>
        </div>

        {/* Schedule — today */}
        <div style={{border:'3px solid var(--ink)',boxShadow:'4px 5px 0 var(--ink)',borderRadius:'22px 26px 20px 24px / 20px 24px 26px 22px',padding:'20px 22px',marginBottom:24,background:'var(--paper)'}}>
          <h2 style={{fontFamily:'"Caveat",cursive',fontSize:32,margin:'0 0 4px'}}>Расписание · сегодня</h2>
          <div style={{color:'var(--ink-soft)',fontSize:15,marginBottom:14}}>Динозаврик отдыхает с 02:00 до 06:00</div>

          {/* 24-hour grid — 8 columns */}
          <div style={{display:'grid',gridTemplateColumns:'repeat(8,1fr)',gap:6}}>
            {Array.from({length:24},(_,h) => {
              const state = HOUR_STATES[h]
              const st = hourStateStyle[state]
              const emoji = hourEmoji[state]
              return (
                <div
                  key={h}
                  style={{
                    border:'2.5px solid var(--ink)',
                    borderRadius:8,
                    boxShadow:'1px 2px 0 var(--ink)',
                    background:st.background,
                    color:st.color,
                    display:'flex',
                    flexDirection:'column',
                    alignItems:'center',
                    justifyContent:'center',
                    padding:'6px 2px',
                    gap:2,
                  }}
                >
                  <span style={{fontSize:16,lineHeight:1}}>{emoji}</span>
                  <span style={{fontFamily:'"Caveat",cursive',fontSize:16,lineHeight:1}}>
                    {String(h).padStart(2,'0')}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Footer note + legend */}
          <div style={{marginTop:10,fontSize:14,color:'var(--ink-soft)'}}>
            Динозаврик отдыхает с 02:00 до 06:00
          </div>
          <div style={{display:'flex',gap:14,marginTop:10,fontSize:15,color:'var(--ink-soft)',flexWrap:'wrap',alignItems:'center'}}>
            <span>🔥 пик</span>
            <span>⚡ работаем</span>
            <span>💤 отдых</span>
            <span>📋 план</span>
          </div>
        </div>

        {/* Niches + Live feed */}
        <div style={{display:'grid',gridTemplateColumns:'1.05fr 1.4fr',gap:24,alignItems:'start'}}>
          {/* Niches */}
          <div style={{background:'var(--paper)',border:'3px solid var(--ink)',boxShadow:'6px 8px 0 var(--ink)',padding:'22px 24px',borderRadius:'28px 24px 30px 22px / 24px 28px 22px 30px',transform:'rotate(-.4deg)'}}>
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:32,margin:0}}>Ниши, которые ищем</h2>
            <div style={{color:'var(--ink-soft)',fontSize:15,marginBottom:14}}>Кликай, чтобы включить или отключить.</div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
              {niche_display_list.map(n => (
                <div key={n.key} onClick={() => toggleNiche(n.key)} style={{display:'flex',alignItems:'center',gap:10,background:n.on?'var(--mint)':'#fff',border:'2.5px solid var(--ink)',borderRadius:'14px 18px 12px 16px / 16px 12px 18px 14px',boxShadow:'2px 3px 0 var(--ink)',padding:'8px 12px 6px',cursor:'pointer',transition:'transform .12s ease'}}>
                  <span style={{fontSize:22}}>{n.ico}</span>
                  <span style={{fontFamily:'"Caveat",cursive',fontSize:22,lineHeight:1}}>{n.label}</span>
                  <span style={{marginLeft:'auto',fontFamily:'"Caveat",cursive',fontSize:18,color:n.on?'var(--ink)':'var(--ink-soft)'}}>{n.cnt}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Live feed */}
          <div style={{background:'var(--paper)',border:'3px solid var(--ink)',boxShadow:'6px 8px 0 var(--ink)',padding:'22px 24px',borderRadius:'24px 30px 22px 28px / 28px 24px 30px 22px',transform:'rotate(.3deg)'}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:6}}>
              <h2 style={{fontFamily:'"Caveat",cursive',fontSize:32,margin:0}}>Очередь обработки</h2>
              <span style={{color:'var(--ink-soft)',fontSize:15,display:'inline-flex',alignItems:'center',gap:6}}>
                <span style={{width:8,height:8,borderRadius:'50%',background:'var(--pink-deep)',display:'inline-block',animation:'factPulse 1.4s infinite'}}></span>
                {autoRefresh ? 'live' : 'пауза'}
              </span>
            </div>
            <div style={{color:'var(--ink-soft)',fontSize:15,marginBottom:14}}>Последние 20 видео в конвейере.</div>

            <div className="fact-feed" style={{display:'grid',gap:12,maxHeight:520,overflowY:'auto'}}>
              {loading && <div style={{fontFamily:'"Caveat",cursive',fontSize:22,color:'var(--ink-soft)',textAlign:'center',padding:20}}>Загружаем…</div>}
              {!loading && discoveries.length === 0 && (
                <div style={{fontFamily:'"Caveat",cursive',fontSize:22,color:'var(--ink-soft)',textAlign:'center',padding:20}}>Очередь пуста 🦖</div>
              )}
              {discoveries.map(item => {
                const st = statusDot(item.status)
                return (
                  <div key={item.id} style={{display:'flex',alignItems:'center',gap:12,background:'#fff',border:'2.5px solid var(--ink)',borderRadius:'16px 20px 14px 18px / 18px 14px 20px 16px',boxShadow:'3px 4px 0 var(--ink)',padding:'10px 14px 8px'}}>
                    <span style={{width:10,height:10,borderRadius:'50%',flexShrink:0,border:'2px solid var(--ink)'}} className={`fact-dot-${st.type}`}></span>
                    <span style={{fontFamily:'"Caveat",cursive',fontSize:18,color:'var(--ink-soft)',flexShrink:0,minWidth:54}}>
                      {new Date(item.discovered_at).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}
                    </span>
                    <span style={{flex:1,lineHeight:1.2,fontSize:16}}>
                      <b style={{fontFamily:'"Caveat",cursive',fontSize:20,fontWeight:'normal'}}>{item.status === 'complete' ? 'готов' : item.status === 'pending' ? 'в очереди' : item.status}</b>
                      {' · '}
                      <a href={item.youtube_url} target="_blank" rel="noopener noreferrer" style={{color:'var(--pink-deep)',textDecoration:'underline'}}>{item.youtube_video_id}</a>
                      {' · '}{item.niche} · {fmtDuration(item.duration_seconds)}
                    </span>
                    <span style={{flexShrink:0,fontFamily:'"Caveat",cursive',fontSize:18,padding:'2px 10px 0',border:'2px solid var(--ink)',borderRadius:'10px 14px 8px 12px / 12px 8px 14px 10px',boxShadow:'1px 2px 0 var(--ink)',background:st.type==='done'?'var(--mint)':st.type==='run'?'var(--yellow)':st.type==='find'?'var(--pink)':'var(--lilac)',color:st.type==='find'?'#fff':'inherit'}}>
                      {st.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Scheduler status */}
        {scheduler && (
          <div style={{marginTop:28,background:'var(--paper)',border:'3px solid var(--ink)',boxShadow:'6px 8px 0 var(--ink)',padding:'22px 24px',borderRadius:'28px 24px 30px 22px / 24px 28px 22px 30px',transform:'rotate(-.2deg)'}}>
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:32,margin:'0 0 14px'}}>
              Планировщик · {scheduler.running ? '🟢 работает' : '🔴 остановлен'}
            </h2>
            <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))',gap:12}}>
              {scheduler.jobs.map(job => (
                <div key={job.id} style={{background:'#fff',border:'2.5px solid var(--ink)',borderRadius:'14px 18px 12px 16px',boxShadow:'2px 3px 0 var(--ink)',padding:'12px 16px'}}>
                  <div style={{fontFamily:'"Caveat",cursive',fontSize:22,lineHeight:1}}>{job.name}</div>
                  <div style={{fontSize:14,color:'var(--ink-soft)',marginTop:4}}>
                    Следующий запуск: {job.next_run ? new Date(job.next_run).toLocaleString('ru-RU') : 'не запланирован'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
