# Kazhakootam Portal

A small full-stack news aggregator focused on **Kazhakootam, Thiruvananthapuram, Kerala (India)**.
It continuously scouts the web (via Google News + public RSS) for Kazhakootam / Technopark /
Trivandrum local news and presents a filterable, searchable feed.

## What it does
- Fetches ~350+ articles per refresh from 50+ publishers (The Hindu, Times of India,
  New Indian Express, Onmanorama, Mathrubhumi, Kerala Kaumudi, Asianet, NDTV, ...).
- Auto-refreshes every 15 minutes (background task) + manual "Refresh" button.
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

## Deploy

### Vercel (serverless)
The project is Vercel-ready:
- `api/index.py` exposes the FastAPI app as a serverless function.
- `vercel.json` routes `/api/*` to the function and serves `public/` as static.
- A cron job refreshes the feed every 30 minutes.

Steps:
```bash
npm i -g vercel
cd "kazhakootam news"
vercel        # follow prompts
```
Set env vars in the Vercel dashboard if you want live social feeds:
`YOUTUBE_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `TWITTER_BEARER_TOKEN`.

Note: on Vercel the filesystem is read-only, so SQLite is replaced by an
in-memory cache that is repopulated on cold starts / cron refresh. For
persistent storage, set `DATABASE_URL` (Postgres) — code falls back to
SQLite/memory otherwise.

### Other hosts
- Render / Railway / Fly.io: use the provided `Dockerfile` or run uvicorn with `$PORT`.
- Local: `./run.sh`

## Customize queries
Edit `QUERIES` in `scraper.py` to track different keywords/areas.

## Legal note
Aggregates publicly available headlines and links; full articles are opened on the
publisher's site. Respect each publisher's terms and robots.txt.
