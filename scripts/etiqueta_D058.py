"""D-058: ingenieria de la etiqueta con LightGBM por bin (mismos videos/folds que D-054)."""
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

OUT = ROOT / "reports" / "etiqueta_D058"
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
    Y = np.stack([T[v]["y_mr"].to_numpy(np.float32) for v in vids])
    REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
    ST = np.stack([T[v]["start"].to_numpy() for v in vids])
    EN = np.stack([T[v]["end"].to_numpy() for v in vids])
    HEAT = [heat_intervals(corrected_graph(meta[v]["heatmap"])) for v in vids]
    assert np.allclose(Y, base["Y"])
    z = lambda a: (a - a.mean(1, keepdims=True)) / (a.std(1, keepdims=True) + 1e-9)  # noqa: E731
    med = np.stack([pd.Series(y).rolling(11, center=True, min_periods=1).median().to_numpy() for y in Y])
    rank10 = np.stack([np.minimum((pd.Series(y).rank(method="first").to_numpy() - 1) / 100 * 10, 9).astype(int) for y in Y])
    variants = {
        "T1_binario_relevante": ("binary", REL.astype(float)),
        "T2_regresion_calor_z": ("regression", z(Y)),
        "T3_regresion_prominencia": ("regression", z(Y - med)),
        "T4_lambdarank_10_grados": ("lambdarank", rank10),
        "T5_regresion_log_calor": ("regression", z(np.log(Y + 1e-3))),
    }
    folds = list(GroupKFold(10).split(np.arange(len(vids)), groups=chan))
    P0 = dict(learning_rate=0.05, num_leaves=15, min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7,
              bagging_freq=1, lambda_l2=10.0, num_threads=8, verbose=-1, seed=SEED, deterministic=True, force_row_wise=True)
    oof = {"T0_lambdarank_5_grados(ref)": base["LGBM_bin"]}
    for name, (obj, lab) in variants.items():
        o = np.zeros_like(Y)
        for tr, te in folds:
            p = dict(P0, objective=obj)
            if obj == "lambdarank":
                p.update(metric="ndcg", lambdarank_truncation_level=20, eval_at=[5])
                if lab.max() > 4:
                    p["label_gain"] = [2 ** g - 1 for g in range(int(lab.max()) + 1)]
            ds = lgb.Dataset(X[tr].reshape(-1, X.shape[2]), lab[tr].reshape(-1),
                             group=[100] * len(tr) if obj == "lambdarank" else None)
            m = lgb.train(p, ds, 300)
            o[te] = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
        oof[name] = o
        print(f"{name} listo ({time.time() - t0:.0f}s)", flush=True)

    def metrics(S):
        r = []
        for i in range(len(vids)):
            k = top_k_nms(ST[i], EN[i], S[i])
            r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                      float(Y[i][k].mean() / Y[i].mean())))
        return np.array(r)

    M = {k: metrics(v) for k, v in oof.items()}
    ref = M["T0_lambdarank_5_grados(ref)"]
    rows = []
    print(f"\n{'variante':30s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}  p(F1)   p(hit)", flush=True)
    for k, a in M.items():
        pf = ph = float("nan")
        if "(ref)" not in k:
            pf = float(stats.wilcoxon(a[:, 1], ref[:, 1]).pvalue)
            x, y = a[:, 0] > 0, ref[:, 0] > 0
            oa, ob = int((x & ~y).sum()), int((~x & y).sum())
            ph = float(stats.binomtest(oa, oa + ob, 0.5).pvalue) if oa + ob else float("nan")
        rows.append(dict(variante=k, hit5=float(a[:, 0].mean()), F1=float(a[:, 1].mean()), lift=float(a[:, 2].mean()),
                         p_F1=pf, p_hit=ph))
        print(f"{k:30s} {a[:, 0].mean():7.1%} {a[:, 1].mean():7.3f} {a[:, 2].mean():6.2f}  {pf:6.3f}  {ph:6.3f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "resultado.csv", index=False)
    np.savez_compressed(OUT / "oof.npz", vids=np.array(vids), **oof)
    print(f"total {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
