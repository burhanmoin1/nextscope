# nextscope 🔭

> JS bundle API endpoint discovery tool for red team engagements and bug bounty hunting.

Crawls a target website with a headless Chromium browser, intercepts every JavaScript chunk as it loads page-by-page, and extracts all hardcoded API endpoints — **no source code required**.

Works against **Next.js, React, Vue, Nuxt** and any modern JS framework that compiles routes into bundles.

## How it works

Modern web apps (Next.js, React, Vue) compile every API path string directly into their JavaScript bundles. As you browse different pages, different chunks are lazy-loaded. `nextscope` automates this by:

1. Visiting every page on the target site with a real Chromium browser
2. Intercepting every `.js` chunk response in real-time as it loads
3. Extracting `/api/...` paths from string literals and template literals
4. Optionally probing each discovered endpoint and reporting HTTP status codes

## Install

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Basic discovery
python nextscope.py https://www.example.com

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
