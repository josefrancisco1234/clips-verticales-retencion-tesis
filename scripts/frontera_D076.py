"""D-076 (exploratorio, desarrollo): variables de FRONTERA entre segmentos (prefijo b_) sobre los 444 videos de D-054.

Calcula 10 variables por bin desde palabras con tiempos y cuadros de audio ya existentes (sin LLM, sin red) y compara
R0 + b_* contra R0, y M17 + b_* contra M17, con los mismos 10 folds por canal. Preregistro: docs/DECISIONES.md D-076.
"""
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
bd, hd, ti, af = (cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps",
                  cfg.path("interim") / "transcripts" / "base", cfg.path("interim") / "audio_frames")
OUT = ROOT / "reports" / "frontera_D076"
OUT.mkdir(parents=True, exist_ok=True)
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
BCOLS = ["b_max_gap", "b_gap_gt2_n", "b_edge_gap_in", "b_edge_gap_out", "b_f0_reset", "b_rms_dip",
         "b_onset_after_gap", "b_lowconf_ratio", "b_rate_change", "b_sent_end_gap"]


def smooth(x, n):
    k = np.ones(n) / n
    return np.convolve(x, k, mode="same")


def bin_feats(words, a, hop, s, e):
    """Variables de frontera de un bin [s, e) a partir de palabras [(texto, ini, fin, prob)] y cuadros de audio."""
    out = dict.fromkeys(BCOLS, np.nan)
    w = [x for x in words if s <= x[1] < e]
    dur = max(e - s, 1e-6)
    if len(w) >= 2:
        ini = np.array([x[1] for x in w])
        fin = np.array([x[2] for x in w])
        gaps = np.maximum(ini[1:] - fin[:-1], 0)
        out["b_max_gap"] = float(gaps.max())
        out["b_gap_gt2_n"] = float((gaps > 2).sum())
        out["b_edge_gap_in"] = float(max(ini[0] - s, 0))
        out["b_edge_gap_out"] = float(max(e - fin[-1], 0))
        out["b_lowconf_ratio"] = float(np.mean([x[3] < 0.6 for x in w]))
        mid = s + dur / 2
        n1, n2 = sum(1 for x in w if x[1] < mid), sum(1 for x in w if x[1] >= mid)
        out["b_rate_change"] = (n2 - n1) / (dur / 2)
        ends = [i for i, x in enumerate(w[:-1]) if x[0].strip()[-1:] in ".?!"]
        out["b_sent_end_gap"] = float(np.mean([max(ini[i + 1] - fin[i], 0) for i in ends])) if ends else 0.0
        j = int(gaps.argmax())
        t0 = fin[j]
    else:
        out["b_max_gap"] = dur
        out["b_edge_gap_in"] = out["b_edge_gap_out"] = dur
        out["b_gap_gt2_n"] = float(dur > 2)
        out["b_lowconf_ratio"] = out["b_rate_change"] = out["b_sent_end_gap"] = 0.0
        t0 = s + dur / 2
    i0, i1 = int(s / hop), max(int(e / hop), int(s / hop) + 2)
    rms = a["rms_z"][i0:i1]
    f0 = np.where(a["voiced"][i0:i1], a["f0_st"][i0:i1], np.nan)
    if len(rms) > 4:
        sm = smooth(rms, max(int(1.0 / hop), 1))
        out["b_rms_dip"] = float(np.median(sm) - sm.min())
        m = len(f0) // 2
        a1, a2 = f0[:m], f0[m:]
        if np.isfinite(a1).sum() > 5 and np.isfinite(a2).sum() > 5:
            out["b_f0_reset"] = float(abs(np.nanmedian(a1) - np.nanmedian(a2)))
        k0 = int((t0 - s) / hop)
        seg = rms[k0:k0 + int(2.0 / hop)]
        if len(seg):
            out["b_onset_after_gap"] = float(seg.max())
    return out


def compute_b(v):
    p = OUT / "bin_b" / f"{v}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    d = pd.read_parquet(bd / f"{v}.parquet")
    words = json.loads((ti / f"{v}.json").read_text(encoding="utf-8"))["words"]
    a = np.load(af / f"{v}.npz")
    hop = float(a["hop_s"])
    b = pd.DataFrame([bin_feats(words, a, hop, float(r.start), float(r.end)) for r in d.itertuples()])
    p.parent.mkdir(exist_ok=True)
    b.to_parquet(p)
    return b


M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
B = {v: compute_b(v) for v in vids}
print("variables b_ calculadas:", len(B), flush=True)
chan = np.array([M[v]["channel_id"] for v in vids])
G = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
ST = np.stack([T[v]["start"].to_numpy() for v in vids])
EN = np.stack([T[v]["end"].to_numpy() for v in vids])
Y = np.stack([T[v]["y_mr"].to_numpy() for v in vids])
HEAT = [heat_intervals(corrected_graph(M[v]["heatmap"])) for v in vids]
sel = [feats.index(k) for k in W if k in feats]
wv = np.array([W[feats[j]] for j in sel], np.float32)
RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
RB = np.stack([B[v][BCOLS].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])


def sh(x, k):
    o = np.roll(x, k, axis=1)
    if k > 0:
        o[:, :k] = 0.5
    else:
        o[:, k:] = 0.5
    return o


def rankrows(a):
    return np.apply_along_axis(lambda z: pd.Series(z).rank(pct=True).to_numpy(), 1, a)


raw = (RK[:, :, sel] * wv).sum(axis=2)
rr = rankrows(raw)[:, :, None].astype(np.float32)
X17 = np.concatenate([RK[:, :, sel], rr, sh(rr, 1), sh(rr, -1), sh(rr, 2), sh(rr, -2)], axis=2)
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def cv(X):
    o = np.zeros(Y.shape)
    for tr, te in GroupKFold(10).split(np.arange(len(vids)), groups=chan):
        m = lgb.train(P, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
        o[te] = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
    return o


def met(S):
    r = []
    for i in range(len(vids)):
        k = top_k_nms(ST[i], EN[i], S[i])
        r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i])))
    return np.array(r)


res = {}
for name, X in {"R0": RK, "R0+B": np.concatenate([RK, RB], 2), "M17": X17, "M17+B": np.concatenate([X17, RB], 2)}.items():
    res[name] = met(cv(X))
    print(f"{name:7s} hit {res[name][:, 0].mean():.1%} F1 {res[name][:, 1].mean():.4f}", flush=True)
out = {"n_videos": len(vids), "metodos": {k: {"hit5": float(v[:, 0].mean()), "F1": float(v[:, 1].mean())} for k, v in res.items()}}
for a, b in (("R0+B", "R0"), ("M17+B", "M17")):
    d = res[a][:, 1] - res[b][:, 1]
    x, y = res[a][:, 0] > 0, res[b][:, 0] > 0
    out[f"{a}_vs_{b}"] = {"dif_F1": float(d.mean()), "p_wilcoxon_bilateral": float(stats.wilcoxon(res[a][:, 1], res[b][:, 1]).pvalue),
                          "solo_a": int((x & ~y).sum()), "solo_b": int((~x & y).sum())}
    print(f"{a} vs {b}: dif F1 {d.mean():+.4f} p={out[f'{a}_vs_{b}']['p_wilcoxon_bilateral']:.4f} | acierto solo-{a}={out[f'{a}_vs_{b}']['solo_a']} solo-{b}={out[f'{a}_vs_{b}']['solo_b']}")
# descriptivo: rho parcial (sin controlar posicion de forma completa: rho dentro de video, mediana entre videos)
rho = {}
for c in BCOLS:
    r = []
    for v in vids:
        x, yv = B[v][c].to_numpy(float), T[v]["y_mr"].to_numpy(float)
        ok = np.isfinite(x)
        if ok.sum() > 20 and np.std(x[ok]) > 0:
            r.append(stats.spearmanr(x[ok], yv[ok])[0])
    rho[c] = float(np.nanmedian(r))
out["rho_mediano_con_calor"] = rho
print("rho mediano con el calor (descriptivo):", {k: round(v, 3) for k, v in rho.items()})
json.dump(out, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
