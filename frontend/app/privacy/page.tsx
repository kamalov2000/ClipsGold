import Link from 'next/link'

export const metadata = {
  title: 'Политика конфиденциальности · ClipsGold',
}

export default function PrivacyPage() {
  return (
    <div style={{margin:0,background:'var(--cream)',color:'var(--ink)',fontFamily:'"Patrick Hand",sans-serif',fontSize:18,lineHeight:1.55,backgroundImage:'radial-gradient(circle at 12% 14%, rgba(255,209,102,.35) 0 2px, transparent 3px),radial-gradient(circle at 88% 22%, rgba(255,143,163,.32) 0 2px, transparent 3px),radial-gradient(circle at 30% 80%, rgba(125,211,192,.32) 0 2px, transparent 3px),radial-gradient(circle at 75% 88%, rgba(201,182,228,.32) 0 2px, transparent 3px)',backgroundSize:'520px 520px',minHeight:'100vh'}}>

      <nav style={{position:'sticky',top:0,zIndex:5,background:'rgba(255,243,214,.92)',backdropFilter:'blur(6px)',borderBottom:'3px solid var(--ink)',display:'flex',justifyContent:'space-between',alignItems:'center',padding:'14px 28px',fontFamily:'"Caveat",cursive'}}>
        <Link href="/" style={{display:'flex',alignItems:'center',gap:8,textDecoration:'none',color:'var(--ink)',fontSize:30,lineHeight:1}}>
          <span style={{display:'inline-grid',placeItems:'center',width:34,height:34,background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'10px 14px 8px 12px',boxShadow:'3px 3px 0 var(--ink)',transform:'rotate(-3deg)'}}>
            <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/></svg>
          </span>
          Clips<span style={{color:'var(--yellow-deep)',textShadow:'1.5px 1.5px 0 var(--ink)'}}>Gold</span>
        </Link>
        <Link href="/" style={{fontFamily:'"Caveat",cursive',fontSize:22,color:'var(--ink)',textDecoration:'none'}}>← на главную</Link>
      </nav>

      <div style={{padding:'14px 28px 0',fontFamily:'"Caveat",cursive',fontSize:20,color:'var(--ink-soft)'}}>
        <Link href="/" style={{color:'var(--ink)',textDecoration:'none',borderBottom:'2px wavy var(--pink-deep)'}}>главная</Link>
        {' '}<span style={{opacity:.5}}>/</span>{' '}
        <span style={{color:'var(--ink)'}}>политика конфиденциальности</span>
      </div>

      <div style={{maxWidth:780,margin:'24px auto 80px',padding:'0 28px'}}>
        <div style={{background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'32px 28px 34px 30px / 28px 32px 30px 34px',boxShadow:'8px 10px 0 var(--ink)',padding:'30px 34px',transform:'rotate(-.4deg)',position:'relative'}}>
          <svg style={{position:'absolute',top:-22,right:-12,transform:'rotate(8deg)'}} width="64" height="68" viewBox="0 0 100 110">
            <ellipse cx="50" cy="62" rx="32" ry="28" fill="#C9B6E4" stroke="#3A2E2A" strokeWidth="3"/>
            <path d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8" stroke="#3A2E2A" strokeWidth="3" fill="#C9B6E4" strokeLinejoin="round"/>
            <path d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round"/>
            <ellipse cx="38" cy="56" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
            <circle cx="40" cy="58" r="2.5" fill="#3A2E2A"/>
            <path d="M28 70 q 8 6 16 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
            <path d="M76 90 L86 100 M64 96 L70 106 M52 96 L52 106" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <div style={{display:'inline-block',background:'var(--lilac)',color:'var(--ink)',border:'2.5px solid var(--ink)',boxShadow:'2px 3px 0 var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',padding:'3px 12px 1px',fontFamily:'"Caveat",cursive',fontSize:18,transform:'rotate(-2deg)',marginBottom:10}}>
            📜 простыми словами
          </div>
          <h1 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:62,lineHeight:1.05,margin:0}}>
            Политика <span style={{color:'var(--yellow-deep)',textShadow:'2px 2px 0 var(--ink)'}}>конфиденциальности</span>
          </h1>
          <div style={{marginTop:8,color:'var(--ink-soft)',fontSize:15}}>обновлено 1 ноября 2026 · версия 0.4 (бета)</div>
        </div>

        <div style={{marginTop:18}}>
          <div style={{marginTop:14,padding:'14px 18px',background:'var(--cream-2)',border:'2.5px dashed var(--ink)',borderRadius:'18px 22px 16px 20px / 16px 22px 18px 20px',fontFamily:'"Caveat",cursive',fontSize:22,color:'var(--ink)',display:'flex',gap:12,alignItems:'flex-start'}}>
            <svg style={{flexShrink:0,marginTop:2}} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3A2E2A" strokeWidth="2.4" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 8 v5"/><circle cx="12" cy="16.5" r="1.2" fill="#3A2E2A"/></svg>
            Это рабочий черновик на время беты. Финальную редакцию подготовим вместе с юристом до публичного релиза — и пришлём ссылку на email за 30 дней до изменений.
          </div>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>1. Что мы собираем</h2>
          <ul style={{paddingLeft:22,margin:'8px 0'}}>
            <li style={{margin:'4px 0'}}><b>Аккаунт:</b> email и пароль (хешируем, в открытом виде не храним).</li>
            <li style={{margin:'4px 0'}}><b>Контент:</b> видео и ссылки, которые ты загружаешь, плюс полученные клипы.</li>
            <li style={{margin:'4px 0'}}><b>Технические данные:</b> IP-адрес, тип устройства, браузер, время заходов — стандартные журналы сервера.</li>
            <li style={{margin:'4px 0'}}><b>Аналитика:</b> агрегированные события вида «нажал кнопку», «дошёл до шага N» — без привязки к личности.</li>
          </ul>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>2. Зачем мы это собираем</h2>
          <ul style={{paddingLeft:22,margin:'8px 0'}}>
            <li style={{margin:'4px 0'}}>Чтобы порезать твоё видео и отдать тебе клипы — это основная функция сервиса.</li>
            <li style={{margin:'4px 0'}}>Чтобы понимать, что ломается, и чинить.</li>
            <li style={{margin:'4px 0'}}>Чтобы изредка написать тебе письмо — только по делу: что-то сломалось, что-то новое, изменения тарифов.</li>
          </ul>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>3. Чего мы НЕ делаем</h2>
          <ul style={{paddingLeft:22,margin:'8px 0'}}>
            <li style={{margin:'4px 0'}}>Не продаём твои данные третьим лицам.</li>
            <li style={{margin:'4px 0'}}>Не используем твои видео для тренировки чужих моделей.</li>
            <li style={{margin:'4px 0'}}>Не показываем твои черновики никому, кроме тебя (публичная ссылка /share — только если ты её сам сгенерировал).</li>
          </ul>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>4. Где это всё хранится</h2>
          <p style={{margin:'8px 0'}}>Серверы — Россия, дата-центр в Москве. Видео-файлы шифруются на диске. Бэкапы делаются раз в сутки и хранятся 14 дней.</p>
          <p style={{margin:'8px 0'}}>Исходные ролики автоматически удаляются через <b>14 дней</b> после рендера. Готовые клипы остаются в твоей истории, пока ты их сам не удалишь.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>5. Куки и счётчики</h2>
          <p style={{margin:'8px 0'}}>Используем строго необходимые куки (сессия, защита от CSRF). Аналитика — собственная, без сторонних трекеров. Никакого Facebook Pixel, Google Analytics и иже с ними.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>6. Твои права</h2>
          <ul style={{paddingLeft:22,margin:'8px 0'}}>
            <li style={{margin:'4px 0'}}>Запросить копию всех своих данных — напиши на <a href="mailto:hello@clipsgold.ru" style={{color:'var(--pink-deep)'}}>hello@clipsgold.ru</a>.</li>
            <li style={{margin:'4px 0'}}>Удалить аккаунт целиком — кнопка в <Link href="/settings#danger" style={{color:'var(--pink-deep)'}}>Настройках → Опасная зона</Link>. Удаляем всё и сразу.</li>
            <li style={{margin:'4px 0'}}>Поправить email или имя — там же, в <Link href="/settings" style={{color:'var(--pink-deep)'}}>Настройках</Link>.</li>
          </ul>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>7. Дети</h2>
          <p style={{margin:'8px 0'}}>ClipsGold не предназначен для пользователей младше 14 лет. Если тебе меньше — попроси родителей зарегистрироваться вместо тебя.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>8. Как мы меняем эту политику</h2>
          <p style={{margin:'8px 0'}}>Если что-то существенно меняется — пишем тебе на email за 30 дней. Дата вверху страницы всегда отражает последнее изменение.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>9. Связаться</h2>
          <p style={{margin:'8px 0'}}>Вопросы и жалобы: <a href="mailto:privacy@clipsgold.ru" style={{color:'var(--pink-deep)'}}>privacy@clipsgold.ru</a>. Отвечаем в рабочие дни в течение 48 часов.</p>
        </div>

        <div style={{display:'flex',gap:14,flexWrap:'wrap',marginTop:14,fontFamily:'"Caveat",cursive',fontSize:22}}>
          <Link href="/terms" style={{color:'var(--ink)',textDecoration:'none',borderBottom:'2px wavy var(--pink-deep)',paddingBottom:1}}>Условия использования →</Link>
          <Link href="/offer" style={{color:'var(--ink)',textDecoration:'none',borderBottom:'2px wavy var(--pink-deep)',paddingBottom:1}}>Публичная оферта →</Link>
        </div>

        <div style={{marginTop:30,display:'flex',gap:12,flexWrap:'wrap',fontFamily:'"Caveat",cursive',fontSize:22}}>
          <Link href="/" style={{display:'inline-flex',alignItems:'center',gap:8,background:'var(--paper)',color:'var(--ink)',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 16px 22px 18px 22px',padding:'8px 18px 6px',boxShadow:'4px 5px 0 var(--ink)',textDecoration:'none'}}>← на главную</Link>
          <Link href="/register" style={{display:'inline-flex',alignItems:'center',gap:8,background:'var(--pink)',color:'#fff',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 16px 22px 18px 22px',padding:'8px 18px 6px',boxShadow:'4px 5px 0 var(--ink)',textDecoration:'none',textShadow:'1px 1px 0 rgba(58,46,42,.35)'}}>Создать аккаунт 🦖</Link>
        </div>
      </div>
    </div>
  )
}
