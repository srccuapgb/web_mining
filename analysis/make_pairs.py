"""Sinh cap bai ung vien (khac trang, cach nhau <= 72h) bang TF-IDF cosine."""
import sqlite3
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

DB = "data/news.db"
MAX_HOURS = 72
MIN_SIM = 0.35      # nguong thap de khong bo sot bai viet lai
CHUNK = 500

db = sqlite3.connect(DB)
df = pd.read_sql(
    "SELECT url, outlet, title, body, first_seen_at FROM articles "
    "WHERE fetch_status='ok' AND body IS NOT NULL", db)
df["t"] = pd.to_datetime(df["first_seen_at"], utc=True)
df = df.reset_index(drop=True)
print("So bai co noi dung:", len(df))

tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
X = tfidf.fit_transform(df["title"].fillna("") + ". " + df["body"])
hours = ((df["t"] - df["t"].min()).dt.total_seconds() / 3600).to_numpy()
outlet = df["outlet"].to_numpy()

rows = []
for s in range(0, len(df), CHUNK):
    sims = (X[s:s + CHUNK] @ X.T).toarray()
    for k in range(sims.shape[0]):
        i = s + k
        cand = np.where(sims[k] >= MIN_SIM)[0]
        for j in cand:
            if j <= i or outlet[j] == outlet[i]:
                continue
            if abs(hours[j] - hours[i]) > MAX_HOURS:
                continue
            a, b = (i, j) if hours[i] <= hours[j] else (j, i)   # a dang truoc
            rows.append((df.url[a], df.url[b], outlet[a], outlet[b],
                         float(sims[k, j]), hours[b] - hours[a]))

pairs = pd.DataFrame(rows, columns=["src_url", "dst_url", "src_outlet",
                                    "dst_outlet", "cosine", "delay_hours"])
pairs.to_csv("data/pairs.csv", index=False)
print("So cap ung vien:", len(pairs))