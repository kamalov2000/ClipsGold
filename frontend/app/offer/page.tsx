import Link from 'next/link'

export const metadata = {
  title: 'Публичная оферта · ClipsGold',
}

export default function OfferPage() {
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
        <span style={{color:'var(--ink)'}}>публичная оферта</span>
      </div>

      <div style={{maxWidth:780,margin:'24px auto 80px',padding:'0 28px'}}>
        <div style={{background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'32px 28px 34px 30px / 28px 32px 30px 34px',boxShadow:'8px 10px 0 var(--ink)',padding:'30px 34px',transform:'rotate(-.4deg)',position:'relative'}}>
          <svg style={{position:'absolute',top:-22,right:-12,transform:'rotate(8deg)'}} width="64" height="68" viewBox="0 0 100 110">
            <ellipse cx="50" cy="62" rx="32" ry="28" fill="#FFD166" stroke="#3A2E2A" strokeWidth="3"/>
            <path d="M22 50 q -10 -8 -4 -22 q 6 -10 14 -8" stroke="#3A2E2A" strokeWidth="3" fill="#FFD166" strokeLinejoin="round"/>
            <path d="M30 38 L36 28 L42 36 M48 32 L54 22 L60 32 M66 36 L72 28 L78 36" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="2.5" strokeLinejoin="round"/>
            <ellipse cx="38" cy="56" rx="6" ry="7" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
            <circle cx="40" cy="58" r="2.5" fill="#3A2E2A"/>
            <path d="M28 70 q 8 6 16 0" stroke="#3A2E2A" strokeWidth="2.5" fill="none" strokeLinecap="round"/>
            <path d="M76 90 L86 100 M64 96 L70 106 M52 96 L52 106" stroke="#3A2E2A" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
          <div style={{display:'inline-block',background:'var(--yellow)',color:'var(--ink)',border:'2.5px solid var(--ink)',boxShadow:'2px 3px 0 var(--ink)',borderRadius:'12px 16px 10px 14px / 14px 10px 16px 12px',padding:'3px 12px 1px',fontFamily:'"Caveat",cursive',fontSize:18,transform:'rotate(-2deg)',marginBottom:10}}>
            📄 договор-оферта
          </div>
          <h1 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:62,lineHeight:1.05,margin:0}}>
            Публичная <span style={{color:'var(--yellow-deep)',textShadow:'2px 2px 0 var(--ink)'}}>оферта</span>
          </h1>
          <div style={{marginTop:8,color:'var(--ink-soft)',fontSize:15}}>обновлено 1 ноября 2026 · версия 0.3 (бета)</div>
        </div>

        <div style={{marginTop:18}}>
          <div style={{marginTop:14,padding:'14px 18px',background:'var(--cream-2)',border:'2.5px dashed var(--ink)',borderRadius:'18px 22px 16px 20px / 16px 22px 18px 20px',fontFamily:'"Caveat",cursive',fontSize:22,color:'var(--ink)',display:'flex',gap:12,alignItems:'flex-start'}}>
            <svg style={{flexShrink:0,marginTop:2}} width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3A2E2A" strokeWidth="2.4" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 8 v5"/><circle cx="12" cy="16.5" r="1.2" fill="#3A2E2A"/></svg>
            Это рабочий черновик. Финальная редакция оферты появится одновременно с подключением платных тарифов и платёжного шлюза.
          </div>

          <div style={{background:'var(--cream-2)',border:'3px solid var(--ink)',borderRadius:'24px 28px 22px 26px / 22px 26px 28px 24px',boxShadow:'5px 6px 0 var(--ink)',padding:'24px 28px',margin:'18px 0',textAlign:'center',transform:'rotate(.4deg)'}}>
            <div style={{fontFamily:'"Caveat",cursive',fontSize:42,lineHeight:1.05}}>Сейчас услуги бесплатные 🦖</div>
            <div style={{marginTop:6,color:'var(--ink-soft)',fontSize:17}}>Пока мы в бете — никаких платежей нет, и сама оферта ещё не вступила в силу. Эта страница нужна, чтобы ты заранее видел, по каким правилам мы заработаем, когда откроемся всем.</div>
          </div>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>1. Стороны</h2>
          <p style={{margin:'8px 0'}}><b>Исполнитель:</b> ИП «ClipsGold» (реквизиты появятся в финальной редакции).<br/>
          <b>Заказчик:</b> любой пользователь, акцептовавший оферту через регистрацию аккаунта.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>2. Предмет договора</h2>
          <p style={{margin:'8px 0'}}>Исполнитель предоставляет Заказчику доступ к онлайн-сервису <b>ClipsGold</b>: автоматическая нарезка длинных видео в вертикальные клипы 9:16 с субтитрами, smart crop по лицам, выгрузка готовых файлов.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>3. Тарифы</h2>
          <p style={{margin:'8px 0'}}>Описание тарифов и цен будет здесь, в момент запуска платных подписок. Текущий тариф для всех — <b>Beta · бесплатно</b>.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>4. Оплата</h2>
          <p style={{margin:'8px 0'}}>Оплата по безналичному расчёту через сертифицированный платёжный шлюз (ЮKassa / CloudPayments). Чеки выдаются в электронном виде на email Заказчика. Реквизиты пришлём перед запуском.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>5. Возвраты</h2>
          <ul style={{paddingLeft:22,margin:'8px 0'}}>
            <li style={{margin:'4px 0'}}>В первые <b>14 дней</b> после первой оплаты — возврат 100% по любой причине.</li>
            <li style={{margin:'4px 0'}}>Если сервис не работал больше 24 часов подряд — возврат пропорционально срокам.</li>
            <li style={{margin:'4px 0'}}>Возврат идёт на ту же карту, с которой была оплата, в течение 5 рабочих дней.</li>
          </ul>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>6. Срок действия</h2>
          <p style={{margin:'8px 0'}}>Договор действует с момента акцепта (регистрации) и до удаления аккаунта или прекращения оказания услуг Исполнителем.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>7. Изменения</h2>
          <p style={{margin:'8px 0'}}>Исполнитель имеет право изменить условия оферты. О любых изменениях, касающихся цен или возвратов, мы сообщаем за <b>30 дней</b> по email и публикуем новую версию здесь с обновлённой датой.</p>

          <h2 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:34,lineHeight:1.05,margin:'30px 0 0'}}>8. Контакты</h2>
          <p style={{margin:'8px 0'}}>Письма по оферте: <a href="mailto:hello@clipsgold.ru" style={{color:'var(--pink-deep)'}}>hello@clipsgold.ru</a>. По вопросам блокировок и злоупотреблений: <a href="mailto:abuse@clipsgold.ru" style={{color:'var(--pink-deep)'}}>abuse@clipsgold.ru</a>.</p>
        </div>

        <div style={{display:'flex',gap:14,flexWrap:'wrap',marginTop:14,fontFamily:'"Caveat",cursive',fontSize:22}}>
          <Link href="/privacy" style={{color:'var(--ink)',textDecoration:'none',borderBottom:'2px wavy var(--pink-deep)',paddingBottom:1}}>Политика конфиденциальности →</Link>
          <Link href="/terms" style={{color:'var(--ink)',textDecoration:'none',borderBottom:'2px wavy var(--pink-deep)',paddingBottom:1}}>Условия использования →</Link>
        </div>

        <div style={{marginTop:30,display:'flex',gap:12,flexWrap:'wrap',fontFamily:'"Caveat",cursive',fontSize:22}}>
          <Link href="/" style={{display:'inline-flex',alignItems:'center',gap:8,background:'var(--paper)',color:'var(--ink)',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 16px 22px 18px 22px',padding:'8px 18px 6px',boxShadow:'4px 5px 0 var(--ink)',textDecoration:'none'}}>← на главную</Link>
          <Link href="/register" style={{display:'inline-flex',alignItems:'center',gap:8,background:'var(--pink)',color:'#fff',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 16px 22px 18px 22px',padding:'8px 18px 6px',boxShadow:'4px 5px 0 var(--ink)',textDecoration:'none',textShadow:'1px 1px 0 rgba(58,46,42,.35)'}}>Создать аккаунт 🦖</Link>
        </div>
      </div>
    </div>
  )
}
