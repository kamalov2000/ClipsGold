import Link from 'next/link'

export default function NotFound() {
  return (
    <>
      <style>{`
        @keyframes wob{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-12px) rotate(5deg)}}
        @keyframes blinkEye{0%,92%,100%{transform:scaleY(1)}94%,98%{transform:scaleY(.1)}}
        @keyframes waveArm{0%,100%{transform:rotate(-8deg)}50%{transform:rotate(20deg)}}
        .nf-eye{transform-origin:center;transform-box:fill-box;animation:blinkEye 4s infinite}
        .nf-arm{transform-origin:24px 50px;animation:waveArm 2.4s ease-in-out infinite}
        .nf-doodle{position:absolute;opacity:.6}
        .nf-d1{top:6%;left:8%;animation:wob 5s ease-in-out infinite}
        .nf-d2{top:14%;right:10%;animation:wob 6s ease-in-out infinite reverse}
        .nf-d3{bottom:14%;left:14%;animation:wob 4.5s ease-in-out infinite}
        .nf-d4{bottom:8%;right:8%;animation:wob 5.5s ease-in-out infinite reverse}
        .nf-btn{font-family:"Caveat",cursive;font-weight:700;font-size:24px;line-height:1;border:3px solid var(--ink);padding:10px 20px 8px;border-radius:18px 14px 20px 16px / 14px 18px 16px 20px;box-shadow:4px 5px 0 var(--ink);background:#fff;display:inline-flex;align-items:center;gap:8px;cursor:pointer;text-decoration:none;color:var(--ink)}
        .nf-btn:hover{transform:translate(-2px,-2px) rotate(-1deg);box-shadow:6px 7px 0 var(--ink)}
        .nf-btn.pink{background:var(--pink);color:#fff;text-shadow:1px 1px 0 rgba(58,46,42,.35)}
        .nf-btn.pink:hover{background:var(--pink-deep)}
      `}</style>
      <div style={{fontFamily:'"Patrick Hand",sans-serif',color:'var(--ink)',fontSize:18,background:'var(--cream)',backgroundImage:'radial-gradient(circle at 8% 8%, rgba(255,209,102,.5) 0,transparent 30%),radial-gradient(circle at 96% 14%, rgba(255,143,163,.4) 0,transparent 28%),radial-gradient(circle at 96% 92%, rgba(125,211,192,.4) 0,transparent 30%),radial-gradient(circle at 4% 92%, rgba(201,182,228,.4) 0,transparent 30%)',minHeight:'100vh',display:'flex',flexDirection:'column'}}>

        <nav style={{maxWidth:1180,width:'100%',margin:'0 auto',padding:'18px 28px'}}>
          <Link href="/" style={{display:'inline-flex',alignItems:'center',gap:8,fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:30,color:'var(--ink)',textDecoration:'none'}}>
            <span style={{width:34,height:34,display:'grid',placeItems:'center',background:'var(--yellow)',border:'3px solid var(--ink)',borderRadius:'14px 12px 16px 10px / 12px 14px 10px 16px',boxShadow:'2px 3px 0 var(--ink)',transform:'rotate(-4deg)'}}>
              <svg width="22" height="22" viewBox="0 0 26 26"><path d="M5 7 L13 13 L21 7 M13 13 V22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="13" r="2.5" fill="#3A2E2A"/></svg>
            </span>
            Clips<span style={{color:'var(--yellow-deep)',textShadow:'1px 2px 0 var(--ink)'}}>Gold</span>
          </Link>
        </nav>

        <div style={{flex:1,display:'grid',placeItems:'center',padding:'20px 28px 60px',position:'relative'}}>
          <svg className="nf-doodle nf-d1" width="44" height="44" viewBox="0 0 24 24"><path d="M12 1 L14 9 L22 11 L14 13 L12 22 L10 13 L2 11 L10 9 Z" fill="#FFD166" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/></svg>
          <svg className="nf-doodle nf-d2" width="40" height="40" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="2"/><path d="M8 13 q4 4 8 0" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round"/><circle cx="9" cy="10" r="1.4" fill="#3A2E2A"/><circle cx="15" cy="10" r="1.4" fill="#3A2E2A"/></svg>
          <svg className="nf-doodle nf-d3" width="50" height="40" viewBox="0 0 30 24"><path d="M3 12 q4-9 12-9 q8 0 12 9 q-4 9-12 9 q-8 0-12-9 z" fill="#B8E6CC" stroke="#3A2E2A" strokeWidth="2"/></svg>
          <svg className="nf-doodle nf-d4" width="44" height="44" viewBox="0 0 24 24"><path d="M12 2 L14 9 L21 12 L14 15 L12 22 L10 15 L3 12 L10 9 Z" fill="#C9B6E4" stroke="#3A2E2A" strokeWidth="2" strokeLinejoin="round"/></svg>

          <div style={{background:'var(--paper)',border:'3px solid var(--ink)',borderRadius:'32px 28px 36px 24px / 26px 32px 24px 36px',boxShadow:'10px 12px 0 var(--ink)',padding:'48px 52px',maxWidth:640,width:'100%',textAlign:'center',transform:'rotate(-1deg)',position:'relative'}}>

            <div style={{margin:'-12px auto 18px',width:200,height:180,position:'relative'}}>
              <div style={{position:'absolute',left:'50%',bottom:-8,transform:'translateX(-50%)',width:120,height:14,background:'rgba(58,46,42,.18)',borderRadius:'50%',filter:'blur(6px)'}}></div>
              <svg viewBox="0 0 200 180" width="200" height="180">
                <g opacity=".6" transform="translate(150 30) rotate(20)">
                  <rect x="-22" y="-16" width="44" height="32" rx="3" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
                  <path d="M-16-8 L-2-4 L4-12 L16-6 M-14 4 L0 8 L12 0" stroke="#3A2E2A" strokeWidth="1.5" fill="none"/>
                  <circle cx="-4" cy="2" r="3" fill="#FF8FA3" stroke="#3A2E2A" strokeWidth="1.5"/>
                </g>
                <ellipse cx="100" cy="115" rx="56" ry="42" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
                <ellipse cx="100" cy="125" rx="36" ry="22" fill="#FFFCF1" stroke="#3A2E2A" strokeWidth="2"/>
                <path d="M58 96 L62 84 L72 92 L78 80 L86 92 L94 78 L102 92" stroke="#3A2E2A" strokeWidth="2.5" fill="#FFD166" strokeLinejoin="round"/>
                <ellipse cx="60" cy="72" rx="34" ry="28" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="3"/>
                <circle className="nf-eye" cx="50" cy="68" r="9" fill="#fff" stroke="#3A2E2A" strokeWidth="2"/>
                <path d="M50 64 a4 4 0 1 1-3 6 a2.5 2.5 0 1 1 1.8-3.8" stroke="#3A2E2A" strokeWidth="1.6" fill="none" strokeLinecap="round"/>
                <path d="M40 56 q5-3 12-1" stroke="#3A2E2A" strokeWidth="2" fill="none" strokeLinecap="round"/>
                <ellipse cx="42" cy="84" rx="3.5" ry="4.5" fill="#3A2E2A"/>
                <circle cx="34" cy="72" r="1.4" fill="#3A2E2A"/>
                <g className="nf-arm">
                  <path d="M88 96 q-12 -8 -24 -22" stroke="#3A2E2A" strokeWidth="3" fill="none" strokeLinecap="round"/>
                  <circle cx="58" cy="62" r="9" fill="#fff" stroke="#3A2E2A" strokeWidth="2.5"/>
                  <path d="M52 68 l-8 8" stroke="#3A2E2A" strokeWidth="3" strokeLinecap="round"/>
                </g>
                <path d="M84 152 v14 h12 v-14 M116 152 v14 h12 v-14" stroke="#3A2E2A" strokeWidth="2.5" fill="#7DD3C0"/>
                <path d="M150 116 q24 8 36 -10" stroke="#3A2E2A" strokeWidth="3" fill="#7DD3C0"/>
                <path d="M82 50 q-3 6 0 9 q3 -3 0 -9 z" fill="#7DD3C0" stroke="#3A2E2A" strokeWidth="1.5"/>
              </svg>
            </div>

            <div style={{fontFamily:'"Caveat",cursive',fontSize:160,lineHeight:1,color:'var(--yellow-deep)',textShadow:'6px 8px 0 var(--ink)',margin:'-20px 0 0'}}>404</div>
            <h1 style={{fontFamily:'"Caveat",cursive',fontWeight:700,fontSize:46,lineHeight:1,margin:'8px 0 0',letterSpacing:'.5px'}}>Динозаврик потерялся 🦖</h1>

            <div style={{display:'inline-block',background:'#fff',border:'3px solid var(--ink)',borderRadius:'18px 22px 16px 20px / 18px 16px 22px 20px',boxShadow:'4px 5px 0 var(--ink)',padding:'10px 18px 8px',fontFamily:'"Caveat",cursive',fontSize:24,lineHeight:1.05,transform:'rotate(-2deg)',position:'relative',margin:'20px 0 6px'}}>
              я тут вообще не был…
              <span style={{content:'',position:'absolute',left:30,bottom:-12,width:18,height:18,background:'#fff',borderRight:'3px solid var(--ink)',borderBottom:'3px solid var(--ink)',transform:'rotate(45deg)',display:'block'}}></span>
            </div>

            <p style={{color:'var(--ink-soft)',fontSize:18,margin:'14px auto 0',maxWidth:480,lineHeight:1.45}}>
              Этой страницы нет — может, ссылка устарела, или мы её ещё не нарисовали. Можешь вернуться на главную или сразу к работе.
            </p>

            <div style={{display:'flex',gap:14,justifyContent:'center',flexWrap:'wrap',marginTop:24}}>
              <Link href="/" className="nf-btn pink">← На главную</Link>
              <Link href="/app" className="nf-btn">В Студию 🦖</Link>
            </div>

            <div style={{marginTop:28,color:'var(--ink-soft)',fontSize:15}}>
              Может тебе надо:{' '}
              <Link href="/register" style={{color:'var(--pink-deep)',textDecoration:'underline',margin:'0 6px'}}>регистрация</Link>
              <Link href="/login" style={{color:'var(--pink-deep)',textDecoration:'underline',margin:'0 6px'}}>вход</Link>
              <Link href="/history" style={{color:'var(--pink-deep)',textDecoration:'underline',margin:'0 6px'}}>история</Link>
              <Link href="/factory" style={{color:'var(--pink-deep)',textDecoration:'underline',margin:'0 6px'}}>фабрика</Link>
            </div>
          </div>
        </div>

        <div style={{textAlign:'center',color:'var(--ink-soft)',fontSize:13,fontFamily:'"Patrick Hand SC",sans-serif',letterSpacing:'2px',textTransform:'uppercase',padding:'0 0 18px'}}>
          err 404 · по этой тропинке мы ещё не ходили
        </div>
      </div>
    </>
  )
}
