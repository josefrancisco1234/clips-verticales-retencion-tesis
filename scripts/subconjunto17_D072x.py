"""D-072x (exploratorio): LightGBM con solo las 17 features de la formula + vecinos +-1,+-2 + contexto (mismos folds que D-054)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
Y = base["Y"]
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
chan = np.array([M[v]["channel_id"] for v in vids])
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
sel = [feats.index(k) for k in W if k in feats]
RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])[:, :, sel]
G = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
ST = np.stack([T[v]["start"].to_numpy() for v in vids])
EN = np.stack([T[v]["end"].to_numpy() for v in vids])
HEAT = [heat_intervals(corrected_graph(M[v]["heatmap"])) for v in vids]
def sh(x, k):
    o = np.roll(x, k, axis=1)
    if k > 0: o[:, :k] = 0.5
    else: o[:, k:] = 0.5
    return o
raw = (RK * np.array([W[feats[j]] for j in sel], np.float32)).sum(axis=2, keepdims=True)
rr = np.stack([pd.Series(r[:, 0]).rank(pct=True).to_numpy() for r in raw])[:, :, None].astype(np.float32)
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=4, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
X = np.concatenate([RK, rr, sh(rr, 1), sh(rr, -1), sh(rr, 2), sh(rr, -2)], axis=2)
o = np.zeros_like(Y)
for tr, te in GroupKFold(10).split(np.arange(len(vids)), groups=chan):
    acc = 0
    for sd in range(5):
        m = lgb.train({**P, "seed": 42 + sd}, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
        p = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
        acc = acc + np.apply_along_axis(lambda z: pd.Series(z).rank(pct=True).to_numpy(), 1, p)
    o[te] = acc / 5
bl = np.apply_along_axis(lambda z: pd.Series(z).rank(pct=True).to_numpy(), 1, base["LGBM_bin"]) + o


def met(S):
    r = []
    for i in range(len(vids)):
        k = top_k_nms(ST[i], EN[i], S[i])
        r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i])))
    return np.array(r)


mb, mc = met(base["LGBM_bin"]), met(o)
mx = met(bl)
print(f"R0 + 17feats(5 semillas) promedio de rangos: hit {mx[:,0].mean():.1%} F1 {mx[:,1].mean():.3f} dif {(mx[:,1]-mb[:,1]).mean():+.4f} p={stats.wilcoxon(mx[:,1], mb[:,1]).pvalue:.3f}")
d = mc[:, 1] - mb[:, 1]
print(f"R0: hit {mb[:, 0].mean():.1%} F1 {mb[:, 1].mean():.3f} | 17 feats + vecinos: hit {mc[:, 0].mean():.1%} F1 {mc[:, 1].mean():.3f}")
print(f"dif F1 {d.mean():+.4f} | Wilcoxon p = {stats.wilcoxon(mc[:, 1], mb[:, 1]).pvalue:.4f}")
