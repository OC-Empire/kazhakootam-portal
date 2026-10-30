"""Small dependency-free release checks for the public frontend."""
from pathlib import Path
import json
import re
import sys

page = Path(__file__).parents[1] / "public" / "index.html"
text = page.read_text(encoding="utf-8")
scraper = (page.parents[1] / "scraper.py").read_text(encoding="utf-8")
api = (page.parents[1] / "main.py").read_text(encoding="utf-8")
readme = (page.parents[1] / "README.md").read_text(encoding="utf-8")
deployment = json.loads((page.parents[1] / "vercel.json").read_text(encoding="utf-8"))
checks = {
    "title": r"<title>[^<]+</title>",
    "description": r'<meta name="description"',
    "canonical": r'<link rel="canonical"',
    "open graph": r'<meta property="og:title"',
    "status region": r'id="status"[^>]+role="status"',
    "error handling": r"Could not refresh stories",
    "escaped titles": r"escapeHtml\(a\.title\)",
    "sticky header": r'<header id="siteHeader" class="sticky',
    "mobile header controls reflow": r"#headerTop\{display:flex;flex-direction:column",
    "mobile search flexes to available width": r"#search\{flex:1;min-width:0;width:auto\}",
    "correct product monogram": r"shadow-indigo-500/30\">K</div>",
    "measured header/status/navigation heights": r"layoutObserver\.observe\(\$\(id\)\)",
    "reels fits measured available viewport": r"#reelsView\{height:calc\(100dvh - var\(--site-header-height,135px\) - var\(--site-status-height,44px\) - var\(--bottom-nav-height,61px\)\)",
    "mobile weather chip does not crowd search": r"#weatherChip\{display:none!important\}",
    "centered desktop feed": r"max-w-3xl mx-auto w-full px-4 py-6",
    "published-story freshness": r"latest published \$\{latestPublishedLabel\(data\)\}",
    "44px navigation targets": r"\.navbtn\{min-width:44px;min-height:44px",
}
missing = [name for name, pattern in checks.items() if not re.search(pattern, text)]
if missing:
    print("Missing checks: " + ", ".join(missing))
    sys.exit(1)
api_checks = {
    "Vercel cron GET route": r'@app\.get\("/api/refresh"\)',
    "optional cron bearer validation": r'hmac\.compare_digest\(request\.headers\.get\("authorization"',
}
missing_api = [name for name, pattern in api_checks.items() if not re.search(pattern, api)]
if missing_api:
    print("Missing API checks: " + ", ".join(missing_api))
    sys.exit(1)
if not any(job.get("path") == "/api/refresh" and job.get("schedule") == "0 6 * * *" for job in deployment.get("crons", [])):
    print("Vercel daily cron must target the supported GET refresh route")
    sys.exit(1)
ids = re.findall(r'\bid=["\']([^"\']+)["\']', text)
duplicates = sorted({item for item in ids if ids.count(item) > 1})
if duplicates:
    print("Duplicate IDs: " + ", ".join(duplicates))
    sys.exit(1)
for node in ("header", "main"):
    if len(re.findall(fr"<{node}\b", text)) != 1:
        print(f"Expected exactly one <{node}> node")
        sys.exit(1)
if len(re.findall(r'<div\b[^>]*\bid=["\']reelsView["\']', text)) != 1:
    print("Expected exactly one reelsView node")
    sys.exit(1)
for nav_id in ("openSocial", "openSOS", "openCommunity", "openExplore"):
    if not re.search(fr'\bid=["\']{nav_id}["\']', text):
        print(f"Missing bottom-nav ID: {nav_id}")
        sys.exit(1)
for city in ('"Trivandrum"', '"Thiruvananthapuram"'):
    if city not in scraper:
        print(f"Missing city-wide RSS query: {city}")
        sys.exit(1)
if "after:{cutoff.isoformat()}" not in scraper or "quote_plus(search_query)" not in scraper:
    print("RSS requests must use URL-encoded rolling seven-day date filters")
    sys.exit(1)
if "For persistent storage, set `DATABASE_URL`" in readme:
    print("README claims DATABASE_URL support that the code does not implement")
    sys.exit(1)
if text.count("<script") != text.count("</script>"):
    print("Unbalanced script tags")
    sys.exit(1)
print(f"OK: {page} ({len(checks)} checks)")
