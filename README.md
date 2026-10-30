# Kazhakootam Portal

A small full-stack news aggregator focused on **Kazhakootam, Thiruvananthapuram, Kerala (India)**.
It continuously scouts the web (via Google News + public RSS) for Kazhakootam / Technopark /
Trivandrum local news and presents a filterable, searchable feed.

## What it does
- Fetches ~350+ articles per refresh from 50+ publishers (The Hindu, Times of India,
  New Indian Express, Onmanorama, Mathrubhumi, Kerala Kaumudi, Asianet, NDTV, ...).
- Refreshes on demand with the "Refresh" button and once daily through Vercel Cron.
- Filter by source, category (crime, politics, infrastructure, tech, ...), full-text search.
- Deduplicates by article URL in SQLite.
- Responsive dark UI.

## Run locally
```bash
cd /home/faizal/Documents/OpenCode
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```
Or use the helper: `./run.sh`

## Project layout
```
main.py       FastAPI app + background refresh loop
scraper.py    Google News RSS fetcher (queries + categorization)
db.py         SQLite storage + filters
static/       Frontend (Tailwind)
data/         SQLite db (auto-created)
```

## Scouting "social media & everywhere"
Direct scraping of Twitter/X, Facebook, Instagram and Reddit is blocked without
authenticated API access and raises legal/ToS concerns. This project therefore:

1. Aggregates the open web via Google News RSS (which already includes many social-origin stories).
2. Provides a **Social / Community** panel in the UI with one-click searches on
   X, Reddit, Facebook, Instagram, YouTube and Google for Kazhakootam topics.
3. Supports optional live social feeds if you supply API keys (see below).

### Optional: live social feeds (plug in your own keys)
Set env vars before running:
- `YOUTUBE_API_KEY`  -> enables YouTube search for Kazhakootam videos
- `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` -> enables r/Trivandrum, r/Kerala posts
- `TWITTER_BEARER_TOKEN` -> enables X/Twitter recent search

Social feed endpoints: `/api/social/youtube`, `/api/social/reddit`, `/api/social/twitter`
(These are stubs that activate only when keys are present; otherwise they return
the curated search links.)

## Live
- Production: https://kazhakootam-news.vercel.app
- GitHub: https://github.com/OC-Empire/kazhakootam-portal

## Features
- Reels-style vertical feed + grid view
- Weather widget (Kazhakootam, via Open-Meteo)
- Emergency SOS panel with one-tap dialing
- Community drawer: issue reporter (upvote), events calendar, Technopark jobs board
- RSS feed output: /api/rss
- PWA (installable, offline-capable)
- Bilingual UI (English / Malayalam)
- Social & community links + optional live feeds
- Auto-refresh (daily cron on Vercel Hobby)

## Verification

Run the static release gate before committing frontend changes:

```bash
python3 scripts/verify.py
```

The gate checks the fixed mobile shell, nested share-menu safety, native-share
and clipboard fallbacks, and required accessible labels.

## Deploy

### Vercel (serverless)
The project is Vercel-ready:
- `api/index.py` exposes the FastAPI app as a serverless function.
- `vercel.json` routes `/api/*` to the function and serves `public/` as static.
- The Vercel cron refreshes the feed daily at 06:00 UTC (the Hobby plan limit).

Steps:
```bash
npm i -g vercel
cd "kazhakootam news"
vercel        # follow prompts
```
Set env vars in the Vercel dashboard if you want live social feeds:
`YOUTUBE_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `TWITTER_BEARER_TOKEN`.

Neon `env pull` stores local values in `.env.local` (or an existing `.env`);
the app loads either file without overriding variables already set by the
process. Both files are git-ignored. Apply `migrations/001_articles.sql` to the
Neon database before deployment; application startup only verifies the schema
and does not require runtime DDL privileges. On Vercel, set `DATABASE_URL` to
the Neon **pooled** connection string and `CRON_SECRET` to a high-entropy
secret. Vercel Cron sends that secret as `Authorization: Bearer ...`; both GET
(scheduled) and POST (manual) refresh requests fail closed when auth is missing
in Vercel and reject invalid tokens. The cron refreshes daily at 06:00 UTC.
Local development without `DATABASE_URL` continues to use SQLite. The feed
refresh control reloads already-ingested stories; only the authenticated cron
endpoint fetches publisher feeds.

### Other hosts
- Render / Railway / Fly.io: use the provided `Dockerfile` or run uvicorn with `$PORT`.
- Local: `./run.sh`

## Customize queries
Edit `QUERIES` in `scraper.py` to track different keywords/areas.

## Legal note
Aggregates publicly available headlines and links; full articles are opened on the
publisher's site. Respect each publisher's terms and robots.txt.
