"""D-081 (exploratorio): curva de aprendizaje de R0 y estrategia de selección de los 5 clips. Preregistro en DECISIONES.md."""
import hashlib
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "explorar_D081"
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])  # noqa: E731
reservados = J("conjunto_confirmacion_fresca_D050.json") | J("conjunto_confirmacion_fresca2_D065.json")
reservados |= set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])


def load(ids):
    V, T, M = [], [], []
    for v in ids:
        p = bd / f"{v}.parquet"
        if v in reservados or not p.exists() or not (hd / f"{v}.json").exists():
            continue
        d = pd.read_parquet(p)
        if len(d) == 100 and all(f in d for f in feats):
            V.append(v)
            T.append(d)
            M.append(json.loads((hd / f"{v}.json").read_text(encoding="utf-8")))
    return V, T, M


V, T, M = load(sorted(p.stem for p in bd.glob("*.parquet")))
hold = np.array([int(hashlib.md5(str(m["channel_id"]).encode()).hexdigest(), 16) % 5 == 0 for m in M])
tr, te = np.where(~hold)[0], np.where(hold)[0]
RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
G = np.stack([d["y_grade"].to_numpy(int) for d in T])
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(m["heatmap"])) for m in M]
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def hit_f1(S, idx):
    o = []
    for k, i in enumerate(idx):
        sel = top_k_nms(ST[i], EN[i], S[k])
        o.append((float(REL[i][sel].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in sel], HEAT[i])))
    return np.array(o)


# ---- A. curva de aprendizaje
rng = np.random.default_rng(0)
res = {}
for n in (50, 100, 200, 300, len(tr)):
    h, f = [], []
    for r in range(5 if n < len(tr) else 1):
        sub = rng.choice(tr, n, replace=False) if n < len(tr) else tr
        m = lgb.train(P, lgb.Dataset(RK[sub].reshape(-1, RK.shape[2]), G[sub].reshape(-1), group=[100] * len(sub)), 300)
        pr = m.predict(RK[te].reshape(-1, RK.shape[2])).reshape(len(te), 100)
        a = hit_f1(pr, te)
        h.append(a[:, 0].mean())
        f.append(a[:, 1].mean())
    res[n] = (float(np.mean(h)), float(np.mean(f)))
    print(f"n={n:4d}  hit@5 {res[n][0]:.1%}  F1 {res[n][1]:.4f}", flush=True)
ns = np.array(list(res))
hs = np.array([res[n][0] for n in ns])
b, a = np.polyfit(np.log(ns), hs, 1)
ext = {str(N): float(np.clip(a + b * np.log(N), 0, 1)) for N in (1000, 2000, 10000, 100000)}
print(f"ajuste hit = {a:.3f} + {b:.3f}*ln(n) -> extrapolado: " + ", ".join(f"n={k}: {v:.1%}" for k, v in ext.items()))

# ---- B. estrategia de seleccion sobre predicciones fuera de fold de D-054
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vb = [str(v) for v in base["vids"]]
Tb = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vb}
Mb = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vb}
S0 = base["LGBM_bin"]


def spaced(st, en, sc, gap_frac=0.10, k=5):
    c = (st + en) / 2
    total = en.max() - st.min()
    out = []
    for i in np.argsort(-sc):
        if all(abs(c[i] - c[j]) >= gap_frac * total for j in out):
            out.append(i)
        if len(out) == k:
            break
    return out


rows = {"S0_nms": [], "S1_espaciado10": []}
for i, v in enumerate(vb):
    d = Tb[v]
    st, en = d["start"].to_numpy(), d["end"].to_numpy()
    rel, heat = d["y_relevant"].to_numpy(), heat_intervals(corrected_graph(Mb[v]["heatmap"]))
    for nm, sel in (("S0_nms", top_k_nms(st, en, S0[i])), ("S1_espaciado10", spaced(st, en, S0[i]))):
        rows[nm].append((float(rel[sel].max() > 0), f1_temporal([(st[j], en[j]) for j in sel], heat)))
r0, r1 = np.array(rows["S0_nms"]), np.array(rows["S1_espaciado10"])
pf = float(stats.wilcoxon(r1[:, 1], r0[:, 1]).pvalue)
x, y = r1[:, 0] > 0, r0[:, 0] > 0
print(f"S0 NMS: hit {r0[:,0].mean():.1%} F1 {r0[:,1].mean():.4f} | S1 espaciado 10%: hit {r1[:,0].mean():.1%} F1 {r1[:,1].mean():.4f}")
print(f"S1 vs S0: dif hit {r1[:,0].mean()-r0[:,0].mean():+.3f} (solo-S1 {(x&~y).sum()}, solo-S0 {(~x&y).sum()}) | dif F1 {r1[:,1].mean()-r0[:,1].mean():+.4f} p={pf:.4f}")
json.dump({"n_train": len(tr), "n_holdout": len(te), "curva": {str(k): v for k, v in res.items()}, "ajuste": {"a": float(a), "b": float(b)},
           "extrapolado_hit": ext, "seleccion": {"S0": r0.mean(0).tolist(), "S1": r1.mean(0).tolist(), "p_F1": pf}},
          open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
