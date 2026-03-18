"""
AI Code Reviewer Pro — Main Application
Run: pip install -r requirements.txt && streamlit run main_app.py
Requires: Free Groq API key → https://console.groq.com
"""

import ast, glob, json, os, time, requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from radon.complexity import cc_visit
from radon.metrics import mi_visit

# ── Auto-load .env file if present ───────────────────────────────────────────
def _load_env_file(folder: str = None) -> str:
    """Look for a .env file in the given folder (or cwd) and load GROQ_API_KEY."""
    search_dirs = []
    if folder and os.path.isdir(folder):
        search_dirs.append(folder)
    search_dirs.append(os.getcwd())
    for d in search_dirs:
        env_path = os.path.join(d, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GROQ_API_KEY"):
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                return parts[1].strip().strip('"').strip("'"), env_path
            except OSError:
                pass
    return "", ""

# ── Auto-load .env from project folder ───────────────────────────────────────
def load_env_key(folder_path: str) -> str:
    """Try to read GROQ_API_KEY from a .env file in the given folder."""
    if not folder_path:
        return ""
    env_path = os.path.join(folder_path, ".env")
    if not os.path.isfile(env_path):
        # also check one level up
        env_path = os.path.join(os.path.dirname(folder_path), ".env")
    if not os.path.isfile(env_path):
        return ""
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GROQ_API_KEY"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""

st.set_page_config(page_title="AI Code Reviewer", layout="wide", page_icon="🧠")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Oxanium:wght@300;400;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ══════════════════════════════════════
   DESIGN TOKENS
══════════════════════════════════════ */
:root{
  --bg:#01020a;--sf:#05070f;--sf2:#080b16;--sf3:#0b0f1c;
  --b1:#0f1628;--b2:#172040;--b3:#1e2e58;
  --cy:#00e5ff;--cy2:#00b8d9;--vi:#bf5af2;--vi2:#9333ea;
  --gn:#00ff9d;--gn2:#00c97a;--rd:#ff4d6d;--yw:#ffd60a;
  --tx:#c8d8f0;--tx2:#8fa8d0;--mt:#3a4d70;--mt2:#263454;
  --glow-cy:0 0 18px rgba(0,229,255,.45),0 0 50px rgba(0,229,255,.18);
  --glow-vi:0 0 18px rgba(191,90,242,.45),0 0 50px rgba(191,90,242,.18);
  --glow-gn:0 0 18px rgba(0,255,157,.45),0 0 50px rgba(0,255,157,.18);
  --mono:'Share Tech Mono',monospace;
  --head:'Oxanium',sans-serif;
  --body:'Space Grotesk',sans-serif;
}

/* ══════════════════════════════════════
   BASE + ANIMATED STARFIELD BACKGROUND
══════════════════════════════════════ */
html,body,[data-testid="stAppViewContainer"],[data-testid="stApp"]{
  background:var(--bg)!important;color:var(--tx)!important;font-family:var(--body)!important;
}
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(ellipse 900px 600px at 15% 10%, rgba(0,229,255,.035) 0%,transparent 65%),
    radial-gradient(ellipse 700px 700px at 85% 85%, rgba(191,90,242,.045) 0%,transparent 65%),
    radial-gradient(ellipse 500px 400px at 55% 45%, rgba(0,255,157,.018) 0%,transparent 65%),
    var(--bg)!important;
}

/* Scrolling dot grid */
[data-testid="stAppViewContainer"]::before{
  content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:radial-gradient(circle,rgba(0,229,255,.18) 1px,transparent 1px);
  background-size:36px 36px;
  animation:dotgrid-scroll 30s linear infinite;opacity:.35;
}
@keyframes dotgrid-scroll{0%{background-position:0 0;}100%{background-position:36px 36px;}}

/* Floating aurora */
[data-testid="stAppViewContainer"]::after{
  content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(ellipse 800px 500px at 20% 20%,rgba(0,229,255,.04) 0%,transparent 70%),
    radial-gradient(ellipse 600px 600px at 80% 80%,rgba(191,90,242,.05) 0%,transparent 70%);
  animation:aurora-float 15s ease-in-out infinite alternate;
}
@keyframes aurora-float{
  0%{transform:translate(0,0) scale(1);}
  50%{transform:translate(30px,-20px) scale(1.04);}
  100%{transform:translate(-20px,30px) scale(.97);}
}
[data-testid="stMain"]>div{position:relative;z-index:1;}

/* ══════════════════════════════════════
   SIDEBAR — GLASS
══════════════════════════════════════ */
[data-testid="stSidebar"]{
  background:linear-gradient(170deg,rgba(5,7,15,.97) 0%,rgba(8,11,22,.97) 100%)!important;
  border-right:1px solid var(--b3)!important;
  box-shadow:4px 0 50px rgba(0,229,255,.06),inset -1px 0 0 rgba(0,229,255,.04)!important;
  backdrop-filter:blur(24px)!important;
}
[data-testid="stSidebar"]::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;z-index:10;
  background:linear-gradient(90deg,transparent 0%,var(--cy) 30%,var(--vi) 60%,var(--gn) 80%,transparent 100%);
  background-size:200% 100%;
  animation:side-bar-flow 3.5s linear infinite;
}
@keyframes side-bar-flow{0%{background-position:200% 0;}100%{background-position:-200% 0;}}
[data-testid="stSidebar"]::after{
  content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(191,90,242,.25),transparent);
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] p{
  color:var(--mt)!important;font-family:var(--mono)!important;font-size:.7rem!important;
  letter-spacing:.1em!important;text-transform:uppercase!important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"]>div>div{
  background:var(--sf2)!important;border:1px solid var(--b3)!important;border-radius:8px!important;
  color:var(--cy)!important;font-family:var(--mono)!important;font-size:.82rem!important;
  transition:all .3s!important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"]>div>div:hover{
  border-color:var(--cy)!important;box-shadow:0 0 14px rgba(0,229,255,.18)!important;
}
[data-testid="stSidebar"] input{
  background:rgba(8,11,22,.9)!important;border:1px solid var(--b3)!important;border-radius:8px!important;
  color:var(--cy)!important;font-family:var(--mono)!important;font-size:.78rem!important;
  caret-color:var(--cy)!important;transition:all .3s!important;
}
[data-testid="stSidebar"] input:focus{
  border-color:var(--cy)!important;
  box-shadow:0 0 0 2px rgba(0,229,255,.14),var(--glow-cy)!important;outline:none!important;
}

/* ══════════════════════════════════════
   BUTTONS — NEON RIPPLE
══════════════════════════════════════ */
.stButton>button{
  background:linear-gradient(135deg,rgba(0,229,255,.07),rgba(0,229,255,.02))!important;
  border:1px solid rgba(0,229,255,.5)!important;border-radius:9px!important;
  color:var(--cy)!important;font-family:var(--mono)!important;font-size:.77rem!important;
  letter-spacing:.14em!important;text-transform:uppercase!important;
  padding:11px 22px!important;width:100%!important;
  transition:all .35s cubic-bezier(.4,0,.2,1)!important;
  box-shadow:0 0 12px rgba(0,229,255,.1),inset 0 1px 0 rgba(0,229,255,.06)!important;
  position:relative!important;overflow:hidden!important;
}
.stButton>button::before{
  content:'';position:absolute;top:50%;left:50%;width:0;height:0;
  background:radial-gradient(circle,rgba(0,229,255,.18) 0%,transparent 70%);
  transform:translate(-50%,-50%);
  transition:width .55s cubic-bezier(.4,0,.2,1),height .55s cubic-bezier(.4,0,.2,1);
  border-radius:50%;pointer-events:none;
}
.stButton>button:hover::before{width:320px;height:320px;}
.stButton>button:hover{
  border-color:var(--vi)!important;color:var(--vi)!important;
  background:linear-gradient(135deg,rgba(191,90,242,.1),rgba(191,90,242,.03))!important;
  box-shadow:var(--glow-vi),inset 0 1px 0 rgba(191,90,242,.08)!important;
  transform:translateY(-2px) scale(1.01)!important;
}
.stButton>button:active{transform:translateY(0) scale(.98)!important;}

/* apply-fix green variant */
.apply-btn .stButton>button,.apply-btn>div>button{
  background:linear-gradient(135deg,rgba(0,255,157,.12),rgba(0,229,255,.07))!important;
  border:1px solid rgba(0,255,157,.55)!important;color:var(--gn)!important;
  box-shadow:0 0 14px rgba(0,255,157,.14)!important;
}
.apply-btn .stButton>button:hover,.apply-btn>div>button:hover{
  box-shadow:var(--glow-gn)!important;background:rgba(0,255,157,.14)!important;
  transform:translateY(-2px) scale(1.01)!important;
}

/* ══════════════════════════════════════
   ANIMATED STAT CARDS (Home page)
══════════════════════════════════════ */
.stat-card{
  background:linear-gradient(135deg,var(--sf2),var(--sf3));
  border:1px solid var(--b2);border-radius:14px;
  padding:20px 22px;position:relative;overflow:hidden;
  transition:transform .35s cubic-bezier(.34,1.3,.64,1),box-shadow .35s;
  animation:stat-pop .55s cubic-bezier(.34,1.4,.64,1) both;
}
@keyframes stat-pop{
  0%{opacity:0;transform:scale(.8) translateY(12px);}
  60%{transform:scale(1.04) translateY(-2px);}
  100%{opacity:1;transform:scale(1) translateY(0);}
}
.stat-card:hover{transform:translateY(-6px) scale(1.02);box-shadow:0 22px 50px rgba(0,0,0,.5);}
.stat-card::before{
  content:'';position:absolute;top:0;left:-150%;width:80%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.04),transparent);
  animation:card-shine 5s ease-in-out infinite;
}
@keyframes card-shine{0%{left:-150%;}60%,100%{left:200%;}}
.stat-card::after{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,currentColor,transparent);
  opacity:.45;
}
.stat-num{
  font-family:var(--mono)!important;font-size:2.4rem;font-weight:800;line-height:1;
  animation:num-in .7s cubic-bezier(.34,1.4,.64,1) .2s both;
}
@keyframes num-in{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
.stat-label{font-family:var(--mono)!important;font-size:.58rem;letter-spacing:.16em;text-transform:uppercase;margin-top:8px;opacity:.5;}

/* ══════════════════════════════════════
   METRIC CARDS (Metrics page)
══════════════════════════════════════ */
.metric-card{
  background:linear-gradient(135deg,var(--sf2),var(--sf3));
  border:1px solid var(--b2);border-radius:14px;padding:24px 26px;
  margin-bottom:14px;position:relative;overflow:hidden;
  transition:transform .3s cubic-bezier(.4,0,.2,1),box-shadow .3s;
  animation:card-enter .5s cubic-bezier(.4,0,.2,1) both;
}
@keyframes card-enter{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:translateY(0);}}
.metric-card:hover{transform:translateY(-4px);box-shadow:0 16px 45px rgba(0,0,0,.45),0 0 25px rgba(0,229,255,.07);}
.metric-card::before{
  content:'';position:absolute;top:0;left:-100%;width:60%;height:1px;
  background:linear-gradient(90deg,transparent,var(--cy),var(--vi),transparent);
  animation:scan-line 4.5s linear infinite;
}
@keyframes scan-line{0%{left:-60%;}100%{left:160%;}}
.metric-card h1{
  font-size:2.9rem;font-weight:800;margin:0;font-family:var(--mono)!important;
  background:linear-gradient(135deg,var(--cy),var(--vi));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  line-height:1;filter:drop-shadow(0 0 10px rgba(0,229,255,.3));
}
.metric-card p{font-size:.66rem;color:var(--mt);margin:7px 0 0;letter-spacing:.15em;text-transform:uppercase;font-family:var(--mono)!important;}

/* ══════════════════════════════════════
   FUNCTION CARDS
══════════════════════════════════════ */
.fn-card{
  background:linear-gradient(90deg,rgba(0,229,255,.04),var(--sf3));
  border:1px solid var(--b1);border-left:2px solid var(--cy);
  border-radius:10px;padding:14px 20px;margin-bottom:6px;
  display:flex;align-items:center;justify-content:space-between;
  font-family:var(--mono);position:relative;overflow:hidden;
  transition:all .28s cubic-bezier(.4,0,.2,1);
  animation:slide-in .4s cubic-bezier(.4,0,.2,1) both;
}
@keyframes slide-in{from{opacity:0;transform:translateX(-10px);}to{opacity:1;transform:translateX(0);}}
.fn-card::after{
  content:'';position:absolute;bottom:0;left:0;right:100%;height:1px;
  background:linear-gradient(90deg,var(--cy),var(--vi));
  transition:right .4s cubic-bezier(.4,0,.2,1);
}
.fn-card:hover{
  background:linear-gradient(90deg,rgba(0,229,255,.07),rgba(191,90,242,.04));
  border-left-color:var(--vi);transform:translateX(4px);
  box-shadow:0 4px 20px rgba(0,0,0,.3),-4px 0 14px rgba(0,229,255,.08);
}
.fn-card:hover::after{right:0;}
.fn-card::before{content:'›';position:absolute;left:7px;top:50%;transform:translateY(-50%);color:var(--cy);font-size:.75rem;opacity:.45;transition:opacity .2s,color .2s;}
.fn-card:hover::before{opacity:1;color:var(--vi);}
.fn-name{font-size:.88rem;color:var(--cy);letter-spacing:.02em;transition:color .2s;}
.fn-card:hover .fn-name{color:#fff;}
.fn-line{font-size:.68rem;color:var(--mt);margin-top:3px;letter-spacing:.04em;}

/* ══════════════════════════════════════
   BADGES
══════════════════════════════════════ */
.fn-badge{
  font-size:.62rem;padding:4px 12px;border-radius:20px;font-weight:700;
  font-family:var(--mono);letter-spacing:.1em;text-transform:uppercase;transition:box-shadow .2s;
}
.badge-ok{background:rgba(0,255,157,.1);color:var(--gn);border:1px solid rgba(0,255,157,.35);box-shadow:0 0 8px rgba(0,255,157,.12);}
.badge-warn{background:rgba(255,214,10,.1);color:var(--yw);border:1px solid rgba(255,214,10,.35);box-shadow:0 0 8px rgba(255,214,10,.12);}
.badge-bad{background:rgba(255,77,109,.1);color:var(--rd);border:1px solid rgba(255,77,109,.35);box-shadow:0 0 8px rgba(255,77,109,.1);}
.badge-doc{background:rgba(0,229,255,.08);color:var(--cy);border:1px solid rgba(0,229,255,.3);box-shadow:0 0 8px rgba(0,229,255,.09);}
.badge-nodoc{background:rgba(255,77,109,.08);color:var(--rd);border:1px solid rgba(255,77,109,.3);}
.fn-badge:hover{filter:brightness(1.2);}

/* ══════════════════════════════════════
   FILE HEADERS
══════════════════════════════════════ */
.file-header{
  background:linear-gradient(90deg,rgba(0,229,255,.08),rgba(0,229,255,.02),transparent);
  border:1px solid var(--b2);border-left:3px solid var(--cy);border-radius:10px;
  padding:12px 18px;margin:18px 0 6px;display:flex;align-items:center;gap:12px;
  font-family:var(--mono);font-size:.82rem;color:var(--cy);letter-spacing:.06em;
  position:relative;overflow:hidden;transition:border-left-color .3s,box-shadow .3s;
  animation:card-enter .4s ease-out;
}
.file-header:hover{border-left-color:var(--vi);box-shadow:0 0 22px rgba(191,90,242,.1);}
.file-header::before{
  content:'';position:absolute;top:0;left:0;bottom:0;width:2px;
  background:linear-gradient(180deg,transparent,var(--cy),transparent);
  animation:vert-scan 3.5s linear infinite;
}
@keyframes vert-scan{0%{top:-100%;}100%{top:200%;}}

/* ══════════════════════════════════════
   ISSUE CARDS
══════════════════════════════════════ */
.issue-card{
  background:linear-gradient(135deg,rgba(255,77,109,.055),rgba(255,77,109,.02));
  border:1px solid rgba(255,77,109,.22);border-left:3px solid var(--rd);
  border-radius:10px;padding:13px 18px;margin:6px 0;
  font-family:var(--mono);font-size:.78rem;
  transition:all .25s;animation:fade-up .32s cubic-bezier(.4,0,.2,1) both;
}
@keyframes fade-up{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
.issue-card:hover{background:rgba(255,77,109,.1);transform:translateX(3px);box-shadow:0 4px 18px rgba(255,77,109,.12);}
.issue-code{color:var(--rd);font-weight:700;letter-spacing:.06em;}
.issue-fn{display:inline-block;background:rgba(0,229,255,.08);color:var(--cy);padding:2px 10px;border-radius:12px;font-size:.7rem;margin-bottom:6px;border:1px solid rgba(0,229,255,.2);}
.issue-msg{color:#f4a4b0;font-size:.77rem;}

/* ══════════════════════════════════════
   STEP CARDS (Home onboarding)
══════════════════════════════════════ */
.step-card{
  border-radius:14px;padding:24px 22px;position:relative;overflow:hidden;
  transition:transform .4s cubic-bezier(.34,1.3,.64,1),box-shadow .4s;
  animation:stat-pop .55s cubic-bezier(.34,1.4,.64,1) both;
}
.step-card:hover{transform:translateY(-7px) scale(1.02);}
.step-card::before{
  content:'';position:absolute;top:-100%;left:-100%;width:300%;height:300%;
  background:conic-gradient(from 0deg at 50% 50%,
    transparent 0deg,rgba(255,255,255,.05) 60deg,transparent 120deg,
    rgba(255,255,255,.03) 180deg,transparent 240deg,rgba(255,255,255,.04) 300deg,transparent 360deg);
  animation:holo-spin 8s linear infinite;opacity:0;transition:opacity .4s;
}
.step-card:hover::before{opacity:1;}
@keyframes holo-spin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}

/* ══════════════════════════════════════
   DOCSTRING BLOCKS
══════════════════════════════════════ */
.docstring-block{
  background:linear-gradient(135deg,#010208,#040310);
  border:1px solid rgba(191,90,242,.25);border-left:3px solid var(--vi);
  border-radius:10px;padding:16px 20px;font-family:var(--mono);
  font-size:.75rem;color:#c4b5fd;white-space:pre;overflow-x:auto;
  line-height:1.8;margin-top:4px;margin-bottom:12px;
  box-shadow:0 4px 22px rgba(191,90,242,.08),inset 0 1px 0 rgba(191,90,242,.06);
}
.docstring-fn-header{
  background:linear-gradient(90deg,rgba(191,90,242,.09),transparent);
  border:1px solid rgba(191,90,242,.22);border-left:3px solid var(--vi);
  border-radius:10px;padding:11px 18px;margin:14px 0 4px;
  font-family:var(--mono);font-size:.8rem;color:var(--vi);
  display:flex;align-items:center;gap:12px;
  transition:all .25s;
}
.docstring-fn-header:hover{background:rgba(191,90,242,.13);transform:translateX(3px);}

/* ══════════════════════════════════════
   JSON VIEWER
══════════════════════════════════════ */
.json-viewer{
  background:linear-gradient(135deg,#010206,#030409);
  border:1px solid var(--b2);border-radius:12px;
  padding:18px 20px;font-family:var(--mono);font-size:.74rem;
  color:#4a9eff;overflow-x:auto;white-space:pre;max-height:380px;overflow-y:auto;
  line-height:1.7;box-shadow:inset 0 2px 10px rgba(0,0,0,.5);
}
.json-viewer::-webkit-scrollbar{width:4px;height:4px;}
.json-viewer::-webkit-scrollbar-thumb{background:var(--b3);border-radius:2px;}
.json-viewer::-webkit-scrollbar-thumb:hover{background:var(--cy);}

/* ══════════════════════════════════════
   FILE PILLS (sidebar)
══════════════════════════════════════ */
.file-pill{
  display:flex;align-items:center;gap:9px;
  background:linear-gradient(90deg,var(--sf3),var(--sf2));
  border:1px solid var(--b1);border-radius:8px;padding:8px 12px;margin-bottom:5px;
  transition:all .25s;position:relative;overflow:hidden;
}
.file-pill::before{
  content:'';position:absolute;left:0;top:0;bottom:0;width:0;
  background:linear-gradient(90deg,rgba(0,229,255,.07),transparent);transition:width .3s;
}
.file-pill:hover{background:rgba(0,229,255,.05);border-color:var(--b2);transform:translateX(3px);}
.file-pill:hover::before{width:100%;}

/* ══════════════════════════════════════
   TABS
══════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"]{
  border-bottom:1px solid var(--b2)!important;gap:4px!important;
  background:rgba(5,7,15,.6)!important;border-radius:10px 10px 0 0!important;padding:4px 4px 0!important;
}
[data-testid="stTabs"] [role="tab"]{
  font-family:var(--mono)!important;font-size:.7rem!important;letter-spacing:.12em!important;
  text-transform:uppercase!important;color:var(--mt)!important;
  border-radius:8px 8px 0 0!important;padding:9px 18px!important;border:none!important;
  transition:all .25s!important;position:relative!important;
}
[data-testid="stTabs"] [role="tab"]::after{
  content:'';position:absolute;bottom:0;left:50%;right:50%;height:2px;
  background:linear-gradient(90deg,var(--cy),var(--vi));
  transition:left .3s,right .3s;border-radius:2px 2px 0 0;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
  color:var(--cy)!important;background:rgba(0,229,255,.06)!important;
  text-shadow:0 0 12px rgba(0,229,255,.4)!important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]::after{left:0!important;right:0!important;}

/* ══════════════════════════════════════
   EXPANDERS
══════════════════════════════════════ */
[data-testid="stExpander"]{
  background:linear-gradient(135deg,rgba(8,11,22,.95),rgba(5,7,15,.95))!important;
  border:1px solid var(--b2)!important;border-radius:12px!important;
  overflow:hidden!important;transition:border-color .2s,box-shadow .2s!important;
}
[data-testid="stExpander"]:hover{border-color:var(--b3)!important;box-shadow:0 4px 20px rgba(0,0,0,.35)!important;}
[data-testid="stExpander"] summary{font-family:var(--mono)!important;font-size:.78rem!important;color:var(--tx)!important;}

/* ══════════════════════════════════════
   st.metric
══════════════════════════════════════ */
[data-testid="stMetric"]{
  background:linear-gradient(135deg,var(--sf2),var(--sf3))!important;
  border:1px solid var(--b2)!important;border-radius:14px!important;padding:18px 22px!important;
  position:relative!important;overflow:hidden!important;transition:all .3s!important;
}
[data-testid="stMetric"]::before{
  content:'';position:absolute;top:0;left:-60%;width:60%;height:1px;
  background:linear-gradient(90deg,transparent,var(--cy),transparent);
  animation:metric-scan 5s linear infinite;
}
@keyframes metric-scan{0%{left:-60%;}100%{left:160%;}}
[data-testid="stMetric"]:hover{
  transform:translateY(-3px)!important;border-color:var(--b3)!important;
  box-shadow:0 10px 35px rgba(0,0,0,.35),0 0 18px rgba(0,229,255,.06)!important;
}
[data-testid="stMetricLabel"]{font-family:var(--mono)!important;font-size:.66rem!important;letter-spacing:.12em!important;text-transform:uppercase!important;color:var(--mt)!important;}
[data-testid="stMetricValue"]{font-family:var(--mono)!important;font-size:2rem!important;color:var(--cy)!important;text-shadow:0 0 14px rgba(0,229,255,.35)!important;}

/* ══════════════════════════════════════
   DATAFRAME / ALERTS / DL BUTTONS
══════════════════════════════════════ */
[data-testid="stDataFrame"]{border:1px solid var(--b2)!important;border-radius:12px!important;overflow:hidden!important;box-shadow:0 4px 22px rgba(0,0,0,.35)!important;}
[data-testid="stAlert"]{
  background:linear-gradient(135deg,rgba(0,255,157,.07),rgba(0,255,157,.02))!important;
  border:1px solid rgba(0,255,157,.28)!important;border-radius:10px!important;
  font-family:var(--mono)!important;font-size:.8rem!important;color:var(--gn)!important;
  animation:alert-pulse 2.5s ease-in-out infinite;
}
@keyframes alert-pulse{0%,100%{box-shadow:0 0 8px rgba(0,255,157,.08);}50%{box-shadow:0 0 20px rgba(0,255,157,.2);}}
[data-testid="stDownloadButton"] button{
  background:linear-gradient(135deg,rgba(0,229,255,.04),transparent)!important;
  border:1px solid var(--b3)!important;border-radius:8px!important;color:var(--tx2)!important;
  font-family:var(--mono)!important;font-size:.7rem!important;letter-spacing:.1em!important;
  text-transform:uppercase!important;transition:all .3s!important;width:100%!important;
}
[data-testid="stDownloadButton"] button:hover{
  border-color:var(--cy)!important;color:var(--cy)!important;
  box-shadow:0 0 14px rgba(0,229,255,.18)!important;transform:translateY(-1px)!important;
}

/* ══════════════════════════════════════
   PROGRESS / SPINNER / SELECTS
══════════════════════════════════════ */
[data-testid="stProgress"]>div>div{
  background:linear-gradient(90deg,var(--cy),var(--vi))!important;
  border-radius:4px!important;box-shadow:0 0 12px rgba(0,229,255,.45)!important;
}
[data-testid="stProgress"]{background:var(--sf2)!important;border-radius:4px!important;}
[data-testid="stSpinner"]>div{border-top-color:var(--cy)!important;border-right-color:rgba(0,229,255,.2)!important;}
[data-testid="stRadio"]>div{display:flex!important;flex-direction:row!important;gap:20px!important;background:var(--sf2)!important;border:1px solid var(--b2)!important;border-radius:10px!important;padding:12px 20px!important;}
[data-testid="stRadio"] label{color:var(--tx)!important;font-family:var(--mono)!important;font-size:.78rem!important;letter-spacing:.04em!important;}
[data-testid="stSelectbox"]>div>div{background:var(--sf2)!important;border:1px solid var(--b2)!important;border-radius:10px!important;color:var(--tx)!important;transition:all .3s!important;}
[data-testid="stSelectbox"]>div>div:focus-within{border-color:var(--cy)!important;box-shadow:0 0 0 2px rgba(0,229,255,.1)!important;}
[data-testid="stTextInput"]>div>div>input{background:var(--sf2)!important;border:1px solid var(--b2)!important;border-radius:10px!important;color:var(--tx)!important;font-family:var(--mono)!important;transition:all .3s!important;caret-color:var(--cy)!important;}
[data-testid="stTextInput"]>div>div>input:focus{border-color:var(--cy)!important;box-shadow:0 0 0 2px rgba(0,229,255,.1)!important;outline:none!important;}

/* ══════════════════════════════════════
   GLOBAL MISC
══════════════════════════════════════ */
::selection{background:rgba(0,229,255,.2);color:var(--cy);}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--sf);}
::-webkit-scrollbar-thumb{background:var(--b3);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--cy);}
#MainMenu,footer,header{visibility:hidden;}
hr{border:none!important;border-top:1px solid var(--b1)!important;margin:22px 0!important;opacity:.5!important;}

/* ══════════════════════════════════════
   AI-FIX SECTION
══════════════════════════════════════ */
.ai-fix-banner{
  background:linear-gradient(135deg,rgba(191,90,242,.11),rgba(0,229,255,.06),rgba(191,90,242,.05));
  border:1px solid rgba(191,90,242,.38);border-left:3px solid var(--vi);
  border-radius:14px;padding:20px 24px;margin:18px 0;position:relative;overflow:hidden;
  box-shadow:0 4px 30px rgba(191,90,242,.09);animation:banner-enter .5s cubic-bezier(.4,0,.2,1) both;
}
@keyframes banner-enter{from{opacity:0;transform:translateY(-8px);}to{opacity:1;transform:translateY(0);}}
.ai-fix-banner::before{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--vi),var(--cy),var(--gn),transparent);
  background-size:200%;animation:side-bar-flow 3s linear infinite;
}
.ai-fix-banner::after{
  content:'';position:absolute;top:-50%;right:-15%;width:220px;height:220px;
  background:radial-gradient(circle,rgba(191,90,242,.09) 0%,transparent 70%);
  animation:float-orb 7s ease-in-out infinite alternate;pointer-events:none;
}
@keyframes float-orb{0%{transform:translate(0,0);}100%{transform:translate(-25px,25px);}}
.ai-fix-header{font-family:var(--mono);font-size:.6rem;color:#9d4edd;letter-spacing:.2em;text-transform:uppercase;margin-bottom:6px;animation:text-flicker 5s ease-in-out infinite;}
@keyframes text-flicker{0%,94%,100%{opacity:.7;}95%,98%{opacity:.3;}}
.ai-fix-title{
  font-family:var(--head);font-size:1.02rem;font-weight:800;
  background:linear-gradient(90deg,var(--vi),var(--cy),var(--vi));background-size:200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  animation:grad-shift 4s linear infinite;margin-bottom:4px;
}
@keyframes grad-shift{0%{background-position:0%;}100%{background-position:200%;}}
.ai-fix-desc{font-family:var(--mono);font-size:.72rem;color:var(--mt);line-height:1.7;}
.fixed-code-block{
  background:linear-gradient(135deg,#010206,#030409);
  border:1px solid rgba(0,255,157,.22);border-left:3px solid var(--gn);
  border-radius:10px;padding:18px 20px;font-family:var(--mono);font-size:.75rem;color:#86efac;
  white-space:pre-wrap;overflow-x:auto;line-height:1.8;margin:10px 0;max-height:500px;overflow-y:auto;
  box-shadow:inset 0 0 30px rgba(0,0,0,.6),0 0 20px rgba(0,255,157,.06);
}
.fixed-code-block::-webkit-scrollbar{width:4px;height:4px;}
.fixed-code-block::-webkit-scrollbar-thumb{background:rgba(0,255,157,.25);border-radius:2px;}
.fix-status-ok{
  background:rgba(0,255,157,.08);border:1px solid rgba(0,255,157,.3);border-radius:8px;
  padding:10px 16px;font-family:var(--mono);font-size:.72rem;color:var(--gn);letter-spacing:.06em;margin:8px 0;
  animation:status-ok-glow 2.5s ease-in-out infinite;
}
@keyframes status-ok-glow{0%,100%{box-shadow:0 0 8px rgba(0,255,157,.1);}50%{box-shadow:0 0 20px rgba(0,255,157,.28);}}
.fix-status-err{
  background:rgba(255,77,109,.08);border:1px solid rgba(255,77,109,.3);border-radius:8px;
  padding:10px 16px;font-family:var(--mono);font-size:.72rem;color:var(--rd);letter-spacing:.06em;margin:8px 0;
  animation:status-err-glow 2.5s ease-in-out infinite;
}
@keyframes status-err-glow{0%,100%{box-shadow:0 0 8px rgba(255,77,109,.1);}50%{box-shadow:0 0 18px rgba(255,77,109,.25);}}
.fix-thinking{
  background:rgba(191,90,242,.06);border:1px solid rgba(191,90,242,.22);
  border-radius:8px;padding:12px 18px;font-family:var(--mono);font-size:.73rem;color:#9d4edd;
  letter-spacing:.04em;animation:ai-thinking .9s ease-in-out infinite;
}
@keyframes ai-thinking{0%,100%{opacity:.55;box-shadow:0 0 8px rgba(191,90,242,.1);}50%{opacity:1;box-shadow:0 0 22px rgba(191,90,242,.32);}}
.diff-added{color:var(--gn);text-shadow:0 0 6px rgba(0,255,157,.3);}
.diff-removed{color:var(--rd);text-shadow:0 0 6px rgba(255,77,109,.3);}

/* ══════════════════════════════════════
   SCANLINES + SELECTION
══════════════════════════════════════ */
body::after{
  content:'';position:fixed;inset:0;z-index:9999;pointer-events:none;
  background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,229,255,.005) 3px,rgba(0,229,255,.005) 4px);
}

</style>""", unsafe_allow_html=True)

# ── NEXT-LEVEL JavaScript: Advanced Particle Universe + FX ───────────────────
st.markdown("""
<canvas id="pcv" style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;"></canvas>
<div id="c-orb"  style="position:fixed;pointer-events:none;z-index:2;will-change:transform;top:0;left:0;"></div>
<div id="c-orb2" style="position:fixed;pointer-events:none;z-index:2;will-change:transform;top:0;left:0;"></div>

<script>
(function(){
'use strict';

/* ═══════════════════════════════════════════════════
   0. WAIT FOR DOM
═══════════════════════════════════════════════════ */
function init(){
  const cv = document.getElementById('pcv');
  if(!cv){ setTimeout(init,200); return; }
  const ctx = cv.getContext('2d');
  let W, H;

  function resize(){
    W = cv.width  = window.innerWidth;
    H = cv.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  /* ─── MOUSE ─── */
  const mouse = { x: W/2, y: H/2, vx:0, vy:0, px:W/2, py:H/2 };
  window.addEventListener('mousemove', e => {
    mouse.vx = e.clientX - mouse.x;
    mouse.vy = e.clientY - mouse.y;
    mouse.px = mouse.x; mouse.py = mouse.y;
    mouse.x  = e.clientX; mouse.y = e.clientY;
  });

  /* ═══════════════════════════════════════════════════
     1. PARTICLE UNIVERSE — 3 layers
     Layer A: large slow glowing orbs (background depth)
     Layer B: medium floating particles (mid)
     Layer C: tiny fast sparks  (foreground sparkle)
  ═══════════════════════════════════════════════════ */
  const PALLETE = [
    [0,229,255],   // cyan
    [191,90,242],  // violet
    [0,255,157],   // green
    [255,214,10],  // yellow
    [255,45,120],  // pink
  ];

  /* ── LAYER A: glowing background orbs ── */
  class Orb {
    constructor(){this.reset(true);}
    reset(init){
      this.x  = Math.random()*W;
      this.y  = init ? Math.random()*H : H + 60;
      this.r  = Math.random()*28 + 14;
      this.vx = (Math.random()-.5)*.18;
      this.vy = -(Math.random()*.22 + .06);
      this.life = 0;
      this.maxL = Math.random()*600+300;
      const c = PALLETE[Math.floor(Math.random()*PALLETE.length)];
      this.rgb = c;
      this.pulse = Math.random()*Math.PI*2;
    }
    update(){
      this.life++;
      this.pulse += .018;
      const pr = .5+Math.sin(this.pulse)*.5;
      this.a = pr * (this.life<40?this.life/40:this.life>this.maxL-40?(this.maxL-this.life)/40:1) * .18;
      // mouse gravity — orbs drift toward cursor slowly
      const dx=mouse.x-this.x, dy=mouse.y-this.y, d=Math.sqrt(dx*dx+dy*dy);
      if(d<300){ this.vx += dx/d*.0015; this.vy += dy/d*.0015; }
      this.vx *= .999; this.vy *= .999;
      this.x += this.vx; this.y += this.vy;
      if(this.life>this.maxL||this.y<-80) this.reset();
    }
    draw(){
      const g = ctx.createRadialGradient(this.x,this.y,0,this.x,this.y,this.r);
      g.addColorStop(0, `rgba(${this.rgb},${this.a})`);
      g.addColorStop(.5,`rgba(${this.rgb},${this.a*.4})`);
      g.addColorStop(1, `rgba(${this.rgb},0)`);
      ctx.beginPath(); ctx.arc(this.x,this.y,this.r,0,Math.PI*2);
      ctx.fillStyle=g; ctx.fill();
    }
  }

  /* ── LAYER B: standard constellation particles ── */
  class Particle {
    constructor(){ this.reset(true); }
    reset(init){
      this.x  = Math.random()*W;
      this.y  = init ? Math.random()*H : H+6;
      this.r  = Math.random()*1.8+.4;
      this.vx = (Math.random()-.5)*.45;
      this.vy = -(Math.random()*.55+.12);
      this.life=0; this.maxL=Math.random()*300+120;
      const c = PALLETE[Math.floor(Math.random()*PALLETE.length)];
      this.rgb=c; this.a=0;
      this.twinkle=Math.random()*Math.PI*2;
    }
    update(){
      this.life++; this.twinkle+=.04;
      const tw = .65 + Math.sin(this.twinkle)*.35;
      this.a = tw*(this.life<30?this.life/30:this.life>this.maxL-30?(this.maxL-this.life)/30:.7);
      // mouse repel
      const dx=this.x-mouse.x, dy=this.y-mouse.y, d=Math.sqrt(dx*dx+dy*dy);
      if(d<120){ const f=.32*(1-d/120); this.vx+=dx/d*f; this.vy+=dy/d*f; }
      // mouse velocity drag (creates swirl trail)
      if(d<200){ this.vx+=mouse.vx*.004; this.vy+=mouse.vy*.004; }
      this.vx*=.998; this.vy*=.998;
      this.x+=this.vx; this.y+=this.vy;
      if(this.life>this.maxL||this.y<-6) this.reset();
    }
    draw(){
      ctx.save();
      ctx.globalAlpha=this.a;
      ctx.shadowColor=`rgb(${this.rgb})`; ctx.shadowBlur=12;
      ctx.fillStyle=`rgb(${this.rgb})`;
      ctx.beginPath(); ctx.arc(this.x,this.y,this.r,0,Math.PI*2); ctx.fill();
      ctx.restore();
    }
  }

  /* ── LAYER C: micro sparks ── */
  class Spark {
    constructor(){ this.reset(true); }
    reset(init){
      this.x  = Math.random()*W;
      this.y  = init ? Math.random()*H : Math.random()*H;
      this.r  = Math.random()*.7+.15;
      const angle = Math.random()*Math.PI*2;
      const spd   = Math.random()*.8+.2;
      this.vx = Math.cos(angle)*spd;
      this.vy = Math.sin(angle)*spd - .3;
      this.life=0; this.maxL=Math.random()*180+60;
      const c=PALLETE[Math.floor(Math.random()*PALLETE.length)];
      this.rgb=c; this.a=0;
    }
    update(){
      this.life++;
      this.a = this.life<20?this.life/20:this.life>this.maxL-20?(this.maxL-this.life)/20:.5;
      this.x+=this.vx; this.y+=this.vy;
      this.vy -= .003;
      if(this.life>this.maxL||this.y<-4||this.y>H+4) this.reset();
    }
    draw(){
      ctx.save(); ctx.globalAlpha=this.a*.5;
      ctx.fillStyle=`rgb(${this.rgb})`;
      ctx.beginPath(); ctx.arc(this.x,this.y,this.r,0,Math.PI*2); ctx.fill();
      ctx.restore();
    }
  }

  /* Spawn all layers */
  const orbs=[]; for(let i=0;i<18;i++) orbs.push(new Orb());
  const particles=[]; for(let i=0;i<90;i++) particles.push(new Particle());
  const sparks=[]; for(let i=0;i<55;i++) sparks.push(new Spark());

  /* ── NEBULA energy lines radiating from mouse ── */
  function drawEnergyLines(){
    if(Math.abs(mouse.vx)+Math.abs(mouse.vy)<2) return;
    const speed = Math.sqrt(mouse.vx*mouse.vx+mouse.vy*mouse.vy);
    const n = Math.min(6, Math.floor(speed/2));
    for(let i=0;i<n;i++){
      const angle = Math.atan2(mouse.vy,mouse.vx) + (Math.random()-.5)*.6;
      const len   = Math.random()*80+20;
      const c     = PALLETE[Math.floor(Math.random()*PALLETE.length)];
      const g     = ctx.createLinearGradient(
        mouse.x, mouse.y,
        mouse.x+Math.cos(angle)*len,
        mouse.y+Math.sin(angle)*len
      );
      g.addColorStop(0, `rgba(${c},.18)`);
      g.addColorStop(1, `rgba(${c},0)`);
      ctx.beginPath();
      ctx.moveTo(mouse.x, mouse.y);
      ctx.lineTo(mouse.x+Math.cos(angle)*len, mouse.y+Math.sin(angle)*len);
      ctx.strokeStyle=g; ctx.lineWidth=Math.random()*1.4+.3;
      ctx.globalAlpha=.6; ctx.stroke(); ctx.globalAlpha=1;
    }
  }

  /* ── Constellation between nearby particles ── */
  function drawConstellation(){
    for(let i=0;i<particles.length;i++){
      for(let j=i+1;j<particles.length;j++){
        const dx=particles[i].x-particles[j].x, dy=particles[i].y-particles[j].y;
        const d=Math.sqrt(dx*dx+dy*dy);
        if(d<90){
          ctx.save();
          ctx.globalAlpha=.06*(1-d/90)*Math.min(particles[i].a,particles[j].a);
          ctx.strokeStyle=`rgb(${particles[i].rgb})`;
          ctx.lineWidth=.35;
          ctx.beginPath(); ctx.moveTo(particles[i].x,particles[i].y);
          ctx.lineTo(particles[j].x,particles[j].y); ctx.stroke();
          ctx.restore();
        }
      }
    }
  }

  /* ── MAIN RENDER LOOP ── */
  let frameCount = 0;
  function frame(){
    frameCount++;
    ctx.clearRect(0,0,W,H);

    // layer A orbs (drawn first — background depth)
    orbs.forEach(o=>{ o.update(); o.draw(); });

    // constellation
    drawConstellation();

    // layer B particles
    particles.forEach(p=>{ p.update(); p.draw(); });

    // energy lines (only every 2nd frame for perf)
    if(frameCount%2===0) drawEnergyLines();

    // layer C sparks
    sparks.forEach(s=>{ s.update(); s.draw(); });

    requestAnimationFrame(frame);
  }
  frame();

  /* ═══════════════════════════════════════════════════
     2. DUAL CURSOR ORBS  — primary + lagging secondary
  ═══════════════════════════════════════════════════ */
  const orb1 = document.getElementById('c-orb');
  const orb2 = document.getElementById('c-orb2');

  // Styling
  orb1.style.cssText = 'position:fixed;top:0;left:0;width:420px;height:420px;border-radius:50%;pointer-events:none;z-index:2;transform:translate(-50%,-50%);background:radial-gradient(circle,rgba(0,229,255,.055) 0%,rgba(0,229,255,.015) 40%,transparent 70%);will-change:transform;transition:none;';
  orb2.style.cssText = 'position:fixed;top:0;left:0;width:220px;height:220px;border-radius:50%;pointer-events:none;z-index:2;transform:translate(-50%,-50%);background:radial-gradient(circle,rgba(191,90,242,.07) 0%,rgba(191,90,242,.02) 45%,transparent 70%);will-change:transform;transition:none;';

  let o1x=W/2,o1y=H/2, o2x=W/2,o2y=H/2;
  let tx=W/2,ty=H/2;
  window.addEventListener('mousemove',e=>{tx=e.clientX;ty=e.clientY;});

  function animOrbs(){
    // orb1: fast follow
    o1x += (tx-o1x)*.12;
    o1y += (ty-o1y)*.12;
    // orb2: slow lag — creates parallax ghost effect
    o2x += (tx-o2x)*.045;
    o2y += (ty-o2y)*.045;

    orb1.style.left = o1x+'px'; orb1.style.top = o1y+'px';
    orb2.style.left = o2x+'px'; orb2.style.top = o2y+'px';
    requestAnimationFrame(animOrbs);
  }
  animOrbs();

  /* ═══════════════════════════════════════════════════
     3. CLICK SHOCKWAVE — expanding ring burst
  ═══════════════════════════════════════════════════ */
  window.addEventListener('click', e => {
    // Shockwave ring
    const ring = document.createElement('div');
    ring.style.cssText = `
      position:fixed;border-radius:50%;pointer-events:none;z-index:9997;
      left:${e.clientX}px;top:${e.clientY}px;
      width:8px;height:8px;
      transform:translate(-50%,-50%) scale(0);
      border:2px solid rgba(0,229,255,.8);
      box-shadow:0 0 12px rgba(0,229,255,.5),inset 0 0 8px rgba(0,229,255,.2);
      animation:shockwave .65s cubic-bezier(0,.5,.3,1) forwards;
    `;
    document.body.appendChild(ring);
    setTimeout(()=>ring.remove(), 700);

    // Second ring — violet, slightly delayed
    const ring2 = document.createElement('div');
    ring2.style.cssText = `
      position:fixed;border-radius:50%;pointer-events:none;z-index:9997;
      left:${e.clientX}px;top:${e.clientY}px;
      width:4px;height:4px;
      transform:translate(-50%,-50%) scale(0);
      border:1px solid rgba(191,90,242,.6);
      animation:shockwave .8s .08s cubic-bezier(0,.5,.3,1) forwards;
    `;
    document.body.appendChild(ring2);
    setTimeout(()=>ring2.remove(), 900);

    // Spark burst from click point
    for(let i=0;i<8;i++){
      const dot=document.createElement('div');
      const angle=Math.random()*Math.PI*2;
      const dist=Math.random()*55+20;
      const c=PALLETE[Math.floor(Math.random()*PALLETE.length)];
      dot.style.cssText=`
        position:fixed;pointer-events:none;z-index:9997;
        left:${e.clientX}px;top:${e.clientY}px;
        width:4px;height:4px;border-radius:50%;
        background:rgb(${c});
        box-shadow:0 0 6px rgb(${c});
        animation:dot-fly .55s cubic-bezier(0,1,.6,1) forwards;
        --tx:${Math.cos(angle)*dist}px;--ty:${Math.sin(angle)*dist}px;
      `;
      document.body.appendChild(dot);
      setTimeout(()=>dot.remove(),600);
    }

    // Button ripple
    const btn=e.target.closest('button');
    if(btn){
      const rip=document.createElement('span');
      const rect=btn.getBoundingClientRect();
      const sz=Math.max(rect.width,rect.height)*2.2;
      rip.style.cssText=`position:absolute;border-radius:50%;background:rgba(0,229,255,.22);pointer-events:none;width:${sz}px;height:${sz}px;left:${e.clientX-rect.left-sz/2}px;top:${e.clientY-rect.top-sz/2}px;transform:scale(0);animation:btn-rip .6s ease-out forwards;`;
      btn.style.position='relative';btn.style.overflow='hidden';
      btn.appendChild(rip);setTimeout(()=>rip.remove(),650);
    }
  });

  /* inject keyframes once */
  if(!document.getElementById('fx-styles')){
    const s=document.createElement('style'); s.id='fx-styles';
    s.textContent=`
      @keyframes shockwave{to{transform:translate(-50%,-50%) scale(22);opacity:0;}}
      @keyframes dot-fly{to{transform:translate(var(--tx),var(--ty)) scale(0);opacity:0;}}
      @keyframes btn-rip{to{transform:scale(1);opacity:0;}}
    `;
    document.head.appendChild(s);
  }

  /* ═══════════════════════════════════════════════════
     4. STAGGER ENTRANCE — spring cascade
  ═══════════════════════════════════════════════════ */
  function runEntrance(){
    const els=[
      ...document.querySelectorAll('[data-testid="stVerticalBlock"]>div'),
      ...document.querySelectorAll('[data-testid="stHorizontalBlock"]>div'),
    ];
    els.forEach((el,i)=>{
      el.style.opacity='0';
      el.style.transform='translateY(22px) scale(.98)';
      el.style.transition=`opacity .6s ease ${i*.055}s, transform .6s cubic-bezier(.34,1.3,.64,1) ${i*.055}s`;
      setTimeout(()=>{el.style.opacity='1';el.style.transform='translateY(0) scale(1)';},120+i*55);
    });
  }
  setTimeout(runEntrance,180);

  /* ═══════════════════════════════════════════════════
     5. HOVER TILT on stat/metric cards
  ═══════════════════════════════════════════════════ */
  document.addEventListener('mousemove', e=>{
    document.querySelectorAll('.stat-card,.metric-card,.step-card').forEach(card=>{
      const r=card.getBoundingClientRect();
      const cx2=r.left+r.width/2, cy2=r.top+r.height/2;
      const dx=(e.clientX-cx2)/r.width, dy=(e.clientY-cy2)/r.height;
      const dist=Math.sqrt(dx*dx+dy*dy);
      if(dist<.85){
        const rx = dy*8, ry = -dx*8;
        card.style.transform=`perspective(600px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
        card.style.boxShadow=`0 20px 50px rgba(0,0,0,.5), 0 0 25px rgba(0,229,255,${.06+dist*.04})`;
      } else {
        card.style.transform='perspective(600px) rotateX(0) rotateY(0) translateY(0)';
        card.style.boxShadow='';
      }
    });
  });

  /* ═══════════════════════════════════════════════════
     6. ANIMATED NUMBER COUNTERS
  ═══════════════════════════════════════════════════ */
  function animCounters(){
    document.querySelectorAll('[data-count]').forEach(el=>{
      const target=+el.dataset.count, dur=1400, start=Date.now();
      const raf=()=>{
        const p=Math.min(1,(Date.now()-start)/dur);
        const ease=1-Math.pow(1-p,4);
        el.textContent=Math.round(target*ease)+(el.dataset.suffix||'');
        if(p<1) requestAnimationFrame(raf);
      };
      raf();
    });
  }
  setTimeout(animCounters,400);

  /* ═══════════════════════════════════════════════════
     7. SCROLL-TRIGGERED FADE-IN for new content
  ═══════════════════════════════════════════════════ */
  const io=new IntersectionObserver(entries=>{
    entries.forEach(en=>{
      if(en.isIntersecting && !en.target._seen){
        en.target._seen=true;
        en.target.style.animation='card-enter .5s cubic-bezier(.4,0,.2,1) forwards';
      }
    });
  },{threshold:.15});
  setTimeout(()=>{
    document.querySelectorAll('.fn-card,.issue-card,.file-header,.stat-card').forEach(el=>io.observe(el));
  },500);

}
init();
})();
</script>
""", unsafe_allow_html=True)

PEP257_RULES = {
    "D100":"Missing docstring in public module","D101":"Missing docstring in public class",
    "D102":"Missing docstring in public method","D103":"Missing docstring in public function",
    "D200":"No blank lines allowed surrounding docstring text",
    "D400":"First line should end with a period, question mark, or exclamation point",
}

def check_pep257(source_code):
    issues = []
    try: tree = ast.parse(source_code)
    except SyntaxError as exc: return [{"code":"SyntaxError","function":"—","line":0,"message":str(exc)}]
    method_names = set()
    for cls in ast.walk(tree):
        if isinstance(cls, ast.ClassDef):
            for node in ast.walk(cls):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_names.add(node.name)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)): continue
        label = getattr(node,"name","module"); docstr = ast.get_docstring(node); lineno = getattr(node,"lineno",0)
        if docstr is None:
            code_map = {ast.Module:"D100",ast.ClassDef:"D101",ast.FunctionDef:"D102" if label in method_names else "D103",ast.AsyncFunctionDef:"D102" if label in method_names else "D103"}
            code = code_map.get(type(node))
            if code: issues.append({"code":code,"function":label,"line":lineno,"message":PEP257_RULES[code],"category":"Missing Docstring"})
            continue
        first = docstr.strip().splitlines()[0].strip()
        if not first.endswith((".",  "?","!")): issues.append({"code":"D400","function":label,"line":lineno,"message":PEP257_RULES["D400"],"category":"End with Period"})
        if len([l for l in docstr.splitlines() if l.strip()])==1 and docstr!=docstr.strip(): issues.append({"code":"D200","function":label,"line":lineno,"message":PEP257_RULES["D200"],"category":"Line Space"})
    return issues

def _get_func_args(source_code, func_name):
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==func_name:
                return [a.arg for a in node.args.args if a.arg!="self"]
    except: pass
    return []

def generate_google_style(func_name, args):
    L = [f"def {func_name}({', '.join(args)}):", '    """Summary line.', ""]
    if args: L += ["    Args:"] + [f"        {a}: Description of {a}." for a in args]
    L += ["", "    Returns:", "        Description of return value.", '    """']
    return "\n".join(L)

def generate_numpy_style(func_name, args):
    L = [f"def {func_name}({', '.join(args)}):", '    """Summary line.', ""]
    if args:
        L += ["    Parameters", "    ----------"]
        for a in args: L += [f"    {a} : type", f"        Description of {a}."]
    L += ["", "    Returns", "    -------", "    type", "        Description of return value.", '    """']
    return "\n".join(L)

def generate_rest_style(func_name, args):
    L = [f"def {func_name}({', '.join(args)}):", '    """Summary line.', ""]
    for a in args: L += [f"    :param {a}: Description of {a}.", f"    :type {a}: type"]
    L += ["    :return: Description of return value.", "    :rtype: type", '    """']
    return "\n".join(L)

STYLE_GENERATORS = {"Google Style":generate_google_style,"NumPy Style":generate_numpy_style,"ReST Style":generate_rest_style}

def run_analysis_from_paths(py_paths):
    all_data, pep_issues = [], {}
    for path in py_paths:
        fname = os.path.basename(path)
        try:
            with open(path,"r",encoding="utf-8",errors="replace") as fh: src = fh.read()
        except OSError as exc:
            pep_issues[fname]=[{"code":"IOError","function":"—","line":0,"message":str(exc)}]; continue
        results = cc_visit(src); mi_score = mi_visit(src,multi=False)
        try: tree = ast.parse(src)
        except SyntaxError: tree = None
        for item in results:
            has_doc = False
            if tree: has_doc = any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==item.name and ast.get_docstring(n) for n in ast.walk(tree))
            cx = item.complexity
            all_data.append({"file_name":fname,"function_name":item.name,"complexity_score":cx,"complexity_level":"Low" if cx<=5 else("Medium" if cx<=10 else "High"),"line_number":item.lineno,"docstring_status":"Documented" if has_doc else "Undocumented","maintainability_index":round(mi_score,2),"file_path":path,"_source":src})
        pep_issues[fname]=check_pep257(src)
    return all_data, pep_issues

def find_py_files(folder):
    return sorted(glob.glob(os.path.join(folder,"**","*.py"),recursive=True))

# ── AI Fix via Groq (free, fast, cloud) ──────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

def ai_fix_pep257(source_code: str, issues: list, api_key: str, model: str) -> dict:
    """Call Groq API to fix PEP 257 issues in the given source code."""
    issue_summary = "\n".join(
        f"- Line {i['line']} | {i['code']} | {i['function']} → {i['message']}"
        for i in issues
    )
    prompt = f"""You are an expert Python developer. Fix ALL the PEP 257 docstring issues listed below in the provided Python source code.

ISSUES TO FIX:
{issue_summary}

RULES:
1. Only fix the listed PEP 257 issues. Do NOT change any logic, variable names, imports, or formatting outside of docstrings.
2. Add missing docstrings where required (D100/D101/D102/D103).
3. Ensure all docstring first lines end with a period, question mark, or exclamation point (D400).
4. Remove blank lines surrounding single-line docstrings (D200).
5. Return ONLY the complete fixed Python source code — no explanation, no markdown fences, no commentary.

ORIGINAL SOURCE CODE:
```python
{source_code}
```

Return ONLY the fixed Python code, nothing else."""

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 8192,
            },
            timeout=60,
        )
        resp.raise_for_status()
        fixed_code = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if model adds them despite instructions
        if fixed_code.startswith("```"):
            lines = fixed_code.splitlines()
            fixed_code = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            ).strip()
        if not fixed_code:
            return {"ok": False, "error": "Model returned an empty response."}
        return {"ok": True, "code": fixed_code}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Cannot connect to Groq API. Check your internet connection."}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "Groq API timed out. Try again."}
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response else "?"
        if status == 401:
            return {"ok": False, "error": "Invalid Groq API key. Check console.groq.com"}
        if status == 429:
            return {"ok": False, "error": "Groq rate limit hit. Wait a moment and try again."}
        return {"ok": False, "error": f"HTTP {status}: {exc}"}
    except (KeyError, IndexError) as exc:
        return {"ok": False, "error": f"Unexpected response format: {exc}"}

# ─────────────────────────────────────────────────────────────────────────────

DEFAULTS = {"active_view":"Home","analysis_data":[],"pep257_issues":{},"scan_count":0,
            "folder_path":r"C:\study material\AI-Powered Code Reviewer and Quality Assistan\examples",
            "last_scan_ts":None,"docstring_style":"Google Style",
            "ai_fixed_sources":{},"groq_api_key":"","groq_model":GROQ_MODELS[0],"env_path":""}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

# Auto-load key from .env on first run if not already set
if not st.session_state.groq_api_key:
    _auto_key, _auto_path = _load_env_file(st.session_state.folder_path)
    if _auto_key:
        st.session_state.groq_api_key = _auto_key
        st.session_state.env_path = _auto_path

with st.sidebar:
    st.markdown("""<div style="padding:20px 4px 12px;"><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#007a8a;letter-spacing:.2em;text-transform:uppercase;margin-bottom:4px;">[ SYSTEM ]</div><div style="font-family:'Oxanium',sans-serif;font-size:1.15rem;font-weight:800;letter-spacing:.06em;background:linear-gradient(135deg,#00e5ff,#bf5af2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">AI CODE REVIEWER</div><div style="font-family:'Share Tech Mono',monospace;font-size:.62rem;color:#3d5080;margin-top:2px;letter-spacing:.06em;">v6.0 · PEP 257 ANALYSER + GROQ FIX</div></div>""", unsafe_allow_html=True)
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,#243060,transparent);margin-bottom:16px;"></div>', unsafe_allow_html=True)
    view_options=["Home","Dashboard","Metrics","Docstring Coverage","Validation"]
    def _on_nav_change():
        st.session_state.active_view=st.session_state._nav_select
    st.selectbox("Navigation",view_options,
        index=view_options.index(st.session_state.active_view),
        key="_nav_select",on_change=_on_nav_change)
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,#243060,transparent);margin:16px 0 12px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.18em;text-transform:uppercase;margin-bottom:8px;">📁 Project Folder</div>', unsafe_allow_html=True)
    folder_input=st.text_input("Path to scan",value=st.session_state.folder_path,placeholder="/path/to/your/project",label_visibility="collapsed")
    st.session_state.folder_path=folder_input.strip()
    fp_live=st.session_state.folder_path
    if fp_live and os.path.isdir(fp_live):
        live_files=find_py_files(fp_live)
        if live_files:
            scanned_names={r["file_name"] for r in st.session_state.analysis_data} if st.session_state.analysis_data else set()
            st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.62rem;color:#3d5080;letter-spacing:.1em;text-transform:uppercase;margin:10px 0 6px;">// {len(live_files)} file(s) detected</div>',unsafe_allow_html=True)
            for fp_item in live_files:
                fname_item=os.path.basename(fp_item); size_kb=round(os.path.getsize(fp_item)/1024,1)
                is_scanned=fname_item in scanned_names; dot_color="#00ff9d" if is_scanned else "#3d5080"; name_color="#00e5ff" if is_scanned else "#8896b0"
                st.markdown(f'<div class="file-pill"><span style="width:6px;height:6px;border-radius:50%;background:{dot_color};flex-shrink:0;box-shadow:0 0 6px {dot_color};"></span><span style="font-family:\'Share Tech Mono\',monospace;font-size:.73rem;color:{name_color};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;">{fname_item}</span><span style="font-size:.62rem;color:#3d5080;font-family:\'Share Tech Mono\',monospace;flex-shrink:0;">{size_kb}kb</span></div>',unsafe_allow_html=True)
        else: st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.65rem;color:#ff4d6d;letter-spacing:.06em;">⚠ no .py files found</div>',unsafe_allow_html=True)
    elif fp_live: st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.65rem;color:#ff4d6d;letter-spacing:.06em;">⚠ path not found</div>',unsafe_allow_html=True)
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,#243060,transparent);margin:14px 0 12px;"></div>',unsafe_allow_html=True)

    # ── Groq API Key + Model selector ──
    st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.18em;text-transform:uppercase;margin-bottom:8px;">🔑 Groq API Key</div>', unsafe_allow_html=True)

    # Re-check .env whenever folder path changes and no key is set yet
    if not st.session_state.groq_api_key:
        _live_key, _live_path = _load_env_file(st.session_state.folder_path)
        if _live_key:
            st.session_state.groq_api_key = _live_key
            st.session_state.env_path = _live_path

    groq_key_input = st.text_input(
        "Groq API Key", value=st.session_state.groq_api_key,
        placeholder="gsk_... or auto-loaded from .env", type="password", label_visibility="collapsed"
    )
    st.session_state.groq_api_key = groq_key_input.strip()

    if st.session_state.groq_api_key:
        if st.session_state.env_path:
            env_name = os.path.basename(st.session_state.env_path)
            st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.62rem;color:#00ff9d;letter-spacing:.06em;">✓ Auto-loaded from <span style="color:#00e5ff;">{env_name}</span> — AI Fix enabled</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.62rem;color:#00ff9d;letter-spacing:.06em;">✓ API key set — AI Fix enabled</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.62rem;color:#3d5080;letter-spacing:.06em;">Add <span style="color:#00e5ff;">GROQ_API_KEY=gsk_...</span> to your <span style="color:#00e5ff;">.env</span> or paste here</div>', unsafe_allow_html=True)

    st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.18em;text-transform:uppercase;margin:10px 0 6px;">🤖 Groq Model</div>', unsafe_allow_html=True)
    saved_model = st.session_state.groq_model
    model_idx = GROQ_MODELS.index(saved_model) if saved_model in GROQ_MODELS else 0
    chosen_model = st.selectbox("Groq Model", GROQ_MODELS, index=model_idx, label_visibility="collapsed")
    st.session_state.groq_model = chosen_model
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,#243060,transparent);margin:14px 0 12px;"></div>',unsafe_allow_html=True)

    scan_label="🔄 Scan Again" if st.session_state.scan_count>0 else "🔍 Scan Code"
    do_scan=st.button(scan_label,use_container_width=True)
    if st.session_state.scan_count>0 and st.session_state.last_scan_ts:
        st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.62rem;color:#3d5080;letter-spacing:.06em;margin-top:6px;text-align:center;">last scan #{st.session_state.scan_count} &nbsp;·&nbsp; {st.session_state.last_scan_ts}</div>',unsafe_allow_html=True)
    st.markdown("""
<div style="font-family:'Share Tech Mono',monospace;font-size:.56rem;color:#1e2d50;
  letter-spacing:.1em;text-align:center;margin-top:22px;line-height:2;
  border-top:1px solid #0f1628;padding-top:14px;">
  <div style="color:#243060;">PEP 257 QUALITY ASSISTANT</div>
  <div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:2px;">
    <span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:#00e5ff;
      animation:ping-dot 1.5s ease-in-out infinite;box-shadow:0 0 6px #00e5ff;"></span>
    <span style="color:#1e2d50;">v6.0 &middot; GROQ POWERED</span>
  </div>
</div>
<style>@keyframes ping-dot{0%,100%{transform:scale(1);opacity:.8;}50%{transform:scale(1.6);opacity:.3;}}</style>
""",unsafe_allow_html=True)

if do_scan:
    fp=st.session_state.folder_path
    if not fp: st.sidebar.error("Please enter a folder path first.")
    elif not os.path.isdir(fp): st.sidebar.error(f"Not a valid directory:\n{fp}")
    else:
        py_files=find_py_files(fp)
        if not py_files: st.sidebar.warning("No .py files found in that folder.")
        else:
            with st.spinner(f"Scanning {len(py_files)} file(s)…"):
                data,pep=run_analysis_from_paths(py_files)
            st.session_state.analysis_data=data; st.session_state.pep257_issues=pep
            st.session_state.scan_count+=1; st.session_state.last_scan_ts=time.strftime("%H:%M:%S")
            st.session_state.ai_fixed_sources={}  # clear fixes on rescan

def cx_badge(level):
    cls={"Low":"badge-ok","Medium":"badge-warn","High":"badge-bad"}.get(level,"badge-ok")
    return f'<span class="fn-badge {cls}">{level}</span>'

def doc_badge(status):
    cls="badge-doc" if status=="Documented" else "badge-nodoc"
    label="✓ Docs" if status=="Documented" else "✗ No Docs"
    return f'<span class="fn-badge {cls}">{label}</span>'

view=st.session_state.active_view

if view=="Home":
    has_data=bool(st.session_state.analysis_data); pep=st.session_state.pep257_issues
    st.markdown("""
<div style="padding:44px 0 32px;position:relative;">
  <!-- glowing orb behind title -->
  <div style="position:absolute;top:-20px;left:-40px;width:340px;height:240px;border-radius:50%;
    background:radial-gradient(ellipse,rgba(0,229,255,.07) 0%,transparent 70%);pointer-events:none;
    animation:hero-orb 6s ease-in-out infinite alternate;"></div>
  <style>@keyframes hero-orb{0%{transform:translate(0,0) scale(1);}100%{transform:translate(20px,-15px) scale(1.08);}}</style>

  <div style="font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#007a8a;
    letter-spacing:.28em;text-transform:uppercase;margin-bottom:12px;
    display:flex;align-items:center;gap:10px;">
    <span style="display:inline-block;width:24px;height:1px;background:linear-gradient(90deg,transparent,#00e5ff);"></span>
    AI · CODE · REVIEW · SYSTEM
    <span style="display:inline-block;width:24px;height:1px;background:linear-gradient(90deg,#00e5ff,transparent);"></span>
  </div>

  <h1 style="margin:0 0 14px;font-family:'Oxanium',sans-serif;font-size:3rem;font-weight:800;
    letter-spacing:.04em;line-height:1.05;
    background:linear-gradient(135deg,#00e5ff 0%,#bf5af2 55%,#00ff9d 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    filter:drop-shadow(0 0 30px rgba(0,229,255,.25));
    animation:title-glow 3s ease-in-out infinite alternate;">
    AI Code Reviewer
  </h1>
  <style>@keyframes title-glow{
    from{filter:drop-shadow(0 0 20px rgba(0,229,255,.2));}
    to{filter:drop-shadow(0 0 40px rgba(191,90,242,.35));}
  }</style>

  <div style="display:flex;flex-direction:column;gap:5px;max-width:560px;">
    <div style="font-family:'Share Tech Mono',monospace;font-size:.82rem;color:#3d5080;line-height:1.9;letter-spacing:.03em;">
      <span style="color:#00e5ff;opacity:.5;">›</span>&nbsp; Analyse Python quality — complexity, docstring coverage &amp; PEP 257
    </div>
    <div style="font-family:'Share Tech Mono',monospace;font-size:.82rem;color:#3d5080;line-height:1.9;letter-spacing:.03em;">
      <span style="color:#00e5ff;opacity:.5;">›</span>&nbsp; Edit in VS Code → hit
      <span style="color:#00e5ff;font-weight:700;text-shadow:0 0 10px rgba(0,229,255,.4);">SCAN AGAIN</span> → live results
    </div>
    <div style="font-family:'Share Tech Mono',monospace;font-size:.82rem;color:#3d5080;line-height:1.9;letter-spacing:.03em;">
      <span style="color:#bf5af2;opacity:.5;">›</span>&nbsp; Use
      <span style="color:#bf5af2;font-weight:700;text-shadow:0 0 10px rgba(191,90,242,.4);">AI FIX</span>
      in Validation to auto-repair violations with Groq
    </div>
  </div>
</div>
""",unsafe_allow_html=True)
    if not has_data:
        st.markdown("""<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:8px 0 28px;"><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid #00e5ff;border-radius:10px;padding:22px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#007a8a;letter-spacing:.16em;margin-bottom:10px;">STEP_01</div><div style="font-family:'Oxanium',sans-serif;font-weight:700;color:#cdd9f5;font-size:.95rem;margin-bottom:8px;">Set Folder Path</div><div style="font-size:.78rem;color:#3d5080;line-height:1.7;font-family:'Share Tech Mono',monospace;">Paste your project folder path in the sidebar.</div></div><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid #bf5af2;border-radius:10px;padding:22px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#5c2a78;letter-spacing:.16em;margin-bottom:10px;">STEP_02</div><div style="font-family:'Oxanium',sans-serif;font-weight:700;color:#cdd9f5;font-size:.95rem;margin-bottom:8px;">Scan Code</div><div style="font-size:.78rem;color:#3d5080;line-height:1.7;font-family:'Share Tech Mono',monospace;">Run analysis across all files — complexity, docs, PEP 257.</div></div><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid #00ff9d;border-radius:10px;padding:22px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#00522e;letter-spacing:.16em;margin-bottom:10px;">STEP_03</div><div style="font-family:'Oxanium',sans-serif;font-weight:700;color:#cdd9f5;font-size:.95rem;margin-bottom:8px;">AI Fix &amp; Rescan</div><div style="font-size:.78rem;color:#3d5080;line-height:1.7;font-family:'Share Tech Mono',monospace;">Use AI Fix in Validation → apply fix → Scan Again.</div></div></div><div style="background:rgba(0,229,255,.03);border:1px solid #1a2340;border-left:2px solid #00e5ff;border-radius:8px;padding:16px 20px;font-family:'Share Tech Mono',monospace;font-size:.75rem;color:#3d5080;letter-spacing:.04em;">▶ Enter folder path in sidebar → click <span style="color:#00e5ff;">SCAN CODE</span> to initialise</div>""",unsafe_allow_html=True)
    else:
        df=pd.DataFrame(st.session_state.analysis_data); total_fn=len(df)
        documented=len(df[df["docstring_status"]=="Documented"]); doc_pct=round(documented/total_fn*100) if total_fn else 0
        avg_mi=df["maintainability_index"].mean(); total_pep=sum(len(v) for v in pep.values()); files_count=df["file_name"].nunique()
        status_color="#34d399" if doc_pct>=80 else("#fbbf24" if doc_pct>=50 else "#f87171")
        status_label="Good" if doc_pct>=80 else("Fair" if doc_pct>=50 else "Needs Work")
        st.markdown(f"""<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;"><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid #00e5ff;border-radius:10px;padding:18px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:2rem;color:#00e5ff;line-height:1;">{files_count}</div><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.14em;text-transform:uppercase;margin-top:6px;">Files Scanned</div></div><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid #bf5af2;border-radius:10px;padding:18px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:2rem;color:#bf5af2;line-height:1;">{total_fn}</div><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.14em;text-transform:uppercase;margin-top:6px;">Total Functions</div></div><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid {status_color};border-radius:10px;padding:18px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:2rem;color:{status_color};line-height:1;">{doc_pct}%</div><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.14em;text-transform:uppercase;margin-top:6px;">Doc Coverage</div></div><div style="background:#080c18;border:1px solid #1a2340;border-top:2px solid #ff4d6d;border-radius:10px;padding:18px 20px;"><div style="font-family:'Share Tech Mono',monospace;font-size:2rem;color:#ff4d6d;line-height:1;">{total_pep}</div><div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#3d5080;letter-spacing:.14em;text-transform:uppercase;margin-top:6px;">PEP 257 Issues</div></div></div>""",unsafe_allow_html=True)
        col_cov,col_mi=st.columns(2)
        with col_cov:
            st.markdown(f"""<div style="background:linear-gradient(135deg,#04060d,#0a0418);border:1px solid #2d1a50;border-top:2px solid #bf5af2;border-radius:12px;padding:28px 26px;position:relative;overflow:hidden;"><div style="font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#5c2a78;letter-spacing:.2em;text-transform:uppercase;margin-bottom:8px;">// DOC COVERAGE</div><div style="font-family:'Oxanium',sans-serif;font-size:3.2rem;font-weight:800;color:#bf5af2;line-height:1;margin-bottom:6px;">{doc_pct}%</div><div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:#3d5080;margin-bottom:14px;">{documented} / {total_fn} functions documented</div><span style="background:rgba(191,90,242,.12);color:#bf5af2;border:1px solid rgba(191,90,242,.3);padding:4px 14px;border-radius:3px;font-size:.65rem;font-family:'Share Tech Mono',monospace;letter-spacing:.1em;">● {status_label.upper()}</span></div>""",unsafe_allow_html=True)
        with col_mi:
            mi_color="#00ff9d" if avg_mi>=65 else("#ffd60a" if avg_mi>=40 else "#ff4d6d")
            mi_label="Maintainable" if avg_mi>=65 else("Moderate" if avg_mi>=40 else "Hard to Maintain")
            st.markdown(f"""<div style="background:linear-gradient(135deg,#04060d,#03100a);border:1px solid #00522e;border-top:2px solid #00ff9d;border-radius:12px;padding:28px 26px;position:relative;overflow:hidden;"><div style="font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#00522e;letter-spacing:.2em;text-transform:uppercase;margin-bottom:8px;">// MAINTAINABILITY INDEX</div><div style="font-family:'Oxanium',sans-serif;font-size:3.2rem;font-weight:800;color:{mi_color};line-height:1;margin-bottom:6px;">{avg_mi:.0f}</div><div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:#3d5080;margin-bottom:14px;">Avg across all scanned files</div><span style="background:rgba(0,255,157,.08);color:{mi_color};border:1px solid rgba(0,255,157,.2);padding:4px 14px;border-radius:3px;font-size:.65rem;font-family:'Share Tech Mono',monospace;letter-spacing:.1em;">● {mi_label.upper()}</span></div>""",unsafe_allow_html=True)
        st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.62rem;color:#243060;margin-top:14px;letter-spacing:.06em;">last_scan: #{st.session_state.scan_count} &nbsp;·&nbsp; {st.session_state.last_scan_ts or "—"} &nbsp;·&nbsp; navigate via sidebar for detailed views</div>',unsafe_allow_html=True)

elif not st.session_state.analysis_data:
    st.markdown('<div style="text-align:center;padding:80px 0;color:#64748b;"><div style="font-size:3.5rem;">🧠</div><h2 style="color:#e2e8f0;margin-bottom:8px;">Select Home from navigation to get started.</h2></div>',unsafe_allow_html=True)

else:
    df=pd.DataFrame(st.session_state.analysis_data)

    if view=="Metrics":
        files_count=df["file_name"].nunique(); avg_mi=df["maintainability_index"].mean()
        total_fn=len(df); high_cx=len(df[df["complexity_level"]=="High"])
        st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#007a8a;letter-spacing:.2em;text-transform:uppercase;margin-bottom:4px;">[ ANALYSIS ]</div><h2 style="font-family:\'Oxanium\',sans-serif;font-size:1.6rem;font-weight:800;margin:0 0 20px;color:#cdd9f5;letter-spacing:.04em;">Code Metrics <span style="font-size:.8rem;color:#3d5080;font-weight:400;font-family:\'Share Tech Mono\',monospace;">// {files_count} file(s) · scan #{st.session_state.scan_count}</span></h2>',unsafe_allow_html=True)
        c1,c2,c3=st.columns(3)
        c1.markdown(f'<div class="metric-card"><h1>{avg_mi:.0f}</h1><p>Avg Maintainability Index</p></div>',unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><h1>{total_fn}</h1><p>Total Functions</p></div>',unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><h1>{high_cx}</h1><p>High Complexity Functions</p></div>',unsafe_allow_html=True)
        st.markdown("---")
        tab_cards,tab_json=st.tabs(["📋 Function Cards","{ } JSON View"])
        with tab_cards:
            for fname,group in df.groupby("file_name"):
                mi_val=group["maintainability_index"].iloc[0]
                st.markdown(f'<div class="file-header">📄 {fname}<span style="margin-left:auto;color:#64748b;font-size:.8rem;">MI: {mi_val:.1f}</span></div>',unsafe_allow_html=True)
                for _,row in group.iterrows():
                    st.markdown(f'<div class="fn-card"><div><div class="fn-name">{row["function_name"]}</div><div class="fn-line">Line {row["line_number"]} &nbsp;·&nbsp; Complexity: {row["complexity_score"]}</div></div><div style="display:flex;gap:8px;align-items:center;">{cx_badge(row["complexity_level"])}{doc_badge(row["docstring_status"])}</div></div>',unsafe_allow_html=True)
        with tab_json:
            export_data=df.drop(columns=["file_path","_source"],errors="ignore").to_dict(orient="records")
            json_str=json.dumps(export_data,indent=2)
            st.markdown(f'<div class="json-viewer">{json_str}</div>',unsafe_allow_html=True)
            col_a,col_b=st.columns(2)
            with col_a: st.download_button("📥 Download JSON",json_str,file_name="metrics.json",mime="application/json")
            with col_b: st.download_button("📊 Download CSV",df.drop(columns=["file_path","_source"],errors="ignore").to_csv(index=False).encode(),file_name="metrics.csv",mime="text/csv")

    elif view=="Docstring Coverage":
        total=len(df); documented=len(df[df["docstring_status"]=="Documented"]); pct=round(documented/total*100) if total else 0
        st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#007a8a;letter-spacing:.2em;text-transform:uppercase;margin-bottom:4px;">[ DOCUMENTATION ]</div><h2 style="font-family:\'Oxanium\',sans-serif;font-size:1.6rem;font-weight:800;margin:0 0 20px;color:#cdd9f5;letter-spacing:.04em;">Docstring Coverage</h2>',unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Total Functions",total); c2.metric("✅ Documented",documented)
        c3.metric("❌ Undocumented",total-documented); c4.metric("Coverage",f"{pct}%")
        st.markdown("---")
        st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#007a8a;letter-spacing:.2em;text-transform:uppercase;margin-bottom:8px;">// Docstring Style</div>',unsafe_allow_html=True)
        selected_style=st.radio("Docstring Style",options=["Google Style","NumPy Style","ReST Style"],
            index=["Google Style","NumPy Style","ReST Style"].index(st.session_state.docstring_style),
            horizontal=True,label_visibility="collapsed")
        st.session_state.docstring_style=selected_style
        style_desc={"Google Style":"Uses indented sections (Args:, Returns:, Raises:). Recommended by Google's Python Style Guide.",
                    "NumPy Style":"Uses underlined section headers. Standard for scientific Python (NumPy, SciPy, pandas).",
                    "ReST Style":"Uses :param:, :type:, :return: directives. Compatible with Sphinx documentation."}
        style_color={"Google Style":"#00e5ff","NumPy Style":"#bf5af2","ReST Style":"#00ff9d"}
        sc=style_color[selected_style]
        st.markdown(f'<div style="background:rgba(0,0,0,.3);border:1px solid {sc}33;border-left:2px solid {sc};border-radius:8px;padding:10px 16px;margin:8px 0 18px;font-family:\'Share Tech Mono\',monospace;font-size:.75rem;color:{sc}99;letter-spacing:.03em;">● {style_desc[selected_style]}</div>',unsafe_allow_html=True)
        st.markdown("---")
        tab_table,tab_generated,tab_json=st.tabs(["📊 Table View","✨ Generated Docstrings","{ } JSON View"])
        with tab_table:
            file_summary=df.groupby("file_name")["docstring_status"].value_counts().unstack().fillna(0)
            st.dataframe(file_summary,use_container_width=True)
        with tab_generated:
            undoc_df=df[df["docstring_status"]=="Undocumented"]
            if undoc_df.empty:
                st.success("🎉 All functions are documented! Nothing to generate.")
            else:
                st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.72rem;color:#3d5080;letter-spacing:.08em;margin-bottom:14px;">// {len(undoc_df)} undocumented function(s) · showing {selected_style} templates</div>',unsafe_allow_html=True)
                generator=STYLE_GENERATORS[selected_style]
                for fname,group in undoc_df.groupby("file_name"):
                    st.markdown(f'<div class="file-header" style="border-left:2px solid {sc};">📄 {fname}<span style="margin-left:auto;font-size:.72rem;color:#3d5080;">{len(group)} undocumented</span></div>',unsafe_allow_html=True)
                    for _,row in group.iterrows():
                        func_name=row["function_name"]; src=row.get("_source","")
                        args=_get_func_args(src,func_name) if src else []; template=generator(func_name,args)
                        st.markdown(f'<div class="docstring-fn-header"><span style="color:{sc};">⚡ {func_name}</span><span style="margin-left:auto;font-size:.68rem;color:#3d5080;">Line {row["line_number"]}</span></div><div class="docstring-block">{template}</div>',unsafe_allow_html=True)
                all_templates={}
                for fname,group in undoc_df.groupby("file_name"):
                    all_templates[fname]=[]
                    for _,row in group.iterrows():
                        fn=row["function_name"]; src=row.get("_source",""); args=_get_func_args(src,fn) if src else []
                        all_templates[fname].append({"function":fn,"template":generator(fn,args)})
                st.markdown("<br>",unsafe_allow_html=True)
                st.download_button(f"📥 Download {selected_style} Templates (JSON)",json.dumps(all_templates,indent=2),
                    file_name=f"docstrings_{selected_style.lower().replace(' ','_')}.json",mime="application/json")
        with tab_json:
            doc_export=df.groupby("file_name").apply(lambda g:{"documented":int((g["docstring_status"]=="Documented").sum()),"undocumented":int((g["docstring_status"]=="Undocumented").sum()),"functions":g[["function_name","line_number","docstring_status"]].to_dict(orient="records")}).to_dict()
            json_str=json.dumps(doc_export,indent=2)
            st.markdown(f'<div class="json-viewer">{json_str}</div>',unsafe_allow_html=True)
            st.download_button("📥 Download Coverage JSON",json_str,file_name="docstring_coverage.json",mime="application/json")

    elif view=="Validation":
        pep=st.session_state.pep257_issues; total_issues=sum(len(v) for v in pep.values())
        groq_api_key=st.session_state.groq_api_key
        groq_model=st.session_state.groq_model

        st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:#007a8a;letter-spacing:.2em;text-transform:uppercase;margin-bottom:4px;">[ COMPLIANCE ]</div><h2 style="font-family:\'Oxanium\',sans-serif;font-size:1.6rem;font-weight:800;margin:0 0 20px;color:#cdd9f5;letter-spacing:.04em;">Project Validation <span style="font-size:.75rem;color:#3d5080;font-weight:400;font-family:\'Share Tech Mono\',monospace;">// PEP 257</span></h2>',unsafe_allow_html=True)

        if total_issues==0:
            st.success("🎉 All files are PEP 257 compliant!")
        else:
            st.markdown(f"<p style='color:#f87171;font-size:.9rem;'>Found <strong>{total_issues}</strong> issue(s). Fix them in VS Code and click <strong>🔄 Scan Again</strong>, or use <strong style='color:#bf5af2;'>⚡ AI Fix</strong> below.</p>",unsafe_allow_html=True)

        # ── AI Fix Banner ──────────────────────────────────────────────────────
        st.markdown(f"""
        <div class="ai-fix-banner">
            <div class="ai-fix-header">// AI · AUTO · FIX · ENGINE · GROQ</div>
            <div class="ai-fix-title">⚡ AI Fix — PEP 257 Auto-Repair (Free via Groq)</div>
            <div class="ai-fix-desc">Uses <strong style="color:#bf5af2;">{groq_model}</strong> via Groq's free API — blazing fast, no local setup needed. Rewrites only docstrings, logic untouched. Review the diff, then apply directly to disk.</div>
        </div>
        """, unsafe_allow_html=True)

        if not groq_api_key:
            st.markdown('<div class="fix-status-err">⚠ Enter your Groq API key in the sidebar to enable AI Fix. Get one free at <strong>console.groq.com</strong></div>', unsafe_allow_html=True)

        # ── Fix All Action Button ──────────────────────────────────────────────
        if total_issues > 0 and groq_api_key:
            files_with_issues = [f for f, issues in pep.items() if issues]
            already_fixed = [f for f in files_with_issues if f in st.session_state.ai_fixed_sources and st.session_state.ai_fixed_sources[f].get("ok")]
            all_fixed = len(already_fixed) == len(files_with_issues)

            col_fixall, col_applyall, col_clearall = st.columns([2, 2, 1])
            with col_fixall:
                fix_all_label = f"⚡ AI Fix All {len(files_with_issues)} File(s)" if not all_fixed else "🔁 Re-Fix All Files"
                if st.button(fix_all_label, key="btn_fix_all", use_container_width=True):
                    progress = st.progress(0, text="Starting AI Fix…")
                    for i, fname_fix in enumerate(files_with_issues):
                        src_fix = next((r["_source"] for r in st.session_state.analysis_data if r["file_name"]==fname_fix), None)
                        if src_fix:
                            progress.progress((i) / len(files_with_issues), text=f"🤖 Fixing {fname_fix}… ({i+1}/{len(files_with_issues)})")
                            result = ai_fix_pep257(src_fix, pep[fname_fix], groq_api_key, groq_model)
                            st.session_state.ai_fixed_sources[fname_fix] = result
                    progress.progress(1.0, text="✓ All files processed!")
                    time.sleep(0.6)
                    progress.empty()
                    st.rerun()

            with col_applyall:
                ok_fixes = {f: st.session_state.ai_fixed_sources[f]["code"] for f in files_with_issues if f in st.session_state.ai_fixed_sources and st.session_state.ai_fixed_sources[f].get("ok")}
                if ok_fixes:
                    if st.button(f"✅ Apply All Fixes ({len(ok_fixes)} file(s))", key="btn_apply_all", use_container_width=True):
                        applied, failed = 0, 0
                        for fname_a, code_a in ok_fixes.items():
                            fpath_a = next((r["file_path"] for r in st.session_state.analysis_data if r["file_name"]==fname_a), None)
                            if fpath_a and os.path.isfile(fpath_a):
                                try:
                                    with open(fpath_a, "w", encoding="utf-8") as fh: fh.write(code_a)
                                    del st.session_state.ai_fixed_sources[fname_a]
                                    applied += 1
                                except OSError: failed += 1
                            else: failed += 1
                        if applied: st.success(f"✓ Applied {applied} fix(es) to disk! Click 🔄 Scan Again to verify.")
                        if failed: st.error(f"✗ {failed} file(s) could not be written.")
                        st.rerun()
                else:
                    st.markdown('<div style="background:rgba(0,229,255,.04);border:1px solid #1a2340;border-radius:6px;padding:10px 14px;font-family:\'Share Tech Mono\',monospace;font-size:.72rem;color:#3d5080;text-align:center;">Run AI Fix first to enable Apply All</div>', unsafe_allow_html=True)

            with col_clearall:
                if st.session_state.ai_fixed_sources:
                    if st.button("🗑 Clear", key="btn_clear_all", use_container_width=True):
                        st.session_state.ai_fixed_sources = {}
                        st.rerun()

            # Status summary row
            if st.session_state.ai_fixed_sources:
                ok_count = sum(1 for v in st.session_state.ai_fixed_sources.values() if v.get("ok"))
                err_count = sum(1 for v in st.session_state.ai_fixed_sources.values() if not v.get("ok"))
                status_parts = []
                if ok_count: status_parts.append(f'<span style="color:#00ff9d;">✓ {ok_count} fixed</span>')
                if err_count: status_parts.append(f'<span style="color:#ff4d6d;">✗ {err_count} failed</span>')
                remaining = len(files_with_issues) - len(st.session_state.ai_fixed_sources)
                if remaining > 0: status_parts.append(f'<span style="color:#3d5080;">{remaining} pending</span>')
                st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.68rem;letter-spacing:.06em;margin-top:4px;padding:6px 2px;">{" &nbsp;·&nbsp; ".join(status_parts)}</div>', unsafe_allow_html=True)

        st.markdown("---")

        if total_issues>0:
            all_issues=[i for issues in pep.values() for i in issues]
            from collections import Counter
            cat_counts=Counter(i.get("category","Missing Docstring") for i in all_issues)
            cat_order=["Missing Docstring","Line Space","End with Period"]
            pie_labels=[c for c in cat_order if c in cat_counts]; pie_values=[cat_counts[c] for c in pie_labels]
            cat_colors={"Missing Docstring":"#ff4d6d","Line Space":"#ffd60a","End with Period":"#00e5ff"}
            col_pie,col_info=st.columns([1,1])
            with col_pie:
                fig=go.Figure(go.Pie(labels=pie_labels,values=pie_values,hole=.45,
                    marker=dict(colors=[cat_colors[l] for l in pie_labels],line=dict(color="#0d0f14",width=2)),
                    textfont=dict(family="Sora, sans-serif",size=13,color="#e2e8f0"),
                    hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
                fig.update_layout(title=dict(text="Violations by Category",font=dict(family="Oxanium,sans-serif",size=14,color="#cdd9f5"),x=0.5,xanchor="center"),
                    paper_bgcolor="#04060d",plot_bgcolor="#04060d",font=dict(color="#cdd9f5",family="Share Tech Mono, monospace"),
                    legend=dict(bgcolor="#080c18",bordercolor="#1a2340",borderwidth=1,font=dict(family="Share Tech Mono, monospace",size=11)),
                    margin=dict(t=50,b=10,l=10,r=10),height=320)
                st.plotly_chart(fig,use_container_width=True)
            with col_info:
                st.markdown("<br>",unsafe_allow_html=True)
                for cat in pie_labels:
                    count=cat_counts[cat]; pct_v=round(count/total_issues*100); color=cat_colors[cat]
                    st.markdown(f'<div style="background:#1c2030;border:1px solid #252a3a;border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;"><div style="display:flex;align-items:center;gap:10px;"><span style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;"></span><span style="color:#e2e8f0;font-size:.85rem;">{cat}</span></div><span style="color:{color};font-family:\'JetBrains Mono\',monospace;font-size:.82rem;font-weight:700;">{count} ({pct_v}%)</span></div>',unsafe_allow_html=True)

        st.markdown("---")

        # ── Per-file issue list + AI Fix ───────────────────────────────────────
        for fname, issues in pep.items():
            color="#f87171" if issues else "#34d399"; icon="❌" if issues else "✅"
            # get file path from analysis data
            file_path = None
            file_src = None
            for row in st.session_state.analysis_data:
                if row["file_name"] == fname:
                    file_path = row.get("file_path")
                    file_src = row.get("_source")
                    break

            st.markdown(f'<div class="file-header" style="border-left:3px solid {color};">{icon} {fname}<span style="margin-left:auto;color:{color};font-size:.8rem;">{len(issues)} issue(s)</span></div>',unsafe_allow_html=True)

            if issues:
                with st.expander(f"View {len(issues)} issue(s) in {fname}", expanded=True):
                    for issue in issues:
                        st.markdown(f'<div class="issue-card"><div><span class="issue-fn">{issue["function"]}</span> &nbsp;·&nbsp; Line {issue["line"]}</div><div><span class="issue-code">{issue["code"]}</span>: <span class="issue-msg">{issue["message"]}</span></div></div>',unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # ── AI Fix button row ──────────────────────────────────────
                    col_fix, col_apply, col_dl = st.columns([1, 1, 1])

                    fix_key = f"fix_{fname}"
                    fixed_result = st.session_state.ai_fixed_sources.get(fname)

                    with col_fix:
                        if groq_api_key and file_src:
                            if st.button(f"⚡ AI Fix  {fname}", key=f"btn_fix_{fname}", use_container_width=True):
                                with st.spinner(f"🤖 Groq ({groq_model}) is rewriting docstrings…"):
                                    result = ai_fix_pep257(file_src, issues, groq_api_key, groq_model)
                                st.session_state.ai_fixed_sources[fname] = result
                                st.rerun()
                        elif not groq_api_key:
                            st.markdown('<div class="fix-status-err" style="text-align:center;padding:10px;">Add Groq API key in sidebar</div>', unsafe_allow_html=True)

                    # Show result if available
                    if fixed_result:
                        if not fixed_result["ok"]:
                            st.markdown(f'<div class="fix-status-err">✗ AI Fix failed: {fixed_result["error"]}</div>', unsafe_allow_html=True)
                        else:
                            fixed_code = fixed_result["code"]
                            st.markdown('<div class="fix-status-ok">✓ AI Fix complete — review the fixed code below before applying</div>', unsafe_allow_html=True)

                            # Tabs: diff view + full fixed code
                            tab_diff, tab_full = st.tabs(["🔍 Diff View", "📄 Full Fixed Code"])

                            with tab_diff:
                                import difflib
                                orig_lines = (file_src or "").splitlines(keepends=True)
                                fixed_lines = fixed_code.splitlines(keepends=True)
                                diff = list(difflib.unified_diff(
                                    orig_lines, fixed_lines,
                                    fromfile=f"original/{fname}",
                                    tofile=f"fixed/{fname}",
                                    lineterm=""
                                ))
                                if diff:
                                    diff_html = ""
                                    for line in diff[:300]:  # cap for safety
                                        esc = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                                        if line.startswith("+++") or line.startswith("---"):
                                            diff_html += f'<span style="color:#64748b;">{esc}</span>\n'
                                        elif line.startswith("+"):
                                            diff_html += f'<span class="diff-added">{esc}</span>\n'
                                        elif line.startswith("-"):
                                            diff_html += f'<span class="diff-removed">{esc}</span>\n'
                                        elif line.startswith("@@"):
                                            diff_html += f'<span style="color:#ffd60a;">{esc}</span>\n'
                                        else:
                                            diff_html += f'<span style="color:#3d5080;">{esc}</span>\n'
                                    st.markdown(f'<div class="fixed-code-block" style="color:inherit;">{diff_html}</div>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<div class="fix-status-ok">✓ No diff — code is identical (already compliant?).</div>', unsafe_allow_html=True)

                            with tab_full:
                                st.markdown(f'<div class="fixed-code-block">{fixed_code.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")}</div>', unsafe_allow_html=True)

                            # Apply + Download buttons
                            col_a2, col_d2 = st.columns(2)
                            with col_a2:
                                if file_path and os.path.isfile(file_path):
                                    apply_key = f"apply_{fname}"
                                    if st.button(f"✅ Apply Fix → {fname}", key=apply_key, use_container_width=True):
                                        try:
                                            with open(file_path, "w", encoding="utf-8") as fh:
                                                fh.write(fixed_code)
                                            # Clear cached fix and trigger rescan hint
                                            del st.session_state.ai_fixed_sources[fname]
                                            st.success(f"✓ Saved! Click 🔄 Scan Again to verify all issues are resolved.")
                                            st.rerun()
                                        except OSError as exc:
                                            st.error(f"Could not write file: {exc}")
                                else:
                                    st.markdown('<div class="fix-status-err" style="font-size:.7rem;padding:8px 12px;">File path unavailable — use Download instead</div>', unsafe_allow_html=True)
                            with col_d2:
                                st.download_button(
                                    f"📥 Download Fixed {fname}",
                                    fixed_code.encode(),
                                    file_name=f"fixed_{fname}",
                                    mime="text/x-python",
                                    key=f"dl_{fname}",
                                    use_container_width=True,
                                )


    elif view=="Dashboard":
        pep=st.session_state.pep257_issues
        total_fn=len(df); documented=len(df[df["docstring_status"]=="Documented"])
        undocumented=total_fn-documented; doc_pct=round(documented/total_fn*100) if total_fn else 0
        total_pep=sum(len(v) for v in pep.values()); files_count=df["file_name"].nunique()
        high_cx=len(df[df["complexity_level"]=="High"]); avg_mi=df["maintainability_index"].mean()

        # ── Header ─────────────────────────────────────────────────────────────
        st.markdown(f"""
        <div style="padding:20px 0 18px;position:relative;">
          <div style="font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#007a8a;letter-spacing:.26em;text-transform:uppercase;margin-bottom:8px;display:flex;align-items:center;gap:8px;">
            <span style="display:inline-block;width:18px;height:1px;background:#00e5ff;"></span>DASHBOARD<span style="display:inline-block;width:18px;height:1px;background:#00e5ff;"></span>
          </div>
          <h2 style="font-family:'Oxanium',sans-serif;font-size:1.8rem;font-weight:800;margin:0 0 6px;
            background:linear-gradient(135deg,#00e5ff,#bf5af2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:.03em;">
            Project Dashboard
          </h2>
          <p style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:#3a4d70;margin:0;letter-spacing:.05em;">
            // scan #{st.session_state.scan_count} &nbsp;·&nbsp; {files_count} file(s) &nbsp;·&nbsp; {total_fn} functions &nbsp;·&nbsp; {total_pep} PEP 257 issues
          </p>
        </div>
        """,unsafe_allow_html=True)

        # ── MINI STAT ROW ───────────────────────────────────────────────────────
        low_cx=len(df[df["complexity_level"]=="Low"]); med_cx=len(df[df["complexity_level"]=="Medium"])
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:24px;">
          <div class="stat-card" style="border-top:2px solid #00e5ff;padding:14px 16px;text-align:center;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:1.6rem;font-weight:800;color:#00e5ff;line-height:1;text-shadow:0 0 16px rgba(0,229,255,.5);">{files_count}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:.56rem;letter-spacing:.14em;color:#3a4d70;margin-top:6px;text-transform:uppercase;">Files</div>
          </div>
          <div class="stat-card" style="border-top:2px solid #bf5af2;padding:14px 16px;text-align:center;animation-delay:.06s;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:1.6rem;font-weight:800;color:#bf5af2;line-height:1;text-shadow:0 0 16px rgba(191,90,242,.5);">{total_fn}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:.56rem;letter-spacing:.14em;color:#3a4d70;margin-top:6px;text-transform:uppercase;">Functions</div>
          </div>
          <div class="stat-card" style="border-top:2px solid {'#00ff9d' if doc_pct>=80 else '#ffd60a' if doc_pct>=50 else '#ff4d6d'};padding:14px 16px;text-align:center;animation-delay:.12s;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:1.6rem;font-weight:800;color:{'#00ff9d' if doc_pct>=80 else '#ffd60a' if doc_pct>=50 else '#ff4d6d'};line-height:1;">{doc_pct}%</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:.56rem;letter-spacing:.14em;color:#3a4d70;margin-top:6px;text-transform:uppercase;">Coverage</div>
          </div>
          <div class="stat-card" style="border-top:2px solid #ff4d6d;padding:14px 16px;text-align:center;animation-delay:.18s;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:1.6rem;font-weight:800;color:#ff4d6d;line-height:1;text-shadow:0 0 16px rgba(255,77,109,.5);">{total_pep}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:.56rem;letter-spacing:.14em;color:#3a4d70;margin-top:6px;text-transform:uppercase;">PEP Issues</div>
          </div>
          <div class="stat-card" style="border-top:2px solid #ffd60a;padding:14px 16px;text-align:center;animation-delay:.24s;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:1.6rem;font-weight:800;color:#ffd60a;line-height:1;text-shadow:0 0 16px rgba(255,214,10,.5);">{high_cx}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:.56rem;letter-spacing:.14em;color:#3a4d70;margin-top:6px;text-transform:uppercase;">High CX</div>
          </div>
        </div>
        """,unsafe_allow_html=True)

        # ── ANALYSIS TOOLS NAV BUTTONS ─────────────────────────────────────────
        if "dashboard_feature" not in st.session_state: st.session_state.dashboard_feature=None
        feat=st.session_state.dashboard_feature

        c1,c2,c3,c4,c5=st.columns(5)
        with c1:
            af=feat=="filters"
            st.markdown(f'<style>.df-btn-f .stButton>button{{background:{"rgba(79,70,229,.25)" if af else "rgba(79,70,229,.07)"}!important;border-color:{"#6d65f0" if af else "rgba(79,70,229,.4)"}!important;color:{"#a5b4fc" if af else "#6d65f0"}!important;box-shadow:{"0 0 18px rgba(79,70,229,.35)" if af else "none"}!important;}}</style>',unsafe_allow_html=True)
            st.markdown('<div class="df-btn-f">',unsafe_allow_html=True)
            if st.button("🔍  Filters",key="feat_filters",use_container_width=True):
                st.session_state.dashboard_feature=None if feat=="filters" else "filters"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with c2:
            as_=feat=="search"
            st.markdown(f'<style>.df-btn-s .stButton>button{{background:{"rgba(219,39,119,.25)" if as_ else "rgba(219,39,119,.07)"}!important;border-color:{"#ec4899" if as_ else "rgba(219,39,119,.4)"}!important;color:{"#f9a8d4" if as_ else "#ec4899"}!important;box-shadow:{"0 0 18px rgba(219,39,119,.35)" if as_ else "none"}!important;}}</style>',unsafe_allow_html=True)
            st.markdown('<div class="df-btn-s">',unsafe_allow_html=True)
            if st.button("🔎  Search",key="feat_search",use_container_width=True):
                st.session_state.dashboard_feature=None if feat=="search" else "search"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with c3:
            at=feat=="tests"
            st.markdown(f'<style>.df-btn-t .stButton>button{{background:{"rgba(16,185,129,.25)" if at else "rgba(16,185,129,.07)"}!important;border-color:{"#10b981" if at else "rgba(16,185,129,.4)"}!important;color:{"#6ee7b7" if at else "#10b981"}!important;box-shadow:{"0 0 18px rgba(16,185,129,.35)" if at else "none"}!important;}}</style>',unsafe_allow_html=True)
            st.markdown('<div class="df-btn-t">',unsafe_allow_html=True)
            if st.button("🧪  Tests",key="feat_tests",use_container_width=True):
                st.session_state.dashboard_feature=None if feat=="tests" else "tests"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with c4:
            ae=feat=="export"
            st.markdown(f'<style>.df-btn-e .stButton>button{{background:{"rgba(8,145,178,.25)" if ae else "rgba(8,145,178,.07)"}!important;border-color:{"#06b6d4" if ae else "rgba(8,145,178,.4)"}!important;color:{"#67e8f9" if ae else "#06b6d4"}!important;box-shadow:{"0 0 18px rgba(8,145,178,.35)" if ae else "none"}!important;}}</style>',unsafe_allow_html=True)
            st.markdown('<div class="df-btn-e">',unsafe_allow_html=True)
            if st.button("📤  Export",key="feat_export",use_container_width=True):
                st.session_state.dashboard_feature=None if feat=="export" else "export"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)
        with c5:
            ah=feat=="help"
            st.markdown(f'<style>.df-btn-h .stButton>button{{background:{"rgba(245,158,11,.25)" if ah else "rgba(245,158,11,.07)"}!important;border-color:{"#f59e0b" if ah else "rgba(245,158,11,.4)"}!important;color:{"#fcd34d" if ah else "#f59e0b"}!important;box-shadow:{"0 0 18px rgba(245,158,11,.35)" if ah else "none"}!important;}}</style>',unsafe_allow_html=True)
            st.markdown('<div class="df-btn-h">',unsafe_allow_html=True)
            if st.button("💡  Help",key="feat_help",use_container_width=True):
                st.session_state.dashboard_feature=None if feat=="help" else "help"; st.rerun()
            st.markdown('</div>',unsafe_allow_html=True)

        st.markdown("<br>",unsafe_allow_html=True)

        # ── Feature Panels ─────────────────────────────────────────────────────
        feat=st.session_state.dashboard_feature

        if feat=="filters":
            st.markdown("""<div style="background:linear-gradient(135deg,#3b1fa8,#7c3aed);border-radius:10px;padding:18px 22px;margin-bottom:16px;">
                <div style="font-family:'Oxanium',sans-serif;font-size:1rem;font-weight:800;color:#fff;">🔍 Advanced Filters</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:rgba(255,255,255,.6);margin-top:4px;">Filter dynamically by file, function, and documentation status</div>
            </div>""",unsafe_allow_html=True)

            col_fs1,col_fs2=st.columns(2)
            with col_fs1:
                doc_filter=st.selectbox("📋 Documentation Status",["All","Documented","Undocumented"],key="df_doc")
            with col_fs2:
                cx_filter=st.selectbox("⚡ Complexity Level",["All","Low","Medium","High"],key="df_cx")

            file_filter=st.selectbox("📄 File",["All"]+sorted(df["file_name"].unique().tolist()),key="df_file")
            fn_search=st.text_input("🔎 Function name contains",placeholder="e.g. calculate",key="df_fn",label_visibility="visible")

            filtered=df.copy()
            if doc_filter!="All": filtered=filtered[filtered["docstring_status"]==doc_filter]
            if cx_filter!="All": filtered=filtered[filtered["complexity_level"]==cx_filter]
            if file_filter!="All": filtered=filtered[filtered["file_name"]==file_filter]
            if fn_search: filtered=filtered[filtered["function_name"].str.contains(fn_search,case=False,na=False)]

            col_show,col_tot=st.columns(2)
            col_show.markdown(f'<div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:8px;padding:18px;text-align:center;"><div style="font-family:\'Share Tech Mono\',monospace;font-size:2rem;color:#fff;font-weight:700;">{len(filtered)}</div><div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:rgba(255,255,255,.6);letter-spacing:.12em;margin-top:4px;">SHOWING</div></div>',unsafe_allow_html=True)
            col_tot.markdown(f'<div style="background:linear-gradient(135deg,#7c3aed,#bf5af2);border-radius:8px;padding:18px;text-align:center;"><div style="font-family:\'Share Tech Mono\',monospace;font-size:2rem;color:#fff;font-weight:700;">{total_fn}</div><div style="font-family:\'Share Tech Mono\',monospace;font-size:.6rem;color:rgba(255,255,255,.6);letter-spacing:.12em;margin-top:4px;">TOTAL</div></div>',unsafe_allow_html=True)

            st.markdown("<br>",unsafe_allow_html=True)
            # Table
            st.markdown('<div style="background:#080c18;border:1px solid #243060;border-radius:8px;overflow:hidden;">',unsafe_allow_html=True)
            st.markdown('<div style="background:linear-gradient(90deg,#3b1fa8,#7c3aed);padding:10px 18px;display:grid;grid-template-columns:1fr 1fr 1fr;font-family:\'Share Tech Mono\',monospace;font-size:.65rem;letter-spacing:.12em;color:rgba(255,255,255,.8);">📁 FILE&nbsp;&nbsp;&nbsp;&nbsp;⚙ FUNCTION&nbsp;&nbsp;&nbsp;&nbsp;✅ DOCSTRING</div>',unsafe_allow_html=True)
            for _,row in filtered.iterrows():
                doc_ok=row["docstring_status"]=="Documented"
                badge=f'<span style="background:{"#00ff9d" if doc_ok else "#ff4d6d"};color:#000;padding:2px 10px;border-radius:12px;font-size:.65rem;font-weight:700;">{"✓ Yes" if doc_ok else "✗ No"}</span>'
                st.markdown(f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;padding:10px 18px;border-top:1px solid #1a2340;font-family:\'Share Tech Mono\',monospace;font-size:.78rem;"><span style="color:#3d5080;">{row["file_name"]}</span><span style="color:#00e5ff;">{row["function_name"]}</span><span>{badge}</span></div>',unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)

        elif feat=="tests":
            # ── build per-file test data ──────────────────────────────────────
            file_stats_t=[]
            for fname,group in df.groupby("file_name"):
                doc_c  = int((group["docstring_status"]=="Documented").sum())
                undoc_c= int((group["docstring_status"]=="Undocumented").sum())
                pep_c  = len(pep.get(fname,[]))
                cx_ok  = int((group["complexity_level"]!="High").sum())
                total_c= len(group)
                t_doc  = doc_c==total_c
                t_pep  = pep_c==0
                t_cx   = cx_ok==total_c
                score  = sum([t_doc,t_pep,t_cx])
                # each file contributes total_c "tests" (one per function)
                # a "test" passes if function is documented AND no pep issue
                fn_pass= int((group["docstring_status"]=="Documented").sum()) - \
                         min(pep_c, doc_c)  # rough: documented minus those with pep issues
                fn_pass= max(0, min(fn_pass, total_c))
                file_stats_t.append({"file":fname,"total":total_c,"passed":doc_c,
                                     "failed":undoc_c,"score":score,"t_doc":t_doc,
                                     "t_pep":t_pep,"t_cx":t_cx,"pep_c":pep_c})

            total_tests = sum(s["total"] for s in file_stats_t)
            total_passed= sum(s["passed"] for s in file_stats_t)
            total_failed= sum(s["failed"] for s in file_stats_t)
            pass_rate   = round(total_passed/total_tests*100,1) if total_tests else 0.0

            # ── "Run All Tests" info bar ──────────────────────────────────────
            st.markdown("""
            <div style="background:rgba(16,185,129,.06);border:1px solid rgba(16,185,129,.22);
              border-left:3px solid #10b981;border-radius:10px;padding:14px 20px;margin-bottom:14px;
              font-family:'Share Tech Mono',monospace;font-size:.76rem;color:#6ee7b7;line-height:1.7;">
              🧪 &nbsp;Click the button below to run all tests. Results will be displayed with
              detailed metrics and visualizations.
            </div>
            """,unsafe_allow_html=True)

            run_col,_=st.columns([1,2])
            with run_col:
                run_tests=st.button("🧪  Run All Tests",key="run_tests_btn",use_container_width=True)
            if "tests_ran" not in st.session_state: st.session_state.tests_ran=False
            if run_tests: st.session_state.tests_ran=True

            if st.session_state.tests_ran:
                # ── 4 stat cards ─────────────────────────────────────────────
                st.markdown(f"""
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0;">

                  <div class="stat-card" style="border:1px solid rgba(100,116,139,.25);border-radius:14px;
                    padding:28px 20px;text-align:center;border-top:2px solid #64748b;">
                    <div style="font-size:2.2rem;margin-bottom:10px;">🧪</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:2.4rem;font-weight:800;
                      color:#94a3b8;line-height:1;">{total_tests}</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.14em;
                      color:#3a4d70;margin-top:8px;text-transform:uppercase;">Total Tests</div>
                  </div>

                  <div class="stat-card" style="border:1px solid rgba(16,185,129,.3);border-radius:14px;
                    padding:28px 20px;text-align:center;border-top:2px solid #10b981;
                    box-shadow:0 0 30px rgba(16,185,129,.08);">
                    <div style="font-size:2.2rem;margin-bottom:10px;">✅</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:2.4rem;font-weight:800;
                      color:#10b981;line-height:1;text-shadow:0 0 20px rgba(16,185,129,.5);">{total_passed}</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.14em;
                      color:#3a4d70;margin-top:8px;text-transform:uppercase;">Passed</div>
                  </div>

                  <div class="stat-card" style="border:1px solid rgba(255,77,109,.25);border-radius:14px;
                    padding:28px 20px;text-align:center;border-top:2px solid #ff4d6d;">
                    <div style="font-size:2.2rem;margin-bottom:10px;">❌</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:2.4rem;font-weight:800;
                      color:#ff4d6d;line-height:1;text-shadow:0 0 20px rgba(255,77,109,.5);">{total_failed}</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.14em;
                      color:#3a4d70;margin-top:8px;text-transform:uppercase;">Failed</div>
                  </div>

                  <div class="stat-card" style="border:1px solid rgba(191,90,242,.28);border-radius:14px;
                    padding:28px 20px;text-align:center;border-top:2px solid #bf5af2;
                    box-shadow:0 0 30px rgba(191,90,242,.07);">
                    <div style="font-size:2.2rem;margin-bottom:10px;">📊</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:2.4rem;font-weight:800;
                      color:#bf5af2;line-height:1;text-shadow:0 0 20px rgba(191,90,242,.5);">{pass_rate}%</div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:.6rem;letter-spacing:.14em;
                      color:#3a4d70;margin-top:8px;text-transform:uppercase;">Pass Rate</div>
                  </div>

                </div>
                """,unsafe_allow_html=True)

                # ── bar chart + test suites side by side ─────────────────────
                col_chart,col_suites=st.columns([3,2])

                with col_chart:
                    st.markdown("""<div style="font-family:'Oxanium',sans-serif;font-weight:700;
                      color:#c8d8f0;font-size:.95rem;margin-bottom:10px;">
                      📊 &nbsp;Test Results by File</div>""",unsafe_allow_html=True)
                    fnames_t=[s["file"] for s in file_stats_t]
                    fig_t=go.Figure()
                    fig_t.add_trace(go.Bar(
                        name="Passed",x=fnames_t,y=[s["passed"] for s in file_stats_t],
                        marker_color="#10b981",marker_line_width=0,
                        hovertemplate="%{x}<br>Passed: %{y}<extra></extra>"))
                    fig_t.add_trace(go.Bar(
                        name="Failed",x=fnames_t,y=[s["failed"] for s in file_stats_t],
                        marker_color="#ff4d6d",marker_line_width=0,
                        hovertemplate="%{x}<br>Failed: %{y}<extra></extra>"))
                    fig_t.update_layout(
                        barmode="stack",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Share Tech Mono,monospace",color="#8fa8d0",size=10),
                        legend=dict(bgcolor="rgba(8,11,22,.7)",bordercolor="#1a2540",borderwidth=1,
                                    font=dict(size=9),orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),
                        margin=dict(t=28,b=6,l=6,r=6),height=260,
                        xaxis=dict(tickangle=-30,gridcolor="rgba(26,37,64,.5)",showline=False,tickfont=dict(size=9)),
                        yaxis=dict(gridcolor="rgba(26,37,64,.5)",showline=False,tickfont=dict(size=9),title="Number of Tests"),
                    )
                    st.plotly_chart(fig_t,use_container_width=True,config={"displayModeBar":False})

                with col_suites:
                    st.markdown("""<div style="font-family:'Oxanium',sans-serif;font-weight:700;
                      color:#c8d8f0;font-size:.95rem;margin-bottom:10px;">
                      📋 &nbsp;Test Suites</div>""",unsafe_allow_html=True)
                    for s in file_stats_t:
                        label=s["file"].replace(".py","").replace("_"," ").title()
                        ok=s["failed"]==0 and s["pep_c"]==0
                        bg  ="rgba(16,185,129,.08)"  if ok else "rgba(255,77,109,.06)"
                        bord="rgba(16,185,129,.28)"  if ok else "rgba(255,77,109,.22)"
                        left="#10b981"               if ok else "#ff4d6d"
                        badge_col="#10b981"          if ok else "#ff4d6d"
                        st.markdown(f"""
                        <div style="background:{bg};border:1px solid {bord};border-left:3px solid {left};
                          border-radius:9px;padding:11px 16px;margin-bottom:7px;
                          display:flex;align-items:center;justify-content:space-between;
                          font-family:'Share Tech Mono',monospace;animation:slide-in .3s ease both;">
                          <div style="display:flex;align-items:center;gap:9px;">
                            <span style="font-size:.85rem;">{"✅" if ok else "❌"}</span>
                            <span style="color:#c8d8f0;font-size:.8rem;font-weight:600;">{label}</span>
                          </div>
                          <span style="background:rgba(16,185,129,.15);color:{badge_col};
                            border:1px solid {bord};border-radius:20px;
                            padding:3px 12px;font-size:.65rem;font-weight:700;letter-spacing:.06em;
                            white-space:nowrap;">{s["passed"]}/{s["total"]} passed</span>
                        </div>
                        """,unsafe_allow_html=True)

        elif feat=="search":
            st.markdown("""<div style="background:linear-gradient(135deg,#db2777,#f472b6);border-radius:10px;padding:18px 22px;margin-bottom:16px;">
                <div style="font-family:'Oxanium',sans-serif;font-size:1rem;font-weight:800;color:#fff;">🔎 Function Search</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:rgba(255,255,255,.6);margin-top:4px;">Search across all scanned functions instantly</div>
            </div>""",unsafe_allow_html=True)

            query=st.text_input("Search functions, files, or complexity...",placeholder="e.g. parse, sample_a.py, High",key="search_q",label_visibility="visible")
            if query:
                mask=(df["function_name"].str.contains(query,case=False,na=False)|
                      df["file_name"].str.contains(query,case=False,na=False)|
                      df["complexity_level"].str.contains(query,case=False,na=False))
                results=df[mask]
                st.markdown(f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.7rem;color:#3d5080;margin-bottom:10px;letter-spacing:.06em;">// {len(results)} result(s) for "{query}"</div>',unsafe_allow_html=True)
                for _,row in results.iterrows():
                    doc_ok=row["docstring_status"]=="Documented"
                    cx_color={"Low":"#00ff9d","Medium":"#ffd60a","High":"#ff4d6d"}.get(row["complexity_level"],"#3d5080")
                    st.markdown(f'<div class="fn-card"><div><div class="fn-name">{row["function_name"]}</div><div class="fn-line">{row["file_name"]} &nbsp;·&nbsp; Line {row["line_number"]}</div></div><div style="display:flex;gap:8px;">{cx_badge(row["complexity_level"])}{doc_badge(row["docstring_status"])}</div></div>',unsafe_allow_html=True)
            else:
                st.markdown('<div style="background:rgba(219,39,119,.06);border:1px solid rgba(219,39,119,.2);border-radius:8px;padding:14px 18px;font-family:\'Share Tech Mono\',monospace;font-size:.75rem;color:#f472b6;letter-spacing:.04em;">👆 Type above to search functions across all scanned files</div>',unsafe_allow_html=True)

        elif feat=="export":
            st.markdown("""<div style="background:linear-gradient(135deg,#0891b2,#06b6d4);border-radius:10px;padding:18px 22px;margin-bottom:16px;">
                <div style="font-family:'Oxanium',sans-serif;font-size:1rem;font-weight:800;color:#fff;">📤 Export Data</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:rgba(255,255,255,.6);margin-top:4px;">Download analysis results in JSON or CSV format</div>
            </div>""",unsafe_allow_html=True)

            st.markdown(f"""<div style="background:rgba(8,145,178,.08);border:1px solid rgba(8,145,178,.25);border-left:3px solid #06b6d4;border-radius:8px;padding:16px 20px;margin-bottom:16px;">
                <div style="font-family:'Oxanium',sans-serif;font-weight:700;color:#06b6d4;margin-bottom:10px;">📊 Export Summary</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.75rem;color:#3d5080;line-height:1.9;">
                • Total Functions: <span style="color:#00e5ff;">{total_fn}</span><br>
                • Documented: <span style="color:#00ff9d;">{documented}</span><br>
                • Missing Docstrings: <span style="color:#ff4d6d;">{undocumented}</span><br>
                • PEP 257 Issues: <span style="color:#ffd60a;">{total_pep}</span><br>
                • Files Scanned: <span style="color:#bf5af2;">{files_count}</span><br>
                • Avg Maintainability: <span style="color:#00e5ff;">{avg_mi:.1f}</span>
                </div>
            </div>""",unsafe_allow_html=True)

            export_df=df.drop(columns=["file_path","_source"],errors="ignore")
            json_export=export_df.to_dict(orient="records")
            csv_export=export_df.to_csv(index=False).encode()

            col_ej,col_ec=st.columns(2)
            with col_ej:
                st.download_button("📥 Export as JSON",json.dumps(json_export,indent=2),file_name="code_review_export.json",mime="application/json",use_container_width=True,key="exp_json")
                st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.65rem;color:#3d5080;text-align:center;margin-top:4px;">💡 JSON format for programmatic access</div>',unsafe_allow_html=True)
            with col_ec:
                st.download_button("📊 Export as CSV",csv_export,file_name="code_review_export.csv",mime="text/csv",use_container_width=True,key="exp_csv")
                st.markdown('<div style="font-family:\'Share Tech Mono\',monospace;font-size:.65rem;color:#3d5080;text-align:center;margin-top:4px;">💡 CSV format for Excel/spreadsheets</div>',unsafe_allow_html=True)

            st.markdown("<br>",unsafe_allow_html=True)
            # Coverage report JSON
            pep_export={"scan_count":st.session_state.scan_count,"doc_coverage_pct":doc_pct,"pep257_issues":total_pep,"files":{}}
            for fname,group in df.groupby("file_name"):
                pep_export["files"][fname]={"functions":group[["function_name","docstring_status","complexity_level","line_number"]].to_dict(orient="records"),"pep_issues":pep.get(fname,[])}
            st.download_button("📥 Download Coverage Report JSON",json.dumps(pep_export,indent=2),file_name="coverage_report.json",mime="application/json",use_container_width=True,key="exp_cov")

        elif feat=="help":
            st.markdown("""<div style="background:linear-gradient(135deg,#059669,#34d399);border-radius:10px;padding:18px 22px;margin-bottom:16px;">
                <div style="font-family:'Oxanium',sans-serif;font-size:1rem;font-weight:800;color:#fff;">💡 Help & Tips</div>
                <div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;color:rgba(255,255,255,.6);margin-top:4px;">Quick reference guide for getting the most out of this tool</div>
            </div>""",unsafe_allow_html=True)

            tips=[
                ("🔍 Scan your project","Enter your project folder path in the sidebar and click Scan Code. All .py files will be analysed recursively."),
                ("⚡ AI Fix with Groq","Add your free Groq API key (console.groq.com) to the sidebar or .env file. Then go to Validation and hit ⚡ AI Fix to auto-repair PEP 257 issues."),
                ("📋 PEP 257 codes","D100=module, D101=class, D102=method, D103=function missing docstring. D400=first line must end with period. D200=no blank lines around single-line docstring."),
                ("🔄 Workflow","Scan → Review Validation → AI Fix All → Apply All → Scan Again. Issues should drop to zero."),
                ("📊 Complexity levels","Low (1-5) = simple. Medium (6-10) = moderate. High (11+) = consider refactoring. Check Metrics view for details."),
                ("💾 .env file","Create a .env file in your project root with GROQ_API_KEY=gsk_... to auto-load your key on startup."),
                ("📥 Exporting","Use the Export panel here to download your full analysis as JSON or CSV for reports or further processing."),
                ("🔎 Filters & Search","Use Advanced Filters to narrow down undocumented or high-complexity functions. Use Search to find a specific function across files."),
            ]
            for emoji_title,desc in tips:
                parts=emoji_title.split(" ",1)
                st.markdown(f'<div style="background:rgba(5,150,105,.06);border:1px solid rgba(52,211,153,.15);border-left:2px solid #34d399;border-radius:8px;padding:12px 16px;margin-bottom:8px;"><div style="font-family:\'Oxanium\',sans-serif;font-weight:700;color:#34d399;font-size:.85rem;margin-bottom:4px;">{emoji_title}</div><div style="font-family:\'Share Tech Mono\',monospace;font-size:.72rem;color:#3d5080;line-height:1.6;">{desc}</div></div>',unsafe_allow_html=True)


