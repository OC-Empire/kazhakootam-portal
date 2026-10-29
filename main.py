import asyncio, os, re, db, scraper
from datetime import datetime, timedelta

# In-memory community data (issues are user-submitted; events/jobs are seed)
_ISSUES = [
    {"id":1,"title":"Pothole near Kazhakootam railway station","desc":"Large pothole causing accidents near the station entrance.","category":"roads","upvotes":12,"status":"open","created":"2026-10-25"},
    {"id":2,"title":"Garbage pile-up at Technopark Phase 3","desc":"Uncollected waste near the Phase 3 gate.","category":"sanitation","upvotes":8,"status":"open","created":"2026-10-26"},
    {"id":3,"title":"Streetlight out on NH-66 service road","desc":"Dark stretch near Karyavattom, safety concern at night.","category":"lighting","upvotes":15,"status":"in-progress","created":"2026-10-22"},
]
_ISSUE_COUNTER = [4]
_EVENTS = [
    {"id":1,"title":"Technopark Job Fair 2026","date":"2026-11-15","time":"10:00 AM","loc":"Technopark Phase 1, Hall A","desc":"50+ companies hiring. Free entry."},
    {"id":2,"title":"Kazhakootam Temple Festival","date":"2026-12-05","time":"6:00 PM","loc":"Kazhakootam Sree Dharma Sastha Temple","desc":"Annual festival with cultural programs and fireworks."},
    {"id":3,"title":"Community Beach Cleanup","date":"2026-11-08","time":"7:00 AM","loc":"Shanghumughom Beach","desc":"Join the monthly cleanup drive. Gloves provided."},
    {"id":4,"title":"Startup Meetup: AI in Kerala","date":"2026-11-22","time":"4:00 PM","loc":"Technopark TBI","desc":"Founders and developers meetup. Free chai."},
]
_JOBS = [
    {"id":1,"title":"Software Engineer (Python)","company":"Infosys","loc":"Technopark Phase 2","type":"Full-time","salary":"₹6-9 LPA","posted":"2026-10-28"},
    {"id":2,"title":"Frontend Developer (React)","company":"TCS","loc":"Technopark Phase 1","type":"Full-time","salary":"₹5-8 LPA","posted":"2026-10-27"},
    {"id":3,"title":"Data Analyst","company":"UST","loc":"Technopark Phase 3","type":"Full-time","salary":"₹4-6 LPA","posted":"2026-10-26"},
    {"id":4,"title":"QA Engineer","company":"QBurst","loc":"Technopark Phase 1","type":"Full-time","salary":"₹4-7 LPA","posted":"2026-10-25"},
    {"id":5,"title":"DevOps Intern","company":"Zoho","loc":"Technopark","type":"Internship","salary":"₹15k/mo","posted":"2026-10-29"},
]

_PULSE = {
    "traffic": [
        {"route":"NH-66 (Kazhakootam stretch)","status":"Moderate","delay":"5 min","color":"amber"},
        {"route":"Technopark Phase 1 entry","status":"Heavy","delay":"15 min","color":"red"},
        {"route":"Karyavattom - Kazhakootam","status":"Clear","delay":"0 min","color":"green"},
        {"route":"Attingal bypass","status":"Clear","delay":"0 min","color":"green"},
    ],
    "outages": [
        {"type":"Power","area":"Kazhakootam ward 3","until":"6:00 PM","note":"Scheduled maintenance"},
        {"type":"Water","area":"Karyavattom","until":"4:00 PM","note":"Pipeline repair"},
    ],
    "buses": [
        {"route":"Kazhakootam - Trivandrum Central","next":"12 min","freq":"Every 15 min"},
        {"route":"Technopark - Airport","next":"8 min","freq":"Every 20 min"},
        {"route":"Kazhakootam - Attingal","next":"22 min","freq":"Every 30 min"},
    ],
    "trains": [
        {"name":"Kazhakootam Express","time":"14:30","platform":"2","status":"On time"},
        {"name":"Trivandrum Rajdhani","time":"16:10","platform":"1","status":"Delayed 10m"},
    ],
}

_DIRECTORY = [
    {"name":"Technopark Medical Centre","cat":"Health","phone":"0471-2700100","addr":"Technopark Phase 1"},
    {"name":"Kazhakootam Police Station","cat":"Emergency","phone":"0471-2412100","addr":"Kazhakootam"},
    {"name":"SBI Kazhakootam","cat":"Bank","phone":"0471-2412345","addr":"NH-66, Kazhakootam"},
    {"name":"Apollo Pharmacy","cat":"Pharmacy","phone":"0471-2412567","addr":"Technopark gate"},
    {"name":"Kazhakootam Govt School","cat":"Education","phone":"0471-2412789","addr":"Kazhakootam"},
    {"name":"Hotel Aiswarya","cat":"Food","phone":"0471-2412901","addr":"NH-66"},
    {"name":"Lulu Mall (nearby)","cat":"Shopping","phone":"0471-2413000","addr":"Akkulam"},
    {"name":"KSRTC Depot Kazhakootam","cat":"Transport","phone":"0471-2413100","addr":"Kazhakootam"},
]

_CLASSIFIEDS = [
    {"id":1,"title":"2BHK flat for rent near Technopark","type":"Rent","price":"₹18,000/mo","contact":"9876543210","desc":"Furnished, 2 balconies, parking. Available immediately."},
    {"id":2,"title":"Roommate wanted - Technopark Phase 2","type":"Roommate","price":"₹8,000/mo","contact":"9876543211","desc":"Male preferred. WiFi included."},
    {"id":3,"title":"Used Honda Activa 2022","type":"Sell","price":"₹65,000","contact":"9876543212","desc":"Single owner, 12k km, excellent condition."},
    {"id":4,"title":"Tuition: Maths & Physics (Class 10-12)","type":"Service","price":"₹500/hr","contact":"9876543213","desc":"Experienced teacher, Kazhakootam area."},
    {"id":5,"title":"Laptop repair service","type":"Service","price":"Call for quote","contact":"9876543214","desc":"All brands. Home visit available."},
]
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Kazhakootam News Aggregator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def ensure_data():
    db.init()
    # Do not fetch synchronously here: on serverless (Vercel) this can exceed
    # the function timeout. Fetching happens via /api/refresh (client-triggered).

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
    return db.stats()

@app.get("/api/weather")
async def weather():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": 8.565, "longitude": 76.872,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "Asia/Kolkata"})
            d = r.json().get("current", {})
            code = d.get("weather_code", 0)
            desc = {0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",51:"Drizzle",61:"Rain",63:"Rain",65:"Heavy rain",80:"Showers",95:"Thunderstorm"}.get(code, "Cloudy")
            return {"temp": d.get("temperature_2m"), "humidity": d.get("relative_humidity_2m"),
                    "wind": d.get("wind_speed_10m"), "desc": desc, "code": code}
    except Exception as e:
        return {"error": str(e)}

_ARTICLE_CACHE = {}

def _decode_google_news(url: str):
    """Resolve a news.google.com/rss/articles/... link to the real publisher URL
    via Google's batchexecute endpoint (googlenewsdecoder)."""
    if not url or "news.google.com" not in url:
        return url
    try:
        from googlenewsdecoder import gnewsdecoder
        r = gnewsdecoder(url)
        if isinstance(r, tuple):
            r = r[0]
        if r and r.get("success"):
            return r.get("decoded_url") or url
    except Exception:
        pass
    return None

@app.get("/api/article")
async def article_reader(url: str):
    try:
        if url in _ARTICLE_CACHE:
            return _ARTICLE_CACHE[url]
        import httpx
        from bs4 import BeautifulSoup
        real_url = _decode_google_news(url)
        if not real_url:
            return {"error": "Could not resolve article link", "url": url}
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(real_url, headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # title
        title = ""
        og = soup.find("meta", property="og:title")
        if og and og.get("content"): title = og["content"]
        if not title and soup.title: title = soup.title.get_text(strip=True)
        if not title:
            h1 = soup.find("h1")
            if h1: title = h1.get_text(strip=True)
        # image
        img = ""
        ogi = soup.find("meta", property="og:image")
        if ogi and ogi.get("content"): img = ogi["content"]
        # author
        author = ""
        oma = soup.find("meta", attrs={"name":"author"})
        if oma and oma.get("content"): author = oma["content"]
        if not author:
            ogau = soup.find("meta", property="article:author")
            if ogau and ogau.get("content"): author = ogau["content"]
        # remove junk
        for tag in soup(["script","style","nav","footer","header","aside","form","iframe","noscript"]):
            tag.decompose()
        # find main container
        container = soup.find("article")
        if not container:
            container = soup.find("main")
        if not container:
            # div with most paragraph text (beats sidebar link-farms)
            best = None; bestn = 0
            for d in soup.find_all("div"):
                n = sum(len(p.get_text(strip=True)) for p in d.find_all("p"))
                if n > bestn:
                    bestn = n; best = d
            container = best if best else soup.body
        paras = []
        if container:
            for p in container.find_all("p"):
                txt = p.get_text(" ", strip=True)
                if len(txt) > 40:
                    paras.append(txt)
        # dedup
        seen = set(); uniq = []
        for p in paras:
            if p in seen: continue
            seen.add(p); uniq.append(p)
        content = "\n\n".join(uniq[:40])
        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(real_url).netloc
        except Exception:
            pass
        result = {"title": title, "image": img, "author": author, "content": content,
                  "url": real_url, "domain": domain, "paragraphs": len(uniq)}
        _ARTICLE_CACHE[url] = result
        return result
    except Exception as e:
        return {"error": str(e), "url": url}

@app.get("/api/rss")
def rss_feed():
    from fastapi.responses import Response
    arts = db.list_articles(limit=50)
    items = ""
    for a in arts:
        items += f"""<item><title>{escape_xml(a.get('title',''))}</title><link>{escape_xml(a.get('link',''))}</link><description>{escape_xml(a.get('summary',''))}</description><pubDate>{a.get('published','')}</pubDate><source>{escape_xml(a.get('source',''))}</source></item>"""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Kazhakootam Portal</title><link>https://kazhakootam-news.vercel.app</link><description>Kazhakootam local news</description>{items}</channel></rss>"""
    return Response(content=xml, media_type="application/rss+xml")

@app.get("/api/issues")
def list_issues():
    return sorted(_ISSUES, key=lambda x: x["upvotes"], reverse=True)

@app.post("/api/issues")
async def create_issue(payload: dict):
    title = (payload.get("title") or "").strip()
    if not title:
        return {"error": "title required"}
    issue = {
        "id": _ISSUE_COUNTER[0],
        "title": title,
        "desc": (payload.get("desc") or "").strip(),
        "category": payload.get("category", "general"),
        "upvotes": 0,
        "status": "open",
        "created": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    _ISSUE_COUNTER[0] += 1
    _ISSUES.append(issue)
    return issue

@app.post("/api/issues/{issue_id}/upvote")
def upvote_issue(issue_id: int):
    for i in _ISSUES:
        if i["id"] == issue_id:
            i["upvotes"] += 1
            return i
    return {"error": "not found"}

@app.get("/api/events")
def list_events():
    return _EVENTS

@app.get("/api/jobs")
def list_jobs():
    return _JOBS

@app.get("/api/pulse")
def pulse():
    return _PULSE

@app.get("/api/directory")
def directory(q: str = None, cat: str = None):
    out = _DIRECTORY
    if cat: out = [d for d in out if d["cat"].lower() == cat.lower()]
    if q: out = [d for d in out if q.lower() in (d["name"]+d["cat"]).lower()]
    return out

@app.get("/api/classifieds")
def classifieds(type: str = None):
    out = _CLASSIFIEDS
    if type: out = [c for c in out if c["type"].lower() == type.lower()]
    return out

@app.get("/api/digest")
def daily_digest():
    arts = db.list_articles(limit=8)
    issues = sorted(_ISSUES, key=lambda x: x["upvotes"], reverse=True)[:3]
    lines = ["📰 Kazhakootam Portal — Daily Digest", ""]
    if arts:
        lines.append("Top stories:")
        for a in arts[:5]:
            lines.append(f"• {a.get('title')} ({a.get('source')})")
        lines.append("")
    if issues:
        lines.append("Top community issues:")
        for i in issues:
            lines.append(f"• {i['title']} ({i['upvotes']} upvotes)")
        lines.append("")
    lines.append("Weather: check the portal for live weather.")
    lines.append("")
    lines.append("Read more: https://kazhakootam-news.vercel.app")
    text = "\n".join(lines)
    import urllib.parse
    wa = "https://wa.me/?text=" + urllib.parse.quote(text)
    tg = "https://t.me/share/url?url=https://kazhakootam-news.vercel.app&text=" + urllib.parse.quote(text)
    return {"text": text, "whatsapp": wa, "telegram": tg}

def escape_xml(s):
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

@app.get("/")
def index():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

if os.path.isdir(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")
