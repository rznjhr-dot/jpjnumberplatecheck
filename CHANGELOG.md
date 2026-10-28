# Changelog

## v2.1.2 (2026-10-28)

### Added
- STOP CURRENT SCAN button (left of KILLSWITCH): aborts the current
  number but keeps the JPJ browser/session alive, so the next number can
  be searched without logging in again
- Saved-login freshness ring: a live ≈5 minute countdown (SVG ring)
  with FORGET. This is a UI freshness window, not JPJ's actual timeout;
  the log still reports whether the saved session was really accepted

### Changed
- Number entry rebuilt as three OTP-style 4-digit boxes side by side
  (1–3 numbers per batch), monospace, centered, with focus ring
- Region selector moved next to EXECUTE SCAN in a tight horizontal row
- KILLSWITCH is now a filled red, pulsing button; STOP CURRENT SCAN is
  amber. Both respect prefers-reduced-motion
- Removed the orange focus ring and the 0/4 character counter from the
  OTP boxes; focus is now a subtle gray border
- Region checkboxes aligned in one tight row (8px gaps, also on mobile)
- EXECUTE SCAN label forced to one line
- Small RESET button next to the number boxes clears all three entries
  without touching existing results
- Completion overlay: full-screen summary with the available plates,
  dismissed by **Esc**, clicking outside the card, or the **✕** button.
  Closing it clears the completion state automatically

## v2.1.1 (2026-10-28)

### Added
- Session reuse + auto-close: after every batch the browser is closed
  and cookies are saved to `sessions/jpj_state.json` (mode 0600). The
  next batch opens a fresh window, tries the saved login, and only asks
  for manual login if JPJ's server session has expired. The log reports
  the saved login age and whether it was still valid; a FORGET button
  deletes the saved login
- KILLSWITCH button during a scan: stops immediately, hard-kills
  Chromium processes launched by the app (with a background
  Playwright close), clears the scan state, and returns to the start page
- "Current Running Numbers" dashboard: parses JPJ's latest-plate page
  (static HTML), groups Peninsular/Sarawak/Sabah, highlights the running
  prefix, caches for 30 minutes, and links to jpj.my

### Changed
- Typography refreshed: system UI sans (SF Pro / Segoe UI / Roboto) for
  all UI text and logs; monospace kept only for plate codes and the
  progress bar. Small labels bumped for readability
- Running-numbers dashboard moved above the search form (scrollable
  340px panel on mobile)
- Palette rebalanced: neutral dark surfaces, off-white primary text,
  gray secondary text, semantic green/amber/red/blue status colors;
  Hermès orange stays as the brand accent. Result cards remain cream
- Region checkboxes rebuilt as proper 18px controls: dark unchecked box
  with a visible border, green filled box with checkmark and white label
  when selected, plus a clear focus ring

### Fixed
- Web design review: WCAG AA contrast for secondary text, footer,
  placeholder, timestamps and error red
- Checkbox styling now targets the real 16px box (was Streamlit red /
  white), removes the accidental orange label chip, adds a visible
  keyboard focus ring and a 44px touch target
- Typing-effect opacity raised for readability

## v2.1 (2026-10-27)

### Added
- Region selector on the search page: Peninsular, Sarawak, Sabah, or
  ALL SEARCH. Default selection is Sarawak + Sabah
- `REGIONS` mapping + `region_state_codes()` helper in jpj_automation

### Changed
- Results are simpler: plate number + state only (price/RM310 removed
  from cards and copy summaries)
- UI recolored to a Hermès-inspired palette (orange, cream, gold on warm
  near-black)
- Progress and header counts now reflect the selected regions

## v2.0 (2026-10-13)

### Added
- Batch mode: enter multiple numbers, all scanned in one login session
  (JpjSession class keeps the browser open between checks)
- Hacker terminal UI: phosphor green on black, monospace, matrix rain
  background, scanline overlay, live verbose log with auto-scroll
- Matrix typing effect at bottom of terminal during scans
- Prefix cache: states sharing the same awalan (e.g. SIBU & MUKAH share
  QS series) skip the duplicate search and reuse the cached result
- Cross-platform installer (install.py) for macOS, Windows, and Linux
- Platform launchers: run.sh (macOS/Linux), run.bat (Windows)
- Color-coded terminal log: yellow (searching), bright green (found),
  gray (not available), red (errors), cyan (targets)
- Kill server button with auto-close tab countdown

### Changed
- 30 states scanned (Putrajaya and Labuan excluded — plates not
  transferable to other states)
- Plate results: white background with black text
- Dynamic state count in header
- Simplified input: multi-number text area, no fast mode toggle

### Removed
- Fast mode (experimental HTTP-based scanning via ZK AU protocol)
- Reverse engineering guide and traffic capture tools
- Old launchers (CekNombor.command, JPJ Checker.command)
- Session badge pill from UI
