# nextscope — Next.js API Endpoint Discovery Tool 🔭

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)
![Stars](https://img.shields.io/github/stars/burhanmoin1/nextscope?style=social)

> **Automated API endpoint discovery by intercepting JS bundle chunks in real-time.**
> No wordlists. No brute force. No source code needed.

**nextscope** is a Next.js API endpoint scanner and JavaScript bundle recon tool for bug bounty hunters and penetration testers. It uses a real Chromium browser to crawl the target, intercepts every JS chunk as it lazy-loads page by page, and extracts every hardcoded API endpoint directly from the bundle — no guessing, no wordlists.

Works against **Next.js, React, Vue, Nuxt, Remix** and any modern JS framework that compiles routes into bundles.

---

## Why nextscope beats wordlist tools

| | nextscope | ffuf / dirsearch / gobuster |
|---|---|---|
| **Method** | Intercepts real JS chunks | Brute-forces with wordlist |
| **False positives** | None — only real endpoints | Many |
| **Finds lazy-loaded routes** | ✅ Yes | ❌ No |
| **Finds internal API paths** | ✅ Yes | ❌ Rarely |
| **Detects secrets in bundles** | ✅ Coming soon | ❌ No |
| **Requires wordlist** | ❌ No | ✅ Yes |
| **Noisy (many 404s)** | ❌ No | ✅ Very |

---

## How it works

Modern web apps compile every API path string directly into their JavaScript bundles. As users browse different pages, different chunks lazy-load. `nextscope` automates this by:

1. Crawling every internal page on the target with a real Chromium browser
2. Intercepting every `.js` chunk response in real-time as it loads
3. Extracting `/api/...` paths from string literals and template literals
4. Optionally probing each discovered endpoint and reporting HTTP status codes

## Install

```bash
# 1. Clone the repo
git clone https://github.com/burhanmoin1/nextscope.git
cd nextscope

# 2. Install — dependencies including Chromium install automatically
pip3 install playwright
playwright install chromium
```

## Usage

```bash
# Basic discovery
python3 nextscope.py https://www.example.com

# With endpoint probing (checks status codes)
python nextscope.py https://www.example.com --probe

# Save results to JSON
python nextscope.py https://www.example.com --probe --output results.json

# Crawl more pages (default: 50)
python nextscope.py https://www.example.com --max-pages 200

# Faster crawl (reduce delay)
python nextscope.py https://www.example.com --delay 0.5
```

## Output

```
[001] https://www.example.com/
  + /api/get-country/        ← main-abc123.js
  + /api/general-settings/   ← main-abc123.js

[002] https://www.example.com/login
  + /api/login/              ← login-def456.js
  + /api/token/refresh/      ← login-def456.js
  + /api/signup/             ← login-def456.js

════════════════════════════════
RESULTS
════════════════════════════════
  Pages crawled  : 12
  JS chunks      : 34
  Endpoints found: 47

All discovered endpoints:
  → /api/backup/
  → /api/general-settings/
  → /api/login/
  ...
```

With `--probe`:
```
  PUBLIC   GET   /api/general-settings/
  AUTH     GET   /api/me/
  ERROR    POST  /api/backup/
  FORBID   GET   /api/admin/
```

## Why this works

The `Content-Security-Policy` header reveals all API hostnames. The JS bundle contains every endpoint string. Neither requires authentication to read — they're public by design. This tool automates what a manual attacker would do in minutes.

## Legal

For authorized penetration testing and bug bounty programs only. Do not use against systems you don't have permission to test.
