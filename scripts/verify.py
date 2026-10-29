#!/usr/bin/env python3
"""Small release gate for the static shell and share/scroll contracts."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "public/index.html").read_text()

required = [
    'class="fixed top-0',
    'overflow-visible',
    'max-height:calc(100dvh - 150px)',
    'function copyShareLink',
    'navigator.share',
    'aria-label="Share article:',
]
missing = [item for item in required if item not in html]
if missing:
    raise SystemExit("Missing UI contract(s): " + ", ".join(missing))

if len(re.findall(r"\.share-pop\.open", html)) != 1:
    raise SystemExit("Share popup must have exactly one open-state rule")

if 'relative overflow-hidden' in html:
    raise SystemExit("Header must not override fixed positioning")

print("Verified mobile layout, share fallback/native-share hooks, and accessibility labels.")
