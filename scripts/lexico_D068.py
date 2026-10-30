"""D-068: lexico de picos aprendido dentro de cada fold (sin fuga) como features para LightGBM por bin."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
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
from src.data.youtube_dataset import transcript_path  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402
from src.transcribe.whisper import Transcript  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
Y = base["Y"]
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
chan = np.array([M[v]["channel_id"] for v in vids])
lang = np.array(["es" if (M[v].get("language") or "en").startswith("es") else "en" for v in vids])
tok = re.compile(r"[a-záéíóúñü']{3,}")
BINWORDS = []                       # BINWORDS[i][b] = set de palabras del bin b del video i
for v in vids:
    tr = Transcript.load(transcript_path(cfg, v, "base"))
    starts = np.array([w.start for w in tr.words])
    st, en = T[v]["start"].to_numpy(), T[v]["end"].to_numpy()
    out = []
    for b in range(100):
        i0, i1 = np.searchsorted(starts, st[b], "left"), np.searchsorted(starts, en[b], "left")
        out.append(frozenset(tok.findall(" ".join(w.text for w in tr.words[i0:i1]).lower())))
    BINWORDS.append(out)
print("tokenizacion lista", flush=True)
TOP = np.argsort(-Y, axis=1)[:, :3]


def build_lexicon(train_idx, lg):
    P, R, npk, nrs = Counter(), Counter(), 0, 0
    for i in train_idx:
        if lang[i] != lg:
            continue
        top = set(TOP[i].tolist())
        for b in range(100):
            if b in top:
                P.update(BINWORDS[i][b])
                npk += 1
            else:
                R.update(BINWORDS[i][b])
                nrs += 1
    w = {}
    for word, c in P.items():
        if c < 15:
            continue
        a, bb = c / npk, (R.get(word, 0) + 1) / (nrs + 1)
        z = (a - bb) / np.sqrt(a * (1 - a) / npk + bb * (1 - bb) / nrs + 1e-12)
        if abs(z) > 2.0:
            w[word] = float(np.log(a / bb))
    return w


def lex_features(i, lex):
    f = np.zeros((100, 3), np.float32)
    for b in range(100):
        ws = [lex[w] for w in BINWORDS[i][b] if w in lex]
        if ws:
            arr = np.array(ws)
            f[b] = [arr.mean(), arr[arr > 0].sum(), arr[arr < 0].sum()]
    return f


RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
G = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
P0 = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
          min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
          num_threads=4, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
o = np.zeros_like(Y)
for k, (tr, te) in enumerate(GroupKFold(10).split(np.arange(len(vids)), groups=chan)):
    lex = {lg: build_lexicon(tr, lg) for lg in ("en", "es")}
    L = np.zeros((len(vids), 100, 3), np.float32)
    for i in list(tr) + list(te):
        L[i] = lex_features(i, lex[lang[i]])
    X = np.concatenate([RK, L], axis=2)
    m = lgb.train(P0, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
    o[te] = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
    print(f"fold {k + 1}/10 | palabras en lexico: en={len(lex['en'])} es={len(lex['es'])}", flush=True)

REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
ST = np.stack([T[v]["start"].to_numpy() for v in vids])
EN = np.stack([T[v]["end"].to_numpy() for v in vids])
HEAT = [heat_intervals(corrected_graph(M[v]["heatmap"])) for v in vids]


def met(S):
    r = []
    for i in range(len(vids)):
        k = top_k_nms(ST[i], EN[i], S[i])
        r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i])))
    return np.array(r)


mb, ml = met(base["LGBM_bin"]), met(o)
d = ml[:, 1] - mb[:, 1]
x, y = ml[:, 0] > 0, mb[:, 0] > 0
oa, ob = int((x & ~y).sum()), int((~x & y).sum())
print(f"\nR0: hit {mb[:, 0].mean():.1%} F1 {mb[:, 1].mean():.3f}  |  R0 + lexico: hit {ml[:, 0].mean():.1%} F1 {ml[:, 1].mean():.3f}")
print(f"dif F1 {d.mean():+.4f} | Wilcoxon bilateral p = {stats.wilcoxon(ml[:, 1], mb[:, 1]).pvalue:.4f} | "
      f"acierto solo-lexico={oa} solo-R0={ob} (McNemar p = {stats.binomtest(oa, oa + ob, 0.5).pvalue if oa + ob else float('nan'):.3f})")
