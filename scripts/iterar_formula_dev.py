"""Iteracion 1 del lazo "atinarle a la mayoria de videos" (D-048). EXPLORATORIO, solo desarrollo.

Meta operativa: que los top-5 clips de un video toquen un pico de retencion en la MAYORIA de
videos (hit@5 = al menos un clip con y_relevant == 1) y que el F1 temporal suba frente a la
formula congelada de D-045 (V0).

Presupuesto: 6 variantes (V1..V6) declaradas ANTES de correr; Bonferroni = 0.05 / 6.
Todo se evalua dejando afuera el CANAL del video evaluado. No se usan los 352 videos de
confirmacion de D-046 ni los 28 de la replica humana.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts.reverse_engineering_formula import (PREFIXES, f1_temporal, heat_intervals,  # noqa: E402
                                                 partial_spearman, safe_spearman, top_k_nms)
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

OUT = ROOT / "reports" / "iteracion_formula"
SEED, N_VARIANTS = 42, 6
ALPHA = 0.05 / N_VARIANTS
RIDGE_ALPHA = 100.0         # fijado a priori
MAX_DUR_S = 45.0            # V1
MIN_GAP_FRAC = 0.10         # V2: separacion minima entre clips = 10 % de la duracion del video
CX_RADIUS_S = 90.0          # V3


def top_k_div(st, en, scores, k, min_gap_s, overlap=0.30):
    order = np.argsort(-np.asarray(scores, float), kind="stable")
    keep = []
    for i in order:
        ok = True
        for j in keep:
            ov = max(0.0, min(en[i], en[j]) - max(st[i], st[j]))
            if ov / max(min(en[i] - st[i], en[j] - st[j]), 1e-9) > overlap:
                ok = False
                break
            if abs((st[i] + en[i]) / 2 - (st[j] + en[j]) / 2) < min_gap_s:
                ok = False
                break
        if ok:
            keep.append(i)
        if len(keep) == k:
            break
    return keep


def cx_matrix(rk: np.ndarray, mid: np.ndarray, radius: float) -> np.ndarray:
    """Contraste local: rango propio menos media de los vecinos a <= radius segundos."""
    near = (np.abs(mid[:, None] - mid[None, :]) <= radius) & ~np.eye(len(mid), dtype=bool)
    cnt = near.sum(axis=1, keepdims=True)
    mean_n = (near @ rk) / np.maximum(cnt, 1)
    return np.where(cnt > 0, rk - mean_n, 0.0)


def main():
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    dev = sorted(json.loads((ROOT / "reports" / "conjunto_desarrollo_D038.json").read_text(encoding="utf-8"))["video_ids"])
    fd, hd = cfg.path("processed") / "features" / "sentence", cfg.path("interim") / "heatmaps"
    frozen = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]

    D, feats_all = {}, None
    for v in dev:
        df = pd.read_parquet(fd / f"{v}.parquet")
        meta = json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))
        fs = [c for c in df.columns if c.startswith(PREFIXES)]
        feats_all = fs if feats_all is None else [c for c in feats_all if c in fs]
        D[v] = dict(df=df, meta=meta, bins=corrected_graph(meta["heatmap"]))
    frac = {f: np.mean([D[v]["df"][f].nunique() <= 1 for v in dev]) for f in feats_all}
    feats = [f for f in feats_all if frac[f] < 0.2]
    chan = {v: D[v]["meta"]["channel_id"] for v in dev}
    fi = {f: i for i, f in enumerate(feats)}
    print(f"{len(dev)} videos | {len(set(chan.values()))} canales | {len(feats)} features")

    rho = pd.DataFrame(np.nan, index=feats, columns=dev)
    X_all, y_all, vid_all = [], [], []
    for v in dev:
        d = D[v]["df"]
        rk = d[feats].rank(pct=True).fillna(0.5).to_numpy()
        D[v]["rk"] = rk
        pos = d["p_rel_pos"].to_numpy()
        y = d["y_mr"].to_numpy(float)
        for f in feats:
            rho.loc[f, v] = partial_spearman(rk[:, fi[f]], y, pos)
        X_all.append(rk)
        y_all.append(d["y_mr"].rank(pct=True).to_numpy() - 0.5)
        vid_all += [v] * len(d)
    X_all, y_all, vid_all = np.vstack(X_all), np.concatenate(y_all), np.array(vid_all)

    def weights_median(train, select=True):
        r = rho[train]
        ch = pd.Series({v: chan[v] for v in r.columns})
        rc = r.T.groupby(ch).mean().T
        med = rc.median(axis=1)
        if not select:
            return med
        npos, nneg = (rc > 0).sum(axis=1), (rc < 0).sum(axis=1)
        mx = np.maximum(npos, nneg)
        p = pd.Series({f: stats.binomtest(int(mx[f]), int(npos[f] + nneg[f]), 0.5).pvalue
                       for f in rc.index if npos[f] + nneg[f] > 0})
        sel = (med.abs() >= 0.05) & (p.reindex(med.index) < 0.05 / len(med))
        return med[sel.fillna(False)]

    cache, rng, rows = {}, np.random.default_rng(SEED), []
    for v in dev:
        c = chan[v]
        if c not in cache:
            tr = [x for x in dev if chan[x] != c]
            wsel = weights_median(tr, True)
            wall = weights_median(tr, False)
            m = np.isin(vid_all, tr)
            Xt, yt = X_all[m], y_all[m]
            A = Xt.T @ Xt + RIDGE_ALPHA * np.eye(Xt.shape[1])
            beta = np.linalg.solve(A, Xt.T @ (yt - yt.mean()))
            cache[c] = (wsel, wall, beta)
        wsel, wall, beta = cache[c]
        d, rk = D[v]["df"], D[v]["rk"]
        st, en = d["start"].to_numpy(), d["end"].to_numpy()
        mid, dur = (st + en) / 2, en - st
        heat_iv = heat_intervals(D[v]["bins"])
        mean_heat = float(d["y_mr"].mean())
        rel = d["y_relevant"].to_numpy()
        dv = float(D[v]["meta"]["duration"])
        idx = lambda names: [fi[n] for n in names]
        s0 = rk[:, idx(list(frozen))] @ np.array(list(frozen.values()))                       # V0 congelada D-045
        s_sel = rk[:, idx(list(wsel.index))] @ wsel.to_numpy() if len(wsel) else np.zeros(len(d))   # V0 re-ajustada LOCO
        cx = cx_matrix(rk, mid, CX_RADIUS_S)
        s_cx = cx[:, idx(list(frozen))] @ np.array(list(frozen.values()))
        z = lambda a: (a - a.mean()) / (a.std() or 1.0)
        variants = {
            "V0_formula_D045": (s0, None),
            "V1_solo_clips_cortos": (np.where(dur <= MAX_DUR_S, s0 - s0.min() + 1.0, 0.0), None),
            "V2_diversificar": (s0, MIN_GAP_FRAC * dv),
            "V3_contraste_local": (s_cx, None),
            "V4_todas_las_features": (rk @ wall.reindex(feats).fillna(0).to_numpy(), None),
            "V5_ridge": (rk @ beta, None),
            "V6_formula_mas_contraste": (z(s0) + z(s_cx), None),
        }
        row = {"video_id": v, "channel_id": c}
        for name, (sc, gap) in variants.items():
            keep = top_k_div(st, en, sc, 5, gap) if gap else top_k_nms(st, en, sc)
            row[f"{name}_F1"] = f1_temporal([(st[i], en[i]) for i in keep], heat_iv)
            row[f"{name}_lift"] = float(d["y_mr"].to_numpy()[keep].mean() / mean_heat)
            row[f"{name}_hit5"] = float(rel[keep].max() > 0)
        draws = []
        for _ in range(100):
            keep = top_k_nms(st, en, rng.random(len(d)))
            draws.append((f1_temporal([(st[i], en[i]) for i in keep], heat_iv),
                          float(d["y_mr"].to_numpy()[keep].mean() / mean_heat), float(rel[keep].max() > 0)))
        row["azar_F1"], row["azar_lift"], row["azar_hit5"] = np.mean(draws, axis=0)
        rows.append(row)
    pv = pd.DataFrame(rows)
    pv.to_csv(OUT / "iter1_por_video.csv", index=False, encoding="utf-8-sig")

    names = ["azar"] + list(variants)
    out = {"n_videos": len(dev), "alpha_bonferroni": ALPHA, "variantes": {}}
    print(f"\n{'variante':28s} {'F1':>7s} {'lift':>6s} {'hit@5':>7s}   vs V0: dif_F1  p      mejor_en")
    for n in names:
        f1, lf, ht = pv[f"{n}_F1"].mean(), pv[f"{n}_lift"].mean(), pv[f"{n}_hit5"].mean()
        entry = {"F1": float(f1), "lift": float(lf), "hit5": float(ht)}
        extra = ""
        if n not in ("azar", "V0_formula_D045"):
            a, b = pv[f"{n}_F1"].to_numpy(), pv["V0_formula_D045_F1"].to_numpy()
            try:
                p = float(stats.wilcoxon(a, b).pvalue)
            except ValueError:
                p = float("nan")
            entry.update(dif_F1_vs_V0=float((a - b).mean()), p_vs_V0=p, mejor_en=int((a > b).sum()),
                         significativa_bonferroni=bool(p < ALPHA))
            extra = f"   {entry['dif_F1_vs_V0']:+.3f}  {p:.4f}  {entry['mejor_en']}/{len(pv)}"
        out["variantes"][n] = entry
        print(f"{n:28s} {f1:7.3f} {lf:6.2f} {ht:7.1%}{extra}")
    json.dump(out, open(OUT / "iter1_resumen.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
