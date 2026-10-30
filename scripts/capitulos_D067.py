"""D-067 (exploratorio, desarrollo): capitulos de YouTube como senal de navegacion + ajuste del acierto por azar por video."""
from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import GroupKFold

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
T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
Y = base["Y"]
chan = np.array([M[v]["channel_id"] for v in vids])
has_ch = np.array([bool(M[v].get("chapters")) and len(M[v]["chapters"]) >= 3 for v in vids])


def chap_feats(v):
    """(inicio de capitulo dentro del bin, distancia en bins al inicio mas cercano, tiene capitulos)."""
    d = T[v]
    ch = M[v].get("chapters")
    if not ch or len(ch) < 3:
        return np.zeros((100, 3), np.float32)
    starts = np.array([c["start_time"] for c in ch if c["start_time"] > 1.0])
    bs, be = d["start"].to_numpy(), d["end"].to_numpy()
    inb = np.array([((starts >= s) & (starts < e)).any() for s, e in zip(bs, be)], dtype=np.float32)
    mid = (bs + be) / 2
    width = float(np.median(be - bs))
    dist = np.min(np.abs(mid[:, None] - starts[None, :]), axis=1) / width
    return np.stack([inb, np.minimum(dist, 10.0), np.ones(100)], axis=1).astype(np.float32)


CH = np.stack([chap_feats(v) for v in vids])
RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
G = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
ST = np.stack([T[v]["start"].to_numpy() for v in vids])
EN = np.stack([T[v]["end"].to_numpy() for v in vids])
HEAT = [heat_intervals(corrected_graph(M[v]["heatmap"])) for v in vids]

# ---- (1) el patron de pausas, ¿es solo un efecto de capitulos? (rho parcial controlando posicion y capitulo)
print("(1) rho parcial (controlando posicion) de las features clave con el calor, por tipo de video")
for name, sel in (("CON capitulos", has_ch), ("SIN capitulos", ~has_ch)):
    out = []
    for f in ("l_silence", "a_pause_ratio", "a_pitch_range", "a_speech_rate"):
        fi = feats.index(f)
        r = [partial_spearman(RK[i, :, fi], Y[i], T[vids[i]]["p_rel_pos"].to_numpy()) for i in np.where(sel)[0]]
        out.append(f"{f}: {np.nanmedian(r):+.3f}")
    print(f"    {name} (n={sel.sum()}): " + " | ".join(out))
print("    controlando ademas el inicio de capitulo (solo videos con capitulos):")
for f in ("l_silence", "a_pause_ratio"):
    fi = feats.index(f)
    r = []
    for i in np.where(has_ch)[0]:
        x, y = RK[i, :, fi], Y[i]
        c = CH[i, :, 0]
        if c.std() < 1e-6:
            continue
        zc = np.column_stack([np.ones(100), c])
        res = [v_ - zc @ np.linalg.lstsq(zc, v_, rcond=None)[0] for v_ in (stats.rankdata(x), stats.rankdata(y))]
        if res[0].std() > 1e-9 and res[1].std() > 1e-9:
            r.append(np.corrcoef(*res)[0, 1])
    print(f"      {f}: rho (sin efecto del inicio de capitulo) mediana {np.median(r):+.3f} (n={len(r)})")

# ---- (2) ¿aportan los capitulos al modelo? (LightGBM por bin, mismos folds que D-054)
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=4, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
Xc = np.concatenate([RK, CH], axis=2)
o = np.zeros_like(Y)
for tr, te in GroupKFold(10).split(np.arange(len(vids)), groups=chan):
    m = lgb.train(P, lgb.Dataset(Xc[tr].reshape(-1, Xc.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
    o[te] = m.predict(Xc[te].reshape(-1, Xc.shape[2])).reshape(len(te), 100)


def metr(S):
    r = []
    for i in range(len(vids)):
        k = top_k_nms(ST[i], EN[i], S[i])
        r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i])))
    return np.array(r)


mb, mc = metr(base["LGBM_bin"]), metr(o)
print("\n(2) LightGBM por bin: rangos (ref) frente a rangos + capitulos")
for name, sel in (("todos", np.ones(len(vids), bool)), ("con capitulos", has_ch), ("sin capitulos", ~has_ch)):
    d = mc[sel, 1] - mb[sel, 1]
    p = stats.wilcoxon(mc[sel, 1], mb[sel, 1]).pvalue if (d != 0).any() else float("nan")
    print(f"    {name:14s} (n={sel.sum():3d}): hit {mb[sel, 0].mean():.1%} -> {mc[sel, 0].mean():.1%} | "
          f"F1 {mb[sel, 1].mean():.3f} -> {mc[sel, 1].mean():.3f} (dif {d.mean():+.4f}, p = {p:.4f})")

# ---- (3) acierto ajustado por azar por video
print("\n(3) acierto frente al azar de ESE video (el 'acierto' depende de cuantos bins son destacados)")
h_rand = np.array([1 - comb(100 - int(REL[i].sum()), 5) / comb(100, 5) for i in range(len(vids))])
ex = mb[:, 0] - h_rand
q = pd.qcut(pd.Series([(Y[i] > 0.5).sum() for i in range(len(vids))]), 4, duplicates="drop")
df = pd.DataFrame({"q": q, "hit": mb[:, 0], "azar": h_rand, "exceso": ex})
print(df.groupby("q", observed=True).mean().round(3).to_string())
print(f"    exceso medio sobre el azar del propio video: {ex.mean():+.3f} (IC95 +-{1.96 * ex.std() / np.sqrt(len(ex)):.3f})")
