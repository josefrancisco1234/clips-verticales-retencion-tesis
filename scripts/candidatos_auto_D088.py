"""D-088: búsqueda automática de duración máxima y solapamiento de los clips candidatos. Preregistro en DECISIONES.md."""
import hashlib
import itertools
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
from scripts.reverse_engineering_formula import top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402

cfg = load_config("configs/gpu.yaml")
sd = cfg.path("processed") / "features" / "sentence"
OUT = ROOT / "reports" / "candidatos_auto_D088"
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])  # noqa: E731
reservados = J("conjunto_confirmacion_fresca_D050.json") | J("conjunto_confirmacion_fresca2_D065.json")
reservados |= set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])

V, T = [], []
for p in sorted(sd.glob("*.parquet")):
    if p.stem in reservados:
        continue
    d = pd.read_parquet(p)
    if len(d) >= 20 and all(f in d for f in feats):
        V.append(p.stem)
        T.append(d.reset_index(drop=True))
CH = np.array([str(d["channel_id"].iloc[0]) for d in T])
hold = np.array([int(hashlib.md5(c.encode()).hexdigest(), 16) % 5 == 0 for c in CH])
tr, te = np.where(~hold)[0], np.where(hold)[0]
print(f"videos={len(V)} | entrenamiento={len(tr)} | holdout={len(te)}", flush=True)
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15, min_data_in_leaf=50,
         feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, num_threads=8, verbose=-1, seed=42,
         deterministic=True, force_row_wise=True)


def rank_feats(d):
    return d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32)


XR = [rank_feats(d) for d in T]


def fit_predict(train_idx, test_idx):
    X = np.concatenate([XR[i] for i in train_idx])
    y = np.concatenate([T[i]["y_grade"].to_numpy(int) for i in train_idx])
    m = lgb.train(P, lgb.Dataset(X, y, group=[len(T[i]) for i in train_idx]), 300)
    return {i: m.predict(XR[i]) for i in test_idx}


def video_excess(i, score, max_dur, overlap, rng):
    d = T[i]
    ok = ((d["end"] - d["start"]) <= max_dur).to_numpy()
    if ok.sum() < 5:
        ok[:] = True
    st, en, rel = d["start"].to_numpy()[ok], d["end"].to_numpy()[ok], d["y_relevant"].to_numpy()[ok]
    sel = top_k_nms(st, en, score[ok], overlap=overlap)
    hit = float(rel[sel].max() > 0)
    az = np.mean([rel[top_k_nms(st, en, rng.random(len(st)), overlap=overlap)].max() > 0 for _ in range(15)])
    return hit, float(az)


CONFIGS = list(itertools.product((30, 45, 60, 90), (0.0, 0.3, 0.5)))
# ---- selección interna (3 particiones por canal dentro del entrenamiento)
oof = {}
for a, b in GroupKFold(3).split(tr, groups=CH[tr]):
    oof.update(fit_predict(tr[a], tr[b]))
inner = {}
for cfgk in CONFIGS:
    rng = np.random.default_rng(0)
    ex = [np.subtract(*video_excess(i, oof[i], *cfgk, rng)) for i in tr]
    inner[cfgk] = float(np.mean(ex))
    print(f"  max_dur={cfgk[0]:3d}s solape={cfgk[1]:.1f} -> exceso interno {inner[cfgk]:+.3f}", flush=True)
best = max(inner, key=inner.get)
default = (45, 0.3)
print("elegida:", best, "| V1 fija:", default)
# ---- holdout: una sola evaluación
pr = fit_predict(tr, te)
rng = np.random.default_rng(1)
res = {}
for name, c in (("elegida", best), ("V1_fija", default)):
    rows = [video_excess(i, pr[i], *c, rng) for i in te]
    res[name] = np.array(rows)
    h, az = res[name][:, 0].mean(), res[name][:, 1].mean()
    print(f"{name:8s} {c}: hit@5 {h:.1%} | azar restringido {az:.1%} | exceso {h - az:+.3f}")
ex_b, ex_d = res["elegida"][:, 0] - res["elegida"][:, 1], res["V1_fija"][:, 0] - res["V1_fija"][:, 1]
p = 1.0 if best == default or not np.any(ex_b != ex_d) else float(stats.wilcoxon(ex_b, ex_d).pvalue)
print(f"elegida vs V1 fija: dif exceso {ex_b.mean() - ex_d.mean():+.4f} | Wilcoxon bilateral p = {p:.3f}")
json.dump({"n_train": len(tr), "n_holdout": len(te), "interno": {f"{k[0]}_{k[1]}": v for k, v in inner.items()}, "elegida": list(best),
           "holdout": {k: {"hit5": float(v[:, 0].mean()), "azar_restringido": float(v[:, 1].mean())} for k, v in res.items()},
           "dif_exceso": float(ex_b.mean() - ex_d.mean()), "p": p}, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
