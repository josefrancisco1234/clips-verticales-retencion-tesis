"""D-059: representaciones de features por bin (absoluto, contexto de video, vecinos). LightGBM, mismos folds que D-054."""
from __future__ import annotations

import json
import sys
import time
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

OUT = ROOT / "reports" / "representacion_D059"
SEED = 42


def shift(a, k):
    """Desplaza k bins a lo largo del eje temporal replicando el borde (a: V,100,F)."""
    if k > 0:
        return np.concatenate([np.repeat(a[:, :1], k, axis=1), a[:, :-k]], axis=1)
    return np.concatenate([a[:, -k:], np.repeat(a[:, -1:], -k, axis=1)], axis=1)


def main():
    t0 = time.time()
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
    base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
    vids = [str(v) for v in base["vids"]]
    feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
    assert not any(f.startswith("p_") for f in feats)
    T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
    meta = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
    chan = np.array([meta[v]["channel_id"] for v in vids])
    RAW = np.stack([T[v][feats].to_numpy(np.float32) for v in vids])
    RAW = np.nan_to_num(RAW, nan=0.0)
    RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
    Y = np.stack([T[v]["y_mr"].to_numpy(np.float32) for v in vids])
    GRADE = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
    REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
    ST = np.stack([T[v]["start"].to_numpy() for v in vids])
    EN = np.stack([T[v]["end"].to_numpy() for v in vids])
    HEAT = [heat_intervals(corrected_graph(meta[v]["heatmap"])) for v in vids]
    assert np.allclose(Y, base["Y"])
    mu = RAW.mean(axis=1, keepdims=True).repeat(100, axis=1)
    sd = RAW.std(axis=1, keepdims=True).repeat(100, axis=1)
    nb = np.concatenate([shift(RK, 1), shift(RK, -1), shift(RK, 2), shift(RK, -2)], axis=2)
    arms = {"R1_rango+absoluto": np.concatenate([RK, RAW], axis=2),
            "R2_rango+contexto_video": np.concatenate([RK, mu, sd], axis=2),
            "R3_rango+vecinos": np.concatenate([RK, nb], axis=2),
            "R4_todo": np.concatenate([RK, RAW, mu, sd, nb], axis=2)}
    folds = list(GroupKFold(10).split(np.arange(len(vids)), groups=chan))
    P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
             min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
             num_threads=8, verbose=-1, seed=SEED, deterministic=True, force_row_wise=True)
    oof = {"R0_rango(ref)": base["LGBM_bin"]}
    for name, Xa in arms.items():
        o = np.zeros_like(Y)
        for tr, te in folds:
            m = lgb.train(P, lgb.Dataset(Xa[tr].reshape(-1, Xa.shape[2]), GRADE[tr].reshape(-1), group=[100] * len(tr)), 300)
            o[te] = m.predict(Xa[te].reshape(-1, Xa.shape[2])).reshape(len(te), 100)
        oof[name] = o
        print(f"{name} listo ({time.time() - t0:.0f}s) con {Xa.shape[2]} columnas", flush=True)

    def metrics(S):
        r = []
        for i in range(len(vids)):
            k = top_k_nms(ST[i], EN[i], S[i])
            r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                      float(Y[i][k].mean() / Y[i].mean())))
        return np.array(r)

    M = {k: metrics(v) for k, v in oof.items()}
    ref = M["R0_rango(ref)"]
    rows = []
    print(f"\n{'brazo':28s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}  p(F1)   p(hit)", flush=True)
    for k, a in M.items():
        pf = ph = float("nan")
        if "(ref)" not in k:
            pf = float(stats.wilcoxon(a[:, 1], ref[:, 1]).pvalue)
            x, y = a[:, 0] > 0, ref[:, 0] > 0
            oa, ob = int((x & ~y).sum()), int((~x & y).sum())
            ph = float(stats.binomtest(oa, oa + ob, 0.5).pvalue) if oa + ob else float("nan")
        rows.append(dict(brazo=k, hit5=float(a[:, 0].mean()), F1=float(a[:, 1].mean()), lift=float(a[:, 2].mean()),
                         p_F1=pf, p_hit=ph))
        print(f"{k:28s} {a[:, 0].mean():7.1%} {a[:, 1].mean():7.3f} {a[:, 2].mean():6.2f}  {pf:6.3f}  {ph:6.3f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "resultado.csv", index=False)
    np.savez_compressed(OUT / "oof.npz", vids=np.array(vids), **oof)
    print(f"total {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
