"""Tong hop so lieu cho muc Datasets cua bao cao tien do."""
import sqlite3
import pandas as pd

db = sqlite3.connect("data/news.db")
df = pd.read_sql(
    "SELECT outlet, fetch_status, published_at, first_seen_at, LENGTH(body) AS n_chars "
    "FROM articles", db)
df["pub"] = pd.to_datetime(df["published_at"].replace("", pd.NA), utc=True, errors="coerce")

rows = []
for o, g in df.groupby("outlet"):
    ok = g[g.fetch_status == "ok"]
    rows.append({
        "outlet": o,
        "collected": len(g),
        "ok": len(ok),
        "empty": int((g.fetch_status == "empty").sum()),
        "pending": int((g.fetch_status == "pending").sum()),
        "no_pub_time": int(g.pub.isna().sum()),
        "avg_chars": round(ok.n_chars.mean()) if len(ok) else 0,
        "pub_min": g.pub.min().strftime("%Y-%m-%d %H:%M") if g.pub.notna().any() else "",
        "pub_max": g.pub.max().strftime("%Y-%m-%d %H:%M") if g.pub.notna().any() else "",
    })
t = pd.DataFrame(rows).sort_values("collected", ascending=False)
t["share_%"] = (t["collected"] / t["collected"].sum() * 100).round(1)
pd.set_option("display.width", 200)
print(t.to_string(index=False))
tot = t[["collected", "ok", "empty", "pending", "no_pub_time"]].sum()
print("\nTONG:", tot.to_dict())
print("Ti le co noi dung: %.1f%%" % (tot["ok"] / tot["collected"] * 100))
print("first_seen_at tu", df.first_seen_at.min(), "den", df.first_seen_at.max())
t.to_csv("data/dataset_summary.csv", index=False)
print("Da ghi data/dataset_summary.csv")