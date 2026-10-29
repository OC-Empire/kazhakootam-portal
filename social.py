import os, httpx

KAZHA_QUERIES = ["Kazhakootam", "Kazhakoottam", "Technopark Trivandrum", "Karyavattom"]

def curated_links():
    q = "Kazhakootam Trivandrum"
    return [
        {"platform":"X / Twitter", "title":"Search X for Kazhakootam", "url": f"https://x.com/search?q={q.replace(' ','%20')}&f=live", "icon":"𝕏"},
        {"platform":"Reddit", "title":"r/Trivandrum", "url":"https://www.reddit.com/r/Trivandrum/search/?q=Kazhakootam&restrict_sr=1&sort=new", "icon":" alien"},
        {"platform":"Reddit", "title":"r/Kerala", "url":"https://www.reddit.com/r/Kerala/search/?q=Kazhakootam&restrict_sr=1&sort=new", "icon":"👽"},
        {"platform":"Facebook", "title":"Facebook search: Kazhakootam", "url": f"https://www.facebook.com/search/top/?q={q.replace(' ','%20')}", "icon":"f"},
        {"platform":"Instagram", "title":"Instagram #Kazhakootam", "url":"https://www.instagram.com/explore/tags/kazhakootam/", "icon":"📷"},
        {"platform":"YouTube", "title":"YouTube search: Kazhakootam", "url": f"https://www.youtube.com/results?search_query={q.replace(' ','+')}", "icon":"▶"},
        {"platform":"Google", "title":"Google: Kazhakootam news", "url": f"https://www.google.com/search?q={q.replace(' ','+')}&tbm=nws", "icon":"G"},
    ]

async def youtube_feed():
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return {"enabled": False, "reason": "YOUTUBE_API_KEY not set", "links": curated_links()}
    items = []
    async with httpx.AsyncClient(timeout=20) as c:
        for q in KAZHA_QUERIES[:2]:
            r = await c.get("https://www.googleapis.com/youtube/v3/search", params={
                "part":"snippet","q":q,"key":key,"type":"video","maxResults":8,
                "regionCode":"IN","order":"date"})
            if r.status_code != 200:
                continue
            for it in r.json().get("items",[]):
                sn = it.get("snippet",{})
                vid = it.get("id",{}).get("videoId")
                if not vid: continue
                items.append({
                    "title": sn.get("title",""),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "source": sn.get("channelTitle","YouTube"),
                    "published": sn.get("publishedAt",""),
                    "summary": sn.get("description","")[:200],
                    "thumbnail": sn.get("thumbnails",{}).get("medium",{}).get("url"),
                })
    # dedup
    seen=set(); out=[]
    for i in items:
        if i["url"] in seen: continue
        seen.add(i["url"]); out.append(i)
    return {"enabled": True, "items": out, "links": curated_links()}

async def reddit_feed():
    cid = os.getenv("REDDIT_CLIENT_ID")
    sec = os.getenv("REDDIT_CLIENT_SECRET")
    if not cid or not sec:
        return {"enabled": False, "reason": "REDDIT_CLIENT_ID/SECRET not set", "links": curated_links()}
    items = []
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            tok_r = await c.post("https://www.reddit.com/api/v1/access_token",
                auth=(cid,sec),
                data={"grant_type":"client_credentials"},
                headers={"User-Agent":"kazha-news/1.0"})
            token = tok_r.json().get("access_token")
            if not token:
                return {"enabled": False, "reason": "reddit auth failed", "links": curated_links()}
            headers = {"Authorization": f"Bearer {token}", "User-Agent":"kazha-news/1.0"}
            for q in ["Kazhakootam","Technopark Trivandrum"]:
                r = await c.get("https://oauth.reddit.com/search",
                    params={"q":q,"sort":"new","limit":15,"t":"month"},
                    headers=headers)
                if r.status_code != 200: continue
                for ch in r.json().get("data",{}).get("children",[]):
                    d = ch.get("data",{})
                    items.append({
                        "title": d.get("title",""),
                        "url": "https://www.reddit.com"+d.get("permalink",""),
                        "source": "r/"+d.get("subreddit",""),
                        "published": "",
                        "summary": (d.get("selftext","") or "")[:200],
                        "score": d.get("score",0),
                    })
    except Exception as e:
        return {"enabled": False, "reason": str(e), "links": curated_links()}
    seen=set(); out=[]
    for i in items:
        if i["url"] in seen: continue
        seen.add(i["url"]); out.append(i)
    return {"enabled": True, "items": out, "links": curated_links()}

async def twitter_feed():
    bearer = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer:
        return {"enabled": False, "reason": "TWITTER_BEARER_TOKEN not set", "links": curated_links()}
    items = []
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get("https://api.twitter.com/2/tweets/search/recent",
                params={"query":"Kazhakootam -is:retweet lang:en OR lang:ml","max_results":20,
                        "tweet.fields":"created_at,public_metrics,author_id"},
                headers={"Authorization": f"Bearer {bearer}"})
            if r.status_code != 200:
                return {"enabled": False, "reason": f"twitter {r.status_code}: {r.text[:200]}", "links": curated_links()}
            for t in r.json().get("data",[]):
                items.append({
                    "title": t.get("text","")[:120],
                    "url": f"https://x.com/i/web/status/{t['id']}",
                    "source": "X/Twitter",
                    "published": t.get("created_at",""),
                    "summary": t.get("text",""),
                })
    except Exception as e:
        return {"enabled": False, "reason": str(e), "links": curated_links()}
    return {"enabled": True, "items": items, "links": curated_links()}
