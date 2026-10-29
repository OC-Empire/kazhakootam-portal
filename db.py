import sqlite3, os, datetime, json

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "news.db")

_MEMORY = []          # fallback store for read-only/serverless envs
_USE_MEMORY = False

def _sqlite_ok():
    global _USE_MEMORY
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        c = sqlite3.connect(DB_PATH)
        c.execute("CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT UNIQUE, source TEXT, published TEXT, summary TEXT, category TEXT, fetched_at TEXT)")
        c.commit(); c.close()
        return True
    except Exception:
        _USE_MEMORY = True
        return False

def init():
    if not _sqlite_ok():
        return
    # ensure schema
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        source TEXT,
        published TEXT,
        summary TEXT,
        category TEXT DEFAULT 'general',
        fetched_at TEXT
    )""")
    c.commit(); c.close()

def _mem_upsert(art):
    for a in _MEMORY:
        if a["link"] == art["link"]:
            return
    rec = dict(art)
    rec["id"] = len(_MEMORY)+1
    rec["fetched_at"] = datetime.datetime.utcnow().isoformat()
    _MEMORY.append(rec)

def upsert(art):
    global _USE_MEMORY
    if _USE_MEMORY:
        _mem_upsert(art); return
    try:
        c = sqlite3.connect(DB_PATH)
        c.execute("""INSERT OR IGNORE INTO articles (title,link,source,published,summary,category,fetched_at)
                    VALUES (?,?,?,?,?,?,?)""",
                  (art["title"], art["link"], art.get("source"), art.get("published"),
                   art.get("summary"), art.get("category","general"), datetime.datetime.utcnow().isoformat()))
        c.commit(); c.close()
    except Exception:
        _USE_MEMORY = True
        _mem_upsert(art)

def list_articles(limit=200, source=None, category=None, q=None):
    global _USE_MEMORY
    if _USE_MEMORY:
        rows = list(_MEMORY)
    else:
        try:
            c = sqlite3.connect(DB_PATH)
            c.row_factory = sqlite3.Row
            sql = "SELECT * FROM articles"
            params = []; where = []
            if source: where.append("source = ?"); params.append(source)
            if category: where.append("category = ?"); params.append(category)
            if q: where.append("(title LIKE ? OR summary LIKE ?)"); params += [f"%{q}%", f"%{q}%"]
            if where: sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY COALESCE(published,'') DESC, id DESC LIMIT ?"
            params.append(limit)
            rows = [dict(r) for r in c.execute(sql, params).fetchall()]
            c.close()
        except Exception:
            _USE_MEMORY = True
            rows = list(_MEMORY)
    # filter memory
    if _USE_MEMORY:
        out = []
        for r in rows:
            if source and r.get("source") != source: continue
            if category and r.get("category") != category: continue
            if q and q.lower() not in ((r.get("title") or "") + " " + (r.get("summary") or "")).lower(): continue
            out.append(r)
        out.sort(key=lambda r: r.get("published") or "", reverse=True)
        return out[:limit]
    return rows

def stats():
    global _USE_MEMORY
    if _USE_MEMORY:
        from collections import Counter
        total = len(_MEMORY)
        sources = Counter(a.get("source") for a in _MEMORY)
        cats = Counter(a.get("category") for a in _MEMORY)
        return {"total": total,
                "sources": [{"source": k, "n": v} for k, v in sources.most_common()],
                "categories": [{"category": k, "n": v} for k, v in cats.most_common()]}
    try:
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        total = c.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        sources = [dict(r) for r in c.execute("SELECT source, COUNT(*) n FROM articles GROUP BY source ORDER BY n DESC").fetchall()]
        cats = [dict(r) for r in c.execute("SELECT category, COUNT(*) n FROM articles GROUP BY category ORDER BY n DESC").fetchall()]
        c.close()
        return {"total": total, "sources": sources, "categories": cats}
    except Exception:
        _USE_MEMORY = True
        return stats()

def total_count():
    return len(_MEMORY) if _USE_MEMORY else None
