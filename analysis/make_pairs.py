"""Sinh cap bai ung vien (khac trang, cach nhau <= 72h) bang TF-IDF cosine.

Thu tu thoi gian:
- Mac dinh dung published_at (gio dang tren RSS, UTC). Dung cho lo du lieu dau
  tien, vi luc do first_seen_at cua moi bai deu la luc ban bat dau crawl.
- Bai khong co published_at (vi du Tuoi Tre) bi LOAI khoi viec ghep cap, vi neu
  roi ve first_seen_at thi bai do se luon bi coi la "dang sau".
  Dat USE_FIRST_SEEN_FALLBACK = True de dung first_seen_at thay the.
"""
import html
import sqlite3

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

DB = "data/news.db"
OUT = "data/pairs.csv"
MAX_HOURS = 72
MIN_SIM = 0.35      # nguong thap de khong bo sot bai viet lai
CHUNK = 500
USE_FIRST_SEEN_FALLBACK = False

db = sqlite3.connect(DB)
df = pd.read_sql(
    "SELECT url, outlet, title, body, first_seen_at, published_at FROM articles "
    "WHERE fetch_status='ok' AND body IS NOT NULL", db)
print("So bai co noi dung:", len(df))
if df.empty:
    raise SystemExit("Chua co bai nao co noi dung (fetch_status='ok'). Chay crawler truoc.")

# Lam sach ma HTML (vi du &amp;apos;) trong tieu de va noi dung
df["title"] = df["title"].fillna("").map(html.unescape)
df["body"] = df["body"].fillna("").map(html.unescape)

# Thoi gian dung de xac dinh bai nao dang truoc
pub = pd.to_datetime(df["published_at"].replace("", pd.NA), utc=True, errors="coerce")
if USE_FIRST_SEEN_FALLBACK:
    df["t"] = pub.fillna(pd.to_datetime(df["first_seen_at"], utc=True))
else:
    df["t"] = pub
    miss = df[df["t"].isna()]
    if len(miss):
        print("Loai", len(miss), "bai khong co published_at:",
              miss["outlet"].value_counts().to_dict())
    df = df[df["t"].notna()]
df = df.reset_index(drop=True)
print("So bai dung de ghep cap:", len(df), "|", df["outlet"].value_counts().to_dict())
if df["outlet"].nunique() < 2:
    raise SystemExit("Can it nhat 2 bao co noi dung de ghep cap.")

tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
X = tfidf.fit_transform(df["title"] + ". " + df["body"])
hours = ((df["t"] - df["t"].min()).dt.total_seconds() / 3600).to_numpy()
outlet = df["outlet"].to_numpy()

rows = []
for s in range(0, len(df), CHUNK):
    sims = (X[s:s + CHUNK] @ X.T).toarray()
    for k in range(sims.shape[0]):
        i = s + k
        for j in np.where(sims[k] >= MIN_SIM)[0]:
            if j <= i or outlet[j] == outlet[i]:
                continue
            if abs(hours[j] - hours[i]) > MAX_HOURS:
                continue
            a, b = (i, j) if hours[i] <= hours[j] else (j, i)   # a dang truoc
            rows.append((df.url[a], df.url[b], outlet[a], outlet[b],
                         float(sims[k, j]), hours[b] - hours[a]))

pairs = pd.DataFrame(rows, columns=["src_url", "dst_url", "src_outlet",
                                    "dst_outlet", "cosine", "delay_hours"])
pairs.to_csv(OUT, index=False)
print("So cap ung vien:", len(pairs))
if len(pairs):
    print(pairs.groupby(["src_outlet", "dst_outlet"]).size().sort_values(ascending=False))