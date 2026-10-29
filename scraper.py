import feedparser, httpx, datetime, re, html

QUERIES = [
    "Kazhakootam",
    "Kazhakoottam",
    "Technopark Trivandrum",
    "Kazhakootam Technopark",
    "Karyavattom",
    "Thiruvananthapuram Kazhakootam",
    "TVM metro Kazhakootam",
    "Kazhakootam NH66",
    "Kazhakkuttom election",
    "Kazhakootam hostel IT",
]

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"

CAT_KEYWORDS = {
    "crime": ["rape","assault","murder","theft","robbery","arrest","police","crime","accident","crash","hit-and-run","theft","scam","fraud"],
    "politics": ["bjp","cpm","congress","mla","election","minister","party","vote","council","panchayat","municipal","ward"],
    "infrastructure": ["metro","highway","road","bridge","railway","train","station","flyover","water","garbage","river","nh ","nh-","bypass","construction","project","traffic","signal"],
    "tech": ["technopark","it ","startup","software","tech","company","employee","hostel"],
    "sports": ["cricket","football","sport","match","tournament","league"],
    "weather": ["rain","flood","weather","storm","heat","cyclone","monsoon"],
    "culture": ["festival","temple","church","mosque","art","music","film","movie","christmas","onam","vishu"],
    "health": ["hospital","health","disease","covid","vaccine","medical","doctor"],
}

def categorize(title):
    t = (title or "").lower()
    for cat, kws in CAT_KEYWORDS.items():
        for k in kws:
            if k in t:
                return cat
    return "general"

def clean_html(s):
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:400]

def fetch_google_news(query):
    url = GOOGLE_NEWS_RSS.format(q=query.replace(" ", "+"))
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    out = []
    for e in feed.entries:
        title = e.get("title","").strip()
        link = e.get("link","").strip()
        source = ""
        if "source" in e:
            source = e.source.get("title","") if hasattr(e,"source") else str(e.get("source",""))
        # feedparser exposes source as dict-like
        try:
            source = e.source.title if hasattr(e, "source") and hasattr(e.source, "title") else source
        except Exception:
            pass
        if not source:
            # try parse from title trailing " - Source"
            m = re.search(r"\s-\s([^-]+)$", title)
            if m:
                source = m.group(1).strip()
                title = title[:m.start()].strip()
        published = e.get("published","") or e.get("updated","")
        summary = clean_html(e.get("summary","") or e.get("description",""))
        if not link or not title:
            continue
        out.append({
            "title": title,
            "link": link,
            "source": source or "Google News",
            "published": published,
            "summary": summary,
            "category": categorize(title),
        })
    return out

import concurrent.futures

def fetch_all():
    results = []
    seen = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fetch_google_news, q) for q in QUERIES]
        for f in concurrent.futures.as_completed(futs):
            try:
                for a in f.result():
                    if a["link"] in seen:
                        continue
                    seen.add(a["link"])
                    results.append(a)
            except Exception:
                pass
    return results
