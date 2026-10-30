"""Confirmacion unica (D-061 B + D-063) de la familia R4 en la cohorte fresca de D-050.

Entrena con el desarrollo ampliado (444 videos) y evalua UNA vez en la cohorte fresca: R0, R4 (primaria),
U = R4+HuBERT, H4, H8 y el ensamble E3 (U + H8 + BiGRU base+HuBERT). Sin reajuste.
"""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import scripts.dl_secuencia_D054 as dl  # noqa: E402
from scripts.representacion_D059 import shift  # noqa: E402
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "confirmacion_cohorte2_D065"
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
dev = [str(v) for v in np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)["vids"]]
fresh = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca2_D065.json").read_text(encoding="utf-8"))["video_ids"]


def load(ids, need_u):
    V, T = [], []
    for v in ids:
        p = bd / f"{v}.parquet"
        if p.exists() and (hd / f"{v}.json").exists():
            d = pd.read_parquet(p)
            ok = len(d) == 100 and all(f in d for f in feats)
            if need_u:
                ok = ok and any(c.startswith("u_") for c in d.columns)
            if ok:
                V.append(v)
                T.append(d)
    return V, T


Vd, Td = load(dev, True)
Vf, Tf = load(fresh, True)
print(f"desarrollo={len(Vd)} | cohorte fresca usable (con HuBERT)={len(Vf)}", flush=True)
if len(Vf) < 10:
    print("insuficiente; reintentar cuando termine la descarga")
    sys.exit(0)
Ucols = sorted(c for c in Td[0].columns if c.startswith("u_"))


def build(T):
    RAW = np.nan_to_num(np.stack([d[feats].to_numpy(np.float32) for d in T]), nan=0.0)
    RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
    U = np.stack([d[Ucols].fillna(0).to_numpy(np.float32) for d in T])
    mu = RAW.mean(axis=1, keepdims=True).repeat(100, axis=1)
    sd = RAW.std(axis=1, keepdims=True).repeat(100, axis=1)
    nb = np.concatenate([shift(RK, 1), shift(RK, -1), shift(RK, 2), shift(RK, -2)], axis=2)
    return RK, np.concatenate([RK, RAW, mu, sd, nb], axis=2), U


RKd, R4d, Ud = build(Td)
RKf, R4f, Uf = build(Tf)
usd = Ud.reshape(-1, Ud.shape[2]).std(0) + 1e-6
Gd = np.stack([d["y_grade"].to_numpy(int) for d in Td])
Yd = np.stack([d["y_mr"].to_numpy(np.float32) for d in Td])
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def fit_lgb(Xd, Xf, **over):
    m = lgb.train(dict(P, **over), lgb.Dataset(Xd.reshape(-1, Xd.shape[2]), Gd.reshape(-1), group=[100] * len(Vd)), 300)
    return m.predict(Xf.reshape(-1, Xf.shape[2])).reshape(len(Vf), 100)


R4U_d, R4U_f = np.concatenate([R4d, Ud / usd], axis=2), np.concatenate([R4f, Uf / usd], axis=2)
pred = {"R0": fit_lgb(RKd, RKf), "R4": fit_lgb(R4d, R4f), "U": fit_lgb(R4U_d, R4U_f),
        "H4": fit_lgb(R4d, R4f, feature_fraction=0.3), "H8": fit_lgb(R4d, R4f, extra_trees=True)}
cfg_gru = ("GRU128_mse_d3", "gru", 128, "mse", 0.3, False)
Xg_d, Xg_f = np.concatenate([RKd, Ud / usd], axis=2), np.concatenate([RKf, Uf / usd], axis=2)
gru = np.mean([dl.fit_predict(torch.tensor(Xg_d, device=dl.DEV), torch.tensor(Yd, device=dl.DEV),
                              torch.tensor(Xg_f, device=dl.DEV), cfg_gru, 42 + s) for s in range(3)], axis=0)
z = lambda a: (a - a.mean(1, keepdims=True)) / (a.std(1, keepdims=True) + 1e-9)  # noqa: E731
pred["E3"] = z(pred["U"]) + z(pred["H8"]) + z(gru)
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
R = {"azar": np.mean([ev(rng.random(Y.shape)) for _ in range(40)], axis=0), "calor_directo": ev(Y)}
for k, v in pred.items():
    R[k] = ev(v)
res = {"n_videos": len(Vf), "n_desarrollo": len(Vd),
       "metodos": {k: {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()), "lift": float(a[:, 2].mean())}
                   for k, a in R.items()}}
ref = R["R0"]
for k in ("R4", "U", "H4", "H8", "E3"):
    d = R[k][:, 1] - ref[:, 1]
    res[f"{k}_vs_R0"] = {"dif_F1": float(d.mean()), "mejor_en": int((d > 0).sum()),
                         "p_unilateral": float(stats.wilcoxon(R[k][:, 1], ref[:, 1], alternative="greater").pvalue),
                         "p_hit_McNemar": None}
    x, y = R[k][:, 0] > 0, ref[:, 0] > 0
    oa, ob = int((x & ~y).sum()), int((~x & y).sum())
    res[f"{k}_vs_R0"]["solo_modelo"], res[f"{k}_vs_R0"]["solo_R0"] = oa, ob
    if oa + ob:
        res[f"{k}_vs_R0"]["p_hit_McNemar"] = float(stats.binomtest(oa, oa + ob, 0.5, alternative="greater").pvalue)
json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
np.savez_compressed(OUT / "pred.npz", vids=np.array(Vf), **pred, gru=gru)
print(f"{'metodo':14s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}")
for k, v in res["metodos"].items():
    print(f"{k:14s} {v['hit5']:7.1%} {v['F1']:7.3f} {v['lift']:6.2f}")
print("\nvs R0 (unilateral; primaria R4 alfa=0.05, secundarias Bonferroni 0.0125):")
for k in ("R4", "U", "H4", "H8", "E3"):
    r = res[f"{k}_vs_R0"]
    print(f"  {k}: dif F1 {r['dif_F1']:+.4f} | mejor en {r['mejor_en']}/{len(Vf)} | p F1 = {r['p_unilateral']:.4f} | "
          f"acierto solo-modelo={r['solo_modelo']} solo-R0={r['solo_R0']} p = {r['p_hit_McNemar']}")


# ---- evidencia combinada cohorte 1 + cohorte 2 (Stouffer ponderado por raiz de n; declarada en D-065)
from scipy.stats import norm  # noqa: E402

c1 = json.loads((ROOT / "reports" / "confirmacion_fresca_D063" / "resultado.json").read_text(encoding="utf-8"))
n1, n2 = c1["n_videos"], len(Vf)
comb = {}
for k in ("R4", "E3"):
    p1 = c1[f"{k}_vs_R0"]["p_unilateral"]
    p2 = res[f"{k}_vs_R0"]["p_unilateral"]
    z1, z2 = norm.isf(p1), norm.isf(p2)
    w1, w2 = np.sqrt(n1), np.sqrt(n2)
    z = (w1 * z1 + w2 * z2) / np.sqrt(w1 ** 2 + w2 ** 2)
    comb[k] = {"p_cohorte1": p1, "p_cohorte2": p2, "z_combinado": float(z), "p_combinado": float(norm.sf(z)),
               "n1": n1, "n2": n2}
res["combinado_cohortes_1_y_2"] = comb
res["descriptiva_n_menor_40"] = bool(n2 < 40)
json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
print("\nEvidencia combinada (Stouffer, descriptiva):")
for k, v in comb.items():
    print(f"  {k}: p1={v['p_cohorte1']:.4f} (n={n1}) | p2={v['p_cohorte2']:.4f} (n={n2}) | combinado p={v['p_combinado']:.4f}")
if n2 < 40:
    print("AVISO: n < 40; resultado descriptivo segun D-065 (enmienda).")
