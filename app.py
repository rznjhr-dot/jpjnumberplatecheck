#!/usr/bin/env python3
"""
JPJ Number Checker — Hermès Terminal Edition.

Batch mode: login once (CAPTCHA sekali), check multiple numbers dalam
satu sesi. Warm Hermès-inspired terminal aesthetic dengan matrix rain background.

Usage: streamlit run app.py
"""

import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent))
from jpj_automation import (
    JpjSession,
    PRODUCTION_STATES,
    REGIONS,
    LoginFailed,
    region_state_codes,
)

# ── Browser speed patch ──────────────────────────────────────────────
_speed = min(max(float(os.environ.get("JPJ_SPEED", "0.5")), 0.1), 1.0)

def _patched_wait(self, timeout):
    time.sleep(int(timeout * _speed) / 1000)

try:
    from playwright.sync_api import Page
    Page.wait_for_timeout = _patched_wait
except Exception:
    pass

# ── Page Config ──
st.set_page_config(
    page_title="JPJ Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════
# CSS — HERMÈS TERMINAL THEME
#   Warm near-black canvas · orange/cream/gold text · monospace
#   Terminal window chrome · scanline overlay · blinking cursor
#   Matrix rain canvas behind content (injected via components.html)
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Streamlit chrome ── */
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent; height: 4px;}
.main .block-container {
    max-width: 900px;
    padding: 32px 24px 64px !important;
}
[data-testid="stForm"] {border: none !important; padding: 0 !important;}

/* ── Base — warm black root, transparent children, orange text ── */
html, body, .stApp {
    background: #0a0705 !important;
    color: #f37021 !important;
    font-family: "SF Mono", ui-monospace, Menlo, Consolas, monospace !important;
}
/* All Streamlit text elements: force orange + monospace */
.stApp p, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[class*="css"],
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {
    color: #f37021 !important;
    font-family: "SF Mono", ui-monospace, Menlo, Consolas, monospace !important;
}
/* Keep containers transparent so matrix rain shows through faintly */
.main .block-container,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
section[data-testid="stVerticalBlock"] > div,
[data-testid="stForm"] {
    background: transparent !important;
}
.stApp {z-index: auto;}

/* ── Header ── */
.term-header {
    border: 1px solid rgba(243,112,33,0.35);
    border-radius: 0;
    padding: 12px 20px;
    margin-bottom: 24px;
    background: rgba(243,112,33,0.03);
    display: flex; align-items: center; justify-content: space-between;
}
.term-header .title {
    font-size: 14px; font-weight: 700; letter-spacing: 0.18em;
    color: #f37021; text-transform: uppercase;
}
.term-header .sub {
    font-size: 11px; color: #8a5730; letter-spacing: 0.12em;
    text-transform: uppercase; margin-top: 2px;
}
.term-header .ver {
    font-size: 10px; color: #c07a3e; letter-spacing: 0.1em;
}

/* ── Session status badge ── */
.session-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px; border-radius: 0;
    border: 1px solid rgba(243,112,33,0.2);
    font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
    background: rgba(243,112,33,0.03);
}
.session-badge .dot {
    width: 7px; height: 7px; border-radius: 50%; flex: none;
}
.session-badge.active .dot {background: #e8b96a; box-shadow: 0 0 6px #e8b96a;}
.session-badge.active {color: #e8b96a; border-color: rgba(232,185,106,0.4);}
.session-badge.dead .dot {background: #d0453a;}
.session-badge.dead {color: #d0453a; border-color: rgba(208,69,58,0.3);}
.session-badge.idle .dot {background: #8a5730;}
.session-badge.idle {color: #8a5730;}

/* ── Input zone ── */
.field-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.2em;
    color: #c07a3e; margin-bottom: 8px; text-transform: uppercase;
}
[data-testid="stTextArea"] textarea {
    background: #120d08 !important;
    border: 1px solid rgba(243,112,33,0.25) !important;
    border-radius: 0 !important;
    color: #f37021 !important;
    font-family: "SF Mono", ui-monospace, monospace !important;
    font-size: 16px !important; line-height: 1.8 !important;
    letter-spacing: 0.04em; padding: 12px 16px !important;
    transition: border-color 120ms ease;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: #f37021 !important;
    box-shadow: 0 0 0 1px rgba(243,112,33,0.3) !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: #5c3a20; font-style: italic;
}
.field-hint {
    font-size: 11px; line-height: 1.6; color: #8a5730;
    margin-top: 8px; letter-spacing: 0.02em;
}
.field-hint b {color: #f37021; font-weight: 400;}

/* ── Buttons ── */
[data-testid="stFormSubmitButton"] button,
.stButton > button[kind="primary"],
.stButton > button[kind="primaryFormSubmit"] {
    background: transparent !important;
    color: #f37021 !important;
    border: 1px solid #f37021 !important;
    border-radius: 0 !important;
    font-family: "SF Mono", monospace !important;
    font-size: 14px !important; font-weight: 700 !important;
    letter-spacing: 0.15em; height: 44px;
    text-transform: uppercase;
    transition: all 120ms ease;
}
[data-testid="stFormSubmitButton"] button:hover,
.stButton > button[kind="primary"]:hover,
.stButton > button[kind="primaryFormSubmit"]:hover {
    background: rgba(243,112,33,0.1) !important;
    box-shadow: 0 0 12px rgba(243,112,33,0.2) !important;
}
[data-testid="stFormSubmitButton"] button:active,
.stButton > button[kind="primary"]:active,
.stButton > button[kind="primaryFormSubmit"]:active {
    background: rgba(243,112,33,0.2) !important;
}
[data-testid="stFormSubmitButton"] button:disabled,
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primaryFormSubmit"]:disabled {
    border-color: #5c3a20 !important; color: #5c3a20 !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(208,69,58,0.4) !important;
    color: #d0453a !important; border-radius: 0 !important;
    font-family: "SF Mono", monospace !important;
    font-size: 12px !important; font-weight: 400 !important;
    letter-spacing: 0.1em; height: 36px;
    text-transform: uppercase;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(208,69,58,0.08) !important;
    border-color: #d0453a !important;
}
.stButton > button[kind="secondary"]:disabled {opacity: 0.3;}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > div {
    border-color: rgba(243,112,33,0.3) !important;
    background: transparent !important;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) > div {
    background: #f37021 !important; border-color: #f37021 !important;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) > div > div {
    background: #0a0705 !important; border-color: #0a0705 !important;
}
[data-testid="stCheckbox"] label {color: #c07a3e !important; font-size: 12px;}

/* ── Terminal window ── */
.term-window {
    border: 1px solid rgba(243,112,33,0.3);
    border-radius: 0;
    background: #0d0906;
    margin-bottom: 24px;
    overflow: hidden;
}
.term-titlebar {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px;
    background: rgba(243,112,33,0.06);
    border-bottom: 1px solid rgba(243,112,33,0.15);
}
.term-dots {display: flex; gap: 6px;}
.term-dots span {
    width: 10px; height: 10px; border-radius: 50%;
}
.term-dots .r {background: #ff5f56;}
.term-dots .y {background: #ffbd2e;}
.term-dots .g {background: #27c93f;}
.term-titlebar .t {
    font-size: 11px; color: #c07a3e; letter-spacing: 0.1em;
    flex: 1; text-align: center;
}
.term-titlebar .live {
    font-size: 10px; color: #e8b96a; letter-spacing: 0.1em;
    display: flex; align-items: center; gap: 4px;
}
.term-titlebar .live .pulse {
    width: 6px; height: 6px; border-radius: 50%; background: #e8b96a;
    animation: pulse 1.2s ease-in-out infinite;
}
.term-titlebar .live.done .pulse {background: #8a5730; animation: none;}
.term-titlebar .live.err .pulse {background: #d0453a; animation: none;}
@keyframes pulse {0%,100% {opacity: 1;} 50% {opacity: 0.2;}}

/* ── Terminal body (scrollable log area) ── */
.term-body {
    padding: 12px 16px;
    position: relative;
    max-height: 460px; overflow-y: auto;
}
.term-body::-webkit-scrollbar {width: 6px;}
.term-body::-webkit-scrollbar-thumb {background: rgba(243,112,33,0.15);}

/* ── Progress line (pinned above scroll area, always visible) ── */
.term-progress {
    background: #0d0906;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(243,112,33,0.15);
}
.term-progress .target {
    font-size: 13px; font-weight: 700; color: #ffcf8a;
    letter-spacing: 0.06em; margin-bottom: 6px;
}
.term-progress .bar {
    font-family: "SF Mono", monospace; font-size: 12px;
    color: #f37021; letter-spacing: 0; line-height: 1.4;
}
.term-progress .bar .fill {color: #f37021;}
.term-progress .bar .empty {color: #5c3a20;}
.term-progress .bar .num {color: #c07a3e; margin-left: 8px;}
.term-progress .bar .pct {color: #8a5730; margin-left: 8px;}

/* ── Matrix typing effect (pinned at bottom, always visible) ── */
.term-typing {
    padding: 8px 16px;
    border-top: 1px solid rgba(243,112,33,0.15);
    background: #080604;
    font-family: "SF Mono", monospace;
    font-size: 12px; color: #f37021;
    letter-spacing: 0.06em; opacity: 0.6;
    white-space: pre; overflow: hidden;
    min-height: 20px;
}

/* ── Log lines ── */
.term-log {font-size: 12px; line-height: 1.7; font-family: "SF Mono", monospace;}
.term-log .line {white-space: pre-wrap; word-break: break-word; min-height: 1.7em;}
.term-log .ts {color: #5c3a20;}
.term-log .arrow {color: #c07a3e;}
.term-log .msg-sys {color: #c07a3e;}
.term-log .msg-scan {color: #ffd166;}
.term-log .msg-ok {color: #e8b96a;}
.term-log .msg-nope {color: #8a7a6a;}
.term-log .msg-err {color: #d0453a;}
.term-log .msg-num {color: #ffcf8a; font-weight: 700;}

/* ── Blinking cursor ── */
.term-cursor {
    display: inline-block; width: 8px; height: 14px;
    background: #f37021; vertical-align: text-bottom;
    animation: blink 1s step-end infinite;
    margin-left: 2px;
}
@keyframes blink {0%,50% {opacity: 1;} 51%,100% {opacity: 0;}}

/* ── Scanline overlay ── */
.term-body::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg, transparent, transparent 2px,
        rgba(243,112,33,0.02) 2px, rgba(243,112,33,0.02) 3px);
    pointer-events: none; z-index: 1;
}

/* ── Progress bar (st.progress) ── */
[data-testid="stProgress"] > div {height: 2px !important; border-radius: 0;}
[data-testid="stProgress"] > div > div {background: #f37021 !important;}

/* ── Results ── */
.result-section {
    border-top: 1px solid rgba(243,112,33,0.15);
    padding-top: 20px; margin-top: 32px;
}
.result-num {
    font-size: 12px; font-weight: 700; color: #ffcf8a;
    letter-spacing: 0.1em; margin-bottom: 4px;
}
.result-count {
    font-size: 11px; color: #c07a3e; margin-bottom: 16px;
    letter-spacing: 0.04em;
}
.result-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px; margin-bottom: 16px;
}
.plate-card {padding: 0;}
.plate {
    background: #f3ece1; border: 1px solid rgba(243,112,33,0.15);
    border-radius: 4px; padding: 12px 10px; text-align: center;
    margin-bottom: 8px;
    font-family: "SF Mono", monospace;
    font-size: 20px; font-weight: 700; letter-spacing: 0.08em;
    color: #2b1b10 !important; font-variant-numeric: tabular-nums;
    box-shadow: inset 0 -2px 0 rgba(43,27,16,0.2);
}
.plate-state {
    font-size: 10px; font-weight: 400; letter-spacing: 0.16em;
    text-transform: uppercase; color: #c07a3e;
    font-family: "SF Mono", monospace; text-align: center;
}
.result-empty {
    font-size: 12px; color: #8a5730; line-height: 1.6;
    padding: 16px 0;
}

/* ── Copy block ── */
.copy-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.2em;
    text-transform: uppercase; color: #c07a3e;
    font-family: "SF Mono", monospace; margin-top: 12px;
}
.copy-sub {font-size: 11px; color: #5c3a20; margin-bottom: 8px;}
[data-testid="stTextArea"] textarea[aria-label="summary"] {
    font-size: 11px !important; color: #c07a3e !important;
    border-color: rgba(243,112,33,0.12) !important;
}

/* ── Alerts ── */
div[data-testid="stAlert"] {
    background: rgba(243,112,33,0.03) !important;
    border: 1px solid rgba(243,112,33,0.15) !important;
    border-radius: 0 !important;
}
div[data-testid="stAlert"] p {color: #f37021 !important; font-size: 12px;}

/* ── Footer ── */
.term-footer {
    margin-top: 32px; padding-top: 12px;
    border-top: 1px solid rgba(243,112,33,0.1);
    font-size: 10px; color: #5c3a20;
    letter-spacing: 0.08em; text-transform: uppercase;
    display: flex; justify-content: space-between; align-items: center;
}

/* ── Focus ── */
button:focus-visible, a:focus-visible, input:focus-visible,
textarea:focus-visible {
    outline: 1px solid #f37021 !important; outline-offset: 1px !important;
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {animation: none !important; transition: none !important;}
}

/* ── Responsive ── */
@media (max-width: 600px) {
    .main .block-container {padding: 20px 12px 48px !important;}
    .result-grid {grid-template-columns: 1fr;}
    .plate {font-size: 17px;}
    .term-header .ver {display: none;}
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# MATRIX RAIN — canvas behind everything
# ═══════════════════════════════════════════════════════════════════
components.html("""
<script>
(function(){
    try {
        var doc = window.parent.document;
        if (doc.getElementById('matrix-rain')) return;
        var canvas = doc.createElement('canvas');
        canvas.id = 'matrix-rain';
        canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:-1;opacity:0.04;pointer-events:none;';
        doc.body.appendChild(canvas);
        var ctx = canvas.getContext('2d');
        var chars = 'アイウエオカキクケコサシスセソタチツテト0123456789JPJMYSIKAP';
        var fs = 14;
        function resize(){
            canvas.width = window.parent.innerWidth;
            canvas.height = window.parent.innerHeight;
        }
        resize();
        window.parent.addEventListener('resize', resize);
        var drops = [];
        function initDrops(){
            var cols = Math.floor(canvas.width / fs);
            drops = [];
            for (var i = 0; i < cols; i++) drops[i] = Math.random() * -50;
        }
        initDrops();
        function draw(){
            ctx.fillStyle = 'rgba(0,0,0,0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#f37021';
            ctx.font = fs + 'px monospace';
            for (var i = 0; i < drops.length; i++){
                var text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fs, drops[i] * fs);
                if (drops[i] * fs > canvas.height && Math.random() > 0.975)
                    drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(draw, 55);

        // ── Persistent auto-scroll: pin terminal to latest line ──
        setInterval(function() {
            try {
                var bodies = doc.querySelectorAll('.term-body');
                bodies.forEach(function(b) { b.scrollTop = b.scrollHeight; });
            } catch(e) {}
        }, 200);

        // ── Matrix typing effect (pinned at bottom of live terminal) ──
        var mChars = 'アイウエオカキクケコサシスセソタチツテト0123456789JPQMYSIKAP█▓▒░';
        var curText = '';
        var phase = 'typing';
        var holdCount = 0;
        function matrixTick() {
            try {
                var el = doc.getElementById('term-typing-live');
                if (!el) { curText = ''; phase = 'typing'; return; }
                if (phase === 'typing') {
                    curText += mChars[Math.floor(Math.random() * mChars.length)];
                    if (curText.length >= 28) { phase = 'holding'; holdCount = 0; }
                } else if (phase === 'holding') {
                    holdCount++;
                    if (Math.random() < 0.35) {
                        var idx = Math.floor(Math.random() * curText.length);
                        curText = curText.substring(0, idx) +
                            mChars[Math.floor(Math.random() * mChars.length)] +
                            curText.substring(idx + 1);
                    }
                    if (holdCount > 10) { phase = 'clearing'; }
                } else {
                    curText = '';
                    phase = 'typing';
                }
                el.textContent = '> ' + curText + '█';
            } catch(e) {}
        }
        setInterval(matrixTick, 85);
    } catch(e) {}
})();
</script>
""", height=0)

# ═══════════════════════════════════════════════════════════════════
# MODULE-LEVEL SESSION (persists across Streamlit reruns)
# ═══════════════════════════════════════════════════════════════════
_jpj_session = None


def _get_session():
    global _jpj_session
    return _jpj_session


def _set_session(session):
    global _jpj_session
    _jpj_session = session


def _close_session():
    global _jpj_session
    if _jpj_session:
        _jpj_session.close()
        _jpj_session = None


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "results": {},          # {number: results_dict}
    "_scan": None,
    "running": False,
    "stop_event": None,
    "_scan_logs": [],
    "_last_numbers": "",
    "_last_visible": False,
    "_region_all": False,
    "_region_peninsular": False,
    "_region_sarawak": True,
    "_region_sabah": True,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v
if st.session_state.stop_event is None:
    st.session_state.stop_event = threading.Event()


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def parse_numbers(text):
    """Parse numbers from text area (newline, comma, or space separated)."""
    nums = []
    seen = set()
    for token in re.split(r'[\n,\s]+', text.strip()):
        token = token.strip()
        if token and token.isdigit():
            n = int(token)
            if 1 <= n <= 9999 and n not in seen:
                nums.append(n)
                seen.add(n)
    return nums


def _now_ts():
    return datetime.now().strftime("%H:%M:%S")


def _selected_regions():
    """Ordered region names currently selected in the UI."""
    if st.session_state.get("_region_all"):
        return list(REGIONS)
    picked = []
    if st.session_state.get("_region_peninsular"):
        picked.append("PENINSULAR")
    if st.session_state.get("_region_sarawak"):
        picked.append("SARAWAK")
    if st.session_state.get("_region_sabah"):
        picked.append("SABAH")
    return picked


def _region_label():
    if st.session_state.get("_region_all"):
        return "ALL SEARCH"
    picked = _selected_regions()
    return " + ".join(picked) if picked else "NONE"


def _target_states(regions):
    """(state_codes or None, number of state/district targets)."""
    if not regions:
        return [], 0
    codes = region_state_codes(regions)
    if codes is None:
        return None, len(PRODUCTION_STATES)
    wanted = set(codes)
    n = sum(1 for code, _, _ in PRODUCTION_STATES if code in wanted)
    return codes, n


def _add_log(scan, msg, mtype="sys"):
    """Add a timestamped log entry to the scan state."""
    with scan["lock"]:
        scan["logs"].append({"ts": _now_ts(), "msg": msg, "type": mtype})


def _make_status_cb(scan):
    """Create an on_status callback that logs messages with timestamps."""
    def cb(msg):
        mtype = "sys"
        mu = msg.upper()
        if "✅" in msg or "✓" in msg or "TERSEDIA" in mu:
            mtype = "ok"
        elif "❌" in msg or "✗" in msg or "TIDAK TERSEDIA" in mu:
            mtype = "nope"
        elif "GAGAL" in mu or "RALAT" in mu or "DILANGKAU" in mu \
                or "SESI TAMAT" in mu:
            mtype = "err"
        elif msg.startswith("[") or msg.startswith("Check "):
            mtype = "scan"
        _add_log(scan, msg, mtype)
    return cb


def _progress_bar(done, total, width=30):
    """ASCII progress bar string."""
    filled = int(width * done / max(total, 1))
    return "█" * filled + "░" * (width - filled)


def _customer_summary(number, results):
    """Generate a text summary for copy-to-clipboard."""
    avail = [v for v in results.values() if v.get("available")]
    nope = [v for v in results.values() if not v.get("available")]
    lines = [
        f"SEMAKAN NOMBOR JPJ — {number}",
        f"Tarikh: {datetime.now().strftime('%d %b %Y %I:%M %p')}",
        "",
    ]
    if avail:
        lines.append(f"NOMBOR TERSEDIA ({len(avail)}):")
        for v in sorted(avail, key=lambda x: x.get("state", "")):
            lines.append(f"✅ {v.get('nombor','')} — {v.get('state','')}")
    else:
        lines.append(f"Nombor {number} TIDAK tersedia di kawasan yang disemak.")
    nope_real = [v for v in nope if "Dilangkau" not in (v.get("status_text") or "")]
    skipped = [v for v in nope if "Dilangkau" in (v.get("status_text") or "")]
    if nope_real:
        states_nope = ", ".join(sorted(v.get("state", "") for v in nope_real))
        lines.append("")
        lines.append(f"Tak tersedia: {states_nope}")
    if skipped:
        states_skip = ", ".join(v.get("state", "") for v in skipped)
        lines.append("")
        lines.append(f"Tidak disemak (masalah teknikal): {states_skip}")
    lines.append("")
    lines.append("*Semakan melalui sistem mySIKAP JPJ")
    return "\n".join(lines)


def _copy_button(text, label="COPY", key="copybtn"):
    payload = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    html = f"""
    <div style="margin-bottom:8px">
      <button id="{key}" style="
        background:transparent; color:#f37021; border:1px solid rgba(243,112,33,0.4);
        border-radius:0; height:36px; padding:0 16px; font-size:11px; font-weight:700;
        cursor:pointer; font-family:'SF Mono',monospace; letter-spacing:0.15em;
        text-transform:uppercase; transition:all 120ms ease;
      " onclick="
        (function(btn){{
          navigator.clipboard.writeText('{payload}').then(function(){{
            btn.textContent='COPIED ✓';
            btn.style.background='rgba(232,185,106,0.1)';
            btn.style.borderColor='#e8b96a';
            btn.style.color='#e8b96a';
            setTimeout(function(){{
              btn.textContent='{label}';
              btn.style.background='transparent';
              btn.style.borderColor='rgba(243,112,33,0.4)';
              btn.style.color='#f37021';
            }}, 1600);
          }});
        }})(this);
      ">{label}</button>
    </div>
    """
    components.html(html, height=40)


def _session_badge():
    """Render the session status badge."""
    session = _get_session()
    if session and session.is_alive():
        st.markdown(
            '<div class="session-badge active"><span class="dot"></span>'
            'SESSION ACTIVE</div>',
            unsafe_allow_html=True,
        )
    elif session and not session.is_alive():
        st.markdown(
            '<div class="session-badge dead"><span class="dot"></span>'
            'SESSION EXPIRED</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="session-badge idle"><span class="dot"></span>'
            'NO SESSION</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════
# TERMINAL PANEL — live scan output (fragment, reruns every 0.4s)
# ═══════════════════════════════════════════════════════════════════
@st.fragment(run_every=0.4)
def _terminal_panel():
    scan = st.session_state.get("_scan")
    if not scan:
        return

    # Stop button
    if st.button("■ STOP", disabled=scan.get("done", False)):
        st.session_state.stop_event.set()

    with scan["lock"]:
        logs = list(scan["logs"])
        events = list(scan["events"])
        numbers = scan.get("numbers", [])
        cur_idx = scan.get("current_idx", 0)
        cur_num = scan.get("current_number")
        done = scan.get("done", False)
        err = scan.get("error")

    total_states = scan.get("total_states") or len(PRODUCTION_STATES)
    done_states = len(events)
    elapsed = time.time() - (scan.get("start_time") or time.time())
    timer = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"

    # Determine live status
    live_cls = ""
    live_txt = "SCANNING"
    if done and err is None:
        live_cls = "done"
        live_txt = "COMPLETE"
    elif done and err:
        live_cls = "err"
        live_txt = "ERROR"

    # Build progress section
    progress_html = ""
    if numbers:
        if cur_num is not None and not done:
            bar = _progress_bar(done_states, total_states)
            pct = int(100 * done_states / max(total_states, 1))
            progress_html = (
                f'<div class="term-progress">'
                f'<div class="target">>>> TARGET {cur_idx+1}/{len(numbers)}: '
                f'{cur_num}</div>'
                f'<div class="bar">'
                f'<span class="fill">{bar}</span>'
                f'<span class="num">{done_states}/{total_states}</span>'
                f'<span class="pct">{pct}% · {timer}</span>'
                f'</div></div>'
            )
        elif done:
            total_avail = sum(
                1 for r in scan.get("all_results", {}).values()
                for d in r.values() if d.get("available")
            )
            progress_html = (
                f'<div class="term-progress">'
                f'<div class="target">>>> BATCH COMPLETE — '
                f'{len(scan.get("all_results", {}))} numbers · '
                f'{total_avail} plates found</div>'
                f'</div>'
            )

    # Build log lines (last 60)
    visible_logs = logs[-60:]
    log_lines = []
    for entry in visible_logs:
        ts = entry["ts"]
        msg = entry["msg"]
        mtype = entry["type"]
        log_lines.append(
            f'<div class="line">'
            f'<span class="ts">[{ts}]</span> '
            f'<span class="arrow">▸</span> '
            f'<span class="msg-{mtype}">{msg}</span>'
            f'</div>'
        )
    log_html = "".join(log_lines)

    st.markdown(
        f'<div class="term-window">'
        f'<div class="term-titlebar">'
        f'<div class="term-dots">'
        f'<span class="r"></span><span class="y"></span><span class="g"></span>'
        f'</div>'
        f'<div class="t">jpj_mysikap@terminal: ~/scan</div>'
        f'<div class="live {live_cls}"><span class="pulse"></span>{live_txt}</div>'
        f'</div>'
        f'{progress_html}'
        f'<div class="term-body">'
        f'<div class="term-log">{log_html}</div>'
        f'</div>'
        f'<div class="term-typing" id="term-typing-live"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.progress(min(done_states / max(total_states, 1), 1.0))

    # Auto-scroll is handled by persistent interval in matrix rain block

    # Completion → hand results to session state
    if done:
        with scan["lock"]:
            st.session_state._scan_logs = list(scan["logs"])
            st.session_state.results = dict(scan.get("all_results", {}))
        stopped = st.session_state.stop_event.is_set()
        error = scan.get("error")
        if stopped:
            st.session_state._scan_status = ("info", "Imbasan dihentikan. Keputusan separa kekal di bawah.")
        elif isinstance(error, LoginFailed):
            st.session_state._scan_status = ("warning", "Login tidak selesai. Tekan Cari untuk cuba lagi.")
        elif error is not None:
            st.session_state._scan_status = ("error", f"Ralat: {error}")
        elif not scan.get("all_results"):
            st.session_state._scan_status = ("warning", "Imbasan tamat tanpa keputusan.")
        else:
            n = sum(1 for r in scan["all_results"].values()
                    for d in r.values() if d.get("available"))
            st.session_state._scan_status = (
                "success", f"Siap — {len(scan['all_results'])} nombor disemak, {n} plates tersedia.")
        st.session_state.running = False
        st.session_state._scan = None
        st.session_state.stop_event = threading.Event()
        st.rerun(scope="app")


# ═══════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════
_, _header_targets = _target_states(_selected_regions())
st.markdown(
    f'<div class="term-header">'
    f'<div><div class="title">JPJ MYSIKAP TERMINAL</div>'
    f'<div class="sub">batch scan mode · {_region_label()} · '
    f'{_header_targets} kawasan · login sekali</div></div>'
    '<div class="ver">v2.1</div>'
    '</div>',
    unsafe_allow_html=True,
)

# Close session button (only when session is active)
session = _get_session()
if session and session.is_alive() and not st.session_state.get("running"):
    if st.button("✕ CLOSE SESSION"):
        _close_session()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════
# REGION SELECTION
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="field-label">▸ KAWASAN CARIAN</div>',
            unsafe_allow_html=True)
_rc_all, _rc_pen, _rc_sar, _rc_sab = st.columns(4)
_rc_all.checkbox("ALL SEARCH", key="_region_all",
                 disabled=st.session_state.get("running", False))
_rc_pen.checkbox("PENINSULAR", key="_region_peninsular",
                 disabled=st.session_state.get("_region_all") or
                 st.session_state.get("running", False))
_rc_sar.checkbox("SARAWAK", key="_region_sarawak",
                 disabled=st.session_state.get("_region_all") or
                 st.session_state.get("running", False))
_rc_sab.checkbox("SABAH", key="_region_sabah",
                 disabled=st.session_state.get("_region_all") or
                 st.session_state.get("running", False))
st.markdown(
    '<div class="field-hint">Default: <b>Sarawak + Sabah</b>. Tandakan '
    '<b>ALL SEARCH</b> untuk semak semua kawasan.</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════
# INPUT — multi-number text area
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="field-label">▸ NOMBOR (satu per baris atau comma)</div>',
            unsafe_allow_html=True)
with st.form("search_form", clear_on_submit=False):
    numbers_text = st.text_area(
        "Nombor-nombor",
        value=st.session_state.get("_last_numbers", ""),
        height=100,
        placeholder="888\n777\n1234",
        label_visibility="collapsed",
        disabled=st.session_state.get("running", False),
    )
    check_btn = st.form_submit_button(
        "⚡ EXECUTE SCAN",
        type="primary",
        disabled=st.session_state.get("running", False),
    )

st.markdown(
    '<div class="field-hint">'
    'Masukkan 2-3 nombor (atau lebih). <b>Login sekali</b> — semua nombor '
    'disemak dalam sesi yang sama. Tetingkap JPJ akan terbuka untuk '
    'password + CAPTCHA, kemudian minimize dan scan berjalan di background.'
    '</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════
# BATCH SCAN LOGIC
# ═══════════════════════════════════════════════════════════════════
if check_btn:
    numbers = parse_numbers(numbers_text)
    regions = _selected_regions()
    scan_states, scan_total = _target_states(regions)
    if not numbers:
        st.error("Masukkan sekurang-kurangnya satu nombor yang sah (1-9999).")
    elif not regions:
        st.error("Pilih sekurang-kurangnya satu kawasan carian.")
    else:
        st.session_state._last_numbers = numbers_text
        st.session_state.running = True
        st.session_state.stop_event = threading.Event()

        scan = {
            "numbers": numbers,
            "states": scan_states,
            "total_states": scan_total,
            "regions": regions,
            "current_idx": 0,
            "current_number": None,
            "events": [],
            "all_results": {},
            "logs": [],
            "lock": threading.Lock(),
            "done": False,
            "error": None,
            "start_time": time.time(),
        }
        st.session_state._scan = scan
        stop_ev = st.session_state.stop_event

        def run_batch():
            try:
                status_cb = _make_status_cb(scan)

                def progress_cb(rd):
                    with scan["lock"]:
                        scan["events"].append(rd)

                # Boot sequence
                _add_log(scan, "INIT chromium browser engine...", "sys")

                session = _get_session()
                if session and session.is_alive():
                    _add_log(scan, "SESSION_REUSED — sambung sesi sedia ada", "ok")
                else:
                    if session and not session.is_alive():
                        _add_log(scan, "SESSION_EXPIRED — perlu login baru", "err")
                        _close_session()
                    _add_log(scan, "CONNECT https://public.jpj.gov.my/public/", "sys")
                    _add_log(scan, "AUTH required — login manual diperlukan", "sys")
                    _add_log(scan, "LOGIN_WINDOW_OPENED — masuk password + CAPTCHA", "sys")

                    new_session = JpjSession(
                        visible=False,
                        on_status=status_cb,
                        stop_event=stop_ev,
                    )
                    new_session.login()
                    _set_session(new_session)

                    _add_log(scan, "AUTH_SUCCESS — session established", "ok")
                    _add_log(scan, "FORM_READY — kategori: Nombor Pendaftaran Semasa", "ok")

                _add_log(scan, f">>> REGIONS: {' + '.join(scan['regions'])} "
                            f"({scan['total_states']} kawasan)", "num")
                _add_log(scan, f">>> BATCH START: {len(numbers)} nombor queued", "num")

                for i, number in enumerate(numbers):
                    if stop_ev.is_set():
                        _add_log(scan, "BATCH STOPPED by user", "err")
                        break

                    with scan["lock"]:
                        scan["current_idx"] = i
                        scan["current_number"] = number
                        scan["events"] = []

                    _add_log(scan, f">>> TARGET {i+1}/{len(numbers)}: {number}", "num")

                    results = _get_session().check_number(
                        number,
                        states=scan.get("states"),
                        on_progress=progress_cb,
                        on_status=status_cb,
                        stop_event=stop_ev,
                    )

                    if results == "__SESSION_LOST__":
                        _add_log(scan, "SESSION_LOST — sesi JPJ tamat", "err")
                        _close_session()
                        break

                    with scan["lock"]:
                        scan["all_results"][number] = results
                        n_avail = sum(1 for d in results.values()
                                      if d.get("available"))
                        n_checked = len(results)
                    _add_log(scan, f">>> {number} COMPLETE: "
                             f"{n_avail}/{n_checked} tersedia", "num")

                if not stop_ev.is_set():
                    _add_log(scan, ">>> BATCH COMPLETE", "ok")
                    session = _get_session()
                    if session and session.is_alive():
                        _add_log(scan, "SESSION_ACTIVE — boleh masuk nombor "
                                 "lagi atau tutup sesi", "ok")

            except LoginFailed as e:
                _add_log(scan, f"LOGIN_FAILED — {e}", "err")
                scan["error"] = e
                _close_session()
            except Exception as e:
                _add_log(scan, f"ERROR — {e}", "err")
                scan["error"] = e
            finally:
                scan["done"] = True

        threading.Thread(target=run_batch, daemon=True).start()

# Terminal panel (live during scan)
if st.session_state.get("_scan"):
    _terminal_panel()

# ═══════════════════════════════════════════════════════════════════
# COMPLETION STATUS
# ═══════════════════════════════════════════════════════════════════
_scan_status = st.session_state.pop("_scan_status", None)
if _scan_status:
    kind, msg = _scan_status
    getattr(st, kind)(msg)

# ═══════════════════════════════════════════════════════════════════
# RESULTS — per number
# ═══════════════════════════════════════════════════════════════════
all_results = st.session_state.get("results", {})
if all_results and not st.session_state.get("running") and not st.session_state.get("_scan"):
    for number, results in all_results.items():
        available = {k: v for k, v in results.items() if v.get("available")}
        n_avail = len(available)
        n_total = len(results)

        st.markdown(
            f'<div class="result-section">'
            f'<div class="result-num">>>> NOMBOR {number}</div>'
            f'<div class="result-count">{n_avail}/{n_total} kawasan tersedia</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if available:
            cards = []
            for k, v in available.items():
                plate = (
                    f"{v['awalan']} {number}"
                    f"{(' ' + v['akhiran']) if v.get('akhiran') else ''}"
                ).strip()
                cards.append(
                    f'<div class="plate-card">'
                    f'<div class="plate">{plate}</div>'
                    f'<div class="plate-state">{v["state"]}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div class="result-grid">{"".join(cards)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="result-empty">'
                f'Nombor {number} TIDAK tersedia di kawasan yang disemak.'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Copy summary for this number
        summary = _customer_summary(number, results)
        st.markdown(
            '<div class="copy-title">▸ Ringkasan untuk pelanggan</div>'
            '<div class="copy-sub">Tekan butang untuk copy, kemudian paste</div>',
            unsafe_allow_html=True,
        )
        _copy_button(summary, label=f"COPY {number}", key=f"copy_{number}")
        st.text_area(
            f"summary_{number}", value=summary, height=140,
            label_visibility="collapsed",
        )

    # Full scan log (verbose history)
    logs = st.session_state.get("_scan_logs", [])
    if logs:
        st.markdown(
            '<div class="copy-title" style="margin-top:24px">'
            '▸ FULL TERMINAL LOG</div>'
            '<div class="copy-sub">Sejarah verbose lengkap</div>',
            unsafe_allow_html=True,
        )
        log_lines = []
        for entry in logs:
            ts = entry["ts"]
            msg = entry["msg"]
            mtype = entry["type"]
            log_lines.append(
                f'<div class="line">'
                f'<span class="ts">[{ts}]</span> '
                f'<span class="arrow">▸</span> '
                f'<span class="msg-{mtype}">{msg}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="term-window">'
            f'<div class="term-titlebar">'
            f'<div class="term-dots">'
            f'<span class="r"></span><span class="y"></span><span class="g"></span>'
            f'</div>'
            f'<div class="t">jpj_mysikap@terminal: ~/scan/history</div>'
            f'<div class="live done"><span class="pulse"></span>ARCHIVED</div>'
            f'</div>'
            f'<div class="term-body" style="max-height:400px">'
            f'<div class="term-log">{"".join(log_lines[-200:])}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Clear results + kill server
    _col_clear, _col_kill = st.columns(2)
    with _col_clear:
        if st.button("✕ CLEAR RESULTS"):
            st.session_state.results = {}
            st.session_state._scan_logs = []
            st.rerun()
    with _col_kill:
        if st.button("■ KILL SERVER"):
            st.session_state._killing = True

    if st.session_state.get("_killing"):
        _close_session()
        components.html("""
        <script>
        (function(){
            try {
                var doc = window.parent.document;
                if (doc.getElementById('kill-overlay')) return;
                var ov = doc.createElement('div');
                ov.id = 'kill-overlay';
                ov.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:#0a0705;z-index:99999;display:flex;align-items:center;justify-content:center;color:#e8b96a;font-family:SF Mono,monospace;font-size:22px;letter-spacing:0.15em;text-transform:uppercase;';
                doc.body.appendChild(ov);
                var left = 3;
                ov.textContent = '■ SERVER STOPPED — closing in ' + left + 's';
                var t = setInterval(function(){
                    left--;
                    if (left > 0) {
                        ov.textContent = '■ SERVER STOPPED — closing in ' + left + 's';
                    } else {
                        clearInterval(t);
                        try { window.parent.close(); } catch(e) {}
                        setTimeout(function(){
                            try { window.parent.location.href = 'about:blank'; } catch(e) {}
                        }, 200);
                        ov.textContent = '■ CLOSE TAB MANUALLY';
                    }
                }, 1000);
            } catch(e) {}
        })();
        </script>
        """, height=0)
        def _delayed_kill():
            time.sleep(3.5)
            os._exit(0)
        threading.Thread(target=_delayed_kill, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="term-footer">'
    f'<span>+ DATA FROM mySIKAP JPJ · LOGIN ONCE · BATCH MODE</span>'
    f'<span>v2.1</span>'
    f'</div>',
    unsafe_allow_html=True,
)
