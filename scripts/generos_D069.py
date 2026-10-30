"""D-069 (exploratorio): rendimiento y firma de features por categoria de YouTube."""
from __future__ import annotations

import json
import sys
from collections import Counter
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, partial_spearman, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
S, Y = base["LGBM_bin"], base["Y"]
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
cat = [(M[v].get("categories") or ["?"])[0] for v in vids]
cnt = Counter(cat)
print("categorias (primera) y n:", dict(cnt.most_common()))
rows = []
for i, v in enumerate(vids):
    d = pd.read_parquet(bd / f"{v}.parquet")
    st, en = d.start.to_numpy(), d.end.to_numpy()
    k = top_k_nms(st, en, S[i])
    rel = d.y_relevant.to_numpy()
    rk = d[feats].rank(pct=True).fillna(0.5).to_numpy()
    pos = d.p_rel_pos.to_numpy()
    rho = {f: partial_spearman(rk[:, j], Y[i], pos) for j, f in enumerate(feats) if f in
           ("l_silence", "a_pause_ratio", "a_pitch_range", "a_speech_rate", "e_laugh_mean", "e_applause_mean", "s_polarity_mean")}
    rows.append(dict(cat=cat[i], hit=float(rel[k].max() > 0), azar=1 - comb(100 - int(rel.sum()), 5) / comb(100, 5),
                     F1=f1_temporal([(st[j], en[j]) for j in k], heat_intervals(corrected_graph(M[v]["heatmap"]))), **rho))
df = pd.DataFrame(rows)
df["exceso"] = df.hit - df.azar
big = [c for c, n in cnt.items() if n >= 15]
g = df[df.cat.isin(big)].groupby("cat")
out = g.agg(n=("hit", "size"), hit=("hit", "mean"), azar=("azar", "mean"), exceso=("exceso", "mean"), F1=("F1", "mean"),
            silencio=("l_silence", "median"), pausas=("a_pause_ratio", "median"), tono=("a_pitch_range", "median"),
            ritmo=("a_speech_rate", "median"), risa=("e_laugh_mean", "median"), aplausos=("e_applause_mean", "median"),
            polaridad=("s_polarity_mean", "median")).round(3)
print("\nRendimiento del modelo y firma (rho parcial mediano con el calor) por categoria con n >= 15:")
print(out.sort_values("n", ascending=False).to_string())
if len(big) >= 3:
    groups = [df[df.cat == c].exceso.to_numpy() for c in big]
    print(f"\nKruskal-Wallis del exceso sobre el azar entre categorias: p = {stats.kruskal(*groups).pvalue:.3f}")
    g2 = [df[df.cat == c].l_silence.dropna().to_numpy() for c in big]
    print(f"Kruskal-Wallis de la firma de silencio entre categorias: p = {stats.kruskal(*g2).pvalue:.3f}")
