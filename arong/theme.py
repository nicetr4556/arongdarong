"""화면 꾸미기(CSS)와 머리말."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&family=Gowun+Dodum&display=swap');
:root{
  --coral:#f26b5b; --mustard:#f2b33d; --mint:#3bb59a; --sky:#4a90d9; --grape:#8e6cc9;
  --ink:#2d2a32; --muted:#7a7280; --paper:#fffbf3; --card:#ffffff; --line:#efe3d1; --chip:#fff1de;
  --coral-t:#fdebe8; --mustard-t:#fdf3dc; --mint-t:#e3f5f0; --sky-t:#e6f0fb; --grape-t:#efe9f8;
}
.stApp{background:var(--paper);}
.block-container{max-width:1180px;padding-top:1.3rem;padding-bottom:3rem;}
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp [data-testid="stMarkdownContainer"]{
  font-family:'Gowun Dodum','Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;
}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.jua{
  font-family:'Jua','Apple SD Gothic Neo','Malgun Gothic',sans-serif !important; font-weight:400 !important;
}
.stApp textarea, .stApp input{font-size:1.02rem;}
/* 기기가 어두운 화면 모드여도 글씨가 잘 보이도록 (.streamlit/config.toml이 빠졌을 때 대비) */
.stApp{color:var(--ink);}
.stApp [data-testid="stMarkdownContainer"] p:not(button p):not([data-testid="stAlert"] p),
.stApp [data-testid="stMarkdownContainer"] li, .stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"] p{color:var(--ink);}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p{color:var(--muted);}

/* ---------- 머리말 ---------- */
.hero{display:flex;align-items:center;justify-content:space-between;gap:16px;background:var(--card);
  border:1px solid var(--line);border-radius:22px;padding:16px 24px;margin-bottom:8px;box-shadow:0 6px 0 #f5e7d2;}
.hero-school{font-size:.92rem;color:var(--muted);}
.hero-title{font-family:'Jua',sans-serif;font-size:2.05rem;line-height:1.3;color:var(--ink);margin:2px 0 4px;}
.tiles{display:inline-flex;gap:5px;vertical-align:middle;margin:0 4px 4px;}
.tiles b{display:inline-flex;align-items:center;justify-content:center;width:1.42em;height:1.42em;border-radius:.34em;
  color:#fff;font-weight:400;font-size:.95em;box-shadow:0 3px 0 rgba(0,0,0,.08);}
.tiles b:nth-child(odd){transform:rotate(-5deg);} .tiles b:nth-child(even){transform:rotate(4deg);}
.c1{background:var(--coral);} .c2{background:var(--mustard);} .c3{background:var(--mint);} .c4{background:var(--sky);}
.hero-sub{color:var(--muted);font-size:1.02rem;}
.hero-sub b{font-weight:700;}
.k1{color:var(--coral);} .k2{color:#d4950f;} .k3{color:var(--mint);} .k4{color:var(--sky);}
.hero-emoji{font-size:3.4rem;line-height:1;}
.hero.compact{padding:10px 18px;box-shadow:none;}
.hero.compact .hero-title{font-size:1.35rem;} .hero.compact .hero-sub,.hero.compact .hero-school{display:none;}
.hero.compact .hero-emoji{font-size:1.8rem;}
@media (max-width:640px){ .hero{padding:14px 16px;} .hero-title{font-size:1.45rem;} .hero-emoji{display:none;} }

/* ---------- 메뉴 ---------- */
.st-key-nav div[role="radiogroup"]{gap:6px;flex-wrap:wrap;}
.st-key-nav div[role="radiogroup"] > label{background:var(--card);border:1px solid var(--line);border-radius:999px;
  padding:6px 14px;margin:0;}
.st-key-nav div[role="radiogroup"] > label:has(input:checked){background:var(--ink);border-color:var(--ink);}
.stApp .st-key-nav div[role="radiogroup"] > label:has(input:checked) p{color:#fff;}
.st-key-nav div[role="radiogroup"] > label > div:first-child:not(:has([data-testid="stMarkdownContainer"])){display:none;}
.me{background:var(--chip);border-radius:999px;padding:6px 14px;display:inline-block;color:var(--ink);}
.me.off{background:transparent;color:var(--muted);}

/* ---------- 쓰기 화면 ---------- */
.daybar{background:var(--chip);border-radius:16px;padding:12px 18px;display:flex;gap:10px;flex-wrap:wrap;
  align-items:center;justify-content:space-between;margin:6px 0 4px;}
.daybar .big{font-family:'Jua',sans-serif;font-size:1.25rem;color:var(--ink);}
.daybar .small{color:var(--muted);}
.sec{display:flex;align-items:center;gap:10px;margin:26px 0 6px;flex-wrap:wrap;}
.sec .num{font-family:'Jua',sans-serif;background:var(--ink);color:#fff;border-radius:50%;width:32px;height:32px;
  display:inline-flex;align-items:center;justify-content:center;font-size:1.05rem;}
.sec .t{font-family:'Jua',sans-serif;font-size:1.38rem;color:var(--ink);}
.sec .d{color:var(--muted);font-size:.93rem;}
.tip{background:var(--sky-t);border-radius:12px;padding:8px 12px;color:#35618f;font-size:.92rem;margin:4px 0;}

/* ---------- 기록 보기 ---------- */
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;}
.chip{background:var(--chip);border-radius:999px;padding:3px 11px;font-size:.88rem;color:var(--ink);white-space:nowrap;}
.chip.num{background:var(--ink);color:#fff;}
.chip.heart{background:#fff0c2;}
.chip.star{background:var(--grape-t);color:#5b3fa0;}
.etitle{font-family:'Jua',sans-serif;font-size:1.7rem;line-height:1.3;color:var(--ink);margin:2px 0 10px;}
.ww{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.ww-cell{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:9px 12px;}
.ww-label{font-family:'Jua',sans-serif;font-size:.95rem;color:var(--muted);}
.ww-text{font-size:1.05rem;color:var(--ink);word-break:keep-all;overflow-wrap:anywhere;}
.tcard{border-radius:16px;padding:12px 16px;margin:8px 0;}
.tcard .tlabel{font-family:'Jua',sans-serif;font-size:1.08rem;margin-bottom:2px;}
.tcard .ttext{font-size:1.05rem;color:var(--ink);word-break:keep-all;overflow-wrap:anywhere;}
.tcard.sol{background:var(--mustard-t);} .tcard.sol .tlabel{color:#a8730a;}
.tcard.learned{background:var(--sky-t);} .tcard.learned .tlabel{color:#2f6db0;}
.tcard.felt{background:var(--coral-t);} .tcard.felt .tlabel{color:#c4473a;}
.tcard.action{background:var(--mint-t);} .tcard.action .tlabel{color:#24806b;}
.bns{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
.bns .tcard{margin:0;}
@media (max-width:760px){ .bns{grid-template-columns:1fr;} .ww{grid-template-columns:1fr;} }
.muted{color:#b3aab8;}
.thumb-empty{background:var(--chip);border-radius:12px;aspect-ratio:16/10;display:flex;align-items:center;
  justify-content:center;font-size:2.4rem;color:var(--muted);text-align:center;}
.thumb-empty small{display:block;font-size:.9rem;}
.ctitle{font-family:'Jua',sans-serif;font-size:1.15rem;line-height:1.3;color:var(--ink);margin:6px 0 2px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.cmeta{color:var(--muted);font-size:.88rem;}

/* ---------- 발표 ---------- */
.slide .etitle{font-size:2.5rem;}
.slide .ww-text{font-size:1.25rem;}
.slide .tcard .ttext{font-size:1.2rem;}
.slide .tcard .tlabel{font-size:1.25rem;}
.cover{background:var(--card);border:1px solid var(--line);border-radius:26px;padding:42px 40px;text-align:center;
  box-shadow:0 8px 0 #f5e7d2;}
.cover-kicker{color:var(--muted);font-size:1.05rem;}
.cover-title{font-family:'Jua',sans-serif;font-size:3rem;line-height:1.3;color:var(--ink);margin:14px 0 18px;}
.cover-title .who{color:var(--coral);}
.cover-chips{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-bottom:20px;}
.cover-chips span{background:var(--chip);border-radius:999px;padding:7px 16px;font-size:1.08rem;}
.script{background:var(--sky-t);border-radius:16px;padding:16px 20px;text-align:left;font-size:1.15rem;color:#24486d;
  max-width:820px;margin:0 auto;line-height:1.7;}
.script b{font-family:'Jua',sans-serif;font-weight:400;}
.pledges{list-style:none;padding:0;margin:0 auto 20px;max-width:760px;text-align:left;}
.pledges li{background:var(--mint-t);border-radius:14px;padding:10px 16px;margin:8px 0;font-size:1.18rem;}
.slidecount{text-align:center;font-family:'Jua',sans-serif;font-size:1.15rem;color:var(--muted);padding-top:6px;}
.speak{color:var(--muted);font-size:.9rem;text-align:center;margin-top:6px;}
@media (max-width:640px){ .cover{padding:26px 18px;} .cover-title{font-size:2rem;} .slide .etitle{font-size:1.8rem;} }

/* ---------- 순위 ---------- */
.medal{font-size:2rem;line-height:1;}
.rankrow{display:flex;align-items:center;gap:10px;background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:8px 12px;margin:6px 0;}
.rankrow .n{font-family:'Jua',sans-serif;width:28px;text-align:center;color:var(--muted);}
.rankrow .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.rankrow .v{white-space:nowrap;}

.foot{color:var(--muted);text-align:center;font-size:.85rem;margin-top:40px;}
@media print{ .st-key-nav, header, [data-testid="stToolbar"], .noprint{display:none !important;} .hero{box-shadow:none;} }
</style>
"""


def hero_html(school_full: str, school_short: str, class_text: str, compact: bool = False) -> str:
    return (
        f'<div class="hero{" compact" if compact else ""}">'
        '<div class="hero-left">'
        f'<div class="hero-school">🏫 {school_full} · 실패 성장 프로젝트</div>'
        f'<div class="hero-title">{school_short} {class_text} '
        '<span class="tiles"><b class="c1">아</b><b class="c2">롱</b><b class="c3">다</b><b class="c4">롱</b></span>'
        ' 프로젝트</div>'
        '<div class="hero-sub"><b class="k1">아</b>까운 <b class="k2">Wrong</b>, '
        '<b class="k3">多</b>(많을 다) <b class="k4">Wrong</b>! '
        '— 아까운 실패가 많을수록, 우리는 더 많이 배워요.</div>'
        '</div>'
        '<div class="hero-emoji">🌈</div>'
        '</div>'
    )
