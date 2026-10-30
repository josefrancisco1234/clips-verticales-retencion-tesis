"""D-099: ¿cuántas variables conviene usar? Fórmula de suma ponderada con las N variables de mayor |peso| (peso = rho parcial de Spearman mediano
por canal, controlando la posición, ajustado SOLO con los 121 videos de desarrollo D-038), evaluada en las cohortes frescas 1 y 2 (fuera de muestra).
Modelo 0/1 (producto) y continuo. Una sola corrida, sin elegir nada mirando la prueba. Salida: reports/curva_numero_variables_D099.json"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import PREFIXES, f1_temporal, heat_intervals, partial_spearman, top_k_nms
from src.common.config import load_config
from src.ranking.labels import corrected_graph
from src.ranking.retention import formula_raw
cfg = load_config("configs/gpu.yaml"); bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
W17 = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])
dev = sorted(J("conjunto_desarrollo_D038.json"))
c1, c2 = J("conjunto_confirmacion_fresca_D050.json"), J("conjunto_confirmacion_fresca2_D065.json")
# variables disponibles (no constantes) en las tablas por bin
tabs = {}
for v in dev:
    p = bd / f"{v}.parquet"
    if p.exists():
        d = pd.read_parquet(p)
        if len(d) == 100: tabs[v] = d
feats = [c for c in next(iter(tabs.values())).columns if c.startswith(PREFIXES)]
feats = [f for f in feats if np.mean([tabs[v][f].nunique() <= 1 for v in tabs]) < 0.2]
print(len(tabs), "videos de desarrollo con tabla;", len(feats), "variables")
chan = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["channel_id"] for v in tabs}
rho = pd.DataFrame(np.nan, index=feats, columns=list(tabs))
for v, d in tabs.items():
    y = d["y_mr"].to_numpy(float); pos = np.arange(100, dtype=float)
    if np.isnan(y).any(): continue
    for f in feats:
        rho.loc[f, v] = partial_spearman(d[f].rank(pct=True).fillna(0.5).to_numpy(), y, pos)
unit = rho.T.groupby(pd.Series(chan)).mean().T       # promedio por canal
Wall = unit.median(axis=1).dropna()
orden = Wall.abs().sort_values(ascending=False).index.tolist()
print("top 20 por |peso|:", [(f, round(float(Wall[f]), 3)) for f in orden[:20]])
solap = [f for f in W17 if f in orden[:17]]
print("coinciden con las 17 originales entre el top 17:", len(solap))
KS = [5, 10, 17, 25, 35, 50, len(orden)]
def evalset(ids, W, binario):
    out = []
    for v in sorted(ids):
        p = bd / f"{v}.parquet"
        if not p.exists() or not (hd / f"{v}.json").exists(): continue
        d = pd.read_parquet(p)
        if len(d) != 100 or not all(k in d for k in W): continue
        heat = heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"]))
        st, en, rel = d["start"].to_numpy(), d["end"].to_numpy(), d["y_relevant"].to_numpy()
        k = top_k_nms(st, en, formula_raw(d, W, binario))
        out.append((float(rel[k].max() > 0), f1_temporal([(st[j], en[j]) for j in k], heat)))
    return np.array(out)
res = {}
for gn, ids in (("cohorte fresca 1", c1), ("cohorte fresca 2", c2)):
    base = evalset(ids, W17, True)
    res[gn] = {"n": len(base), "17 originales (0/1)": {"hit5": float(base[:, 0].mean()), "F1": float(base[:, 1].mean())}}
    print(f"\n{gn} (n={len(base)})  17 originales 0/1: {base[:,0].mean():.1%} / {base[:,1].mean():.3f}")
    for k in KS:
        W = {f: float(Wall[f]) for f in orden[:k]}
        for modo, b in (("0/1", True), ("continuo", False)):
            a = evalset(ids, W, b)
            dF = a[:, 1] - base[:, 1]
            p = float(stats.wilcoxon(a[:, 1], base[:, 1]).pvalue) if np.any(dF != 0) else 1.0
            res[gn][f"top {k} | {modo}"] = {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()), "dF1_vs_17orig_01": float(dF.mean()), "p": p}
            print(f"  top {k:2d} {modo:8s} {a[:,0].mean():5.1%} / {a[:,1].mean():.3f}  dF1 vs 17orig(0/1) {dF.mean():+.4f} p={p:.3f}")
res["pesos_ajustados"] = {f: float(Wall[f]) for f in orden}
(ROOT / "reports" / "curva_numero_variables_D099.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
