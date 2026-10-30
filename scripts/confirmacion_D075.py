"""Confirmacion unica D-075: mezcla R0 + submodelo de 17 variables (D-073) en los videos nuevos de D-071.

Entrena con el desarrollo (444 videos de D-054) y evalua UNA vez en los videos de
`reports/conjunto_entrenamiento_extra_D071.json` que tengan features y curva. Nada se reajusta tras ver el resultado.
Correr una sola vez; el script se niega a repetirse si ya existe `reports/confirmacion_D075/resultado.json`.
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
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "confirmacion_D075"
if (OUT / "resultado.json").exists():
    sys.exit("D-075 ya se corrio una vez; no se repite (regla de confirmacion unica).")
OUT.mkdir(parents=True, exist_ok=True)

feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
dev = [str(v) for v in np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)["vids"]]
new = []
for _f in ("conjunto_libres_D078.json", "conjunto_entrenamiento_extra_D071.json"):  # D-078 amplia el conjunto de D-075
    _p = ROOT / "reports" / _f
    if _p.exists():
        new += json.loads(_p.read_text(encoding="utf-8"))["video_ids"]
new = list(dict.fromkeys(new))
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
sel = [feats.index(k) for k in W if k in feats]
wv = np.array([W[feats[j]] for j in sel], np.float32)


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


def sh(x, k):
    o = np.roll(x, k, axis=1)
    if k > 0:
        o[:, :k] = 0.5
    else:
        o[:, k:] = 0.5
    return o


def rankrows(a):
    return np.apply_along_axis(lambda z: pd.Series(z).rank(pct=True).to_numpy(), 1, a)


def build(T):
    RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
    raw = (RK[:, :, sel] * wv).sum(axis=2)
    rr = rankrows(raw)[:, :, None].astype(np.float32)
    X17 = np.concatenate([RK[:, :, sel], rr, sh(rr, 1), sh(rr, -1), sh(rr, 2), sh(rr, -2)], axis=2)
    return RK, X17


Vd, Td = load(dev)
Vn, Tn = load(new)
print(f"desarrollo={len(Vd)} | videos nuevos D-071 usables={len(Vn)}", flush=True)
if len(Vn) < 10:
    sys.exit("insuficiente; reintentar cuando termine D-071")
RKd, X17d = build(Td)
RKn, X17n = build(Tn)
Gd = np.stack([d["y_grade"].to_numpy(int) for d in Td])
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def fit(Xd, Xn, seeds):
    acc = 0
    for s in range(seeds):
        m = lgb.train({**P, "seed": 42 + s}, lgb.Dataset(Xd.reshape(-1, Xd.shape[2]), Gd.reshape(-1), group=[100] * len(Vd)), 300)
        acc = acc + rankrows(m.predict(Xn.reshape(-1, Xn.shape[2])).reshape(len(Vn), 100))
    return acc / seeds


pred = {"R0": fit(RKd, RKn, 1), "M17": fit(X17d, X17n, 5)}
pred["MIX"] = rankrows(pred["R0"]) + pred["M17"]

Y = np.stack([d["y_mr"].to_numpy() for d in Tn])
ST = np.stack([d["start"].to_numpy() for d in Tn])
EN = np.stack([d["end"].to_numpy() for d in Tn])
REL = np.stack([d["y_relevant"].to_numpy() for d in Tn])
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in Vn}
HEAT = [heat_intervals(corrected_graph(M[v]["heatmap"])) for v in Vn]


def ev(S):
    o = []
    for i in range(len(Vn)):
        k = top_k_nms(ST[i], EN[i], S[i])
        o.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                  float(Y[i][k].mean() / Y[i].mean())))
    return np.array(o)


rng = np.random.default_rng(0)
R = {"azar": np.mean([ev(rng.random(Y.shape)) for _ in range(40)], axis=0), "calor_directo": ev(Y)}
for k, v in pred.items():
    R[k] = ev(v)
chn = {M[v].get("channel_id") for v in Vn}
chd = {json.loads((hd / f"{v}.json").read_text(encoding="utf-8")).get("channel_id") for v in Vd}
res = {"n_videos": len(Vn), "n_desarrollo": len(Vd), "n_canales": len(chn), "canales_ya_en_desarrollo": len(chn & chd),
       "metodos": {k: {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()), "lift": float(a[:, 2].mean())} for k, a in R.items()}}
ref = R["R0"]
for k in ("MIX", "M17"):
    d = R[k][:, 1] - ref[:, 1]
    r = {"dif_F1": float(d.mean()), "mejor_en": int((d > 0).sum()),
         "p_unilateral": float(stats.wilcoxon(R[k][:, 1], ref[:, 1], alternative="greater").pvalue)}
    x, y = R[k][:, 0] > 0, ref[:, 0] > 0
    r["solo_modelo"], r["solo_R0"] = int((x & ~y).sum()), int((~x & y).sum())
    n = r["solo_modelo"] + r["solo_R0"]
    r["p_hit_McNemar"] = float(stats.binomtest(r["solo_modelo"], n, 0.5, alternative="greater").pvalue) if n else None
    res[f"{k}_vs_R0"] = r
res["descriptiva_n_menor_40"] = bool(len(Vn) < 40)
json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
np.savez_compressed(OUT / "pred.npz", vids=np.array(Vn), **pred)
print(f"n={len(Vn)} videos, {len(chn)} canales ({len(chn & chd)} ya en desarrollo)")
print(f"{'metodo':14s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}")
for k, v in res["metodos"].items():
    print(f"{k:14s} {v['hit5']:7.1%} {v['F1']:7.3f} {v['lift']:6.2f}")
for k in ("MIX", "M17"):
    r = res[f"{k}_vs_R0"]
    print(f"{k} vs R0: dif F1 {r['dif_F1']:+.4f} | mejor en {r['mejor_en']}/{len(Vn)} | p = {r['p_unilateral']:.4f} | "
          f"acierto solo-modelo={r['solo_modelo']} solo-R0={r['solo_R0']} p = {r['p_hit_McNemar']}")
