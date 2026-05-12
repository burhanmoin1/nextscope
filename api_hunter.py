#!/usr/bin/env python3
"""
api-hunter — Automated API Endpoint Discovery Tool
====================================================
Crawls a target website using a headless browser, intercepts all JS chunks
as they load page-by-page, and extracts every hardcoded API endpoint.

Usage:
    python api_hunter.py https://www.example.com
    python api_hunter.py https://www.example.com --probe --output results.json

Author: github.com/burhanmoin1
"""

import argparse
import asyncio
import json
import re
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

# ── ANSI Colors ──────────────────────────────────────────────────────────────
R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"
C = "\033[96m"; B = "\033[94m"; W = "\033[97m"; RESET = "\033[0m"
BOLD = "\033[1m"

def banner():
    print(f"""{C}{BOLD}
  ___  ____  ____      _   _ _   _ _   _ _____ _____ ____
 / _ \|  _ \|  _|    | | | | | | | \ | |_   _| ____|  _ \\
| |_| | |_) | |  ___  | |_| | | | |  \| | | | |  _| | |_) |
|  _  |  __/| | |___| |  _  | |_| | |\  | | | | |___|  _ <
|_| |_|_|  |___|     |_| |_|\___/|_| \_| |_| |_____|_| \_\\
{RESET}{W}  Automated API Endpoint Discovery Tool — Red Team Edition{RESET}
""")

# ── Regex Patterns ───────────────────────────────────────────────────────────
PATTERNS = [
    # Quoted string literals: "/api/something/"
    re.compile(r'"(/api/[a-zA-Z0-9/_\-\.]+)"'),
    re.compile(r"'(/api/[a-zA-Z0-9/_\-\.]+)'"),
    # Template literals: `${API_URL}/api/something/`
    re.compile(r'`(?:\$\{[^}]+\})?(/api/[a-zA-Z0-9/_\-\.]+)'),
    # fetch/axios calls with full URLs
    re.compile(r'fetch\(["\`]https?://[^/]+(/api/[a-zA-Z0-9/_\-\.]+)'),
    # apiFetch / apiGet patterns
    re.compile(r'apiFetch\(["\`][^"\'`]*/(/api/[a-zA-Z0-9/_\-\.]+)'),
    # Webhook paths
    re.compile(r'"(/api/[a-zA-Z0-9/_\-\.]*(?:webhook|callback|notify)[a-zA-Z0-9/_\-\.]*)"'),
]

NOISE = {'/api/', '/api/v1', '/api/v2', '/api/v3'}

def extract_endpoints_from_js(js: str) -> set:
    found = set()
    for pattern in PATTERNS:
        for match in pattern.finditer(js):
            ep = match.group(1).rstrip('.,;)')
            if ep not in NOISE and len(ep) > 5:
                found.add(ep)
    return found

# ── Crawler ──────────────────────────────────────────────────────────────────

async def hunt(target: str, probe: bool, output: str | None, max_pages: int, delay: float):
    parsed = urlparse(target)
    base_domain = parsed.netloc
    api_base = f"{parsed.scheme}://api.{base_domain.replace('www.', '')}"

    endpoints: set[str]   = set()
    secrets: dict[str, list] = {}
    chunks_seen: set[str] = set()
    pages_visited: list[str] = []
    queue: deque[str]     = deque([target])
    visited: set[str]     = set()

    print(f"{C}[*]{RESET} Target   : {BOLD}{target}{RESET}")
    print(f"{C}[*]{RESET} API Base : {BOLD}{api_base}{RESET}")
    print(f"{C}[*]{RESET} Max pages: {max_pages}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        )

        # ── Intercept every JS chunk response ────────────────────────────────
        async def handle_response(response):
            url = response.url
            ct  = response.headers.get("content-type", "")
            if "javascript" not in ct and not url.endswith(".js"):
                return
            if url in chunks_seen:
                return
            chunks_seen.add(url)
            try:
                body = await response.text()
                found = extract_endpoints_from_js(body)
                new   = found - endpoints
                if new:
                    endpoints.update(new)
                    chunk_name = url.split("/")[-1][:40]
                    for ep in sorted(new):
                        print(f"  {G}+{RESET} {ep}  {Y}←{RESET} {chunk_name}")
            except Exception:
                pass

        page = await context.new_page()
        page.on("response", handle_response)

        # ── Page crawler ─────────────────────────────────────────────────────
        while queue and len(pages_visited) < max_pages:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            try:
                print(f"\n{B}[{len(pages_visited)+1:03d}]{RESET} {url}")
                resp = await page.goto(url, wait_until="networkidle", timeout=30000)
                if not resp or resp.status >= 400:
                    print(f"  {R}✗{RESET} Status {resp.status if resp else '?'}")
                    continue

                pages_visited.append(url)
                await asyncio.sleep(delay)

                # Discover more internal links
                links = await page.eval_on_selector_all(
                    "a[href]",
                    "els => els.map(e => e.href)"
                )
                for link in links:
                    lp = urlparse(link)
                    if base_domain in lp.netloc and link not in visited and link not in queue:
                        queue.append(link)

            except Exception as e:
                print(f"  {R}✗{RESET} Error: {e}")

        await browser.close()

    # ── Probe endpoints ──────────────────────────────────────────────────────
    probe_results = []
    if probe and endpoints:
        print(f"\n{C}{'─'*60}{RESET}")
        print(f"{BOLD}[PROBE] Testing {len(endpoints)} endpoints against {api_base}{RESET}\n")

        import urllib.request
        import urllib.error

        for ep in sorted(endpoints):
            for method in (["GET"] if not any(x in ep for x in ["login","signup","backup","restore","webhook","payment"]) else ["POST"]):
                url = api_base + ep
                try:
                    req = urllib.request.Request(url, method=method,
                        headers={"Content-Type": "application/json",
                                 "Origin": f"https://www.{base_domain.replace('www.','')}"}
                    )
                    if method == "POST":
                        req.data = b"{}"
                    with urllib.request.urlopen(req, timeout=8) as r:
                        status = r.status
                except urllib.error.HTTPError as e:
                    status = e.code
                except Exception:
                    status = 0

                color = G if status == 200 else (Y if status in (401,403) else (R if status == 500 else W))
                label = {200:"PUBLIC ",401:"AUTH   ",403:"FORBID ",404:"MISSING",500:"ERROR  "}.get(status, f"{status}    ")
                print(f"  {color}{label}{RESET}  {method:4}  {ep}")
                probe_results.append({"endpoint": ep, "method": method, "status": status})

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{C}{'═'*60}{RESET}")
    print(f"{BOLD}RESULTS{RESET}")
    print(f"{C}{'═'*60}{RESET}")
    print(f"  Pages crawled : {len(pages_visited)}")
    print(f"  JS chunks     : {len(chunks_seen)}")
    print(f"  Endpoints found: {G}{BOLD}{len(endpoints)}{RESET}\n")

    print(f"{BOLD}All discovered endpoints:{RESET}")
    for ep in sorted(endpoints):
        print(f"  {G}→{RESET} {ep}")

    # ── Output ───────────────────────────────────────────────────────────────
    if output:
        result = {
            "target": target,
            "api_base": api_base,
            "pages_crawled": len(pages_visited),
            "chunks_intercepted": len(chunks_seen),
            "endpoints": sorted(endpoints),
            "probe_results": probe_results,
        }
        Path(output).write_text(json.dumps(result, indent=2))
        print(f"\n{G}[✓]{RESET} Results saved to {output}")

    return sorted(endpoints)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="api-hunter — Automated API endpoint discovery via JS chunk interception"
    )
    parser.add_argument("target", help="Target URL e.g. https://www.example.com")
    parser.add_argument("--probe",  action="store_true", help="Probe discovered endpoints and report HTTP status")
    parser.add_argument("--output", metavar="FILE",      help="Save results to JSON file")
    parser.add_argument("--max-pages", type=int, default=50, metavar="N", help="Max pages to crawl (default: 50)")
    parser.add_argument("--delay",     type=float, default=1.0, metavar="S", help="Delay between page loads in seconds (default: 1.0)")
    args = parser.parse_args()

    banner()
    try:
        asyncio.run(hunt(args.target, args.probe, args.output, args.max_pages, args.delay))
    except KeyboardInterrupt:
        print(f"\n{Y}[!] Interrupted.{RESET}")
        sys.exit(0)
