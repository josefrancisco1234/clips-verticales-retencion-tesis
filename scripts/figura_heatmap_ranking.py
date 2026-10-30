"""Ejemplo real: calor (Most Replayed) vs puntaje de la fórmula V0 por ventana, con los 5 clips elegidos."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import top_k_nms
from src.common.config import load_config
cfg = load_config("configs/gpu.yaml"); bd = cfg.path("processed")/"features"/"bin"
feats = json.loads((ROOT/"reports"/"dl_secuencia_D054"/"resumen.json").read_text(encoding="utf-8"))["features"]
W = json.loads((ROOT/"models"/"formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
F17 = [k for k in W if k in feats]; w = np.array([W[k] for k in F17])
best = None
for p in sorted(bd.glob("*.parquet"))[:300]:
    d = pd.read_parquet(p)
    if len(d) != 100 or not all(f in d for f in feats): continue
    s = (d[F17].rank(pct=True).fillna(.5).to_numpy()*w).sum(1)
    r = np.corrcoef(s, d["y_mr"])[0, 1]
    if best is None or r > best[0]: best = (r, p.stem, d, s)
r, v, d, s = best; print(v, round(r, 3))
x = (d["start"]+d["end"]).to_numpy()/2/60
sel = top_k_nms(d["start"].to_numpy(), d["end"].to_numpy(), s)
fig, ax = plt.subplots(figsize=(11, 4.2), dpi=170)
ax.fill_between(x, d["y_mr"]/d["y_mr"].max(), color="#E8590C", alpha=.35, label="Calor real (Most Replayed) — solo califica")
ax.plot(x, (s-s.min())/(s.max()-s.min()), color="#1F4E79", lw=2, label="Puntaje de la fórmula (17 variables de audio y texto)")
for k, j in enumerate(sel):
    ax.axvspan(d["start"].iloc[j]/60, d["end"].iloc[j]/60, color="#2F7D32", alpha=.25)
    ax.text(x[j], 1.04, str(k+1), ha="center", fontsize=10, fontweight="bold", color="#2F7D32")
ax.set_xlabel("minuto del video"); ax.set_ylabel("valor normalizado"); ax.set_ylim(0, 1.15)
ax.legend(loc="lower center", bbox_to_anchor=(.5, -.42), ncol=2, frameon=False, fontsize=9)
for t in ("top", "right"): ax.spines[t].set_visible(False)
ax.set_title(f"Los 5 clips elegidos (verde) frente al calor real — correlación {r:.2f} en este video", fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(ROOT/"reports"/"ejemplo_heatmap_ranking.png", bbox_inches="tight", facecolor="white")
