"""Bateria de metodos (D-050). EXPLORATORIO sobre el "desarrollo ampliado" = 121 de desarrollo
+ 352 de D-046 (473 videos). La confirmacion se hara en la cohorte fresca D-050.

Meta: encontrar la regla que mas "atina" (hit@5) sin perder F1 frente a la formula congelada.
Presupuesto declarado ANTES de correr: 9 modelos x 3 selecciones; Bonferroni sobre los 9 modelos.
Validacion: GroupKFold(10) por CANAL (ningun canal en entrenamiento y prueba a la vez).
Selecciones: "all" (todos los candidatos), "short" (<= 45 s), "short_q" (<= 45 s + inicio no colgado
y final completo). Todas las features son de contenido (sin posicion, sin HuBERT).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import PREFIXES, f1_temporal, heat_intervals, ndcg_at, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

OUT = ROOT / "reports" / "bateria_D050"
SEED, MAX_S, CTX_S = 42, 45.0, 90.0
ROUNDS = 300
MODELS = ["M1_lgbm_lambdarank", "M2_lgbm_regresion", "M3_lgbm_binario", "M4_ridge", "M5_logistica",
          "M6_lgbm_contexto", "M7_ensamble_formula_M1", "M8_ensamble_formula_M3", "M9_lgbm_contexto_binario"]
ALPHA = 0.05 / len(MODELS)


def local_mean(rk: np.ndarray, mid: np.ndarray) -> np.ndarray:
    near = (np.abs(mid[:, None] - mid[None, :]) <= CTX_S) & ~np.eye(len(mid), dtype=bool)
    cnt = near.sum(axis=1, keepdims=True)
    return np.where(cnt > 0, (near @ rk) / np.maximum(cnt, 1), rk)


def main():
    t0 = time.time()
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    fd, hd = cfg.path("processed") / "features" / "sentence", cfg.path("interim") / "heatmaps"
    dev = set(json.loads((ROOT / "reports" / "conjunto_desarrollo_D038.json").read_text(encoding="utf-8"))["video_ids"])
    rep = set(json.loads((ROOT / "reports" / "conjunto_humano_D040.json").read_text(encoding="utf-8"))["replica_independiente"])
    snap = ROOT / "reports" / "conjunto_manifest_previo_D050.json"      # universo previo a D-050
    allowed = set(json.loads(snap.read_text(encoding="utf-8"))["video_ids"])
    frozen = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]

    vids, feats_all = [], None
    V = {}
    for p in sorted(fd.glob("*.parquet")):
        v = p.stem
        if v in rep or v not in allowed or not (hd / f"{v}.json").exists():
            continue
        d = pd.read_parquet(p)
        meta = json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))
        if not meta.get("heatmap") or "y_relevant" not in d:
            continue
        fs = [c for c in d.columns if c.startswith(PREFIXES)]
        feats_all = fs if feats_all is None else [c for c in feats_all if c in fs]
        V[v] = (d, meta)
        vids.append(v)
    const = {f: np.mean([V[v][0][f].nunique() <= 1 for v in vids]) for f in feats_all}
    feats = [f for f in feats_all if const[f] < 0.2]
    print(f"{len(vids)} videos (desarrollo ampliado) | {len(feats)} features | {time.time()-t0:.0f}s")

    chan = np.array([V[v][1]["channel_id"] for v in vids])
    rows_X, rows_C, rows_y, rows_g, rows_rel, rows_v, info = [], [], [], [], [], [], {}
    for v in vids:
        d, meta = V[v]
        rk = d[feats].rank(pct=True).fillna(0.5).to_numpy()
        mid = ((d["start"] + d["end"]) / 2).to_numpy()
        lm = local_mean(rk, mid)
        rows_X.append(rk)
        rows_C.append(np.hstack([rk, lm]))
        rows_y.append(d["y_mr"].rank(pct=True).to_numpy() - 0.5)
        rows_g.append(d["y_grade"].to_numpy(int))
        rows_rel.append(d["y_relevant"].to_numpy(int))
        rows_v.append(np.full(len(d), v, dtype=object))
        info[v] = dict(st=d["start"].to_numpy(), en=d["end"].to_numpy(), ok=((d["f_starts_dangling"] == 0) & (d["f_ends_complete"] == 1)).to_numpy(),
                       heat=heat_intervals(corrected_graph(meta["heatmap"])), ymr=d["y_mr"].to_numpy(float),
                       grade=d["y_grade"].to_numpy(), rel=d["y_relevant"].to_numpy(int),
                       v0=rk[:, [feats.index(c) for c in frozen]] @ np.array(list(frozen.values())))
    X, XC = np.vstack(rows_X), np.vstack(rows_C)
    yr, yg, yb = np.concatenate(rows_y), np.concatenate(rows_g), np.concatenate(rows_rel)
    vid_row = np.concatenate(rows_v)
    sizes = {v: len(info[v]["st"]) for v in vids}
    print("matriz:", X.shape, "| contexto:", XC.shape)

    P = dict(learning_rate=0.05, num_leaves=15, min_data_in_leaf=200, feature_fraction=0.7, bagging_fraction=0.7,
             bagging_freq=1, lambda_l2=10.0, num_threads=8, verbose=-1, seed=SEED, deterministic=True, force_row_wise=True)
    preds = {m: np.zeros(len(X)) for m in MODELS}
    gkf = GroupKFold(n_splits=10)
    vid_chan = {v: c for v, c in zip(vids, chan)}
    row_chan = np.array([vid_chan[v] for v in vid_row])
    for fold, (tr, te) in enumerate(gkf.split(X, groups=row_chan)):
        t1 = time.time()
        trv = pd.unique(vid_row[tr])
        grp = [sizes[v] for v in trv]       # filas contiguas por video: vid_row esta ordenado por video
        # M1 lambdarank
        m = lgb.train({**P, "objective": "lambdarank", "metric": "ndcg", "lambdarank_truncation_level": 20},
                      lgb.Dataset(X[tr], yg[tr], group=grp), ROUNDS)
        preds["M1_lgbm_lambdarank"][te] = m.predict(X[te])
        # M2 regresion sobre rango del calor
        m = lgb.train({**P, "objective": "regression"}, lgb.Dataset(X[tr], yr[tr]), ROUNDS)
        preds["M2_lgbm_regresion"][te] = m.predict(X[te])
        # M3 binario y_relevant
        m = lgb.train({**P, "objective": "binary"}, lgb.Dataset(X[tr], yb[tr]), ROUNDS)
        preds["M3_lgbm_binario"][te] = m.predict(X[te])
        # M4 ridge
        A = X[tr].T @ X[tr] + 100.0 * np.eye(X.shape[1])
        beta = np.linalg.solve(A, X[tr].T @ (yr[tr] - yr[tr].mean()))
        preds["M4_ridge"][te] = X[te] @ beta
        # M5 logistica
        lr = LogisticRegression(C=0.05, max_iter=300).fit(X[tr], yb[tr])
        preds["M5_logistica"][te] = lr.decision_function(X[te])
        # M6 contexto lambdarank / M9 contexto binario
        m = lgb.train({**P, "objective": "lambdarank", "metric": "ndcg", "lambdarank_truncation_level": 20},
                      lgb.Dataset(XC[tr], yg[tr], group=grp), ROUNDS)
        preds["M6_lgbm_contexto"][te] = m.predict(XC[te])
        m = lgb.train({**P, "objective": "binary"}, lgb.Dataset(XC[tr], yb[tr]), ROUNDS)
        preds["M9_lgbm_contexto_binario"][te] = m.predict(XC[te])
        print(f"fold {fold+1}/10 listo ({time.time()-t1:.0f}s)")

    off = {}
    pos = 0
    for v in vids:
        off[v] = (pos, pos + sizes[v])
        pos += sizes[v]
    z = lambda a: (a - a.mean()) / (a.std() or 1.0)
    rng = np.random.default_rng(SEED)
    rows = []
    for v in vids:
        a, b = off[v]
        I = info[v]
        st, en = I["st"], I["en"]
        dur = en - st
        short, short_q = dur <= MAX_S, (dur <= MAX_S) & I["ok"]
        scores = {"V0_formula": I["v0"]}
        for m in MODELS[:6] + ["M9_lgbm_contexto_binario"]:
            scores[m] = preds[m][a:b]
        scores["M7_ensamble_formula_M1"] = z(I["v0"]) + z(preds["M1_lgbm_lambdarank"][a:b])
        scores["M8_ensamble_formula_M3"] = z(I["v0"]) + z(preds["M3_lgbm_binario"][a:b])
        mh = float(I["ymr"].mean())
        row = {"video_id": v, "channel_id": vid_chan[v]}

        def met(sc, mask):
            s = np.where(mask, sc - sc[mask].min() + 1.0, 0.0) if mask is not None else sc
            k = top_k_nms(st, en, s)
            return (float(I["rel"][k].max() > 0), f1_temporal([(st[i], en[i]) for i in k], I["heat"]),
                    float(I["ymr"][k].mean() / mh))
        for name, sc in scores.items():
            for sel, mask in (("all", None), ("short", short), ("shortq", short_q)):
                if mask is not None and mask.sum() < 5:
                    mask = None
                row[f"{name}|{sel}|hit"], row[f"{name}|{sel}|F1"], row[f"{name}|{sel}|lift"] = met(sc, mask)
        for sel, mask in (("all", None), ("short", short), ("shortq", short_q)):
            dr = [met(rng.random(len(st)), mask if (mask is None or mask.sum() >= 5) else None) for _ in range(30)]
            row[f"azar|{sel}|hit"], row[f"azar|{sel}|F1"], row[f"azar|{sel}|lift"] = np.mean(dr, axis=0)
        rows.append(row)
    pv = pd.DataFrame(rows)
    pv.to_csv(OUT / "por_video.csv", index=False, encoding="utf-8-sig")

    names = ["azar", "V0_formula"] + MODELS
    summ, lines = {}, []
    ref_hit = pv["V0_formula|short|hit"].to_numpy() > 0       # V1 (D-049)
    ref_f1 = pv["V0_formula|all|F1"].to_numpy()
    lines.append(f"{'metodo':28s} {'sel':7s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}   p(hit vs V1)  p(F1 vs V0)")
    for n in names:
        for sel in ("all", "short", "shortq"):
            h, f, l = (pv[f"{n}|{sel}|{k}"].mean() for k in ("hit", "F1", "lift"))
            e = {"hit5": float(h), "F1": float(f), "lift": float(l)}
            ph = pf = float("nan")
            if n not in ("azar",) and not (n == "V0_formula" and sel == "short"):
                a = pv[f"{n}|{sel}|hit"].to_numpy() > 0
                oa, ob = int((a & ~ref_hit).sum()), int((~a & ref_hit).sum())
                ph = float(stats.binomtest(oa, oa + ob, 0.5).pvalue) if oa + ob else float("nan")
                try:
                    pf = float(stats.wilcoxon(pv[f"{n}|{sel}|F1"], ref_f1).pvalue)
                except ValueError:
                    pass
            e.update(p_hit_vs_V1=ph, p_F1_vs_V0=pf)
            summ[f"{n}|{sel}"] = e
            lines.append(f"{n:28s} {sel:7s} {h:7.1%} {f:7.3f} {l:6.2f}   {ph:10.4f}   {pf:10.4f}")
    json.dump({"n_videos": len(vids), "n_canales": int(len(set(chan))), "alpha_bonferroni": ALPHA, "metodos": summ},
              open(OUT / "resumen.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n".join(lines))
    print(f"total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
