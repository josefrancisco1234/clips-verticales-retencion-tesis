"""Confirmacion unica (D-061 B) de la representacion R4 en la cohorte fresca de D-050.

LightGBM por bin entrenado con el desarrollo ampliado (444 videos): R0 (rangos) frente a R4 (rango + valor
absoluto + contexto del video + vecinos). Hiperparametros de D-054, sin reajuste.
H-R4: R4 > R0 en F1 temporal@5 (Wilcoxon pareado, unilateral, alfa = 0.05).
"""
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
from scripts.representacion_D059 import shift  # noqa: E402
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "replicacion_R4_D061"
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
dev = [str(v) for v in np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)["vids"]]
fresh = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca_D050.json").read_text(encoding="utf-8"))["video_ids"]


def load(ids):
    V, T = [], []
    for v in ids:
        p = bd / f"{v}.parquet"
        if p.exists() and (hd / f"{v}.json").exists():
            d = pd.read_parquet(p)
            if len(d) == 100 and all(f in d for f in feats):
                V.append(v)
                T.append(d)
    return V, T


def build(T):
    RAW = np.nan_to_num(np.stack([d[feats].to_numpy(np.float32) for d in T]), nan=0.0)
    RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
    mu = RAW.mean(axis=1, keepdims=True).repeat(100, axis=1)
    sd = RAW.std(axis=1, keepdims=True).repeat(100, axis=1)
    nb = np.concatenate([shift(RK, 1), shift(RK, -1), shift(RK, 2), shift(RK, -2)], axis=2)
    return RK, np.concatenate([RK, RAW, mu, sd, nb], axis=2)


Vd, Td = load(dev)
Vf, Tf = load(fresh)
print(f"desarrollo={len(Vd)} | cohorte fresca usable={len(Vf)}", flush=True)
if len(Vf) < 10:
    print("insuficiente; reintentar cuando termine la descarga")
    sys.exit(0)
RKd, R4d = build(Td)
RKf, R4f = build(Tf)
Gd = np.stack([d["y_grade"].to_numpy(int) for d in Td])
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
pred = {}
for name, (Xd, Xf) in {"R0": (RKd, RKf), "R4": (R4d, R4f)}.items():
    m = lgb.train(P, lgb.Dataset(Xd.reshape(-1, Xd.shape[2]), Gd.reshape(-1), group=[100] * len(Vd)), 300)
    pred[name] = m.predict(Xf.reshape(-1, Xf.shape[2])).reshape(len(Vf), 100)
Y = np.stack([d["y_mr"].to_numpy() for d in Tf])
ST = np.stack([d["start"].to_numpy() for d in Tf])
EN = np.stack([d["end"].to_numpy() for d in Tf])
REL = np.stack([d["y_relevant"].to_numpy() for d in Tf])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in Vf]


def ev(S):
    o = []
    for i in range(len(Vf)):
        k = top_k_nms(ST[i], EN[i], S[i])
        o.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                  float(Y[i][k].mean() / Y[i].mean())))
    return np.array(o)


rng = np.random.default_rng(0)
R = {"azar": np.mean([ev(rng.random(Y.shape)) for _ in range(40)], axis=0), "R0": ev(pred["R0"]), "R4": ev(pred["R4"]),
     "calor_directo": ev(Y)}
res = {"n_videos": len(Vf), "metodos": {k: {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()),
                                           "lift": float(a[:, 2].mean())} for k, a in R.items()}}
d = R["R4"][:, 1] - R["R0"][:, 1]
res["H_R4_dif_F1"] = float(d.mean())
res["H_R4_mejor_en"] = int((d > 0).sum())
res["H_R4_wilcoxon_unilateral_p"] = float(stats.wilcoxon(R["R4"][:, 1], R["R0"][:, 1], alternative="greater").pvalue)
res["R4_vs_azar_F1_p"] = float(stats.wilcoxon(R["R4"][:, 1], R["azar"][:, 1], alternative="greater").pvalue)
json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
print(f"{'metodo':16s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}")
for k, v in res["metodos"].items():
    print(f"{k:16s} {v['hit5']:7.1%} {v['F1']:7.3f} {v['lift']:6.2f}")
print("H-R4: dif F1 %+.4f, mejor en %d/%d, p unilateral = %.4f" % (res["H_R4_dif_F1"], res["H_R4_mejor_en"], len(Vf),
                                                             res["H_R4_wilcoxon_unilateral_p"]))
