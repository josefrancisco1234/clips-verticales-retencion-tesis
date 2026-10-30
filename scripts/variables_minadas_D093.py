"""D-093 (exploratorio, desarrollo): 4 variables propuestas por el minero de papers (prefijo m_) y su efecto sobre R0 y M17. Preregistro en DECISIONES.md."""
import hashlib
import json
import re
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
ti, af = cfg.path("interim") / "transcripts" / "base", cfg.path("interim") / "audio_frames"
OUT = ROOT / "reports" / "variables_minadas_D093"
(OUT / "bin_m").mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
F17 = [k for k in W if k in feats]
MCOLS = ["m_repeat_rate", "m_filler_rate", "m_turn_pm", "m_cap_ratio"]
FILL = {"eh", "em", "mm", "mmm", "este", "bueno", "pues", "um", "uh", "like", "hmm", "erm"}
FILL2 = {("o", "sea"), ("you", "know"), ("i", "mean")}


def clean(w):
    return re.sub(r"[^\wáéíóúüñ']", "", w.lower())


def bin_m(words, a, hop, s, e):
    out = dict.fromkeys(MCOLS, np.nan)
    w = [x for x in words if s <= x[1] < e]
    dur_min = max((e - s) / 60.0, 1e-6)
    if len(w) >= 5:
        tk = [clean(x[0]) for x in w]
        rep = sum(1 for i in range(len(tk)) if tk[i] and any(tk[i] == tk[j] for j in range(max(0, i - 3), i)))
        out["m_repeat_rate"] = rep / len(tk)
        fl = sum(1 for t in tk if t in FILL) + sum(1 for i in range(len(tk) - 1) if (tk[i], tk[i + 1]) in FILL2)
        out["m_filler_rate"] = 100.0 * fl / len(tk)
        caps = 0
        for i, x in enumerate(w):
            t = x[0].strip()
            prev = w[i - 1][0].strip() if i else "."
            if t[:1].isupper() and prev[-1:] not in ".?!" and i > 0:
                caps += 1
        out["m_cap_ratio"] = caps / len(w)
        ini = np.array([x[1] for x in w])
        fin = np.array([x[2] for x in w])
        gaps = ini[1:] - fin[:-1]
        f0 = np.where(a["voiced"], a["f0_st"], np.nan)
        n = 0
        for g in np.nonzero(gaps >= 0.35)[0]:
            t0 = fin[g]
            i_b, i_a = int((t0 - 1.5) / hop), int((t0 + gaps[g] + 1.5) / hop)
            b = f0[max(i_b, 0):int(t0 / hop)]
            c = f0[int((t0 + gaps[g]) / hop):i_a]
            if np.isfinite(b).sum() > 5 and np.isfinite(c).sum() > 5 and abs(np.nanmedian(b) - np.nanmedian(c)) >= 2.5:
                n += 1
        out["m_turn_pm"] = n / dur_min
    return out


def compute_m(v):
    p = OUT / "bin_m" / f"{v}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    d = pd.read_parquet(bd / f"{v}.parquet")
    words = json.loads((ti / f"{v}.json").read_text(encoding="utf-8"))["words"]
    a = np.load(af / f"{v}.npz")
    hop = float(a["hop_s"])
    m = pd.DataFrame([bin_m(words, a, hop, float(r.start), float(r.end)) for r in d.itertuples()])
    m.to_parquet(p)
    return m


J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"]) if (ROOT / "reports" / f).exists() else set()  # noqa: E731
reservados = J("conjunto_confirmacion_fresca_D050.json") | J("conjunto_confirmacion_fresca2_D065.json") | J("conjunto_confirmacion_fresca3_D091.json")
reservados |= set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])
reservados |= J("conjunto_libres_D078.json") | J("conjunto_entrenamiento_extra_D071.json")  # se usan en confirmaciones posteriores
V, T, M, CH = [], [], [], []
for p in sorted(bd.glob("*.parquet")):
    v = p.stem
    if v in reservados or not (hd / f"{v}.json").exists() or not (ti / f"{v}.json").exists() or not (af / f"{v}.npz").exists():
        continue
    d = pd.read_parquet(p)
    if len(d) == 100 and all(f in d for f in feats):
        V.append(v)
        T.append(d)
        M.append(compute_m(v))
        CH.append(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["channel_id"])
CH = np.array(CH)
print(f"videos de desarrollo con variables m_: {len(V)}", flush=True)
G = np.stack([d["y_grade"].to_numpy(int) for d in T])
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
Y = np.stack([d["y_mr"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in V]
sel = [feats.index(k) for k in F17]
wv = np.array([W[feats[j]] for j in sel], np.float32)
RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
RM = np.stack([m[MCOLS].rank(pct=True).fillna(0.5).to_numpy(np.float32) for m in M])


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
    for tr, te in GroupKFold(10).split(np.arange(len(V)), groups=CH):
        m = lgb.train(P, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
        o[te] = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
    return o


def met(S):
    r = []
    for i in range(len(V)):
        k = top_k_nms(ST[i], EN[i], S[i])
        r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i])))
    return np.array(r)


res = {}
for name, X in {"R0": RK, "R0+M": np.concatenate([RK, RM], 2), "M17": X17, "M17+M": np.concatenate([X17, RM], 2)}.items():
    res[name] = met(cv(X))
    print(f"{name:7s} hit {res[name][:, 0].mean():.1%} F1 {res[name][:, 1].mean():.4f}", flush=True)
out = {"n_videos": len(V), "metodos": {k: {"hit5": float(v[:, 0].mean()), "F1": float(v[:, 1].mean())} for k, v in res.items()}}
for a, b in (("R0+M", "R0"), ("M17+M", "M17")):
    d = res[a][:, 1] - res[b][:, 1]
    x, y = res[a][:, 0] > 0, res[b][:, 0] > 0
    out[f"{a}_vs_{b}"] = {"dif_F1": float(d.mean()), "p_wilcoxon_bilateral": float(stats.wilcoxon(res[a][:, 1], res[b][:, 1]).pvalue),
                          "solo_a": int((x & ~y).sum()), "solo_b": int((~x & y).sum())}
    r = out[f"{a}_vs_{b}"]
    print(f"{a} vs {b}: dif F1 {d.mean():+.4f} p={r['p_wilcoxon_bilateral']:.4f} | acierto solo-{a}={r['solo_a']} solo-{b}={r['solo_b']}")
rho = {}
for c in MCOLS:
    r = []
    for v, m, t in zip(V, M, T):
        x, yv = m[c].to_numpy(float), t["y_mr"].to_numpy(float)
        ok = np.isfinite(x)
        if ok.sum() > 20 and np.std(x[ok]) > 0:
            r.append(stats.spearmanr(x[ok], yv[ok])[0])
    rho[c] = float(np.nanmedian(r))
out["rho_mediano_con_calor"] = rho
print("rho mediano con el calor (descriptivo):", {k: round(v, 3) for k, v in rho.items()})
json.dump(out, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
