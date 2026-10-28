# JPJ Number Checker

Check vehicle registration number availability on JPJ mySIKAP — batch
mode, one login, terminal UI.

Enter 1–3 numbers in OTP-style boxes, pick your regions, log in once
(manual CAPTCHA), and the tool scans every state/district in the
selected regions automatically. Results are displayed as plate cards
with copy-ready summaries.

## Features

- **OTP-style entry** — 1–3 numbers in large 4-digit boxes, side by side,
  with a small RESET to clear them for the next search
- **STOP CURRENT SCAN** — abort the current number but keep the JPJ
  session alive for the next one (no re-login)
- **KILLSWITCH** — stop a running scan instantly, close Chromium, and
  return to the start page
- **Login reuse + auto-close** — the browser closes after every batch;
  saved cookies let the next batch skip manual login until JPJ expires
  the server session. A live ≈5 minute freshness ring shows the saved
  login state
- **Running numbers dashboard** — current JPJ plate series for every
  state/district, fetched from jpj.my and cached for 30 minutes
- **Region filter** — search Peninsular, Sarawak, Sabah, or all regions
  (default: Sarawak + Sabah). Covers 30 states & districts
  (Putrajaya and Labuan excluded — plates not transferable)
- **Prefix cache** — states sharing the same number series (e.g. Sibu &
  Mukah share QS) are only searched once, saving time
- **Hermès-inspired dark UI** — neutral surfaces, off-white text, orange
  accents, semantic green/red/blue status colors, matrix rain background
- **Completion overlay** — a summary card appears when a scan finishes;
  close it with Esc, clicking outside, or ✕
- **Color-coded results** — green (found), amber (scanning), muted
  (not available), red (errors)
- **Copy summaries** — formatted plate availability summary for each
  number, ready to paste to customers

## Prerequisites

- **Python 3.9 or newer** ([python.org](https://python.org))
- **Internet connection**
- **A valid JPJ mySIKAP account** (you log in yourself — the tool does
  not provide credentials)

## Installation

### macOS / Linux

```bash
git clone https://github.com/rznjhr-dot/jpjnumberplatecheck.git
cd jpjnumberplatecheck
python3 install.py
```

### Windows

```cmd
git clone https://github.com/jpjnumberplatecheck/jpjnumberplatecheck.git
cd jpjnumberplatecheck
python install.py
```

The installer creates a virtual environment (`.venv/`), installs
Streamlit and Playwright, and downloads the Chromium browser (~150MB).

## Usage

### Start the app

**macOS / Linux:**
```bash
./run.sh
```

**Windows:**
```cmd
run.bat
```

Then open `http://localhost:8501` in your browser.

### Scan numbers

1. Enter 1–3 numbers in the OTP-style boxes (max 4 digits each).
   Use **↺ RESET** to clear all three boxes for a new search
2. Tick the regions next to the button — **ALL**, **Peninsular**,
   **Sarawak**, or **Sabah** (default: Sarawak + Sabah)
3. Click **EXECUTE SCAN**
4. A browser window opens — log in to JPJ mySIKAP with your password
   and CAPTCHA (this happens once per session)
5. The browser minimizes — scanning runs in the background
6. Watch the terminal log for live progress
7. When done, results appear as plate cards with availability status

### macOS .app bundle (optional)

For a double-clickable macOS app:

```bash
./build_streamlit_app.sh
```

This creates `JPJ Checker.app` in the project directory.

## How It Works

1. **Login**: A Chromium browser (via Playwright) opens the JPJ mySIKAP
   portal. You log in manually — the tool does **not** bypass, solve, or
   automate CAPTCHA.

2. **Batch scanning**: After login, the browser session stays open.
   Each number is checked across every state/district in the selected
   regions. The tool selects each state, picks the available prefix
   (awalan), enters the number, and reads the result.

3. **Prefix caching**: When multiple states share the same number
   series prefix, only the first state searches it. Subsequent states
   reuse the cached result (shown as "cached" in the terminal log).

4. **Results**: Available plates are shown as cards with the full plate
   number and state. A text summary is generated for copy-pasting.

5. **Running numbers dashboard**: `jpj.my/JPJ_Latest_Number_Plates.htm`
   is static HTML maintained by JPJ (no API) — the page states its own
   "as on" timestamp. The app fetches that HTML, parses the three region
   lists, highlights the running prefix, and caches the result for
   30 minutes. Putrajaya and Labuan are shown for reference but are not
   part of scans.

6. **Session lifecycle**: At the end of a batch the browser is closed
   and the login cookies are saved to `sessions/jpj_state.json` (local
   only, git-ignored, mode 0600). The next batch opens a fresh window,
   loads those cookies, and skips manual login if JPJ's server session
   is still alive. If it has expired, you are asked to log in again. The
   terminal log reports the saved login's age and whether it was still
   valid — that is the real JPJ lifetime observed, not a hardcoded
   timeout. The dashboard shows a live ≈5 minute freshness ring; it is
   only a visual guide, not a guarantee. Use **FORGET** to delete the
   saved login.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `streamlit: command not found` | Use `python -m streamlit run app.py` |
| Browser doesn't open | Run `python -m playwright install chromium` |
| Port 8501 already in use | Edit `run.sh`/`run.bat`: change `--server.port 8501` to another port |
| JPJ login page doesn't load | Check internet connection; JPJ may restrict non-Malaysian IPs |
| Scan stops mid-way | The JPJ session may have expired. Restart the app and scan again |
| Scan hangs / need to abort | Press **KILLSWITCH** in the terminal panel — it closes Chromium and resets the page |
| Need to change number mid-scan | Press **STOP CURRENT SCAN** — it aborts the number but keeps the JPJ session for the next one |
| Chrome window stays open | It auto-closes at the end of every batch. If one lingers, press **KILLSWITCH** or **CLOSE SESSION NOW** |
| Saved login rejected | JPJ's server session expired — log in again when prompted, or press **FORGET** first |

## Project Structure

```
jpjnumberplatecheck/
├── app.py                  # Streamlit GUI (main entry point)
├── jpj_automation.py       # Browser automation engine + JpjSession
├── install.py              # Cross-platform installer
├── run.sh                  # macOS/Linux launcher
├── run.bat                 # Windows launcher
├── build_streamlit_app.sh  # macOS .app bundle builder (optional)
├── requirements.txt        # Python dependencies
├── CHANGELOG.md            # Version history
├── LICENSE                 # MIT license
└── .env.example            # Environment variable template (empty)
```

## Disclaimer

THIS TOOL IS NOT AFFILIATED WITH, ENDORSED BY, OR CONNECTED TO
Jabatan Pengangkutan Jalan (JPJ) OR THE MALAYSIAN GOVERNMENT.

- **Your own account**: You need your own valid JPJ mySIKAP account.
  The tool does not provide credentials.
- **CAPTCHA is manual**: The tool does NOT bypass, solve, or automate
  CAPTCHA. You type it yourself every session.
- **Personal use**: This tool is intended for personal, non-commercial
  use only.
- **No warranty**: This software is provided "as is" without warranty.
  It may stop working if JPJ changes their website.
- **Terms of service**: Users are responsible for complying with JPJ's
  terms of service regarding automated access.
- **Privacy**: The tool runs entirely locally. No data is sent to any
  server except JPJ's own website during your manual login and scan.
  No telemetry, no analytics, no tracking.
- **Malaysian access**: JPJ mySIKAP may restrict access to Malaysian IP
  addresses. Users outside Malaysia may need a VPN.

## License

[MIT](LICENSE)
