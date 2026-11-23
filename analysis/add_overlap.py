"""Them dac trung trung lap van ban cho cac cap bai da co trong data/to_label.csv.

overlap5      : ti le cum 5 tu cua bai SAU (dst) xuat hien trong bai TRUOC (src)
shared_sents  : so cau (>= 8 tu) cua bai sau giong het mot cau cua bai truoc
Ket qua ghi ra data/to_label_overlap.csv (giu nguyen cot label).
"""
import html
import re
import sqlite3

import pandas as pd

DB = "data/news.db"
IN = "data/to_label.csv"
OUT = "data/to_label_overlap.csv"
N = 5

db = sqlite3.connect(DB)
body = dict(db.execute("SELECT url, body FROM articles WHERE body IS NOT NULL"))
d = pd.read_csv(IN)


def words(t):
    return re.findall(r"\w+", html.unescape(t or "").lower())


def shingles(w):
    return {" ".join(w[i:i + N]) for i in range(len(w) - N + 1)}


def sents(t):
    out = set()
    for s in re.split(r"[.!?\n]+", html.unescape(t or "").lower()):
        w = words(s)
        if len(w) >= 8:
            out.add(" ".join(w))
    return out


ov, ss = [], []
for r in d.itertuples():
    a, b = body.get(r.src_url, ""), body.get(r.dst_url, "")
    sa, sb = shingles(words(a)), shingles(words(b))
    ov.append(round(len(sa & sb) / len(sb), 3) if sb else 0.0)
    ss.append(len(sents(a) & sents(b)))
d["overlap5"] = ov
d["shared_sents"] = ss
d.to_csv(OUT, index=False, encoding="utf-8-sig")
print("Da ghi", OUT, "|", len(d), "cap")
if "label" in d.columns:
    print(d.groupby("label")[["cosine", "overlap5", "shared_sents"]].median().round(3))