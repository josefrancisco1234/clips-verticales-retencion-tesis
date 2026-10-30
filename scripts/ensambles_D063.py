"""D-063: ensambles por promedio de z-scores de predicciones fuera de fold ya calculadas (sin reentrenar)."""
import json
import sys
from pathlib import Path

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
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
a = np.load(ROOT / "reports" / "r4_ajuste_D061" / "oof.npz", allow_pickle=True)
b = np.load(ROOT / "reports" / "texto_semantico_D056" / "oof.npz", allow_pickle=True)
c = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in a["vids"]]
assert vids == [str(v) for v in b["vids"]] == [str(v) for v in c["vids"]]
T = {v: pd.read_parquet(bd / f"{v}.parquet", columns=["start", "end", "y_relevant", "y_mr"]) for v in vids}
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in vids]
z = lambda x: (x - x.mean(1, keepdims=True)) / (x.std(1, keepdims=True) + 1e-9)  # noqa: E731
U, H4, H8, R4 = a["U_R4+HuBERT"], a["H4_ff0.3"], a["H8_extra_trees"], a["R4_default"]
G, V0 = b["GRU128|base+hubert"], c["V0"]
E = {"U_R4+HuBERT (ref)": U,
     "E1_U + GRU_hubert": z(U) + z(G),
     "E2_R4 + H4 + H8": z(R4) + z(H4) + z(H8),
     "E3_U + H8 + GRU_hubert": z(U) + z(H8) + z(G),
     "E4_U + V0": z(U) + z(V0)}


def metrics(S):
    o = []
    for i, v in enumerate(vids):
        st, en = T[v].start.to_numpy(), T[v].end.to_numpy()
        k = top_k_nms(st, en, S[i])
        o.append((float(T[v].y_relevant.to_numpy()[k].max() > 0), f1_temporal([(st[j], en[j]) for j in k], HEAT[i]),
                  float(T[v].y_mr.to_numpy()[k].mean() / T[v].y_mr.mean())))
    return np.array(o)


M = {k: metrics(v) for k, v in E.items()}
ref = M["U_R4+HuBERT (ref)"]
print(f"{'ensamble':26s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}  p(F1 vs U)  p(hit vs U)")
for k, m in M.items():
    pf = ph = float("nan")
    if "(ref)" not in k:
        pf = float(stats.wilcoxon(m[:, 1], ref[:, 1]).pvalue)
        x, y = m[:, 0] > 0, ref[:, 0] > 0
        oa, ob = int((x & ~y).sum()), int((~x & y).sum())
        ph = float(stats.binomtest(oa, oa + ob, 0.5).pvalue) if oa + ob else float("nan")
    print(f"{k:26s} {m[:, 0].mean():7.1%} {m[:, 1].mean():7.3f} {m[:, 2].mean():6.2f}  {pf:9.4f}  {ph:9.4f}")
