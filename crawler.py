"""RSS crawler for Vietnamese news sites (IT4868E capstone).

Usage:
    pip install -r requirements.txt
    python crawler.py run            # chay lien tuc, moi 10 phut
    python crawler.py run --once     # chay 1 vong de thu
    python crawler.py stats          # thong ke du lieu

Quy tac: first_seen_at duoc ghi NGAY khi phat hien URL moi trong RSS,
truoc khi tai noi dung bai, de tai that bai khong lam mat moc thoi gian.
"""
import argparse
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests
import trafilatura

UA = "HUST-WebMining-StudentCrawler/0.1 (contact: phamgiabaohust68@gmail.com)"  # doi email
DB_PATH = "data/news.db"
DELAY = 1.5          # giay giua hai request tai noi dung
MAX_ATTEMPTS = 3
BODY_BATCH = 2000     # so bai tai noi dung moi vong

# URL RSS: PHAI tu kiem tra tung URL tren trinh duyet truoc khi chay.
FEEDS = {
    "vnexpress": [
        "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "https://vnexpress.net/rss/thoi-su.rss",
        "https://vnexpress.net/rss/the-gioi.rss",
        "https://vnexpress.net/rss/kinh-doanh.rss",
        "https://vnexpress.net/rss/phap-luat.rss",
    ],
    "tuoitre": ["https://tuoitre.vn/rss/tin-moi-nhat.rss"],
    "thanhnien": ["https://thanhnien.vn/rss/home.rss"],
    "dantri": ["https://dantri.com.vn/rss/home.rss"],       # chua xac minh
    "vietnamnet": ["http://vietnamnet.vn/rss/thoi-su.rss"],  # chua xac minh
}

log = logging.getLogger("crawler")
_robots = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_url(url):
    p = urlsplit(url.strip())
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))  # bo query, fragment


def allowed(url):
    host = urlsplit(url)
    key = f"{host.scheme}://{host.netloc}"
    if key not in _robots:
        rp = robotparser.RobotFileParser(key + "/robots.txt")
        try:
            rp.read()
        except Exception as e:
            log.warning("khong doc duoc robots.txt cua %s: %s", key, e)
        _robots[key] = rp
    return _robots[key].can_fetch(UA, url)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """CREATE TABLE IF NOT EXISTS articles(
        url TEXT PRIMARY KEY, outlet TEXT, feed TEXT, title TEXT, summary TEXT,
        published_at TEXT, first_seen_at TEXT,
        body TEXT, fetched_at TEXT,
        fetch_status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0)"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_outlet ON articles(outlet, first_seen_at)")
    return db


def discover(db):
    for outlet, feeds in FEEDS.items():
        for feed_url in feeds:
            try:
                d = feedparser.parse(feed_url, agent=UA)
            except Exception as e:
                log.error("loi feed %s: %s", feed_url, e)
                continue
            if not d.entries:
                log.warning("feed khong co bai (kiem tra URL?): %s", feed_url)
                continue
            new = 0
            for e in d.entries:
                link = e.get("link")
                if not link:
                    continue
                pub = ""
                if e.get("published_parsed"):
                    pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                cur = db.execute(
                    "INSERT OR IGNORE INTO articles"
                    "(url,outlet,feed,title,summary,published_at,first_seen_at)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (clean_url(link), outlet, feed_url, e.get("title", ""),
                     e.get("summary", ""), pub, now_iso()),
                )
                new += cur.rowcount
            db.commit()
            log.info("%s | %s | %d bai moi / %d", outlet, feed_url, new, len(d.entries))


def fetch_bodies(db, limit=BODY_BATCH):
    rows = db.execute(
        "SELECT url FROM articles WHERE fetch_status='pending' AND attempts<? "
        "ORDER BY first_seen_at LIMIT ?", (MAX_ATTEMPTS, limit),
    ).fetchall()
    for (url,) in rows:
        status, body = "ok", None
        if not allowed(url):
            status = "blocked"
        else:
            try:
                r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
                r.raise_for_status()
                body = trafilatura.extract(
                    r.text, include_comments=False, include_tables=False,
                    favor_precision=True)
                if not body or len(body) < 200:
                    status = "empty"
            except Exception as e:
                log.warning("loi tai %s: %s", url, e)
                db.execute("UPDATE articles SET attempts=attempts+1 WHERE url=?", (url,))
                db.commit()
                time.sleep(DELAY)
                continue
        db.execute(
            "UPDATE articles SET body=?, fetched_at=?, fetch_status=?, attempts=attempts+1 "
            "WHERE url=?", (body, now_iso(), status, url))
        db.commit()
        time.sleep(DELAY)


def stats(db):
    print("== So bai theo trang va trang thai ==")
    for row in db.execute(
        "SELECT outlet, fetch_status, COUNT(*) FROM articles GROUP BY 1,2 ORDER BY 1,2"):
        print(row)
    print("== So bai moi ngay (theo first_seen_at) ==")
    for row in db.execute(
        "SELECT substr(first_seen_at,1,10) d, COUNT(*) FROM articles GROUP BY d ORDER BY d"):
        print(row)
    n = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    print("Tong:", n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "stats"])
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler("crawler.log")])
    db = init_db()
    if a.cmd == "stats":
        return stats(db)
    while True:
        discover(db)
        fetch_bodies(db)
        if a.once:
            break
        time.sleep(a.interval)


if __name__ == "__main__":
    main()