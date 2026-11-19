"""Danh gia nguong cosine tren tap nhan, dung copy network, tinh PageRank/HITS."""
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 1. Danh gia baseline tren tap da gan nhan ----
lab = pd.read_csv("data/to_label.csv")
lab = lab[lab.label.isin(["verbatim", "near", "rewrite", "unrelated"])]
lab["y"] = (lab.label != "unrelated").astype(int)
print("So cap da gan nhan:", len(lab), "| copy:", lab.y.sum())
best = (0, 0.5)
for th in [x / 100 for x in range(35, 96, 5)]:
    pred = (lab.cosine >= th).astype(int)
    tp = ((pred == 1) & (lab.y == 1)).sum()
    fp = ((pred == 1) & (lab.y == 0)).sum()
    fn = ((pred == 0) & (lab.y == 1)).sum()
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    f = 2 * p * r / (p + r) if p + r else 0
    print(f"threshold={th:.2f}  P={p:.2f}  R={r:.2f}  F1={f:.2f}")
    if f > best[0]:
        best = (f, th)
TH = best[1]
print("Nguong tot nhat:", TH, "F1 =", round(best[0], 3))

# ---- 2. Copy network cap trang bao ----
pairs = pd.read_csv("data/pairs.csv")
pairs = pairs[pairs.cosine >= TH]
G = nx.DiGraph()
for r in pairs.itertuples():
    w = G.get_edge_data(r.src_outlet, r.dst_outlet, {}).get("weight", 0)
    G.add_edge(r.src_outlet, r.dst_outlet, weight=w + r.cosine)
print("Nut:", G.number_of_nodes(), "Canh:", G.number_of_edges())

# canh src -> dst nghia la dst chep src; PageRank tren do thi dao = "nguon goc"
pr = nx.pagerank(G.reverse(), weight="weight")
hubs, auth = nx.hits(G, max_iter=500)
first = pairs.groupby("src_outlet").size()
table = pd.DataFrame({"pagerank_origin": pr, "hub": hubs, "authority": auth,
                      "n_first": first}).fillna(0).sort_values(
                      "pagerank_origin", ascending=False)
print(table.round(3))
table.to_csv("data/outlet_ranking.csv")

# ---- 3. Hinh minh hoa ----
pos = nx.spring_layout(G, seed=1)
w = [G[u][v]["weight"] for u, v in G.edges]
nx.draw_networkx(G, pos, node_size=900, node_color="#9FE1CB", width=[x / max(w) * 4 for x in w],
                 arrows=True, arrowsize=18, font_size=9)
plt.axis("off")
plt.savefig("data/copy_network.png", dpi=150, bbox_inches="tight")
print("Da luu data/copy_network.png")