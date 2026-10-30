"""Demo: prueba varios metodos sobre UN video (el del PPT) y dice en que rango queda el primer acierto. NO es evidencia de generalizacion."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import heat_intervals, top_k_nms
from src.common.config import load_config
from src.ranking.labels import corrected_graph
from src.ranking.retention import formula_raw, load_formula
vid = sys.argv[1] if len(sys.argv) > 1 else "-Gzz2LZGowU"
cfg = load_config("configs/gpu.yaml")
meta = json.loads((cfg.path("interim") / "heatmaps" / f"{vid}.json").read_text(encoding="utf-8"))
df = pd.read_parquet(cfg.path("processed") / "features" / "bin" / f"{vid}.parquet")
st, en, vals = corrected_graph(meta["heatmap"])
S, E = df.start.to_numpy(), df.end.to_numpy()
hot = heat_intervals((st, en, vals))
touch = lambda i: any(min(E[i], b) - max(S[i], a) > 0 for a, b in hot)
heat = np.array([vals[(en > S[i]) & (st < E[i])].mean() for i in range(len(df))])
f = load_formula(ROOT / "models"); raw = formula_raw(df, f["weights"])
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]; lgb = base["LGBM_bin"][vids.index(vid)]
rk = lambda x: pd.Series(x).rank(pct=True).to_numpy()
M = {"V0 formula": raw, "LightGBM fuera de fold": lgb, "V0+LGBM (rangos)": rk(raw) + rk(lgb)}
for q in (50, 20, 10):
    M[f"fusion: top {q}% calor, ordena por formula"] = np.where(heat >= np.percentile(heat, 100 - q), raw, -9)
M["calor directo (solo curva)"] = heat
print(f"Rango caliente real: {[(round(a/60,1), round(b/60,1)) for a,b in hot]} (min)")
print(f"{'metodo':46s} primer acierto en el puesto  clips que tocan el pico")
for k, s in M.items():
    top = top_k_nms(S, E, s, k=5); h = [r + 1 for r, i in enumerate(top) if touch(i)]
    print(f"{k:46s} {str(h[0]) if h else 'ninguno':>8s}                 {len(h)}/5")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(3, 1, figsize=(13, 7.2), sharex=True)
rows = [("1) Solo contenido: formula V0 (no ve la curva)", raw, "#1b9e77"),
        ("2) Fusion: el modelo propone, la curva valida (top 10% calor)", M["fusion: top 10% calor, ordena por formula"], "#7570b3"),
        ("3) Con curva: ordenar por calor (modo auto cuando hay heatmap)", heat, "#e6550d")]
mid = (st + en) / 2
for a, (t, s, c) in zip(ax, rows):
    a.fill_between(mid / 60, vals, color="#d9d9d9", step="mid"); a.plot(mid / 60, vals, color="#555", lw=1)
    top = top_k_nms(S, E, s, k=5)
    for r, i in enumerate(top, 1):
        a.axvspan(S[i] / 60, E[i] / 60, color=c, alpha=0.7)
        a.text((S[i] + E[i]) / 120, 1.06, f"#{r}", ha="center", fontsize=9, color=c, fontweight="bold")
    for x0, x1 in hot: a.axvspan(x0 / 60, x1 / 60, color="#d62728", alpha=0.18)
    n = sum(touch(i) for i in top)
    a.set_title(f"{t}  ->  {n}/5 clips tocan el pico real", fontsize=10, loc="left")
    a.set_ylim(0, 1.2); a.set_ylabel("calor")
ax[-1].set_xlabel("minuto del video (rojo = pico real de YouTube)")
fig.suptitle(meta["title"][:80], fontsize=11); plt.tight_layout()
out = ROOT / "reports" / "demo_video_ppt" / f"metodos_{vid}.png"; plt.savefig(out, dpi=130); print("Grafico:", out)
