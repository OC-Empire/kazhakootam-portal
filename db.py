import sqlite3, os, datetime, json
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "news.db")
# Respect process-injected variables first; among dotenv files, .env.local is
# authoritative over the shared .env file (for example after `neon env pull`).
load_dotenv(os.path.join(BASE, ".env.local"), override=False)
load_dotenv(os.path.join(BASE, ".env"), override=False)
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

_MEMORY = []          # fallback store for read-only/serverless envs
_USE_MEMORY = False
_PG_INITIALIZED = False

def _postgres():
    if not DATABASE_URL and os.environ.get("VERCEL") == "1":
        raise RuntimeError("DATABASE_URL is required on Vercel; refusing instance-local memory storage")
    return bool(DATABASE_URL)

def _pg_connect():
    # Vercel uses short-lived Python functions; DATABASE_URL should be Neon's
    # pooled endpoint so independent invocations share durable storage safely.
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(DATABASE_URL, connect_timeout=8, row_factory=dict_row)

def _sqlite_ok():
    global _USE_MEMORY
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        c = sqlite3.connect(DB_PATH)
        c.execute("CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, link TEXT UNIQUE, source TEXT, published TEXT, published_ts INTEGER DEFAULT 0, summary TEXT, category TEXT, image TEXT, fetched_at TEXT)")
        c.commit(); c.close()
        return True
    except Exception:
        _USE_MEMORY = True
        return False

def _ensure_column(c, col, decl):
    cols = [r[1] for r in c.execute(f"PRAGMA table_info(articles)").fetchall()]
    if col not in cols:
        try:
            c.execute(f"ALTER TABLE articles ADD COLUMN {col} {decl}")
            c.commit()
        except Exception:
            pass

def init():
    global _PG_INITIALIZED
    if _postgres():
        if _PG_INITIALIZED:
            return
        # Production schema is provisioned through versioned SQL migrations.
        # Fail clearly if the migration was not applied; never run DDL at startup.
        with _pg_connect() as c:
            c.execute("SELECT id, title, link, source, published, published_ts, summary, category, image, fetched_at FROM articles LIMIT 0")
        _PG_INITIALIZED = True
        return
    if not _sqlite_ok():
        return
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        source TEXT,
        published TEXT,
        published_ts INTEGER DEFAULT 0,
        summary TEXT,
        category TEXT DEFAULT 'general',
        image TEXT,
        fetched_at TEXT
    )""")
    _ensure_column(c, "published_ts", "INTEGER DEFAULT 0")
    _ensure_column(c, "image", "TEXT")
    c.commit(); c.close()

def _mem_upsert(art):
    for a in _MEMORY:
        if a["link"] == art["link"]:
            return
    rec = dict(art)
    rec["id"] = len(_MEMORY)+1
    rec["published_ts"] = art.get("published_ts", 0)
    rec["fetched_at"] = datetime.datetime.utcnow().isoformat()
    _MEMORY.append(rec)

def upsert_many(articles):
    global _USE_MEMORY
    articles = list(articles)
    if not articles:
        return 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    records = [
        (art["title"], art["link"], art.get("source"), art.get("published"),
         art.get("published_ts", 0), art.get("summary"), art.get("category", "general"),
         art.get("image"), now)
        for art in articles
    ]
    if _USE_MEMORY:
        for art in articles:
            for old in _MEMORY:
                if old.get("link") == art["link"]:
                    old.update({k: v for k, v in art.items() if v not in (None, "")})
                    old["fetched_at"] = now
                    break
            else:
                _mem_upsert(art)
        return len(articles)
    if _postgres():
        with _pg_connect() as c:
            c.cursor().executemany("""INSERT INTO articles
                (title,link,source,published,published_ts,summary,category,image,fetched_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (link) DO UPDATE SET
                    title = COALESCE(NULLIF(EXCLUDED.title, ''), articles.title),
                    source = COALESCE(NULLIF(EXCLUDED.source, ''), articles.source),
                    published = CASE WHEN EXCLUDED.published_ts >= COALESCE(articles.published_ts, 0) THEN COALESCE(NULLIF(EXCLUDED.published, ''), articles.published) ELSE articles.published END,
                    published_ts = GREATEST(COALESCE(articles.published_ts, 0), COALESCE(EXCLUDED.published_ts, 0)),
                    summary = COALESCE(NULLIF(EXCLUDED.summary, ''), articles.summary),
                    category = COALESCE(NULLIF(EXCLUDED.category, ''), articles.category),
                    image = COALESCE(NULLIF(EXCLUDED.image, ''), articles.image),
                    fetched_at = EXCLUDED.fetched_at""", records)
        return len(articles)
    try:
        c = sqlite3.connect(DB_PATH)
        c.executemany("""INSERT INTO articles
            (title,link,source,published,published_ts,summary,category,image,fetched_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(link) DO UPDATE SET
                title=COALESCE(NULLIF(excluded.title,''), articles.title),
                source=COALESCE(NULLIF(excluded.source,''), articles.source),
                published=CASE WHEN excluded.published_ts >= COALESCE(articles.published_ts,0) THEN COALESCE(NULLIF(excluded.published,''),articles.published) ELSE articles.published END,
                published_ts=MAX(COALESCE(articles.published_ts,0),COALESCE(excluded.published_ts,0)),
                summary=COALESCE(NULLIF(excluded.summary,''),articles.summary),
                category=COALESCE(NULLIF(excluded.category,''),articles.category),
                image=COALESCE(NULLIF(excluded.image,''),articles.image),
                fetched_at=excluded.fetched_at""", records)
        c.commit(); c.close()
        return len(articles)
    except Exception:
        _USE_MEMORY = True
        for art in articles:
            _mem_upsert(art)
        return len(articles)

def upsert(art):
    return upsert_many([art])

def set_image(link, url):
    global _USE_MEMORY
    if _USE_MEMORY:
        for a in _MEMORY:
            if a.get("link") == link:
                a["image"] = url
                return
        return
    if _postgres():
        with _pg_connect() as c:
            c.execute("UPDATE articles SET image=%s WHERE link=%s", (url, link))
        return
    try:
        c = sqlite3.connect(DB_PATH)
        c.execute("UPDATE articles SET image=? WHERE link=?", (url, link))
        c.commit(); c.close()
    except Exception as e:
        print("set_image error:", e)

def list_articles(limit=200, source=None, category=None, q=None):
    global _USE_MEMORY
    if _USE_MEMORY:
        rows = list(_MEMORY)
    elif _postgres():
        sql = "SELECT * FROM articles"
        params = []; where = []
        if source: where.append("source = %s"); params.append(source)
        if category: where.append("category = %s"); params.append(category)
        if q: where.append("(title ILIKE %s OR summary ILIKE %s)"); params += [f"%{q}%", f"%{q}%"]
        if where: sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY COALESCE(published_ts,0) DESC, id DESC LIMIT %s"
        params.append(limit)
        with _pg_connect() as c:
            rows = c.execute(sql, params).fetchall()
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
            sql += " ORDER BY COALESCE(published_ts,0) DESC, id DESC LIMIT ?"
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
        out.sort(key=lambda r: r.get("published_ts") or 0, reverse=True)
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
    if _postgres():
        with _pg_connect() as c:
            total = c.execute("SELECT COUNT(*) AS total FROM articles").fetchone()["total"]
            sources = c.execute("SELECT source, COUNT(*) AS n FROM articles GROUP BY source ORDER BY n DESC").fetchall()
            cats = c.execute("SELECT category, COUNT(*) AS n FROM articles GROUP BY category ORDER BY n DESC").fetchall()
        return {"total": total, "sources": sources, "categories": cats}
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
