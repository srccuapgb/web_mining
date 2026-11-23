"""Danh gia cosine tren tap nhan, dung network cap bao, tinh PageRank/HITS.

Nhan: verbatim, near, rewrite, same_event, unrelated
Ba cach dinh nghia "positive":
  story   : moi nhan khac 'unrelated' (cung su viec, ke ca tu viet doc lap)
  derived : verbatim + near + rewrite (bai sau co dau hieu dua vao bai truoc)
  reuse   : chi verbatim + near (trung chu ro ret)
Neu ti le positive qua cao (vd 95%) thi P/R/F1 khong co y nghia, can doc AUC.
Do thi copy network chi dung cac cap thuoc nhom 'derived' (GRAPH_MODE = "derived").
"""
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score

LABELED = "data/to_label_overlap.csv"   # neu chua chay add_overlap.py thi doi thanh data/to_label.csv
PAIRS = "data/pairs.csv"
GRAPH_MODE = "derived"                   # "derived": cap da gan nhan derived; "threshold": cosine >= GRAPH_TH
GRAPH_TH = 0.45

try:
    lab = pd.read_csv(LABELED)
except FileNotFoundError:
    LABELED = "data/to_label.csv"
    lab = pd.read_csv(LABELED)
lab = lab[lab.label.isin(["verbatim", "near", "rewrite", "same_event", "unrelated"])].copy()
print("File nhan:", LABELED, "| so cap da gan nhan:", len(lab))
print(lab.label.value_counts().to_dict())
lab["story"] = (lab.label != "unrelated").astype(int)
lab["derived"] = lab.label.isin(["verbatim", "near", "rewrite"]).astype(int)
lab["reuse"] = lab.label.isin(["verbatim", "near"]).astype(int)

scores = [c for c in ["cosine", "overlap5"] if c in lab.columns]
for target in ["story", "derived", "reuse"]:
    y = lab[target]
    print(f"\n=== Target '{target}': positive = {y.sum()}/{len(y)} ({y.mean():.0%}) ===")
    if y.nunique() < 2:
        print("Chi co mot lop, khong danh gia duoc.")
        continue
    for sc in scores:
        print(f"AUC cua {sc}: {roc_auc_score(y, lab[sc]):.3f}   (0.5 = ngau nhien)")
    for sc in scores:
        lo, hi = (0.35, 0.96) if sc == "cosine" else (0.05, 0.96)
        print(f"-- nguong tren {sc}")
        t = lo
        while t < hi:
            pred = (lab[sc] >= t).astype(int)
            tp = ((pred == 1) & (y == 1)).sum()
            fp = ((pred == 1) & (y == 0)).sum()
            fn = ((pred == 0) & (y == 1)).sum()
            p = tp / (tp + fp) if tp + fp else 0
            r = tp / (tp + fn) if tp + fn else 0
            f = 2 * p * r / (p + r) if p + r else 0
            print(f"  >= {t:.2f}  P={p:.2f}  R={r:.2f}  F1={f:.2f}  (du doan {pred.sum()})")
            t += 0.10 if sc == "overlap5" else 0.05

# ---- Copy network cap bao ----
if GRAPH_MODE == "derived":
    edges = lab[lab.derived == 1]
    print(f"\nDo thi tu {len(edges)} cap derived (verbatim/near/rewrite)")
else:
    edges = pd.read_csv(PAIRS)
    edges = edges[edges.cosine >= GRAPH_TH]
    print(f"\nDo thi tu cac cap co cosine >= {GRAPH_TH}: {len(edges)} cap")
if edges.empty:
    raise SystemExit("Khong co cap nao de dung do thi.")
G = nx.DiGraph()
for r in edges.itertuples():
    w = G.get_edge_data(r.src_outlet, r.dst_outlet, {}).get("weight", 0)
    G.add_edge(r.src_outlet, r.dst_outlet, weight=w + r.cosine)
print(f"Nut {G.number_of_nodes()}, canh {G.number_of_edges()}")

# canh src -> dst: dst dang sau src. PageRank tren do thi dao = "nguon dang truoc"
pr = nx.pagerank(G.reverse(), weight="weight")
hubs, auth = nx.hits(G, max_iter=500)
first = edges.groupby("src_outlet").size()
table = pd.DataFrame({"pagerank_origin": pr, "hub": hubs, "authority": auth,
                      "n_first": first}).fillna(0).sort_values(
                      "pagerank_origin", ascending=False)
print(table.round(3))
table.to_csv("data/outlet_ranking.csv")

pos = nx.spring_layout(G, seed=1)
w = [G[u][v]["weight"] for u, v in G.edges]
nx.draw_networkx(G, pos, node_size=900, node_color="#9FE1CB",
                 width=[x / max(w) * 4 for x in w], arrows=True, arrowsize=18, font_size=9)
plt.axis("off")
plt.savefig("data/copy_network.png", dpi=150, bbox_inches="tight")
print("Da luu data/copy_network.png, data/outlet_ranking.csv")