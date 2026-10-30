"""D-098: costo medido de usar variables 0/1 en la formula V0 (17 pesos). Descriptivo, UNA sola corrida, sin elegir variantes: el umbral 0.75 lo fijo el autor.
Cohortes frescas 1 y 2 (tablas por bin de 35 s) + desarrollo. Compara percentil continuo vs 0/1 (con desempate continuo 1e-4)."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms
from src.common.config import load_config
from src.ranking.labels import corrected_graph
from src.ranking.retention import formula_raw
cfg = load_config("configs/gpu.yaml"); bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])
grupos = {"cohorte fresca 1": J("conjunto_confirmacion_fresca_D050.json"), "cohorte fresca 2": J("conjunto_confirmacion_fresca2_D065.json")}
grupos["desarrollo (443)"] = {p.stem for p in bd.glob("*.parquet")} - set().union(*grupos.values())
out = {}
for g, ids in grupos.items():
    R = {"continuo": [], "binario": [], "azar": []}
    rng = np.random.default_rng(0)
    for v in sorted(ids):
        p = bd / f"{v}.parquet"
        if not p.exists() or not (hd / f"{v}.json").exists(): continue
        d = pd.read_parquet(p)
        if len(d) != 100 or not all(k in d for k in W): continue
        heat = heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"]))
        st, en, rel = d["start"].to_numpy(), d["end"].to_numpy(), d["y_relevant"].to_numpy()
        for nom, S in (("continuo", formula_raw(d, W)), ("binario", formula_raw(d, W, True)), ("azar", rng.random(100))):
            k = top_k_nms(st, en, S)
            R[nom].append((float(rel[k].max() > 0), f1_temporal([(st[j], en[j]) for j in k], heat)))
    A = {k: np.array(x) for k, x in R.items()}
    n = len(A["continuo"])
    d = A["binario"][:, 1] - A["continuo"][:, 1]
    p = float(stats.wilcoxon(A["binario"][:, 1], A["continuo"][:, 1]).pvalue) if np.any(d != 0) else 1.0
    out[g] = {"n": n, **{k: {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean())} for k, a in A.items()}, "dif_F1_bin_menos_cont": float(d.mean()), "p_wilcoxon": p}
    print(f"{g} (n={n}): azar {A['azar'][:,0].mean():.1%}/{A['azar'][:,1].mean():.3f} | continuo {A['continuo'][:,0].mean():.1%}/{A['continuo'][:,1].mean():.3f} | binario {A['binario'][:,0].mean():.1%}/{A['binario'][:,1].mean():.3f} | dif F1 {d.mean():+.4f} p={p:.3f}")
Path(ROOT / "reports" / "costo_binario_D098.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
