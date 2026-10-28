#!/usr/bin/env python3
"""
JPJ Number Checker — Hermès Terminal Edition.

Batch mode: login once (CAPTCHA sekali), check multiple numbers dalam
satu sesi. Warm Hermès-inspired terminal aesthetic dengan matrix rain background.

Usage: streamlit run app.py
"""

import html as _html
import math
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

JPJ_LATEST_URL = "https://www.jpj.my/JPJ_Latest_Number_Plates.htm"

sys.path.insert(0, str(Path(__file__).parent))
from jpj_automation import (
    JpjSession,
    PRODUCTION_STATES,
    REGIONS,
    LoginFailed,
    forget_saved_session,
    region_state_codes,
    saved_session_age_seconds,
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

:root {
    --font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
    --font-mono: "SF Mono", ui-monospace, Menlo, Consolas,
                 "Liberation Mono", monospace;
}

/* ── Base — warm black root, transparent children, orange text ── */
html, body, .stApp {
    background: #0f1115 !important;
    color: #ece8e1 !important;
    font-family: var(--font-ui) !important;
}
/* All Streamlit text elements: force orange + UI font */
.stApp p, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[class*="css"],
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span {
    color: #ece8e1 !important;
    font-family: var(--font-ui) !important;
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
    font-size: 11px; color: #a9a49c; letter-spacing: 0.12em;
    text-transform: uppercase; margin-top: 2px;
}
.term-header .ver {
    font-size: 10px; color: #8f8a83; letter-spacing: 0.1em;
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
.session-badge.active .dot {background: #34d399; box-shadow: 0 0 6px #34d399;}
.session-badge.active {color: #34d399; border-color: rgba(52,211,153,0.4);}
.session-badge.dead .dot {background: #f87171;}
.session-badge.dead {color: #f87171; border-color: rgba(248,113,113,0.3);}
.session-badge.idle .dot {background: #5b6068;}
.session-badge.idle {color: #8f8a83;}

/* ── Input zone ── */
.field-label {
    font-size: 11px; font-weight: 700; letter-spacing: 0.14em;
    color: #d5d0c8; margin-bottom: 8px; text-transform: uppercase;
}
[data-testid="stTextArea"] textarea {
    background: #1a1e24 !important;
    border: 1px solid rgba(243,112,33,0.25) !important;
    border-radius: 0 !important;
    color: #ece8e1 !important;
    font-family: var(--font-ui) !important;
    font-variant-numeric: tabular-nums;
    font-size: 16px !important; line-height: 1.8 !important;
    letter-spacing: 0.04em; padding: 12px 16px !important;
    transition: border-color 120ms ease;
}
[data-testid="stTextArea"] textarea:focus {
    border-color: #f37021 !important;
    box-shadow: 0 0 0 1px rgba(243,112,33,0.3) !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: #8f8a83; font-style: italic;
}

/* ── OTP-style number entry ── */
[data-testid="stTextInput"] div[data-baseweb="input"] {
    background: #1a1e24 !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    border-radius: 6px !important;
    height: 58px !important;
    padding: 0 10px !important;
    box-shadow: none !important;
    transition: border-color 120ms ease;
}
[data-testid="stTextInput"] div[data-baseweb="base-input"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
    border-color: #8f8a83 !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    color: #f5f0e8 !important;
    font-family: var(--font-mono) !important;
    font-size: 24px !important;
    font-weight: 600 !important;
    letter-spacing: 0.25em !important;
    text-align: center !important;
    text-indent: 0.25em;
    padding: 0 !important;
    height: 100% !important;
    font-variant-numeric: tabular-nums;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextInput"] input:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] input::placeholder {
    color: #8f8a83 !important;
    letter-spacing: 0.25em !important;
}
/* Hide Streamlit's max_chars counter (0/4) */
[data-testid="InputInstructions"] {display: none !important;}
.field-hint {
    font-size: 11px; line-height: 1.6; color: #a9a49c;
    margin-top: 8px; letter-spacing: 0.02em;
}
.field-hint b {color: #f37021; font-weight: 400;}

/* Region row — tight, aligned checkboxes */
[class*="st-key-region_row"] {
    gap: 8px !important;
    align-items: center !important;
    flex-wrap: wrap;
}
[class*="st-key-region_row"] [data-testid="stCheckbox"] {
    margin: 0 !important;
}

.saved-login {
    display: flex; align-items: center; gap: 10px;
    padding: 2px 0 16px;
}
.saved-ring {flex: 0 0 auto;}
.saved-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.14em;
    color: #34d399; text-transform: uppercase;
    font-family: var(--font-ui);
}
.saved-sub {
    font-size: 10px; color: #8f8a83; letter-spacing: 0.03em;
    margin-top: 2px; font-family: var(--font-ui);
}

/* ── Buttons ── */
[data-testid="stFormSubmitButton"] button,
.stButton > button[kind="primary"],
.stButton > button[kind="primaryFormSubmit"] {
    background: transparent !important;
    color: #f37021 !important;
    border: 1px solid #f37021 !important;
    border-radius: 0 !important;
    font-family: var(--font-ui) !important;
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
    border-color: #5b6068 !important; color: #5b6068 !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid rgba(208,69,58,0.4) !important;
    color: #f87171 !important; border-radius: 0 !important;
    font-family: var(--font-ui) !important;
    font-size: 12px !important; font-weight: 400 !important;
    letter-spacing: 0.1em; height: 44px;
    text-transform: uppercase;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(208,69,58,0.08) !important;
    border-color: #d0453a !important;
}
.stButton > button[kind="secondary"]:disabled {opacity: 0.3;}

/* Small reset button next to the number boxes */
[class*="st-key-reset_numbers"] button[kind="secondary"] {
    height: 28px !important;
    min-height: 28px !important;
    padding: 0 10px !important;
    background: transparent !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    color: #a9a49c !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase;
}
[class*="st-key-reset_numbers"] button[kind="secondary"]:hover {
    border-color: #f37021 !important;
    color: #f37021 !important;
    background: rgba(243,112,33,0.06) !important;
}
[class*="st-key-reset_numbers"] button p {
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    white-space: nowrap !important;
}

/* Keep the EXECUTE label on one line */
.stButton > button[kind="primary"] p,
[data-testid="stFormSubmitButton"] button p {
    white-space: nowrap !important;
    font-size: 14px !important;
    letter-spacing: 0.08em !important;
    line-height: 1.1 !important;
}

/* Stop current scan — amber outline */
[class*="st-key-stop_scan"] button[kind="secondary"] {
    background: rgba(251,191,36,0.08) !important;
    border: 1px solid rgba(251,191,36,0.55) !important;
    color: #fbbf24 !important;
    font-weight: 700 !important;
}
[class*="st-key-stop_scan"] button[kind="secondary"]:hover {
    background: rgba(251,191,36,0.16) !important;
    border-color: #fbbf24 !important;
}
[class*="st-key-stop_scan"] button[kind="secondary"]:disabled {opacity: 0.4;}

/* Killswitch — filled red, pulsing */
[class*="st-key-killswitch"] button[kind="secondary"] {
    background: #dc2626 !important;
    border: 1px solid #f87171 !important;
    color: #ffffff !important;
    font-weight: 800 !important;
    letter-spacing: 0.08em !important;
    box-shadow: 0 0 0 1px rgba(220,38,38,0.55),
                0 0 16px rgba(220,38,38,0.28);
    animation: kill-pulse 1.8s ease-in-out infinite;
}
[class*="st-key-killswitch"] button[kind="secondary"]:hover {
    background: #ef4444 !important;
    box-shadow: 0 0 0 1px rgba(248,113,113,0.9),
                0 0 26px rgba(239,68,68,0.55);
}
[class*="st-key-killswitch"] button[kind="secondary"]:disabled {
    opacity: 0.4; animation: none;
}
@keyframes kill-pulse {
    0%, 100% {
        box-shadow: 0 0 0 1px rgba(220,38,38,0.55),
                    0 0 10px rgba(220,38,38,0.2);
    }
    50% {
        box-shadow: 0 0 0 2px rgba(248,113,113,0.9),
                    0 0 26px rgba(239,68,68,0.5);
    }
}
@media (prefers-reduced-motion: reduce) {
    [class*="st-key-killswitch"] button[kind="secondary"] {animation: none;}
}
.term-titlebar .live.stop {color: #fbbf24;}
.term-titlebar .live.stop .pulse {background: #fbbf24; animation: none;}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label[data-baseweb="checkbox"] > span:first-child {
    width: 18px !important; height: 18px !important;
    background-color: #1a1e24 !important;
    border: 2px solid #7c828d !important;
    border-radius: 3px !important;
    transition: background-color 120ms ease, border-color 120ms ease;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:hover > span:first-child {
    border-color: #f37021 !important;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) > span:first-child {
    background-color: #15803d !important;
    border-color: #15803d !important;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:focus-visible) > span:first-child {
    outline: 2px solid #ffcf8a;
    outline-offset: 2px;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"] p {
    color: #b9b3a9 !important; font-size: 12px;
}
[data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:checked) p {
    color: #f5f0e8 !important; font-weight: 600;
}
[data-testid="stCheckbox"] label {
    min-height: 44px; padding: 10px 0;
}

/* ── Terminal window ── */
.term-window {
    border: 1px solid rgba(243,112,33,0.3);
    border-radius: 0;
    background: #15181d;
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
    font-size: 11px; color: #a9a49c; letter-spacing: 0.1em;
    flex: 1; text-align: center;
    font-family: var(--font-mono);
}
.term-titlebar .live {
    font-size: 10px; color: #34d399; letter-spacing: 0.1em;
    display: flex; align-items: center; gap: 4px;
    font-family: var(--font-mono);
}
.term-titlebar .live .pulse {
    width: 6px; height: 6px; border-radius: 50%; background: #34d399;
    animation: pulse 1.2s ease-in-out infinite;
}
.term-titlebar .live.done .pulse {background: #5b6068; animation: none;}
.term-titlebar .live.err .pulse {background: #f87171; animation: none;}
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
    background: #15181d;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(243,112,33,0.15);
}
.term-progress .target {
    font-size: 13px; font-weight: 700; color: #f5f0e8;
    letter-spacing: 0.06em; margin-bottom: 6px;
}
.term-progress .bar {
    font-family: var(--font-mono); font-size: 12px;
    color: #f37021; letter-spacing: 0; line-height: 1.4;
}
.term-progress .bar span {font-family: var(--font-mono) !important;}
.term-progress .bar .fill {color: #f37021;}
.term-progress .bar .empty {color: #3a3f47;}
.term-progress .bar .num {color: #a9a49c; margin-left: 8px;}
.term-progress .bar .pct {color: #8f8a83; margin-left: 8px;}

/* ── Matrix typing effect (pinned at bottom, always visible) ── */
.term-typing {
    padding: 8px 16px;
    border-top: 1px solid rgba(243,112,33,0.15);
    background: #0c0e12;
    font-family: var(--font-mono);
    font-size: 12px; color: #f37021;
    letter-spacing: 0.06em; opacity: 0.85;
    white-space: pre; overflow: hidden;
    min-height: 20px;
}

/* ── Log lines ── */
.term-log {font-size: 12px; line-height: 1.7; font-family: var(--font-ui) !important;}
.term-log .line {white-space: pre-wrap; word-break: break-word; min-height: 1.7em;}
.term-log .ts {color: #8f8a83 !important;}
.term-log .arrow {color: #8f8a83 !important;}
.term-log .msg-sys {color: #60a5fa !important;}
.term-log .msg-scan {color: #fbbf24 !important;}
.term-log .msg-ok {color: #34d399 !important;}
.term-log .msg-nope {color: #8f8a83 !important;}
.term-log .msg-err {color: #f87171 !important;}
.term-log .msg-num {color: #f5f0e8 !important; font-weight: 700;}

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
    font-size: 12px; font-weight: 700; color: #f5f0e8;
    letter-spacing: 0.1em; margin-bottom: 4px;
}
.result-count {
    font-size: 11px; color: #a9a49c; margin-bottom: 16px;
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
    font-family: var(--font-mono);
    font-size: 20px; font-weight: 700; letter-spacing: 0.08em;
    color: #2b1b10 !important; font-variant-numeric: tabular-nums;
    box-shadow: inset 0 -2px 0 rgba(43,27,16,0.2);
}
.plate-state {
    font-size: 11px; font-weight: 400; letter-spacing: 0.12em;
    text-transform: uppercase; color: #a9a49c;
    font-family: var(--font-ui); text-align: center;
}
.result-empty {
    font-size: 12px; color: #a9a49c; line-height: 1.6;
    padding: 16px 0;
}

/* ── Copy block ── */
.copy-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.2em;
    text-transform: uppercase; color: #d5d0c8;
    font-family: var(--font-ui); margin-top: 12px;
}
.copy-sub {font-size: 11px; color: #8f8a83; margin-bottom: 8px;}
[data-testid="stTextArea"] textarea[aria-label="summary"] {
    font-size: 12px !important; color: #ece8e1 !important;
    border-color: rgba(243,112,33,0.12) !important;
}

/* ── Alerts ── */
div[data-testid="stAlert"] {
    background: rgba(243,112,33,0.03) !important;
    border: 1px solid rgba(243,112,33,0.15) !important;
    border-radius: 0 !important;
}
div[data-testid="stAlert"] p {color: #ece8e1 !important; font-size: 12px;}

/* ── Running numbers dashboard ── */
.running-board {
    border: 1px solid rgba(243,112,33,0.22);
    background: #15181d;
    margin: 0 0 24px;
}
.running-head {
    display: flex; justify-content: space-between; align-items: baseline;
    gap: 12px; padding: 10px 14px;
    border-bottom: 1px solid rgba(243,112,33,0.12);
}
.running-board .running-title {
    font-size: 10px; font-weight: 700; letter-spacing: 0.2em;
    color: #a9a49c !important; text-transform: uppercase;
    font-family: var(--font-ui);
}
.running-board .running-updated {
    font-size: 10px; letter-spacing: 0.08em; color: #8f8a83 !important;
    text-transform: uppercase; text-decoration: none;
    font-family: var(--font-ui);
}
.running-board .running-updated:hover {color: #f37021 !important;}
.running-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px;
    background: rgba(243,112,33,0.12);
}
.running-col {
    background: #15181d; padding: 10px 14px 12px;
    max-height: 280px; overflow-y: auto;
}
.running-board .running-region {
    font-size: 10px; font-weight: 700; letter-spacing: 0.18em;
    color: #f37021 !important; text-transform: uppercase; margin-bottom: 4px;
    font-family: var(--font-ui);
}
.running-row {
    display: flex; justify-content: space-between; align-items: baseline;
    gap: 10px; padding: 3px 0;
    border-bottom: 1px dashed rgba(243,112,33,0.08);
}
.running-board .running-state {
    font-size: 11px; color: #a9a49c !important; letter-spacing: 0.04em;
    text-transform: uppercase; font-family: var(--font-ui);
}
.running-board .running-plate, .running-board .running-plate span {
    font-family: var(--font-mono) !important; font-size: 12px;
    color: #f5f0e8 !important;
    letter-spacing: 0.08em; white-space: nowrap;
    font-variant-numeric: tabular-nums;
}
.running-board .running-prefix {
    color: #f37021 !important; font-weight: 700;
    margin-right: 4px;
}
.running-board .running-num {color: #f5f0e8 !important;}
.running-board .running-suffix {
    color: #f37021 !important; font-weight: 700;
    margin-left: 4px;
}
.running-board .running-row.is-off .running-state,
.running-board .running-row.is-off .running-prefix,
.running-board .running-row.is-off .running-num,
.running-board .running-row.is-off .running-suffix {color: #5b6068 !important;}
.running-empty {
    padding: 14px; font-size: 11px; color: #a9a49c !important;
    font-family: var(--font-ui);
}
.running-foot {
    display: flex; justify-content: space-between; gap: 12px;
    padding: 8px 14px; border-top: 1px solid rgba(243,112,33,0.12);
    font-size: 10px; letter-spacing: 0.06em;
    text-transform: uppercase; font-family: var(--font-ui);
}
.running-board .running-foot span {color: #8f8a83 !important;}
.running-col::-webkit-scrollbar {width: 4px;}
.running-col::-webkit-scrollbar-thumb {
    background: rgba(243,112,33,0.35);
}
.running-col::-webkit-scrollbar-track {background: transparent;}
@media (max-width: 768px) {
    .running-grid {grid-template-columns: 1fr;}
    .running-col {max-height: none; overflow: visible;}
    .running-head {flex-direction: column; align-items: flex-start; gap: 4px;}
    .running-foot {flex-direction: column; gap: 4px;}
    .running-board {max-height: 340px; overflow-y: auto;}
    .running-board::-webkit-scrollbar {width: 4px;}
    .running-board::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.16);
    }
}

[class*="st-key-dismiss_completion"] {
    position: fixed !important; left: -10000px !important; top: 0 !important;
    width: 1px !important; height: 1px !important; overflow: hidden !important;
}

/* ── Footer ── */
.term-footer > span {color: #8f8a83 !important;}
.term-footer {
    margin-top: 32px; padding-top: 12px;
    border-top: 1px solid rgba(243,112,33,0.1);
    font-size: 10px; color: #8f8a83;
    letter-spacing: 0.08em; text-transform: uppercase;
    font-family: var(--font-ui);
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
    saved = False
    if _jpj_session:
        try:
            saved = bool(_jpj_session.close())
        finally:
            _jpj_session = None
    return saved


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════
_DEFAULTS = {
    "results": {},          # {number: results_dict}
    "_scan": None,
    "running": False,
    "stop_event": None,
    "_scan_logs": [],
    "_completion": None,
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


def _reset_number_inputs():
    """Clear the three OTP-style number boxes (keeps old results)."""
    for key in ("_num1", "_num2", "_num3"):
        st.session_state[key] = ""


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


# ═══════════════════════════════════════════════════════════════════
# RUNNING NUMBERS (JPJ latest plate page)
# ═══════════════════════════════════════════════════════════════════
def _parse_running_numbers(raw):
    """Parse https://www.jpj.my/JPJ_Latest_Number_Plates.htm (static HTML)."""
    text = _html.unescape(re.sub(r"<[^>]+>", "\n", raw))
    m = re.search(r"as on\s+([^\n]+?\([A-Za-z]+\))", text, re.I)
    updated = " ".join(m.group(1).split()) if m else ""
    parts = re.split(r"\b(Peninsular|Sarawak|Sabah)\b", text)
    regions = {}
    for i in range(1, len(parts) - 1, 2):
        name = parts[i].upper()
        rows = []
        for line in parts[i + 1].splitlines():
            line = " ".join(line.split())
            mm = re.match(
                r"^([A-Z][A-Z ]{1,30}?)\s*-\s*([A-Z]{1,4}\d{1,4}[A-Z]?)(\*?)$",
                line, re.I,
            )
            if mm:
                rows.append({
                    "state": mm.group(1).strip().upper(),
                    "plate": mm.group(2).upper(),
                    "unavailable": bool(mm.group(3)),
                })
        if rows:
            regions[name] = rows
    if not regions:
        raise RuntimeError("JPJ page format changed")
    return {"updated": updated, "regions": regions}


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_running_numbers():
    import urllib.request
    req = urllib.request.Request(
        JPJ_LATEST_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=6) as resp:
        raw = resp.read().decode("utf-8", "replace")
    return _parse_running_numbers(raw)


def _render_running_numbers():
    try:
        data = _fetch_running_numbers()
    except Exception:
        data = None

    if not data:
        st.markdown(
            f'<div class="running-board">'
            f'<div class="running-head">'
            f'<span class="running-title">▸ CURRENT RUNNING NUMBERS</span>'
            f'<a class="running-updated" href="{JPJ_LATEST_URL}" '
            f'target="_blank" rel="noopener">OPEN JPJ.MY ↗</a>'
            f'</div>'
            f'<div class="running-empty">Data nombor semasa JPJ tidak dapat '
            f'dimuatkan. Buka pautan di atas.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    cols = []
    for region in ("PENINSULAR", "SARAWAK", "SABAH"):
        rows = data["regions"].get(region, [])
        items = []
        for row in rows:
            plate = row["plate"]
            pm = re.match(r"([A-Z]+)(\d+)([A-Z]*)$", plate)
            if pm:
                plate_html = (
                    f'<span class="running-prefix">{pm.group(1)}</span>'
                    f'<span class="running-num">{pm.group(2)}</span>'
                    f'<span class="running-suffix">{pm.group(3)}</span>'
                )
            else:
                plate_html = _html.escape(plate)
            off = " is-off" if row["unavailable"] else ""
            items.append(
                f'<div class="running-row{off}">'
                f'<span class="running-state">{_html.escape(row["state"])}</span>'
                f'<span class="running-plate">{plate_html}</span>'
                f'</div>'
            )
        body = "".join(items) or '<div class="running-state">tiada data</div>'
        cols.append(
            f'<div class="running-col">'
            f'<div class="running-region">{region} · {len(rows)}</div>'
            f'{body}'
            f'</div>'
        )

    updated = _html.escape(data.get("updated") or "")
    updated_txt = f"UPDATED {updated} · " if updated else ""
    st.markdown(
        f'<div class="running-board">'
        f'<div class="running-head">'
        f'<span class="running-title">▸ CURRENT RUNNING NUMBERS</span>'
        f'<a class="running-updated" href="{JPJ_LATEST_URL}" target="_blank" '
        f'rel="noopener">{updated_txt}OPEN JPJ.MY ↗</a>'
        f'</div>'
        f'<div class="running-grid">{"".join(cols)}</div>'
        f'<div class="running-foot">'
        f'<span>SUMBER · JPJ.MY · CACHE 30 MIN</span>'
        f'<span>PUTRAJAYA / LABUAN TIDAK DISEMAK · * UPDATE UNAVAILABLE</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _force_kill_playwright_browsers():
    """Best-effort hard kill of Chromium processes launched by this app.

    Playwright's sync API is thread-affine, so closing from the UI thread
    can raise. Kill the browser processes (descendants of this Streamlit
    process that use a Playwright temp profile) first, then let
    session.close() clean up.
    """
    if sys.platform == "win32":
        return
    try:
        import subprocess
        out = subprocess.check_output(
            ["ps", "-axo", "pid=,ppid=,command=", "-ww"],
            text=True, timeout=5,
        )
    except Exception:
        return

    parents = {}
    cmds = {}
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        parents[pid] = ppid
        cmds[pid] = parts[2]

    children = {}
    for pid, ppid in parents.items():
        children.setdefault(ppid, []).append(pid)

    stack = [os.getpid()]
    descendants = set()
    while stack:
        cur = stack.pop()
        for child in children.get(cur, []):
            if child not in descendants:
                descendants.add(child)
                stack.append(child)

    for pid in descendants:
        cmd = cmds.get(pid, "")
        if "playwright_chromiumdev_profile" not in cmd:
            continue
        try:
            os.kill(pid, 9)
        except Exception:
            pass


def _close_session_quietly(session):
    _force_kill_playwright_browsers()
    try:
        session.close()
    except Exception:
        pass


def _close_session_now():
    """Close an idle browser from the UI thread without Playwright races."""
    session = _get_session()
    _set_session(None)
    if session is not None:
        threading.Thread(
            target=_close_session_quietly, args=(session,), daemon=True
        ).start()
    st.rerun()


def _request_stop_scan(scan):
    """Stop the current number but keep the JPJ session alive."""
    scan["keep_session"] = True
    scan["stop_requested"] = True
    ev = st.session_state.get("stop_event")
    if ev is not None:
        try:
            ev.set()
        except Exception:
            pass
    _add_log(scan, "STOP_REQUESTED — hentikan nombor semasa, "
             "sesi JPJ dikekalkan", "scan")


def _kill_scan():
    """Hard stop: signal the scan, close Chromium, reset to the start page."""
    ev = st.session_state.get("stop_event")
    if ev is not None:
        try:
            ev.set()
        except Exception:
            pass
    scan = st.session_state.get("_scan")
    if scan is not None:
        try:
            scan["kill_requested"] = True
        except Exception:
            pass

    session = _get_session()
    _set_session(None)
    if session is not None:
        threading.Thread(
            target=_close_session_quietly, args=(session,), daemon=True
        ).start()

    st.session_state.running = False
    st.session_state._scan = None
    st.session_state.stop_event = threading.Event()
    st.session_state.results = {}
    st.session_state._scan_logs = []
    st.session_state._completion = None
    st.session_state._last_visible = False
    st.session_state._scan_status = (
        "info", "KILLSWITCH — browser ditutup. Kembali ke muka depan.")
    st.rerun(scope="app")


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
        cursor:pointer; font-family:inherit; letter-spacing:0.15em;
        text-transform:uppercase; transition:all 120ms ease;
      " onclick="
        (function(btn){{
          navigator.clipboard.writeText('{payload}').then(function(){{
            btn.textContent='COPIED ✓';
            btn.style.background='rgba(232,185,106,0.1)';
            btn.style.borderColor='#34d399';
            btn.style.color='#34d399';
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
# SAVED LOGIN BADGE — live ≈5 min freshness ring
# ═══════════════════════════════════════════════════════════════════
@st.fragment(run_every=1)
def _saved_login_badge():
    age = saved_session_age_seconds()
    if age is None:
        return
    window = 300.0
    remaining = max(0.0, window - age)
    frac = remaining / window
    color = "#34d399" if remaining > 0 else "#fbbf24"
    mins, secs = divmod(int(remaining), 60)
    label = f"{mins}:{secs:02d}" if remaining > 0 else "AGED"
    circ = 2 * math.pi * 16
    dash = circ * frac
    if remaining > 0:
        sub = "FRESH ≈5 MIN — batch seterusnya cuba guna semula"
    else:
        sub = f"{int(age // 60)} MIN LALU — akan dicuba, mungkin perlu login"
    st.markdown(
        f'<div class="saved-login">'
        f'<svg class="saved-ring" width="44" height="44" '
        f'viewBox="0 0 44 44">'
        f'<circle cx="22" cy="22" r="16" fill="none" '
        f'stroke="rgba(255,255,255,0.12)" stroke-width="3"/>'
        f'<circle cx="22" cy="22" r="16" fill="none" stroke="{color}" '
        f'stroke-width="3" stroke-linecap="round" '
        f'stroke-dasharray="{circ:.1f}" '
        f'stroke-dashoffset="{circ - dash:.1f}" '
        f'transform="rotate(-90 22 22)"/>'
        f'<text x="22" y="25.5" text-anchor="middle" fill="{color}" '
        f'font-size="8.5" font-family="SF Mono, monospace">{label}</text>'
        f'</svg>'
        f'<div class="saved-copy">'
        f'<div class="saved-title">LOGIN DISIMPAN</div>'
        f'<div class="saved-sub">{sub}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _clear_completion():
    st.session_state._completion = None


def _completion_overlay():
    """Full-screen completion card, dismissed by Esc, backdrop, or ✕.

    The card is moved into the parent document from a 0-height iframe so
    it can cover the whole app. Closing it also clicks a hidden
    Streamlit button, which clears the session flag and reruns.
    """
    data = st.session_state.get("_completion")
    if not data:
        return

    st.button("TUTUP", key="dismiss_completion", on_click=_clear_completion)

    avail = data.get("available", [])
    rows = []
    for item in avail[:8]:
        rows.append(
            f'<div class="jpj-row">'
            f'<span class="jpj-plate">{_html.escape(item["plate"])}</span>'
            f'<span class="jpj-state">{_html.escape(item["state"])}</span>'
            f'</div>'
        )
    if len(avail) > 8:
        rows.append(f'<div class="jpj-more">+{len(avail) - 8} lagi</div>')
    rows_html = "".join(rows) or (
        '<div class="jpj-empty">Tiada plate tersedia.</div>'
    )

    accent = data.get("accent", "#34d399")
    html = """<style id="jpj-complete-style">
#jpj-complete-overlay {
    position: fixed; inset: 0; z-index: 2147483000;
    display: flex; align-items: center; justify-content: center;
    padding: 16px; background: rgba(6,8,12,0.72);
    backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
}
#jpj-complete-overlay .jpj-card {
    width: min(460px, 100%); max-height: 82vh; overflow: auto;
    position: relative; color: #ece8e1;
    background: #15181d; border: 1px solid rgba(255,255,255,0.14);
    border-top: 3px solid __ACCENT__; border-radius: 10px;
    padding: 20px 22px; box-shadow: 0 24px 80px rgba(0,0,0,0.55);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    animation: jpj-in 180ms ease-out;
}
@keyframes jpj-in {
    from {opacity: 0; transform: translateY(8px) scale(0.985);}
    to {opacity: 1; transform: none;}
}
@media (prefers-reduced-motion: reduce) {
    #jpj-complete-overlay .jpj-card {animation: none;}
}
#jpj-complete-overlay .jpj-close {
    position: absolute; top: 8px; right: 8px;
    background: transparent; border: 0; color: #8f8a83;
    font-size: 16px; line-height: 1; cursor: pointer;
    padding: 6px 8px; border-radius: 6px;
}
#jpj-complete-overlay .jpj-close:hover {
    color: #f5f0e8; background: rgba(255,255,255,0.06);
}
#jpj-complete-overlay .jpj-kicker {
    font-size: 9px; letter-spacing: 0.18em; color: #8f8a83;
    text-transform: uppercase; margin-bottom: 6px;
}
#jpj-complete-overlay .jpj-title {
    font-size: 14px; font-weight: 800; letter-spacing: 0.12em;
    text-transform: uppercase; color: __ACCENT__; margin-bottom: 4px;
}
#jpj-complete-overlay .jpj-sub {
    font-size: 11px; color: #a9a49c; letter-spacing: 0.03em;
    margin-bottom: 14px;
}
#jpj-complete-overlay .jpj-rows {
    border-top: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;
}
#jpj-complete-overlay .jpj-row {
    display: flex; justify-content: space-between; gap: 12px;
    padding: 7px 0; border-bottom: 1px dashed rgba(255,255,255,0.07);
}
#jpj-complete-overlay .jpj-plate {
    font-family: "SF Mono", ui-monospace, Menlo, Consolas, monospace;
    font-size: 12px; color: #f5f0e8; letter-spacing: 0.06em;
    white-space: nowrap;
}
#jpj-complete-overlay .jpj-state {
    font-size: 10px; color: #8f8a83; text-transform: uppercase;
    letter-spacing: 0.04em; text-align: right;
}
#jpj-complete-overlay .jpj-empty,
#jpj-complete-overlay .jpj-more {
    font-size: 10px; color: #8f8a83; padding: 10px 0;
}
#jpj-complete-overlay .jpj-hint {
    font-size: 9px; color: #8f8a83; letter-spacing: 0.06em;
    text-transform: uppercase;
}
</style>
<div id="jpj-complete-source">
<div id="jpj-complete-overlay" role="dialog" aria-modal="true"
     aria-label="__TITLE__">
  <div class="jpj-card">
    <button class="jpj-close" type="button" aria-label="Tutup">✕</button>
    <div class="jpj-kicker">JPJ MYSIKAP</div>
    <div class="jpj-title">__TITLE__</div>
    <div class="jpj-sub">__SUBTITLE__</div>
    <div class="jpj-rows">__ROWS__</div>
    <div class="jpj-hint">ESC atau klik luar untuk tutup</div>
  </div>
</div>
</div>
<script>
(() => {
    const doc = window.parent.document;
    if (doc.getElementById('jpj-complete-overlay')) return;
    const style = document.getElementById('jpj-complete-style');
    const source = document.getElementById('jpj-complete-source');
    if (!style || !source) return;
    const overlay = source.firstElementChild;
    doc.head.appendChild(style);
    doc.body.appendChild(overlay);

    const closeBtn = overlay.querySelector('.jpj-close');
    let closed = false;
    const clickDismiss = (tries) => {
        const btn = doc.querySelector(
            '[class*="st-key-dismiss_completion"] button');
        if (btn) { btn.click(); return; }
        if (tries < 12) setTimeout(() => clickDismiss(tries + 1), 150);
    };
    const dismiss = () => {
        if (closed) return;
        closed = true;
        doc.removeEventListener('keydown', onKey);
        overlay.remove();
        const st = doc.getElementById('jpj-complete-style');
        if (st) st.remove();
        clickDismiss(0);
    };
    const onKey = (e) => { if (e.key === 'Escape') dismiss(); };
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) dismiss();
    });
    closeBtn.addEventListener('click', dismiss);
    doc.addEventListener('keydown', onKey);
    closeBtn.focus();
})();
</script>"""
    html = (html.replace("__TITLE__", _html.escape(data.get("title", "")))
                .replace("__SUBTITLE__", _html.escape(data.get("subtitle", "")))
                .replace("__ROWS__", rows_html)
                .replace("__ACCENT__", accent))
    components.html(html, height=0)


# ═══════════════════════════════════════════════════════════════════
# TERMINAL PANEL — live scan output (fragment, reruns every 0.4s)
# ═══════════════════════════════════════════════════════════════════
@st.fragment(run_every=0.4)
def _terminal_panel():
    scan = st.session_state.get("_scan")
    if not scan:
        return

    _stop_col, _kill_col = st.columns(2, gap="small")
    with _stop_col:
        if st.button("⏸ STOP CURRENT SCAN", key="stop_scan",
                     disabled=scan.get("done", False) or
                     scan.get("stop_requested", False),
                     help="Hentikan nombor semasa sahaja. Sesi JPJ kekal "
                          "aktif untuk nombor seterusnya."):
            _request_stop_scan(scan)
    with _kill_col:
        if st.button("■ KILLSWITCH — CLOSE BROWSER", key="killswitch",
                     disabled=scan.get("done", False),
                     help="Hentikan serta-merta, tutup Chromium, dan "
                          "kembali ke muka depan."):
            _kill_scan()

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
    if scan.get("stop_requested") and not done:
        live_cls = "stop"
        live_txt = "STOPPING"
    elif done and err is None:
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
        kept = bool(scan.get("keep_session") and _get_session())
        error = scan.get("error")
        if stopped:
            if kept:
                st.session_state._scan_status = (
                    "info", "Nombor semasa dihentikan — sesi JPJ masih aktif. "
                    "Teruskan cari nombor lain tanpa login.")
            else:
                st.session_state._scan_status = (
                    "info", "Imbasan dihentikan. Keputusan separa kekal di bawah.")
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
        avail = []
        for _num, _res in scan.get("all_results", {}).items():
            for _rd in _res.values():
                if _rd.get("available"):
                    avail.append({"number": _num,
                                  "plate": _rd.get("nombor", ""),
                                  "state": _rd.get("state", "")})
        if error is not None:
            _title = "IMBASAN TIDAK SELESAI"
            _sub = str(error)[:160]
            _accent = "#f87171"
        elif stopped and kept:
            _title = "IMBASAN DIHENTIKAN"
            _sub = ("Nombor semasa dihentikan — sesi JPJ masih aktif. "
                    f"{len(avail)} plate ditemui.")
            _accent = "#fbbf24"
        elif stopped:
            _title = "IMBASAN DIHENTIKAN"
            _sub = (f"Keputusan separa disimpan · {len(avail)} plate ditemui.")
            _accent = "#fbbf24"
        else:
            _title = "IMBASAN SELESAI"
            _sub = (f"{len(scan.get('numbers', []))} nombor disemak · "
                    f"{len(avail)} plate tersedia.")
            _accent = "#34d399"
        st.session_state._completion = {
            "title": _title, "subtitle": _sub, "accent": _accent,
            "available": avail,
        }

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
    '<div class="ver">v2.1.2</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════
# RUNNING NUMBERS DASHBOARD (top of page)
# ═══════════════════════════════════════════════════════════════════
_render_running_numbers()

# Session status — active browser or saved login for the next batch
session = _get_session()
if not st.session_state.get("running"):
    if session and session.is_alive():
        if st.button("✕ CLOSE SESSION NOW", key="close_session_now"):
            _close_session_now()
    else:
        if saved_session_age_seconds() is not None:
            _sc1, _sc2 = st.columns([5, 1], gap="small")
            with _sc1:
                _saved_login_badge()
            with _sc2:
                if st.button("FORGET", key="forget_login",
                             width="stretch",
                             help="Padam login tersimpan; batch seterusnya "
                                  "perlu login baru."):
                    forget_saved_session()
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════
# NUMBER ENTRY (OTP-style) + REGIONS + EXECUTE
# ═══════════════════════════════════════════════════════════════════
_num_disabled = st.session_state.get("running", False)
_num_lbl, _num_reset = st.columns([5, 1], vertical_alignment="center")
_num_lbl.markdown(
    '<div class="field-label">▸ NOMBOR (1–3 nombor · max 4 digit)</div>',
    unsafe_allow_html=True,
)
with _num_reset:
    st.button("↺ RESET", key="reset_numbers",
              on_click=_reset_number_inputs,
              disabled=_num_disabled,
              help="Kosongkan ketiga-tiga kotak nombor. Keputusan lama kekal.")
_n1, _n2, _n3 = st.columns(3, gap="small")
num1 = _n1.text_input("Nombor 1", max_chars=4, placeholder="0000",
                      key="_num1", label_visibility="collapsed",
                      disabled=_num_disabled)
num2 = _n2.text_input("Nombor 2", max_chars=4, placeholder="0000",
                      key="_num2", label_visibility="collapsed",
                      disabled=_num_disabled)
num3 = _n3.text_input("Nombor 3", max_chars=4, placeholder="0000",
                      key="_num3", label_visibility="collapsed",
                      disabled=_num_disabled)

_btn_col, _reg_col = st.columns([0.7, 3], gap="small",
                                vertical_alignment="center")
with _btn_col:
    check_btn = st.button("⚡ EXECUTE SCAN", type="primary",
                          width="stretch", disabled=_num_disabled)
with _reg_col:
    with st.container(horizontal=True, gap="small", key="region_row",
                      vertical_alignment="center"):
        st.checkbox("ALL", key="_region_all", disabled=_num_disabled)
        st.checkbox("PENINSULAR", key="_region_peninsular",
                    disabled=st.session_state.get("_region_all") or
                    _num_disabled)
        st.checkbox("SARAWAK", key="_region_sarawak",
                    disabled=st.session_state.get("_region_all") or
                    _num_disabled)
        st.checkbox("SABAH", key="_region_sabah",
                    disabled=st.session_state.get("_region_all") or
                    _num_disabled)

st.markdown(
    '<div class="field-hint">'
    'Default <b>Sarawak + Sabah</b> · <b>ALL</b> = semua kawasan · '
    '<b>Login sekali</b> untuk seluruh batch. Tetingkap JPJ akan terbuka '
    'untuk password + CAPTCHA, kemudian minimize dan scan berjalan di '
    'background.'
    '</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════
# BATCH SCAN LOGIC
# ═══════════════════════════════════════════════════════════════════
if check_btn:
    _raw_nums = [num1, num2, num3]
    _bad = []
    for _v in _raw_nums:
        _v = _v.strip()
        if not _v:
            continue
        if not _v.isdigit() or not (1 <= int(_v) <= 9999):
            _bad.append(_v)
    numbers = parse_numbers(" ".join(_raw_nums))
    regions = _selected_regions()
    scan_states, scan_total = _target_states(regions)
    if _bad:
        st.error("Setiap nombor mesti digit sahaja, 1–9999 (max 4 digit).")
    elif not numbers:
        st.error("Masukkan sekurang-kurangnya satu nombor.")
    elif not regions:
        st.error("Pilih sekurang-kurangnya satu kawasan carian.")
    else:
        st.session_state._completion = None
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
            "keep_session": False,
            "stop_requested": False,
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

            except LoginFailed as e:
                _add_log(scan, f"LOGIN_FAILED — {e}", "err")
                scan["error"] = e
                _close_session()
            except Exception as e:
                _add_log(scan, f"ERROR — {e}", "err")
                scan["error"] = e
            finally:
                # Close the browser at the end of every batch. Cookies are
                # saved first, so the next batch can still skip manual login
                # if JPJ's server session is still alive.
                had_session = _get_session() is not None
                if scan.get("keep_session") and had_session:
                    _add_log(scan, "SESSION_KEPT — sesi masih aktif untuk "
                             "nombor seterusnya", "ok")
                else:
                    try:
                        saved = _close_session()
                        if had_session:
                            if saved:
                                _add_log(scan, "SESSION_CLOSED — login disimpan "
                                         "untuk batch seterusnya", "ok")
                            else:
                                _add_log(scan, "SESSION_CLOSED — browser ditutup "
                                         "(login tidak dapat disimpan)", "err")
                    except Exception as e:
                        _add_log(scan, f"SESSION_CLOSE_WARN — {e}", "err")
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
                ov.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:#0f1115;z-index:99999;display:flex;align-items:center;justify-content:center;color:#f5f0e8;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:22px;letter-spacing:0.15em;text-transform:uppercase;';
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
    f'<span>v2.1.2</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# Completion summary overlay (Esc / click outside / ✕)
_completion_overlay()
