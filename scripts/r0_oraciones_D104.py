"""D-104: R0 (LightGBM LambdaRank) entrenado sobre ventanas de oraciones y medido UNA vez en los grupos de videos nuevos 1 y 2.

Variantes: R0-O (ventanas de 15 a 90 s) y R0-O45 (solo ventanas de 45 s o menos, como V1). Frente a azar, V0 y V1.
Guarda el modelo en models/r0_oraciones_D104.txt (+ meta) y los resultados en reports/r0_oraciones_D104/.
"""
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
fd, hd = cfg.path("processed") / "features" / "sentence", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "r0_oraciones_D104"
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
dev = [str(v) for v in np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)["vids"]]
W = json.load(open(ROOT / "models" / "formula_calor_D045.json", encoding="utf-8"))["weights"]
G1 = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca_D050.json").read_text(encoding="utf-8"))["video_ids"]
G2 = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca2_D065.json").read_text(encoding="utf-8"))["video_ids"]
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def rk(d):
    return d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32)


# ---- entrenamiento (444 videos de desarrollo, un video = un grupo)
X, Y, grp = [], [], []
for v in dev:
    p = fd / f"{v}.parquet"
    if not p.exists():
        continue
    d = pd.read_parquet(p)
    if any(f not in d for f in feats) or "y_grade" not in d:
        continue
    X.append(rk(d)); Y.append(d["y_grade"].to_numpy(int)); grp.append(len(d))
print(f"entrenamiento: {len(grp)} videos, {sum(grp)} ventanas", flush=True)
model = lgb.train(P, lgb.Dataset(np.vstack(X), np.concatenate(Y), group=grp), 300)
model.save_model(str(ROOT / "models" / "r0_oraciones_D104.txt"))
json.dump({"features": feats, "entrenado_con": len(grp), "decision": "D-104", "params": P, "rondas": 300},
          open(ROOT / "models" / "r0_oraciones_D104_meta.json", "w", encoding="utf-8"), indent=1)


# ---- evaluación única
def evaluar(ids, nombre):
    rng = np.random.default_rng(42)
    filas = []
    for v in ids:
        p, h = fd / f"{v}.parquet", hd / f"{v}.json"
        if not p.exists() or not h.exists():
            continue
        d = pd.read_parquet(p); meta = json.load(open(h, encoding="utf-8"))
        if not meta.get("heatmap") or any(c not in d for c in feats) or any(c not in d for c in W) or "y_relevant" not in d:
            continue
        st, en = d.start.to_numpy(), d.end.to_numpy(); short = (en - st) <= 45.0
        if short.sum() < 5:
            continue
        heat_iv = heat_intervals(corrected_graph(meta["heatmap"]))
        rel, ymr = d.y_relevant.to_numpy(), d.y_mr.to_numpy(); mh = float(d.y_mr.mean())
        s0 = d[list(W)].rank(pct=True).fillna(0.5).to_numpy() @ np.array(list(W.values()))
        r0 = model.predict(rk(d))

        def m(sc):
            k = top_k_nms(st, en, sc)
            return (float(rel[k].max() > 0), f1_temporal([(st[i], en[i]) for i in k], heat_iv), float(ymr[k].mean() / mh))
        cand = {"V0": s0, "V1": np.where(short, s0 - s0.min() + 1.0, 0.0), "R0-O": r0, "R0-O45": np.where(short, r0 - r0.min() + 1.0, 0.0)}
        r = {"video_id": v}
        for k, sc in cand.items():
            r[f"{k}_hit"], r[f"{k}_F1"], r[f"{k}_lift"] = m(sc)
        az = np.mean([m(rng.random(len(d))) for _ in range(100)], axis=0)
        r["azar_hit"], r["azar_F1"], r["azar_lift"] = az
        azc = np.mean([m(np.where(short, rng.random(len(d)), -1.0)) for _ in range(100)], axis=0)
        r["azar_corto_hit"], r["azar_corto_F1"], r["azar_corto_lift"] = azc
        filas.append(r)
    pv = pd.DataFrame(filas)
    pv.to_csv(OUT / f"por_video_{nombre}.csv", index=False, encoding="utf-8-sig")
    met = ["azar", "azar_corto", "V0", "V1", "R0-O", "R0-O45"]
    res = {"n_videos": len(pv), "hit5": {k: float(pv[f"{k}_hit"].mean()) for k in met},
           "F1": {k: float(pv[f"{k}_F1"].mean()) for k in met}, "lift": {k: float(pv[f"{k}_lift"].mean()) for k in met}}
    a, b = pv["R0-O45_hit"].to_numpy() > 0, pv["V1_hit"].to_numpy() > 0
    oa, ob = int((a & ~b).sum()), int((~a & b).sum())
    res["H_R0O_vs_V1_McNemar"] = {"solo_R0O45": oa, "solo_V1": ob,
                                  "p_unilateral": float(stats.binomtest(oa, oa + ob, 0.5, alternative="greater").pvalue) if oa + ob else None}
    res["F1_R0O45_vs_V1_wilcoxon_bilateral_p"] = float(stats.wilcoxon(pv["R0-O45_F1"], pv["V1_F1"]).pvalue)
    res["F1_dif_R0O45_menos_V1"] = float((pv["R0-O45_F1"] - pv["V1_F1"]).mean())
    return res


R = {"grupo_nuevo_1": evaluar(G1, "g1"), "grupo_nuevo_2": evaluar(G2, "g2")}
json.dump(R, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
for g, r in R.items():
    print(f"\n== {g} ({r['n_videos']} videos) ==")
    for k in ("azar", "azar_corto", "V0", "V1", "R0-O", "R0-O45"):
        print(f"{k:11s} acierto@5 {r['hit5'][k]:6.1%} | F1 {r['F1'][k]:.3f} | calor {r['lift'][k]:.2f}x")
    print("H-R0O (R0-O45 vs V1, McNemar):", r["H_R0O_vs_V1_McNemar"], "| F1 p bilateral", round(r["F1_R0O45_vs_V1_wilcoxon_bilateral_p"], 3),
          "| dif F1", round(r["F1_dif_R0O45_menos_V1"], 4))
