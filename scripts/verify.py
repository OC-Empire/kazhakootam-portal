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
if text.count("<script") != text.count("</script>"):
    print("Unbalanced script tags")
    sys.exit(1)
print(f"OK: {page} ({len(checks)} checks)")
