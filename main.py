import asyncio, db, scraper
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kazhakootam News Aggregator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def ensure_data():
    st = db.stats()
    if st["total"] == 0:
        try:
            arts = scraper.fetch_all()
            for a in arts:
                db.upsert(a)
        except Exception as e:
            print("ensure_data error:", e)

@app.on_event("startup")
async def startup():
    db.init()
    ensure_data()
    try:
        asyncio.create_task(refresh_loop())
    except Exception:
        pass

async def refresh_loop():
    while True:
        await asyncio.sleep(15*60)
        await do_refresh()

async def do_refresh():
    try:
        arts = await asyncio.to_thread(scraper.fetch_all)
        for a in arts:
            db.upsert(a)
        return len(arts)
    except Exception as e:
        print("refresh error:", e)
        return 0

@app.post("/api/refresh")
async def refresh():
    # ensure data exists first
    ensure_data()
    n = await do_refresh()
    return {"fetched": n, "total": db.stats()["total"]}

@app.get("/api/articles")
def articles(limit: int = 200, source: str = None, category: str = None, q: str = None):
    ensure_data()
    resp = JSONResponse(db.list_articles(limit=limit, source=source, category=category, q=q))
    resp.headers["Cache-Control"] = "s-maxage=300, stale-while-revalidate=600"
    return resp

@app.get("/api/stats")
def stats():
    ensure_data()
    return db.stats()

import social
@app.get("/api/social/links")
async def social_links():
    return social.curated_links()
@app.get("/api/social/youtube")
async def social_youtube():
    return await social.youtube_feed()
@app.get("/api/social/reddit")
async def social_reddit():
    return await social.reddit_feed()
@app.get("/api/social/twitter")
async def social_twitter():
    return await social.twitter_feed()

@app.get("/")
def index():
    return FileResponse("public/index.html")

app.mount("/static", StaticFiles(directory="public"), name="static")
