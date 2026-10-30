"""Confirmacion unica (D-054) del modelo profundo de secuencia en la cohorte fresca de D-050.

Compara, en los mismos bins: azar, formula V0 congelada, LightGBM por bin (entrenado con el desarrollo
ampliado), modelo profundo congelado (models/dl_secuencia_D054.pt), calor directo y la fusion
"valida con el 20 % superior del calor y ordena por modelo". Sin reajuste.
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
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "replicacion_DL_D054"
OUT.mkdir(parents=True, exist_ok=True)
ck = torch.load(ROOT / "models" / "dl_secuencia_D054.pt", weights_only=False)
name, arch, h, loss, drop, cx = ck["config"]
feats = ck["features"]
w = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
fresh = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca_D050.json").read_text(encoding="utf-8"))["video_ids"]
snap = set(json.loads((ROOT / "reports" / "conjunto_manifest_previo_D050.json").read_text(encoding="utf-8"))["video_ids"])
rep = set(json.loads((ROOT / "reports" / "conjunto_humano_D040.json").read_text(encoding="utf-8"))["replica_independiente"])


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


# LightGBM por bin con el desarrollo ampliado (mismas condiciones que en D-054)
dev_ids = [p.stem for p in sorted(bd.glob("*.parquet")) if p.stem in snap and p.stem not in rep]
Vd, Td = load(dev_ids)
Xd = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in Td])
Gd = np.stack([d["y_grade"].to_numpy(int) for d in Td])
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
gbm = lgb.train(P, lgb.Dataset(Xd.reshape(-1, Xd.shape[2]), Gd.reshape(-1), group=[100] * len(Vd)), 300)

V, T = load(fresh)
print(f"cohorte fresca con bins y curva: {len(V)} videos | entrenamiento LGBM: {len(Vd)} videos", flush=True)
if len(V) < 5:
    print("insuficientes videos; se reintenta cuando termine la descarga")
    sys.exit(0)
X = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
Xt = torch.tensor(X, device=dl.DEV)
src = dl.add_cx(Xt) if cx else Xt
preds = []
for sd in ck["state_dicts"]:
    net = dl.Net(src.shape[2], arch, h, drop).to(dl.DEV)
    net.load_state_dict(sd)
    net.eval()
    acc = torch.zeros(len(V), 100, device=dl.DEV)
    cnt = torch.zeros_like(acc)
    with torch.no_grad():
        for s in range(0, 100 - dl.CROP + 1, 5):
            p = net(src[:, s:s + dl.CROP])
            p = (p - p.mean(1, keepdim=True)) / (p.std(1, keepdim=True) + 1e-6)
            acc[:, s:s + dl.CROP] += p
            cnt[:, s:s + dl.CROP] += 1
    preds.append((acc / cnt.clamp(min=1)).cpu().numpy())
S = np.mean(preds, axis=0)
L = gbm.predict(X.reshape(-1, X.shape[2])).reshape(len(V), 100)
V0 = X[:, :, [feats.index(c) for c in w]] @ np.array(list(w.values()))
Y = np.stack([d["y_mr"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in V]
thr = np.quantile(Y, 0.8, axis=1, keepdims=True)


def ev(sc):
    o = []
    for i in range(len(V)):
        k = top_k_nms(ST[i], EN[i], sc[i])
        o.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                  float(Y[i][k].mean() / Y[i].mean())))
    return np.array(o)


rng = np.random.default_rng(0)
R = {"azar": np.mean([ev(rng.random(Y.shape)) for _ in range(40)], axis=0), "formula_V0": ev(V0),
     "LightGBM_bin": ev(L), f"DL_{name}": ev(S), "calor_directo": ev(Y),
     "valida20_ordena_DL": ev(np.where(Y >= thr, S - S.min() + 1.0, 0.0))}
res = {"n_videos": len(V), "metodos": {k: {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()),
                                           "lift": float(a[:, 2].mean())} for k, a in R.items()}}
for a_, b_ in ((f"DL_{name}", "azar"), (f"DL_{name}", "formula_V0"), (f"DL_{name}", "LightGBM_bin")):
    res[f"{a_}_vs_{b_}_F1_wilcoxon_p"] = float(stats.wilcoxon(R[a_][:, 1], R[b_][:, 1]).pvalue)
json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
print(f"{'metodo':26s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}")
for k, d in res["metodos"].items():
    print(f"{k:26s} {d['hit5']:7.1%} {d['F1']:7.3f} {d['lift']:6.2f}")
for k, v in res.items():
    if k.endswith("_p"):
        print(k, round(v, 4))
