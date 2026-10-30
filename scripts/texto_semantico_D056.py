"""D-056: embeddings semanticos del habla por bin (+ HuBERT) con LightGBM y BiGRU por bin.

Mismos videos y folds que D-054 (comparacion pareada con reports/dl_secuencia_D054/oof.npz).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import scripts.dl_secuencia_D054 as dl  # noqa: E402
from scripts.reverse_engineering_formula import PREFIXES, f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.data.youtube_dataset import transcript_path  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402
from src.transcribe.whisper import Transcript  # noqa: E402

OUT = ROOT / "reports" / "texto_semantico_D056"
SEED = 42


def main():
    t0 = time.time()
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
    base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
    vids = [str(v) for v in base["vids"]]
    feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
    T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
    meta = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
    chan = np.array([meta[v]["channel_id"] for v in vids])
    X = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
    Ucols = [c for c in T[vids[0]].columns if c.startswith("u_")]
    U = np.stack([T[v][Ucols].fillna(0).to_numpy(np.float32) for v in vids])
    Y = np.stack([T[v]["y_mr"].to_numpy(np.float32) for v in vids])
    REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
    GRADE = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
    ST = np.stack([T[v]["start"].to_numpy() for v in vids])
    EN = np.stack([T[v]["end"].to_numpy() for v in vids])
    HEAT = [heat_intervals(corrected_graph(meta[v]["heatmap"])) for v in vids]
    assert np.allclose(Y, base["Y"]), "los videos no coinciden con D-054"

    emb_path = cfg.path("interim") / "bin_text_emb_D056.npy"
    if emb_path.exists():
        E = np.load(emb_path)
    else:
        from sentence_transformers import SentenceTransformer

        st_model = SentenceTransformer(cfg.keywords["embedding_model"], device="cuda" if torch.cuda.is_available() else "cpu")
        texts = []
        for v in vids:
            tr = Transcript.load(transcript_path(cfg, v, "base"))
            ws = tr.words
            starts = np.array([w.start for w in ws])
            for s, e in zip(T[v]["start"], T[v]["end"]):
                i0, i1 = np.searchsorted(starts, s, "left"), np.searchsorted(starts, e, "left")
                texts.append("".join(w.text for w in ws[i0:i1]).strip()[:1500])
        E = st_model.encode(texts, batch_size=256, normalize_embeddings=True, show_progress_bar=False)
        E = E.reshape(len(vids), 100, -1).astype(np.float32)
        np.save(emb_path, E)
    print(f"embeddings {E.shape} listos ({time.time() - t0:.0f}s)", flush=True)

    folds = list(GroupKFold(10).split(np.arange(len(vids)), groups=chan))
    P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
             min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
             num_threads=8, verbose=-1, seed=SEED, deterministic=True, force_row_wise=True)
    cfg_gru = ("GRU128_mse_d3", "gru", 128, "mse", 0.3, False)
    arms = {"base+texto": (True, False), "base+hubert": (False, True), "base+texto+hubert": (True, True)}
    oof = {}
    for arm, (use_t, use_u) in arms.items():
        lg = np.zeros_like(Y)
        gr = np.zeros_like(Y)
        for tr, te in folds:
            parts_tr, parts_te = [X[tr]], [X[te]]
            if use_t:
                pca = PCA(32, random_state=SEED).fit(E[tr].reshape(-1, E.shape[2]))
                f = lambda a: pca.transform(a.reshape(-1, E.shape[2])).reshape(a.shape[0], 100, 32).astype(np.float32)  # noqa: E731
                zt = f(E[tr])
                sd = zt.reshape(-1, 32).std(0) + 1e-6
                parts_tr.append(zt / sd)
                parts_te.append(f(E[te]) / sd)
            if use_u:
                sd = U[tr].reshape(-1, U.shape[2]).std(0) + 1e-6
                parts_tr.append(U[tr] / sd)
                parts_te.append(U[te] / sd)
            Xtr, Xte = np.concatenate(parts_tr, axis=2), np.concatenate(parts_te, axis=2)
            m = lgb.train(P, lgb.Dataset(Xtr.reshape(-1, Xtr.shape[2]), GRADE[tr].reshape(-1), group=[100] * len(tr)), 300)
            lg[te] = m.predict(Xte.reshape(-1, Xte.shape[2])).reshape(len(te), 100)
            gr[te] = dl.fit_predict(torch.tensor(Xtr, device=dl.DEV), torch.tensor(Y[tr], device=dl.DEV),
                                    torch.tensor(Xte, device=dl.DEV), cfg_gru, SEED)
        oof[f"LGBM|{arm}"], oof[f"GRU128|{arm}"] = lg, gr
        print(f"brazo {arm} listo ({time.time() - t0:.0f}s)", flush=True)
    oof["LGBM|base"], oof["GRU128|base"] = base["LGBM_bin"], base["GRU128_mse_d3"]

    def metrics(S):
        o = []
        for i in range(len(vids)):
            k = top_k_nms(ST[i], EN[i], S[i])
            o.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                      float(Y[i][k].mean() / Y[i].mean())))
        return np.array(o)

    M = {k: metrics(v) for k, v in oof.items()}
    rows = []
    print(f"\n{'modelo|brazo':28s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}  p(F1 vs base)  p(hit vs base)", flush=True)
    for k, a in M.items():
        model = k.split("|")[0]
        ref = M[f"{model}|base"]
        pf = ph = float("nan")
        if not k.endswith("|base"):
            pf = float(stats.wilcoxon(a[:, 1], ref[:, 1]).pvalue)
            x, y = a[:, 0] > 0, ref[:, 0] > 0
            oa, ob = int((x & ~y).sum()), int((~x & y).sum())
            ph = float(stats.binomtest(oa, oa + ob, 0.5).pvalue) if oa + ob else float("nan")
        rows.append(dict(modelo_brazo=k, hit5=float(a[:, 0].mean()), F1=float(a[:, 1].mean()), lift=float(a[:, 2].mean()),
                         p_F1_vs_base=pf, p_hit_vs_base=ph))
        print(f"{k:28s} {a[:, 0].mean():7.1%} {a[:, 1].mean():7.3f} {a[:, 2].mean():6.2f}  {pf:12.4f}  {ph:12.4f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "resultado.csv", index=False)
    np.savez_compressed(OUT / "oof.npz", vids=np.array(vids), **oof)
    print(f"total {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
