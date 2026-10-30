"""D-099: usar las 68 variables y filtrar cuáles cuentan en cada video (sin mirar la curva, que no existe para un video nuevo).
Variantes definidas ANTES de correr (una sola corrida, sin elegir con las cohortes):
  A  todas las 68 con su peso (referencia)
  B  global: solo las 34 de mayor |peso|
  C  por video: se descartan las variables degeneradas EN ESE VIDEO (menos de 20 valores distintos entre sus candidatos, o 90 % o más de empates con la moda)
  D  por video + peso: C y además |peso| >= mediana de |pesos|
  R  las 17 originales (referencia)
Pesos = rho parcial mediano de 121 videos de desarrollo (D-045). Protocolo D-048: clips candidatos, V1 = clips <= 45 s, 0/1 y continuo."""
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
med = float(np.median([abs(w) for w in WALL.values()]))
TOP34 = {f: w for f, w in WALL.items() if abs(w) >= med}
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])
G = {"cohorte fresca 1": J("conjunto_confirmacion_fresca_D050.json"), "cohorte fresca 2": J("conjunto_confirmacion_fresca2_D065.json")}
VAR = ["R 17 originales", "A todas (68)", "B top 34 por peso", "C por video: sin degeneradas", "D por video + peso >= mediana"]
def pesos(var, d):
    if var.startswith("R"): return W17
    if var.startswith("A"): return WALL
    if var.startswith("B"): return TOP34
    base = WALL if var.startswith("C") else TOP34
    ok = {}
    for f, w in base.items():
        x = d[f].to_numpy()
        vc = pd.Series(x).value_counts(normalize=True)
        if pd.Series(x).nunique() >= 20 and float(vc.iloc[0]) < 0.9: ok[f] = w
    return ok
out = {}
for g, ids in G.items():
    R = {(v, m): [] for v in VAR for m in ("0/1", "continuo")}
    kept = []
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
        for v in VAR:
            W = pesos(v, d)
            if v.startswith("C"): kept.append(len(W))
            for mo, b in (("0/1", True), ("continuo", False)):
                s0 = formula_raw(d, W, b); s1 = np.where(short, s0 - s0.min() + 1.0, 0.0)
                k = top_k_nms(st, en, s1)
                R[(v, mo)].append((float(rel[k].max() > 0), f1_temporal([(st[i], en[i]) for i in k], heat)))
    A = {k: np.array(x) for k, x in R.items()}
    out[g] = {"n": n, "variables_conservadas_C_mediana": float(np.median(kept)), "min": int(np.min(kept)), "max": int(np.max(kept))}
    print(f"\n=== {g} (n={n}); en C se conservan en mediana {np.median(kept):.0f} variables por video (rango {np.min(kept)}-{np.max(kept)})")
    for (v, mo), a in A.items():
        base = A[("R 17 originales", mo)]; dF = a[:, 1] - base[:, 1]
        p = float(stats.wilcoxon(a[:, 1], base[:, 1]).pvalue) if (not v.startswith("R") and np.any(dF != 0)) else None
        out[g][f"{v} | {mo}"] = {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()), "dF1_vs_17": float(dF.mean()), "p": p}
        print(f"  {v:34s} {mo:8s} hit@5 {a[:,0].mean():5.1%}  F1 {a[:,1].mean():.3f}" + (f"  dF1 vs 17 {dF.mean():+.4f} p={p:.3f}" if p is not None else ""))
(ROOT / "reports" / "filtro_por_video_D099.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
