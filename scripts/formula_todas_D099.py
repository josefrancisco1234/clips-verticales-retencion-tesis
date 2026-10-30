"""D-099: fórmula con TODAS las variables (sin filtro de selección). Pesos = rho parcial de Spearman mediano con el calor (121 videos de desarrollo, D-045),
para las 68 variables candidatas; mismo protocolo que D-048/D-065 (clips candidatos, V1 = clips <= 45 s, top-5 con NMS), en las cohortes frescas 1 y 2.
Compara la fórmula de 17 variables (modelo de D-045) con la de todas, en versión 0/1 (producto) y continua. Una sola corrida."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms
from src.common.config import load_config
from src.ranking.labels import corrected_graph
from src.ranking.retention import formula_raw
cfg = load_config("configs/gpu.yaml"); fd, hd = cfg.path("processed") / "features" / "sentence", cfg.path("interim") / "heatmaps"
W17 = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
tab = pd.read_csv(ROOT / "reports" / "reverse_engineering_dev121" / "features_por_video_resumen.csv", encoding="utf-8-sig")
WALL = {r.feature: float(r.heat_rho_parcial_mediano) for r in tab.itertuples() if pd.notna(r.heat_rho_parcial_mediano)}
print(len(WALL), "variables candidatas con peso;", len(set(WALL) & set(W17)), "de las 17 incluidas")
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])
G = {"cohorte fresca 1": J("conjunto_confirmacion_fresca_D050.json"), "cohorte fresca 2": J("conjunto_confirmacion_fresca2_D065.json")}
FORM = {"17 variables": W17, "todas (%d)" % len(WALL): WALL}
out = {}
for g, ids in G.items():
    R = {(f, m, v): [] for f in FORM for m in ("0/1", "continuo") for v in ("V0", "V1")}
    n = 0
    for vid in sorted(ids):
        p = fd / f"{vid}.parquet"
        if not p.exists() or not (hd / f"{vid}.json").exists(): continue
        d = pd.read_parquet(p); meta = json.loads((hd / f"{vid}.json").read_text(encoding="utf-8"))
        if not meta.get("heatmap") or "y_relevant" not in d or any(c not in d for c in WALL): continue
        st, en = d.start.to_numpy(), d.end.to_numpy(); short = (en - st) <= 45.0
        if short.sum() < 5: continue
        n += 1
        heat = heat_intervals(corrected_graph(meta["heatmap"])); rel = d.y_relevant.to_numpy()
        def m(sc):
            k = top_k_nms(st, en, sc)
            return (float(rel[k].max() > 0), f1_temporal([(st[i], en[i]) for i in k], heat))
        for f, W in FORM.items():
            for mo, b in (("0/1", True), ("continuo", False)):
                s0 = formula_raw(d, W, b)
                R[(f, mo, "V0")].append(m(s0)); R[(f, mo, "V1")].append(m(np.where(short, s0 - s0.min() + 1.0, 0.0)))
    A = {k: np.array(x) for k, x in R.items()}
    out[g] = {"n": n}
    print(f"\n=== {g} (n={n})")
    for (f, mo, v), a in A.items():
        base = A[("17 variables", mo, v)]
        dF = a[:, 1] - base[:, 1]
        p = float(stats.wilcoxon(a[:, 1], base[:, 1]).pvalue) if (f != "17 variables" and np.any(dF != 0)) else None
        out[g][f"{f} | {mo} | {v}"] = {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()), "dF1_vs_17": float(dF.mean()), "p": p}
        print(f"  {f:16s} {mo:8s} {v}  hit@5 {a[:,0].mean():5.1%}  F1 {a[:,1].mean():.3f}" + (f"  dF1 vs 17 {dF.mean():+.4f} p={p:.3f}" if p is not None else ""))
(ROOT / "reports" / "formula_todas_D099.json").write_text(json.dumps({"pesos": WALL, **out}, ensure_ascii=False, indent=1), encoding="utf-8")
