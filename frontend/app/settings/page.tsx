'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface UserProfile {
  email: string
  name?: string
  plan?: string
}

interface TelegramSettings {
  telegram_chat_id?: string
  telegram_enabled?: boolean
}

export default function SettingsPage() {
  const [user, setUser] = useState<UserProfile | null>(null)
  const [tgSettings, setTgSettings] = useState<TelegramSettings>({})
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [pwdMsg, setPwdMsg] = useState('')
  const [pwdErr, setPwdErr] = useState(false)
  const [toast, setToast] = useState('')
  const [notifyPressed, setNotifyPressed] = useState(false)
  const [activeSection, setActiveSection] = useState('account')
  const [notifToggles, setNotifToggles] = useState([true, true, false, false])

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get('/auth/me')
        setUser(res.data)
      } catch {}
      try {
        const res = await api.get('/settings')
        setTgSettings(res.data || {})
      } catch {}
      setNotifyPressed(localStorage.getItem('cg_notify_integrations') === '1')
    }
    load()
  }, [])

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(''), 2200)
  }

  const handleChangePassword = async () => {
    setPwdMsg('')
    setPwdErr(false)
    if (!oldPassword || !newPassword) {
      setPwdErr(true)
      setPwdMsg('Заполни оба поля')
      return
    }
    try {
      await api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword })
      setPwdMsg('Пароль изменён 🦖')
      setOldPassword('')
      setNewPassword('')
    } catch (e: any) {
      setPwdErr(true)
      setPwdMsg(e?.response?.data?.detail || 'Ошибка — проверь старый пароль')
    }
  }

  const handleDeleteAccount = async () => {
    const confirmed = window.confirm('Удалить аккаунт? Это нельзя откатить. Email освободится через 30 дней.')
    if (!confirmed) return
    try {
      await api.delete('/auth/account')
      window.location.href = '/'
    } catch (e: any) {
      showToast(e?.response?.data?.detail || 'Ошибка при удалении')
    }
  }

  const handleNotifyMe = () => {
    localStorage.setItem('cg_notify_integrations', '1')
    setNotifyPressed(true)
    showToast('Запомнили! Напишем первым 🦖')
  }

  const initials = user?.name ? user.name[0].toUpperCase() : user?.email?.[0]?.toUpperCase() ?? 'У'

  const sideLinks = [
    { id: 'account', label: 'Аккаунт', dot: 'var(--pink)' },
    { id: 'plan', label: 'Тариф', dot: 'var(--yellow)' },
    { id: 'integrations', label: 'Интеграции', dot: 'var(--mint)' },
    { id: 'notif', label: 'Уведомления', dot: 'var(--teal)' },
    { id: 'danger', label: 'Опасная зона', dot: 'var(--pink-deep)' },
  ]

  return (
    <>
      <style>{`
        .set-input{background:#fff;border:2.5px solid var(--ink);border-radius:14px 18px 12px 16px / 16px 12px 18px 14px;padding:9px 14px 7px;font-size:18px;font-family:"Patrick Hand",sans-serif;box-shadow:2px 3px 0 var(--ink);outline:none;min-width:220px;color:var(--ink)}
        .set-input:focus{box-shadow:3px 4px 0 var(--pink-deep);border-color:var(--pink-deep)}
        .set-btn{font-family:"Caveat",cursive;font-weight:700;font-size:22px;line-height:1;border:2.5px solid var(--ink);padding:8px 18px 6px;border-radius:18px 14px 20px 16px / 14px 18px 16px 20px;box-shadow:3px 4px 0 var(--ink);background:#fff;display:inline-flex;align-items:center;gap:6px;cursor:pointer;color:var(--ink)}
        .set-btn:hover{transform:translate(-2px,-2px) rotate(-1deg);box-shadow:5px 6px 0 var(--ink)}
        .set-btn.pink{background:var(--pink);color:#fff;text-shadow:1px 1px 0 rgba(58,46,42,.35)}
        .set-btn.yellow{background:var(--yellow)}
        .set-btn.danger{color:var(--pink-deep);border-color:var(--pink-deep)}
        .set-card{background:var(--paper);border:3px solid var(--ink);box-shadow:6px 8px 0 var(--ink);padding:24px 28px;border-radius:24px 28px 22px 26px / 22px 26px 28px 24px;margin-bottom:24px}
        .toggle-sw{position:relative;width:48px;height:28px;background:#fff;border:2.5px solid var(--ink);border-radius:16px;cursor:pointer;transition:background .2s;flex:none;display:inline-block}
        .toggle-sw.on{background:var(--mint)}
        .toggle-sw::after{content:"";position:absolute;top:1px;left:1px;width:20px;height:20px;border-radius:50%;background:var(--ink);transition:left .2s}
        .toggle-sw.on::after{left:23px}
        .ig-card{background:#fff;border:2.5px solid var(--ink);border-radius:16px 20px 14px 18px / 18px 14px 20px 16px;box-shadow:3px 4px 0 var(--ink);padding:14px 16px;display:flex;align-items:center;gap:12px;opacity:.78;background:repeating-linear-gradient(135deg,#fff 0 14px,#FFF8E5 14px 28px)}
        .soon-badge{display:inline-block;background:var(--lilac);color:var(--ink);border:2.5px solid var(--ink);box-shadow:2px 3px 0 var(--ink);border-radius:11px 14px 9px 13px / 13px 9px 14px 11px;padding:3px 11px 1px;font-family:"Caveat",cursive;font-size:18px;line-height:1;transform:rotate(-3deg);flex:none}
        @media (max-width:880px){.set-layout{grid-template-columns:1fr!important}}
      `}</style>

      <nav style={{maxWidth:1280,margin:'0 auto',padding:'18px 28px',display:'flex',justifyContent:'space-between',alignItems:'center',gap:24}}>
        <Link href="/" style={{display:'flex',alignItems:'center',gap:8,fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:30,color:'var(--ink)',textDecoration:'none'}}>
          <span style={{width:34,height:34,display:'grid',placeItems:'center',background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'14px 12px 16px 10px / 12px 14px 10px 16px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-4deg)'}}>
            <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/></svg>
          </span>
          Clips<span style={{color:'var(--yellow-deep)',textShadow:'1px 2px 0 var(--ink)'}}>Gold</span>
        </Link>
        <div style={{display:'inline-flex',alignItems:'center',gap:6,fontFamily:'"Caveat",cursive',fontSize:20,lineHeight:1,background:'var(--mint)',border:'2.5px solid var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',padding:'4px 12px 2px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-1.5deg)'}}>
          🦖 <b>Beta · бесплатно</b>
        </div>
      </nav>

      <div style={{maxWidth:1280,margin:'0 auto',padding:'0 28px 6px',display:'flex',alignItems:'center',gap:10,color:'var(--ink-soft)',fontSize:16}}>
        <Link href="/app" style={{color:'var(--ink-soft)',textDecoration:'none'}}>← Студия</Link>
        <span style={{opacity:.5}}>/</span>
        <span style={{color:'var(--ink)'}}>Настройки</span>
      </div>

      <div className="set-layout" style={{maxWidth:1280,margin:'0 auto',padding:'6px 28px 80px',display:'grid',gridTemplateColumns:'240px 1fr',gap:32}}>
        <div style={{gridColumn:'1/-1',marginBottom:8}}>
          <h1 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:60,lineHeight:1,margin:0}}>
            Настройки <span style={{color:'var(--yellow-deep)',textShadow:'2px 3px 0 var(--ink)'}}>динозаврика</span> 🦖
          </h1>
          <div style={{color:'var(--ink-soft)',fontSize:18,marginTop:4}}>Аккаунт, тарифы, интеграции, что-как-резать по умолчанию.</div>
        </div>

        {/* Sidebar */}
        <aside style={{position:'sticky',top:18,alignSelf:'start',display:'grid',gap:6}}>
          {sideLinks.map(l => (
            <a key={l.id} href={`#${l.id}`} onClick={() => setActiveSection(l.id)} style={{display:'flex',alignItems:'center',gap:10,fontFamily:'"Caveat",cursive',fontSize:24,lineHeight:1,padding:'10px 14px',border:'2.5px solid',borderColor:activeSection===l.id?'var(--ink)':'transparent',borderRadius:'14px 18px 12px 16px / 16px 12px 18px 14px',background:activeSection===l.id?'var(--paper)':'transparent',boxShadow:activeSection===l.id?'3px 4px 0 var(--ink)':'none',transform:activeSection===l.id?'rotate(-.6deg)':'none',textDecoration:'none',color:'var(--ink)'}}>
              <span style={{width:10,height:10,borderRadius:'50%',background:l.dot,flexShrink:0,display:'inline-block'}}></span>
              {l.label}
            </a>
          ))}
        </aside>

        <main>
          {/* ACCOUNT */}
          <section className="set-card" id="account">
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:34,lineHeight:1,margin:0}}>Аккаунт</h2>
            <div style={{color:'var(--ink-soft)',marginTop:2,fontSize:16}}>Email и смена пароля.</div>

            <div style={{display:'flex',alignItems:'center',gap:18,marginTop:12}}>
              <div style={{width:88,height:88,borderRadius:'50%',border:'3px solid var(--ink)',background:'var(--lilac)',display:'grid',placeItems:'center',fontFamily:'"Caveat",cursive',fontSize:48,fontWeight:700,boxShadow:'4px 5px 0 var(--ink)',transform:'rotate(-3deg)'}}>{initials}</div>
              <div>
                <div style={{fontFamily:'"Caveat",cursive',fontSize:26,lineHeight:1}}>{user?.name || user?.email || '—'}</div>
                <div style={{color:'var(--ink-soft)',fontSize:14,marginTop:4}}>{user?.email}</div>
                <div style={{marginTop:6,display:'inline-block',fontFamily:'"Caveat",cursive',fontSize:16,background:'var(--mint)',border:'2px solid var(--ink)',padding:'2px 10px',borderRadius:'8px 12px 8px 12px',boxShadow:'1px 2px 0 var(--ink)'}}>
                  {user?.plan || 'Beta · бесплатно'}
                </div>
              </div>
            </div>

            <div style={{marginTop:22}}>
              <div style={{fontFamily:'"Caveat",cursive',fontSize:22,marginBottom:10}}>Сменить пароль</div>
              <div style={{display:'flex',gap:14,flexWrap:'wrap',alignItems:'flex-end'}}>
                <label style={{display:'grid',gap:4}}>
                  <span style={{fontFamily:'"Patrick Hand SC",sans-serif',fontSize:13,letterSpacing:'1px',textTransform:'uppercase',color:'var(--ink-soft)'}}>Старый пароль</span>
                  <input className="set-input" type="password" value={oldPassword} onChange={e=>setOldPassword(e.target.value)} placeholder="••••••••" />
                </label>
                <label style={{display:'grid',gap:4}}>
                  <span style={{fontFamily:'"Patrick Hand SC",sans-serif',fontSize:13,letterSpacing:'1px',textTransform:'uppercase',color:'var(--ink-soft)'}}>Новый пароль</span>
                  <input className="set-input" type="password" value={newPassword} onChange={e=>setNewPassword(e.target.value)} placeholder="••••••••" />
                </label>
                <button className="set-btn yellow" onClick={handleChangePassword}>Сменить</button>
              </div>
              {pwdMsg && <div style={{marginTop:8,fontSize:15,color:pwdErr?'var(--pink-deep)':'#0a8a4f'}}>{pwdMsg}</div>}
            </div>
          </section>

          {/* PLAN */}
          <section className="set-card" id="plan">
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:34,lineHeight:1,margin:0}}>Тариф</h2>
            <div style={{display:'flex',alignItems:'center',gap:24,background:'linear-gradient(135deg,#FFE9B8 0%,#FFF3D6 60%,#B8E6CC 130%)',border:'3px dashed var(--ink)',borderRadius:'24px 30px 22px 28px / 22px 26px 30px 24px',padding:'22px 26px',marginTop:14,position:'relative',flexWrap:'wrap'}}>
              <div style={{flexShrink:0,transform:'rotate(-5deg)'}}>
                <svg viewBox="0 0 100 110" width="86" height="92">
                  <ellipse cx="50" cy="62" rx="32" ry="28" fill="#B8E6CC" stroke="#3A2E2A" strokeWidth="3"/>
                  <path d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8" stroke="#3A2E2A" strokeWidth="3" fill="#B8E6CC" strokeLinejoin="round"/>
                  <path d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round"/>
                  <ellipse cx="38" cy="56" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
                  <circle cx="40" cy="58" r="2.5" fill="#3A2E2A"/>
                  <path d="M28 70 q 8 6 16 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
                  <path d="M76 90 L86 100 M64 96 L70 106 M52 96 L52 106" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round"/>
                </svg>
              </div>
              <div style={{flex:1}}>
                <div style={{display:'inline-block',background:'var(--pink)',color:'#fff',border:'2.5px solid var(--ink)',boxShadow:'2px 3px 0 var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',padding:'3px 12px 1px',fontFamily:'"Caveat",cursive',fontSize:20,transform:'rotate(-2deg)',textShadow:'1px 1px 0 rgba(58,46,42,.35)',marginBottom:14}}>
                  🎉 ты в бете
                </div>
                <h3 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:30,lineHeight:1.35,margin:'0 0 14px'}}>
                  Сейчас все пользователи на <span style={{color:'var(--yellow-deep)',textShadow:'2px 2px 0 var(--ink)',display:'inline-block',padding:'0 2px'}}>Beta — бесплатно</span>
                </h3>
                <p style={{fontSize:16,color:'var(--ink-soft)',lineHeight:1.5,margin:'0 0 12px',maxWidth:520}}>Платные тарифы появятся после публичного релиза. До того момента — режь сколько хочется, динозаврик не против.</p>
                <div style={{display:'flex',gap:18,flexWrap:'wrap',fontSize:14,color:'var(--ink-soft)'}}>
                  <span>📅 действует до 31 декабря 2026</span>
                  <span>💌 за месяц до изменений напишем на email</span>
                </div>
              </div>
            </div>
          </section>

          {/* INTEGRATIONS */}
          <section className="set-card" id="integrations">
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:34,lineHeight:1,margin:0}}>Интеграции</h2>
            <div style={{color:'var(--ink-soft)',marginTop:2,fontSize:16}}>Пока публикуем по «скачай и закинь сам» — авто-постинг едет следом 🚂</div>

            <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:12,marginTop:14}}>
              {[
                {name:'TikTok',sub:'авто-постинг в один клик',icoBg:'#000',ico:<svg width="22" height="22" viewBox="0 0 24 24" fill="#fff"><path d="M19.6 6.3a5.2 5.2 0 0 1-3.6-1.5v8.6a5 5 0 1 1-5-5h.5v2.5h-.5a2.5 2.5 0 1 0 2.5 2.5V2h2.5a5.2 5.2 0 0 0 3.6 4.3z"/></svg>},
                {name:'YouTube Shorts',sub:'авто-постинг в один клик',icoBg:'#FF0033',ico:<svg width="22" height="16" viewBox="0 0 24 16" fill="#fff"><rect width="24" height="16" rx="3" fill="#FF0033"/><path d="M10 5 L16 8 L10 11 Z" fill="#fff"/></svg>},
                {name:'Instagram Reels',sub:'авто-постинг в один клик',icoBg:'linear-gradient(45deg,#feda75,#fa7e1e,#d62976,#962fbf)',ico:<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1.2" fill="#fff"/></svg>},
                {name:'X (Twitter)',sub:'авто-постинг в один клик',icoBg:'#000',ico:<svg width="22" height="20" viewBox="0 0 24 22" fill="#fff"><path d="M14.4 9.3 23 0h-2L13.5 8.1 7.5 0H0l9 12.5L0 22h2l8-9 6.5 9H24L14.4 9.3z"/></svg>},
              ].map(ig => (
                <div key={ig.name} className="ig-card">
                  <div style={{width:42,height:42,borderRadius:12,border:'2.5px solid var(--ink)',display:'grid',placeItems:'center',flexShrink:0,background:ig.icoBg}}>{ig.ico}</div>
                  <div style={{flex:1}}>
                    <div style={{fontFamily:'"Caveat",cursive',fontSize:24,lineHeight:1}}>{ig.name}</div>
                    <div style={{fontSize:14,color:'var(--ink-soft)',marginTop:2}}>{ig.sub}</div>
                  </div>
                  <span className="soon-badge">Скоро</span>
                </div>
              ))}
            </div>

            <div style={{marginTop:14,display:'flex',justifyContent:'space-between',alignItems:'center',gap:14,flexWrap:'wrap',background:'var(--cream)',border:'2.5px solid var(--ink)',borderRadius:'16px 20px 14px 18px / 18px 14px 20px 16px',padding:'10px 16px 9px',fontFamily:'"Caveat",cursive',fontSize:22}}>
              <span>🔔 Хочешь, дёрнем тебя первым, как только заработает?</span>
              <button className="set-btn yellow" onClick={handleNotifyMe} disabled={notifyPressed} style={{opacity:notifyPressed ? 0.7 : 1}}>
                {notifyPressed ? 'Окей, ждём 🦖' : 'Уведомить меня'}
              </button>
            </div>
          </section>

          {/* NOTIF */}
          <section className="set-card" id="notif">
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:34,lineHeight:1,margin:0}}>Уведомления</h2>
            <div style={{color:'var(--ink-soft)',marginTop:2,fontSize:16}}>Telegram и email — когда писать.</div>

            {tgSettings.telegram_chat_id ? (
              <div style={{marginTop:14,padding:'12px 16px',background:'var(--mint)',border:'2.5px solid var(--ink)',borderRadius:'14px 18px 12px 16px',boxShadow:'2px 3px 0 var(--ink)',fontSize:16}}>
                ✅ Telegram подключён · chat_id: {tgSettings.telegram_chat_id}
              </div>
            ) : (
              <div style={{marginTop:14,padding:'12px 16px',background:'var(--cream-2)',border:'2.5px dashed var(--ink-soft)',borderRadius:'14px 18px 12px 16px',fontSize:15,color:'var(--ink-soft)'}}>
                Telegram не подключён. Напиши боту <a href="https://t.me/ClipsGoldBot" target="_blank" rel="noopener" style={{color:'var(--pink-deep)'}}>@ClipsGoldBot</a> команду /start, чтобы получать уведомления о готовых клипах.
              </div>
            )}

            {[
              {label:'Готов клип',sub:'— основное, рекомендуем'},
              {label:'Завершилась пачка из Фабрики',sub:'— раз в день'},
              {label:'Новые фичи и обновления',sub:''},
              {label:'Маркетинговые письма',sub:''},
            ].map((item,i) => (
              <div key={i} style={{display:'flex',alignItems:'center',gap:14,marginTop:14}}>
                <div className={`toggle-sw${notifToggles[i]?' on':''}`} onClick={() => setNotifToggles(t => t.map((v,j) => j===i ? !v : v))}></div>
                <div>
                  <span style={{fontFamily:'"Caveat",cursive',fontSize:22,lineHeight:1}}>{item.label}</span>
                  {item.sub && <small style={{color:'var(--ink-soft)',marginLeft:4,fontSize:14}}>{item.sub}</small>}
                </div>
              </div>
            ))}
          </section>

          {/* DANGER */}
          <section className="set-card" id="danger" style={{borderColor:'var(--pink-deep)',background:'#FFF5F7'}}>
            <h2 style={{fontFamily:'"Caveat",cursive',fontSize:34,lineHeight:1,margin:0,color:'var(--pink-deep)'}}>Опасная зона 🦖</h2>
            <div style={{color:'var(--ink-soft)',marginTop:2,fontSize:16}}>Динозаврик предупреждает: эти штуки нельзя откатить.</div>

            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:18,gap:14,flexWrap:'wrap'}}>
              <div>
                <div style={{fontFamily:'"Caveat",cursive',fontSize:22,lineHeight:1}}>Удалить аккаунт</div>
                <div style={{color:'var(--ink-soft)',fontSize:14}}>Email освободится через 30 дней.</div>
              </div>
              <button className="set-btn danger" onClick={handleDeleteAccount}>Удалить</button>
            </div>
          </section>
        </main>
      </div>

      {toast && (
        <div style={{position:'fixed',left:'50%',bottom:34,transform:'translateX(-50%) rotate(-1deg)',background:'var(--mint)',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 18px 16px 22px 20px',boxShadow:'5px 6px 0 var(--ink)',padding:'12px 22px 10px',fontFamily:'"Caveat",cursive',fontSize:24,zIndex:50,whiteSpace:'nowrap'}}>
          {toast}
        </div>
      )}
    </>
  )
}
