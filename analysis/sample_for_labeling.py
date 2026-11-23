"""Lay mau cap bai theo cac khoang do giong de ca nhom gan nhan."""
import sqlite3
import pandas as pd

N_PER_BIN = 200
pairs = pd.read_csv("data/pairs.csv")
db = sqlite3.connect("data/news.db")
title = dict(db.execute("SELECT url, title FROM articles"))

bins = [(0.35, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]
parts = []
for lo, hi in bins:
    sub = pairs[(pairs.cosine >= lo) & (pairs.cosine < hi)]
    parts.append(sub.sample(min(N_PER_BIN, len(sub)), random_state=42))
s = pd.concat(parts).reset_index(drop=True)
s["src_title"] = s.src_url.map(title)
s["dst_title"] = s.dst_url.map(title)
s["label"] = ""   # verbatim / near / rewrite / unrelated
s.to_csv("data/to_label.csv", index=False, encoding="utf-8-sig")
print("Da ghi data/to_label.csv:", len(s), "cap")