"""D-061 (A): ajuste fino y semillas sobre la representacion R4 (LightGBM por bin, mismos folds que D-054)."""
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
from scripts.representacion_D059 import shift  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

OUT = ROOT / "reports" / "r4_ajuste_D061"
SEED = 42


def main():
    t0 = time.time()
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
    base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
    r4o = np.load(ROOT / "reports" / "representacion_D059" / "oof.npz", allow_pickle=True)
    vids = [str(v) for v in base["vids"]]
    feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
    T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
    meta = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
    chan = np.array([meta[v]["channel_id"] for v in vids])
    RAW = np.nan_to_num(np.stack([T[v][feats].to_numpy(np.float32) for v in vids]), nan=0.0)
    RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
    Ucols = [c for c in T[vids[0]].columns if c.startswith("u_")]
    U = np.stack([T[v][Ucols].fillna(0).to_numpy(np.float32) for v in vids])
    Y = np.stack([T[v]["y_mr"].to_numpy(np.float32) for v in vids])
    GRADE = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
    REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
    ST = np.stack([T[v]["start"].to_numpy() for v in vids])
    EN = np.stack([T[v]["end"].to_numpy() for v in vids])
    HEAT = [heat_intervals(corrected_graph(meta[v]["heatmap"])) for v in vids]
    mu = RAW.mean(axis=1, keepdims=True).repeat(100, axis=1)
    sd = RAW.std(axis=1, keepdims=True).repeat(100, axis=1)
    nb = np.concatenate([shift(RK, 1), shift(RK, -1), shift(RK, 2), shift(RK, -2)], axis=2)
    R4 = np.concatenate([RK, RAW, mu, sd, nb], axis=2)
    folds = list(GroupKFold(10).split(np.arange(len(vids)), groups=chan))
    P0 = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
              min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
              num_threads=8, verbose=-1, seed=SEED, deterministic=True, force_row_wise=True)
    cfgs = {"H1_hojas7_400r": (dict(num_leaves=7), 400), "H2_hojas31": (dict(num_leaves=31), 300),
            "H3_min_data150": (dict(min_data_in_leaf=150), 300), "H4_ff0.3": (dict(feature_fraction=0.3), 300),
            "H5_ff0.5_500r": (dict(feature_fraction=0.5), 500), "H6_lr0.03_600r": (dict(learning_rate=0.03), 600),
            "H7_l2_50_400r": (dict(lambda_l2=50.0), 400), "H8_extra_trees": (dict(extra_trees=True), 300)}
    oof = {"R0_rango(ref)": base["LGBM_bin"], "R4_default": r4o["R4_todo"]}

    def run(X, params, rounds):
        o = np.zeros_like(Y)
        for tr, te in folds:
            m = lgb.train(params, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), GRADE[tr].reshape(-1), group=[100] * len(tr)), rounds)
            o[te] = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
        return o

    for name, (over, rounds) in cfgs.items():
        oof[name] = run(R4, dict(P0, **over), rounds)
        print(f"{name} listo ({time.time() - t0:.0f}s)", flush=True)
    zs = lambda a: (a - a.mean(1, keepdims=True)) / (a.std(1, keepdims=True) + 1e-9)  # noqa: E731
    seeds = [zs(run(R4, dict(P0, seed=s, bagging_seed=s, feature_fraction_seed=s), 300)) for s in (1, 2, 3, 4)]
    oof["S5_5_semillas"] = (zs(oof["R4_default"]) + sum(seeds)) / 5
    print(f"S5 listo ({time.time() - t0:.0f}s)", flush=True)
    Ur = U / (U.reshape(-1, U.shape[2]).std(0) + 1e-6)
    oof["U_R4+HuBERT"] = run(np.concatenate([R4, Ur], axis=2), P0, 300)
    print(f"U listo ({time.time() - t0:.0f}s)", flush=True)

    def metrics(S):
        r = []
        for i in range(len(vids)):
            k = top_k_nms(ST[i], EN[i], S[i])
            r.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                      float(Y[i][k].mean() / Y[i].mean())))
        return np.array(r)

    M = {k: metrics(v) for k, v in oof.items()}
    ref, r4 = M["R0_rango(ref)"], M["R4_default"]
    rows = []
    print(f"\n{'brazo':20s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}  p(F1 vs R0)  p(F1 vs R4)", flush=True)
    for k, a in M.items():
        p0 = p4 = float("nan")
        if k != "R0_rango(ref)":
            p0 = float(stats.wilcoxon(a[:, 1], ref[:, 1]).pvalue)
        if k not in ("R0_rango(ref)", "R4_default"):
            try:
                p4 = float(stats.wilcoxon(a[:, 1], r4[:, 1]).pvalue)
            except ValueError:
                pass
        rows.append(dict(brazo=k, hit5=float(a[:, 0].mean()), F1=float(a[:, 1].mean()), lift=float(a[:, 2].mean()),
                         p_vs_R0=p0, p_vs_R4=p4))
        print(f"{k:20s} {a[:, 0].mean():7.1%} {a[:, 1].mean():7.3f} {a[:, 2].mean():6.2f}  {p0:10.4f}  {p4:10.4f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "resultado.csv", index=False)
    np.savez_compressed(OUT / "oof.npz", vids=np.array(vids), **oof)
    print(f"total {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
