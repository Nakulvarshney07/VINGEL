"""
CSS + JS injection for VINGEL.

Theming uses CSS custom properties.
Call inject_styles(is_dark) once at the top of app.py.
"""
import streamlit as st
import streamlit.components.v1 as components

# ── Theme variable sets ──────────────────────────────────────────────────────
_DARK_VARS = """
:root {
  --bg:          #07070c;
  --surface:     #0f0f18;
  --surface-2:   #171723;
  --surface-3:   #1e1e2e;
  --border:      rgba(255,255,255,0.07);
  --border-mid:  rgba(255,255,255,0.12);
  --border-hi:   rgba(99,102,241,0.4);
  --ring:        rgba(99,102,241,0.35);
  --t1:          #f4f4f8;
  --t2:          #c8c8d8;
  --t3:          #8888a0;
  --t4:          #454560;
  --sh-sm:       0 1px 4px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04);
  --sh-md:       0 4px 20px rgba(0,0,0,0.7);
  --sh-lg:       0 16px 50px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.04);
  --sidebar-bg:  #09090f;
  --input-bg:    rgba(255,255,255,0.04);
  --metric-bg:   rgba(15,15,24,0.9);
  --tab-bg:      rgba(9,9,15,0.95);
  --tab-active:  rgba(99,102,241,0.15);
  --tab-text:    #a5b4fc;
  --chart-bg:    #07070c;
  --chart-grid:  rgba(255,255,255,0.04);
  --chart-text:  #6b6b80;
  --hover-bg:    rgba(255,255,255,0.04);
  --scrollbar:   rgba(255,255,255,0.08);
  --drop-bg:     #131320;
  --expand-bg:   rgba(13,13,20,0.97);
  --glass:       rgba(255,255,255,0.03);
  --glow-a:      rgba(99,102,241,0.25);
  --glow-b:      rgba(139,92,246,0.2);
}
"""

_LIGHT_VARS = """
:root {
  --bg:          #f2f2f8;
  --surface:     #ffffff;
  --surface-2:   #f5f5fc;
  --surface-3:   #eeeef6;
  --border:      rgba(0,0,0,0.07);
  --border-mid:  rgba(0,0,0,0.12);
  --border-hi:   rgba(99,102,241,0.4);
  --ring:        rgba(99,102,241,0.22);
  --t1:          #09090d;
  --t2:          #3d3d52;
  --t3:          #707088;
  --t4:          #b0b0c0;
  --sh-sm:       0 1px 3px rgba(0,0,0,0.05), 0 0 0 1px rgba(0,0,0,0.06);
  --sh-md:       0 4px 16px rgba(0,0,0,0.09);
  --sh-lg:       0 16px 50px rgba(0,0,0,0.14), 0 0 0 1px rgba(0,0,0,0.04);
  --sidebar-bg:  #ffffff;
  --input-bg:    #ffffff;
  --metric-bg:   rgba(255,255,255,0.97);
  --tab-bg:      rgba(255,255,255,0.97);
  --tab-active:  rgba(99,102,241,0.1);
  --tab-text:    #4338ca;
  --chart-bg:    #ffffff;
  --chart-grid:  rgba(0,0,0,0.06);
  --chart-text:  #a1a1aa;
  --hover-bg:    rgba(0,0,0,0.03);
  --scrollbar:   rgba(0,0,0,0.1);
  --drop-bg:     #ffffff;
  --expand-bg:   rgba(250,250,252,0.97);
  --glass:       rgba(255,255,255,0.7);
  --glow-a:      rgba(99,102,241,0.1);
  --glow-b:      rgba(139,92,246,0.08);
}
"""

# ── Animations ───────────────────────────────────────────────────────────────
_ANIMATIONS = """
@keyframes fadeUp    { from{opacity:0;transform:translateY(22px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn    { from{opacity:0} to{opacity:1} }
@keyframes gradFlow  { 0%,100%{background-position:0% 50%} 50%{background-position:100% 50%} }
@keyframes orbPulse  { 0%,100%{transform:scale(1);opacity:.9} 50%{transform:scale(1.18);opacity:.6} }
@keyframes floatY    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
@keyframes shimmer   { 0%{left:-100%} 100%{left:200%} }
@keyframes spin      { to{transform:rotate(360deg)} }
@keyframes pulseRing {
  0%  { box-shadow: 0 0 0 0 rgba(99,102,241,0.55); }
  70% { box-shadow: 0 0 0 8px rgba(99,102,241,0); }
  100%{ box-shadow: 0 0 0 0 rgba(99,102,241,0); }
}
@keyframes glowPulse {
  0%,100% { box-shadow: 0 0 20px var(--glow-a); }
  50%     { box-shadow: 0 0 40px var(--glow-a), 0 0 80px var(--glow-b); }
}
@keyframes borderAnim {
  0%,100% { background-position: 0% 50%; }
  50%      { background-position: 100% 50%; }
}
@keyframes slideDown { from{opacity:0;transform:translateY(-12px)} to{opacity:1;transform:translateY(0)} }
@keyframes slideUp   { from{opacity:0;transform:translateY(12px)}  to{opacity:1;transform:translateY(0)} }
"""

# ── Base CSS ──────────────────────────────────────────────────────────────────
_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── Reset / base ─────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
  background-color: var(--bg) !important;
  color: var(--t1) !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Gradient glow at top of page */
.stApp::before {
  content: '';
  position: fixed; top: -120px; left: -10%; width: 120%; height: 480px;
  background: radial-gradient(ellipse at 50% 0%,
    rgba(99,102,241,0.09) 0%, rgba(139,92,246,0.05) 40%, transparent 70%);
  pointer-events: none; z-index: 0;
}

/* Main content area */
section[data-testid="stMain"] {
  background: transparent !important;
}
.main .block-container {
  padding-top: 2rem !important;
  max-width: 1280px !important;
}

#MainMenu, footer, header, div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"] {
  visibility: hidden !important; display: none !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,.5); }

/* ── Sidebar ──────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: var(--sidebar-bg) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div:first-child {
  padding-top: 1.5rem !important;
}
section[data-testid="stSidebar"] * { color: var(--t1) !important; }

/* Logo block */
.vg-logo-wrap {
  display: flex; align-items: center; justify-content: space-between;
  padding: .1rem 0 .9rem;
}
.vg-logo-name {
  font-size: 1.15rem; font-weight: 900; letter-spacing: -.02em;
  background: linear-gradient(135deg, #818cf8 0%, #a78bfa 55%, #60a5fa 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.vg-logo-tag {
  font-size: .6rem; font-weight: 700; letter-spacing: .12em;
  text-transform: uppercase; color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important;
}

/* Sidebar section header */
.sb-sec {
  font-size: .6rem; font-weight: 800; letter-spacing: .15em;
  text-transform: uppercase; color: var(--t4) !important;
  -webkit-text-fill-color: var(--t4) !important;
  padding: .1rem 0; margin: 1rem 0 .4rem;
  display: flex; align-items: center; gap: .5rem;
}
.sb-sec::after { content:''; flex:1; height:1px; background: var(--border); }

/* ── Labels ───────────────────────────────────────────────────────────── */
label,
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] label {
  color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important;
  font-size: .72rem !important; font-weight: 600 !important;
  letter-spacing: .06em !important; text-transform: uppercase !important;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"] {
  background: var(--input-bg) !important;
  border: 1px solid var(--border-mid) !important;
  border-radius: 9px !important;
  box-shadow: var(--sh-sm) !important;
  transition: border-color .18s, box-shadow .18s !important;
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="base-input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
  border-color: rgba(99,102,241,.6) !important;
  box-shadow: 0 0 0 3px var(--ring) !important;
}
input[type="text"], input[type="number"], textarea,
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {
  background: transparent !important;
  color: var(--t1) !important;
  font-size: .9rem !important;
}
input::placeholder, textarea::placeholder {
  color: var(--t4) !important;
  -webkit-text-fill-color: var(--t4) !important;
}

/* ── Select ───────────────────────────────────────────────────────────── */
div[data-baseweb="select"] > div {
  background: var(--input-bg) !important;
  border: 1px solid var(--border-mid) !important;
  border-radius: 9px !important;
  color: var(--t1) !important;
}
div[data-baseweb="select"] svg { fill: var(--t3) !important; }
ul[data-baseweb="menu"], div[data-baseweb="popover"] {
  background: var(--drop-bg) !important;
  border: 1px solid var(--border-mid) !important;
  border-radius: 12px !important;
  box-shadow: var(--sh-lg) !important;
  overflow: hidden !important;
}
li[role="option"] { color: var(--t2) !important; background: transparent !important; }
li[role="option"]:hover { background: var(--hover-bg) !important; color: var(--t1) !important; }

/* ── Slider ───────────────────────────────────────────────────────────── */
div[data-testid="stSlider"] > div > div > div { background: var(--surface-3) !important; }
div[data-testid="stSlider"] [role="slider"] {
  background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
  border: 2px solid rgba(255,255,255,0.3) !important;
  transition: box-shadow .2s !important;
}
div[data-testid="stSlider"] [role="slider"]:hover {
  animation: pulseRing 1s forwards !important;
}
div[data-testid="stSlider"] p,
div[data-testid="stSlider"] [data-testid="stTickBarMin"],
div[data-testid="stSlider"] [data-testid="stTickBarMax"] {
  color: var(--t3) !important; font-size: .72rem !important;
}
div[data-testid="stSliderThumbValue"] { color: #a5b4fc !important; font-weight: 700 !important; }

/* ── Buttons ──────────────────────────────────────────────────────────── */
button[kind="primary"] {
  background: linear-gradient(135deg, #5f5ff7 0%, #8855f5 100%) !important;
  color: #fff !important; border: none !important;
  border-radius: 9px !important; font-weight: 600 !important;
  font-size: .88rem !important; letter-spacing: .02em !important;
  box-shadow: 0 1px 2px rgba(0,0,0,.3), 0 4px 14px rgba(99,102,241,.5) !important;
  transition: all .2s cubic-bezier(.4,0,.2,1) !important;
  position: relative !important; overflow: hidden !important;
}
button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 2px 6px rgba(0,0,0,.3), 0 10px 30px rgba(99,102,241,.65) !important;
  filter: brightness(1.1) !important;
}
button[kind="primary"]:active { transform: translateY(0px) !important; filter: brightness(.95) !important; }

button[kind="secondary"], button[data-testid="baseButton-secondary"] {
  background: var(--surface) !important;
  color: var(--t2) !important;
  border: 1px solid var(--border-mid) !important;
  border-radius: 9px !important; font-weight: 500 !important;
  box-shadow: var(--sh-sm) !important;
  transition: all .2s cubic-bezier(.4,0,.2,1) !important;
  position: relative !important; overflow: hidden !important;
}
button[kind="secondary"]:hover, button[data-testid="baseButton-secondary"]:hover {
  border-color: rgba(99,102,241,.5) !important;
  color: #a5b4fc !important;
  -webkit-text-fill-color: #a5b4fc !important;
  background: rgba(99,102,241,.07) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--sh-md) !important;
}
button[kind="secondary"]:active, button[data-testid="baseButton-secondary"]:active {
  transform: translateY(0) !important;
}

/* ── Metrics ──────────────────────────────────────────────────────────── */
div[data-testid="stMetric"] {
  background: var(--metric-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important; padding: 1.15rem 1.1rem !important;
  box-shadow: var(--sh-sm) !important;
  transition: border-color .22s, transform .22s, box-shadow .22s !important;
  animation: slideUp .5s cubic-bezier(.4,0,.2,1) both !important;
  position: relative !important; overflow: hidden !important;
}
div[data-testid="stMetric"]::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #6366f1, #a78bfa, #38bdf8);
  opacity: 0; transition: opacity .22s;
}
div[data-testid="stMetric"]:hover {
  border-color: rgba(99,102,241,.3) !important;
  transform: translateY(-3px) !important;
  box-shadow: var(--sh-md), 0 0 0 1px rgba(99,102,241,.15) !important;
}
div[data-testid="stMetric"]:hover::before { opacity: 1 !important; }
div[data-testid="stMetricLabel"] p {
  color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important;
  font-size: .67rem !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: .1em !important;
}
div[data-testid="stMetricValue"] {
  color: var(--t1) !important;
  -webkit-text-fill-color: var(--t1) !important;
  font-size: 1.6rem !important; font-weight: 800 !important;
}
div[data-testid="stMetricDelta"] { color: #4ade80 !important; -webkit-text-fill-color: #4ade80 !important; }

/* ── Tabs ─────────────────────────────────────────────────────────────── */
div[data-baseweb="tab-list"] {
  background: var(--tab-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important; padding: 3px !important; gap: 2px !important;
  box-shadow: var(--sh-sm) !important;
}
button[data-baseweb="tab"] {
  color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important;
  font-weight: 500 !important; font-size: .85rem !important;
  border-radius: 9px !important; padding: .44rem 1rem !important;
  transition: all .18s cubic-bezier(.4,0,.2,1) !important;
  background: transparent !important; border: none !important;
}
button[data-baseweb="tab"]:hover {
  color: var(--t2) !important;
  -webkit-text-fill-color: var(--t2) !important;
  background: var(--hover-bg) !important;
}
button[aria-selected="true"][data-baseweb="tab"] {
  color: var(--tab-text) !important;
  -webkit-text-fill-color: var(--tab-text) !important;
  background: var(--tab-active) !important;
  box-shadow: var(--sh-sm) !important;
  font-weight: 600 !important;
}
div[data-baseweb="tab-highlight"] { display: none !important; }
div[data-baseweb="tab-border"]    { display: none !important; }

/* Tab panel */
div[data-baseweb="tab-panel"] {
  padding-top: 1.2rem !important;
}

/* ── DataFrame ────────────────────────────────────────────────────────── */
div[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: 12px !important; overflow: hidden !important;
  box-shadow: var(--sh-sm) !important;
}
iframe { background: var(--bg) !important; }

/* ── Expander ─────────────────────────────────────────────────────────── */
details {
  background: var(--expand-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important; padding: .5rem .75rem !important;
  transition: border-color .2s, box-shadow .2s !important;
  box-shadow: var(--sh-sm) !important;
}
details[open] { border-color: var(--border-mid) !important; }
details summary {
  color: var(--t2) !important;
  -webkit-text-fill-color: var(--t2) !important;
  font-weight: 500 !important; font-size: .86rem !important; cursor: pointer !important;
}
details summary:hover {
  color: var(--t1) !important;
  -webkit-text-fill-color: var(--t1) !important;
}

/* ── Alerts ───────────────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
  border-radius: 10px !important; border-left-width: 3px !important;
  background: var(--surface) !important;
  box-shadow: var(--sh-sm) !important;
  animation: slideUp .35s ease both !important;
}
div[data-testid="stAlert"] p {
  color: var(--t2) !important;
  -webkit-text-fill-color: var(--t2) !important;
}

/* ── Spinner ──────────────────────────────────────────────────────────── */
div[data-testid="stSpinner"] p {
  color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important;
}

/* ── Typography ───────────────────────────────────────────────────────── */
p, li { color: var(--t2) !important; }
h1,h2,h3,h4,h5 { color: var(--t1) !important; -webkit-text-fill-color: var(--t1) !important; }
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }
small, .stCaption, div[data-testid="stCaptionContainer"] p {
  color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important;
  font-size: .74rem !important;
}
a { color: #818cf8 !important; -webkit-text-fill-color: #818cf8 !important; }
a:hover { color: #a5b4fc !important; -webkit-text-fill-color: #a5b4fc !important; }

/* Button text must not inherit the p/li color rule */
button[kind="primary"] p, button[kind="primary"] span,
button[data-testid="baseButton-primary"] p,
button[data-testid="baseButton-primary"] span {
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
}
button[kind="secondary"] p, button[kind="secondary"] span,
button[data-testid="baseButton-secondary"] p,
button[data-testid="baseButton-secondary"] span {
  color: var(--t2) !important;
  -webkit-text-fill-color: var(--t2) !important;
}

/* ── Page links (st.page_link) ────────────────────────────────────────── */
div[data-testid="stPageLink"] a {
  display: flex !important; align-items: center !important; gap: .5rem !important;
  padding: .38rem .65rem !important; border-radius: 8px !important;
  color: var(--t2) !important; -webkit-text-fill-color: var(--t2) !important;
  font-size: .83rem !important; font-weight: 500 !important;
  text-decoration: none !important;
  transition: background .15s, color .15s !important;
  margin-bottom: 1px !important;
}
div[data-testid="stPageLink"] a:hover {
  background: var(--hover-bg) !important;
  color: var(--t1) !important; -webkit-text-fill-color: var(--t1) !important;
}
div[data-testid="stPageLink-active"] a,
div[data-testid="stPageLink"] a[aria-current="page"] {
  background: var(--tab-active) !important;
  color: var(--tab-text) !important;
  -webkit-text-fill-color: var(--tab-text) !important;
  font-weight: 600 !important;
}

/* code blocks */
code {
  background: var(--surface-2) !important;
  border: 1px solid var(--border-mid) !important;
  border-radius: 5px !important; padding: .1em .4em !important;
  font-size: .84em !important; color: var(--t2) !important;
  -webkit-text-fill-color: var(--t2) !important;
}
pre code { padding: 0 !important; background: transparent !important; border: none !important; }
pre {
  background: var(--surface-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important; padding: 1rem !important;
}

/* ═══════════════════════════════════════════════════════════════
   CUSTOM COMPONENTS
═══════════════════════════════════════════════════════════════ */

/* ── Hero ─────────────────────────────────────────────────────────────── */
.vg-hero { position: relative; overflow: hidden; padding: 3.5rem 0 2.5rem; }
.vg-orb  { position: absolute; border-radius: 50%; filter: blur(90px); pointer-events: none; z-index: 0; }
.vg-orb-a {
  width: 560px; height: 560px; top: -200px; left: -2%;
  background: radial-gradient(circle, rgba(99,102,241,.25) 0%, transparent 70%);
  animation: orbPulse 9s ease-in-out infinite;
}
.vg-orb-b {
  width: 400px; height: 400px; top: -80px; right: 3%;
  background: radial-gradient(circle, rgba(139,92,246,.2) 0%, transparent 70%);
  animation: orbPulse 13s ease-in-out infinite 3s;
}
.vg-orb-c {
  width: 280px; height: 280px; bottom: -40px; left: 45%;
  background: radial-gradient(circle, rgba(6,182,212,.15) 0%, transparent 70%);
  animation: orbPulse 17s ease-in-out infinite 6s;
}
.vg-hero-inner { position: relative; z-index: 1; }

.vg-badge {
  display: inline-flex; align-items: center; gap: .45rem;
  background: rgba(99,102,241,.1); border: 1px solid rgba(99,102,241,.3);
  border-radius: 100px; padding: .28rem .9rem;
  font-size: .67rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase;
  color: #a5b4fc !important; -webkit-text-fill-color: #a5b4fc !important;
  margin-bottom: .9rem; animation: floatY 4s ease-in-out infinite, fadeUp .5s ease both;
}
.vg-badge-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #a78bfa);
  animation: pulseRing 1.8s ease-in-out infinite;
  flex-shrink: 0;
}

.vg-title {
  font-size: clamp(2.2rem, 5.5vw, 3.6rem); font-weight: 900; line-height: 1.07;
  letter-spacing: -.03em; margin-bottom: .6rem;
  background: linear-gradient(135deg, #c7d2fe 0%, #a78bfa 30%, #818cf8 55%, #38bdf8 80%, #c7d2fe 100%);
  background-size: 300% 300%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  animation: gradFlow 6s ease infinite, fadeUp .55s ease .05s both;
}
.vg-sub {
  font-size: 1.05rem; line-height: 1.75; max-width: 560px;
  color: var(--t2) !important; -webkit-text-fill-color: var(--t2) !important;
  animation: fadeUp .55s ease .15s both;
}

/* ── Stats row (below hero) ───────────────────────────────────────────── */
.vg-stats {
  display: flex; gap: 2.5rem; flex-wrap: wrap;
  margin: 1.5rem 0 0; animation: fadeUp .55s ease .25s both;
}
.vg-stat-item {
  display: flex; flex-direction: column;
}
.vg-stat-num {
  font-size: 1.5rem; font-weight: 900; letter-spacing: -.02em;
  background: linear-gradient(135deg, #818cf8, #a78bfa);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.vg-stat-lbl {
  font-size: .7rem; font-weight: 600; letter-spacing: .07em; text-transform: uppercase;
  color: var(--t3) !important; -webkit-text-fill-color: var(--t3) !important;
}

/* ── Feature cards ────────────────────────────────────────────────────── */
.vg-cards {
  display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin: 2rem 0 1.75rem;
}
.vg-card {
  background: var(--glass);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  border-radius: 16px; padding: 1.5rem 1.3rem;
  box-shadow: var(--sh-sm);
  transition: all .28s cubic-bezier(.4,0,.2,1);
  animation: fadeUp .6s cubic-bezier(.4,0,.2,1) both;
  cursor: default; position: relative; overflow: hidden;
}
/* gradient glow border on hover via ::after */
.vg-card::after {
  content: ''; position: absolute; inset: 0; border-radius: 16px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6, #06b6d4, #6366f1);
  background-size: 400%; opacity: 0;
  transition: opacity .35s;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  padding: 1px; animation: borderAnim 5s ease infinite;
}
.vg-card:hover { transform: translateY(-5px); box-shadow: var(--sh-lg); }
.vg-card:hover::after { opacity: 1; }
.vg-card:nth-child(1){animation-delay:.06s}
.vg-card:nth-child(2){animation-delay:.12s}
.vg-card:nth-child(3){animation-delay:.18s}
.vg-card:nth-child(4){animation-delay:.24s}

.vg-card-icon {
  font-size: 1.9rem; margin-bottom: .75rem; display: block;
  filter: drop-shadow(0 0 10px rgba(99,102,241,.4));
}
.vg-card-title {
  font-weight: 700; font-size: .94rem;
  color: var(--t1) !important; -webkit-text-fill-color: var(--t1) !important;
  margin-bottom: .35rem;
}
.vg-card-desc {
  font-size: .79rem; color: var(--t3) !important;
  -webkit-text-fill-color: var(--t3) !important; line-height: 1.65;
}

/* ── Shimmer loading bar ──────────────────────────────────────────────── */
.vg-shimmer {
  height: 2px; border-radius: 1px; margin-bottom: 1.2rem;
  background: var(--surface-2); position: relative; overflow: hidden;
}
.vg-shimmer::after {
  content: ''; position: absolute; top: 0; height: 100%; width: 50%;
  background: linear-gradient(90deg, transparent, #818cf8, transparent);
  animation: shimmer 1.3s ease-in-out infinite;
}

/* ── Result header ────────────────────────────────────────────────────── */
.vg-result-title {
  font-size: clamp(1.8rem, 4vw, 2.8rem); font-weight: 900;
  letter-spacing: -.025em; line-height: 1.1;
  background: linear-gradient(135deg, #c7d2fe 0%, #a78bfa 40%, #38bdf8 80%, #c7d2fe 100%);
  background-size: 300%;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  animation: gradFlow 6s ease infinite, fadeUp .4s ease both;
}
.vg-result-sub {
  font-size: .85rem; margin-top: .3rem;
  color: var(--t3) !important; -webkit-text-fill-color: var(--t3) !important;
  animation: fadeUp .4s ease .1s both;
}

/* ── Section headings (vault etc.) ───────────────────────────────────── */
.vg-section-head {
  font-size: .95rem; font-weight: 700;
  color: var(--t1) !important; -webkit-text-fill-color: var(--t1) !important;
  padding: .5rem 0 .4rem; border-bottom: 1px solid var(--border); margin-bottom: .8rem;
  display: flex; align-items: center; gap: .5rem;
}
.vg-section-head::before {
  content: ''; display: inline-block; width: 3px; height: 1em;
  background: linear-gradient(to bottom, #6366f1, #a78bfa);
  border-radius: 2px; flex-shrink: 0;
}
.vg-section-sub {
  font-size: .82rem; color: var(--t2) !important;
  -webkit-text-fill-color: var(--t2) !important;
  margin-bottom: 1rem; line-height: 1.6;
}

/* ── Vault hash ───────────────────────────────────────────────────────── */
.vg-hash {
  font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
  font-size: .78rem; color: #4ade80 !important; -webkit-text-fill-color: #4ade80 !important;
  background: rgba(74,222,128,.07); border: 1px solid rgba(74,222,128,.22);
  border-radius: 10px; padding: .7rem 1rem; word-break: break-all; letter-spacing: .02em;
  animation: fadeUp .4s ease both;
}

/* ── Legend ───────────────────────────────────────────────────────────── */
.vg-legend { display: flex; gap: 1.2rem; flex-wrap: wrap; padding: .5rem 0; margin-top: .3rem; }
.vg-legend span {
  font-size: .77rem; font-weight: 500; display: flex; align-items: center; gap: .32rem;
  color: var(--t2) !important; -webkit-text-fill-color: var(--t2) !important;
}
.vg-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex-shrink: 0; }

/* ── Divider ──────────────────────────────────────────────────────────── */
.vg-divider { height: 1px; background: var(--border); margin: .9rem 0; }
"""

# ── JS effects ───────────────────────────────────────────────────────────────
_JS = """
(function() {
  const pdoc = window.parent.document;
  if (pdoc.getElementById('vg-fx')) return;

  const s = pdoc.createElement('style');
  s.id = 'vg-fx';
  s.textContent = `
    /* Ripple */
    .vg-ripple {
      position: absolute; pointer-events: none; border-radius: 50%;
      width: 120px; height: 120px; margin: -60px 0 0 -60px;
      background: radial-gradient(circle, rgba(255,255,255,.25) 0%, transparent 65%);
      transform: scale(0); animation: vg-r .7s cubic-bezier(.4,0,.2,1) forwards;
    }
    @keyframes vg-r { to { transform: scale(4.5); opacity: 0; } }

    /* Page entrance animation */
    section[data-testid="stMain"] > div:first-child {
      animation: vg-pg .4s cubic-bezier(.4,0,.2,1);
    }
    @keyframes vg-pg {
      from { opacity: 0; transform: translateY(10px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* Hover glow on stMetric */
    div[data-testid="stMetric"]:hover {
      border-color: rgba(99,102,241,.35) !important;
    }
  `;
  pdoc.head.appendChild(s);

  /* Ripple on all button clicks */
  pdoc.addEventListener('click', function(e) {
    const btn = e.target.closest('button');
    if (!btn) return;
    const r = pdoc.createElement('span');
    r.className = 'vg-ripple';
    const rect = btn.getBoundingClientRect();
    r.style.left = (e.clientX - rect.left) + 'px';
    r.style.top  = (e.clientY - rect.top)  + 'px';
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(r);
    setTimeout(() => r.remove(), 750);
  });
})();
"""


def inject_styles(is_dark: bool = True) -> None:
    theme_vars = _DARK_VARS if is_dark else _LIGHT_VARS
    st.markdown(
        f"<style>{theme_vars}{_ANIMATIONS}{_BASE_CSS}</style>",
        unsafe_allow_html=True,
    )


def inject_effects() -> None:
    components.html(f"<script>{_JS}</script>", height=0)
