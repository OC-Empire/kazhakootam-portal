"""Small dependency-free release checks for the public frontend."""
from pathlib import Path
import re
import sys

page = Path(__file__).parents[1] / "public" / "index.html"
text = page.read_text(encoding="utf-8")
checks = {
    "title": r"<title>[^<]+</title>",
    "description": r'<meta name="description"',
    "canonical": r'<link rel="canonical"',
    "open graph": r'<meta property="og:title"',
    "status region": r'id="status"[^>]+role="status"',
    "error handling": r"Could not refresh stories",
    "escaped titles": r"escapeHtml\(a\.title\)",
}
missing = [name for name, pattern in checks.items() if not re.search(pattern, text)]
if missing:
    print("Missing checks: " + ", ".join(missing))
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
if text.count("<script") != text.count("</script>"):
    print("Unbalanced script tags")
    sys.exit(1)
print(f"OK: {page} ({len(checks)} checks)")
