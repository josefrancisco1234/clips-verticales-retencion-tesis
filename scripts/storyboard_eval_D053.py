"""Evaluacion del piloto visual (D-053): ¿las features de storyboard mejoran V0 o LightGBM?

GroupKFold(10) por canal sobre los videos de desarrollo con storyboard. Presupuesto: 3 contrastes,
Bonferroni 0.05/3. No toca la cohorte fresca ni los videos de confirmacion previos.
"""
from __future__ import annotations

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
from scripts.reverse_engineering_formula import PREFIXES, f1_temporal, heat_intervals, partial_spearman, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

OUT = ROOT / "reports" / "piloto_visual_D053"
ALPHA = 0.05 / 3
VIS = ["v_motion_mean", "v_motion_max", "v_cut_rate", "v_bright_std", "v_edge_mean", "v_contrast_mean",
       "v_motion_cx", "v_edge_cx"]


def vis_features(d: pd.DataFrame, sb: np.lib.npyio.NpzFile) -> pd.DataFrame:
    fps = float(sb["fps"])
    n = int(sb["n"])
    diff, hdiff, edge, bright, contrast = (sb[k][:n] for k in ("diff", "hdiff", "edge", "bright", "contrast"))
    thr = np.quantile(hdiff, 0.85)
    st, en = d["start"].to_numpy(), d["end"].to_numpy()
    out = np.zeros((len(d), len(VIS)))
    mid = (st + en) / 2
    for i, (a, b) in enumerate(zip(st, en)):
        i0 = int(np.clip(np.floor(a * fps), 0, n - 2))
        i1 = int(np.clip(np.ceil(b * fps), i0 + 2, n))
        sl = slice(i0, i1)
        out[i, :6] = [diff[sl][1:].mean(), diff[sl][1:].max(), (hdiff[sl][1:] > thr).mean(),
                      bright[sl].std(), edge[sl].mean(), contrast[sl].mean()]
    near = (np.abs(mid[:, None] - mid[None, :]) <= 90) & ~np.eye(len(mid), dtype=bool)
    cnt = np.maximum(near.sum(axis=1), 1)
    out[:, 6] = out[:, 0] - (near @ out[:, 0]) / cnt
    out[:, 7] = out[:, 4] - (near @ out[:, 4]) / cnt
    return pd.DataFrame(out, columns=VIS, index=d.index)


def main():
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    fd, hd, sd = (cfg.path("processed") / "features" / "sentence", cfg.path("interim") / "heatmaps",
                  cfg.path("interim") / "storyboard")
    frozen = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
    dev = sorted(json.loads((ROOT / "reports" / "conjunto_desarrollo_D038.json").read_text(encoding="utf-8"))["video_ids"])
    vids, D = [], {}
    for v in dev:
        if not (sd / f"{v}.npz").exists():
            continue
        d = pd.read_parquet(fd / f"{v}.parquet")
        meta = json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))
        sb = np.load(sd / f"{v}.npz")
        if int(sb["n"]) < 20:
            continue
        D[v] = dict(d=d, meta=meta, vis=vis_features(d, sb))
        vids.append(v)
    feats = [c for c in D[vids[0]]["d"].columns if c.startswith(PREFIXES)]
    feats = [f for f in feats if all(f in D[v]["d"] for v in vids) and np.mean([D[v]["d"][f].nunique() <= 1 for v in vids]) < 0.2]
    print(f"{len(vids)} videos con storyboard | {len(feats)} features de contenido | {len(VIS)} visuales")

    chan = np.array([D[v]["meta"]["channel_id"] for v in vids])
    fi = {f: i for i, f in enumerate(feats)}
    Xc, Xv, yg, vrow, sizes = [], [], [], [], {}
    rho_c = pd.DataFrame(np.nan, index=feats, columns=vids)
    rho_v = pd.DataFrame(np.nan, index=VIS, columns=vids)
    for v in vids:
        d = D[v]["d"]
        rk = d[feats].rank(pct=True).fillna(0.5).to_numpy()
        rv = D[v]["vis"].rank(pct=True).fillna(0.5).to_numpy()
        y, pos = d["y_mr"].to_numpy(float), d["p_rel_pos"].to_numpy()
        for j, f in enumerate(VIS):
            rho_v.loc[f, v] = partial_spearman(rv[:, j], y, pos)
        Xc.append(rk), Xv.append(rv), yg.append(d["y_grade"].to_numpy(int))
        vrow.append(np.full(len(d), v, dtype=object))
        sizes[v] = len(d)
    Xc, Xv, yg, vrow = np.vstack(Xc), np.vstack(Xv), np.concatenate(yg), np.concatenate(vrow)
    wv0 = np.array([frozen[c] for c in frozen])
    cols_v0 = [fi[c] for c in frozen]

    P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
             min_data_in_leaf=200, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
             num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
    S = {k: np.zeros(len(Xc)) for k in ("V0", "vis_only", "V0+vis", "M1", "M1+vis")}
    vid_chan = dict(zip(vids, chan))
    row_chan = np.array([vid_chan[v] for v in vrow])
    sel_report = []
    for tr, te in GroupKFold(10).split(Xc, groups=row_chan):
        trv = pd.unique(vrow[tr])
        r = rho_v[list(trv)]
        ch = pd.Series({v: vid_chan[v] for v in trv})
        rc = r.T.groupby(ch).mean().T
        med = rc.median(axis=1)
        npos, nneg = (rc > 0).sum(axis=1), (rc < 0).sum(axis=1)
        p = pd.Series({f: stats.binomtest(int(max(npos[f], nneg[f])), int(npos[f] + nneg[f]), 0.5).pvalue for f in rc.index})
        wsel = med[(med.abs() >= 0.03) & (p < 0.05 / len(VIS))]
        sel_report.append({k: round(float(x), 3) for k, x in wsel.items()})
        jv = [VIS.index(f) for f in wsel.index]
        v0 = Xc[te][:, cols_v0] @ wv0
        vs = Xv[te][:, jv] @ wsel.to_numpy() if jv else np.zeros(len(te))
        S["V0"][te], S["vis_only"][te], S["V0+vis"][te] = v0, vs, v0 + vs
        grp = [sizes[v] for v in trv]
        m = lgb.train(P, lgb.Dataset(Xc[tr], yg[tr], group=grp), 300)
        S["M1"][te] = m.predict(Xc[te])
        Xa, Xb = np.hstack([Xc[tr], Xv[tr]]), np.hstack([Xc[te], Xv[te]])
        m = lgb.train(P, lgb.Dataset(Xa, yg[tr], group=grp), 300)
        S["M1+vis"][te] = m.predict(Xb)

    rng = np.random.default_rng(42)
    rows, pos_ = [], 0
    for v in vids:
        a, b = pos_, pos_ + sizes[v]
        pos_ = b
        d = D[v]["d"]
        st, en = d["start"].to_numpy(), d["end"].to_numpy()
        heat = heat_intervals(corrected_graph(D[v]["meta"]["heatmap"]))
        rel, mh = d["y_relevant"].to_numpy(), float(d["y_mr"].mean())
        r = {"video_id": v}
        for name, sc in S.items():
            k = top_k_nms(st, en, sc[a:b])
            r[f"{name}_hit"] = float(rel[k].max() > 0)
            r[f"{name}_F1"] = f1_temporal([(st[i], en[i]) for i in k], heat)
            r[f"{name}_lift"] = float(d["y_mr"].to_numpy()[k].mean() / mh)
        dr = [top_k_nms(st, en, rng.random(b - a)) for _ in range(100)]
        r["azar_hit"] = float(np.mean([rel[k].max() > 0 for k in dr]))
        r["azar_F1"] = float(np.mean([f1_temporal([(st[i], en[i]) for i in k], heat) for k in dr]))
        rows.append(r)
    pv = pd.DataFrame(rows)
    pv.to_csv(OUT / "por_video.csv", index=False, encoding="utf-8-sig")

    def cmp(a, b):
        x, y = pv[f"{a}_hit"].to_numpy() > 0, pv[f"{b}_hit"].to_numpy() > 0
        oa, ob = int((x & ~y).sum()), int((~x & y).sum())
        ph = float(stats.binomtest(oa, oa + ob, 0.5).pvalue) if oa + ob else float("nan")
        try:
            pf = float(stats.wilcoxon(pv[f"{a}_F1"], pv[f"{b}_F1"]).pvalue)
        except ValueError:
            pf = float("nan")
        return {"hit_a": float(x.mean()), "hit_b": float(y.mean()), "solo_a": oa, "solo_b": ob, "p_hit": ph,
                "F1_a": float(pv[f"{a}_F1"].mean()), "F1_b": float(pv[f"{b}_F1"].mean()), "p_F1": pf}
    res = {"n_videos": len(vids), "alpha": ALPHA,
           "medias": {k: {"hit": float(pv[f"{k}_hit"].mean()), "F1": float(pv[f"{k}_F1"].mean()),
                          "lift": float(pv.get(f"{k}_lift", pd.Series([np.nan])).mean())} for k in list(S) + ["azar"]},
           "V0+vis_vs_V0": cmp("V0+vis", "V0"), "M1+vis_vs_M1": cmp("M1+vis", "M1"), "vis_only_vs_azar": cmp("vis_only", "azar"),
           "features_visuales_elegidas_por_fold": sel_report}
    json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
