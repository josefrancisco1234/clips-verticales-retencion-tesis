"""D-099: figuras de resultados en el estilo de un notebook de Python (matplotlib + scikit-learn), como pidió la profesora.
Matriz de confusión con mapa de calor azul, curva ROC con AUC y curva precisión-exhaustividad de las 100 ventanas de cada uno de los videos
que no se usaron para fijar la fórmula (V1: solo ventanas de hasta 45 s, solo contenido). Guarda también los arreglos para el notebook.
Salidas: reports/matriz_confusion_azul_D099.png, reports/roc_pr_D099.png, reports/ventanas_eval_D099.npz"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import auc, average_precision_score, confusion_matrix, precision_recall_curve, roc_curve

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402
from src.ranking.retention import formula_raw, load_formula  # noqa: E402

cfg = load_config("configs/gpu.yaml")
W = load_formula(ROOT / "models")["weights"]
dev = set(json.loads((ROOT / "reports" / "conjunto_desarrollo_D038.json").read_text(encoding="utf-8"))["video_ids"])
ids = sorted(p.stem for p in (cfg.path("processed") / "features" / "bin").glob("*.parquet") if p.stem not in dev)
Yt, Ys, Yp, Vid = [], [], [], []
for v in ids:
    hp = cfg.path("interim") / "heatmaps" / f"{v}.json"
    if not hp.exists():
        continue
    m = json.loads(hp.read_text(encoding="utf-8"))
    df = pd.read_parquet(cfg.path("processed") / "features" / "bin" / f"{v}.parquet")
    st, en, vals = corrected_graph(m["heatmap"])
    S, E = df.start.to_numpy(), df.end.to_numpy()
    raw = formula_raw(df, W)
    sel = top_k_nms(S, E, np.where((E - S) <= 45, raw, raw.min() - 10), k=5)
    hot_idx = np.nonzero(vals > 0.5)[0]
    hot_idx = hot_idx[np.argsort(vals[hot_idx])[::-1]][:20]
    if len(hot_idx) == 0:
        hot_idx = np.argsort(vals)[::-1][:5]
    hot = np.zeros(len(df), bool)
    for i in range(len(df)):   # ventana caliente: comparte tiempo con algún tramo caliente de la curva
        hot[i] = any(min(E[i], en[b]) - max(S[i], st[b]) > 0 for b in hot_idx)
    pred = np.zeros(len(df), bool)
    pred[sel] = True
    Yt.append(hot)
    Ys.append(np.where((E - S) <= 45, raw, raw.min() - 10))
    Yp.append(pred)
    Vid += [v] * len(df)
Yt, Ys, Yp = np.concatenate(Yt), np.concatenate(Ys), np.concatenate(Yp)
np.savez_compressed(ROOT / "reports" / "ventanas_eval_D099.npz", y_true=Yt, score=Ys, elegida=Yp, video=np.array(Vid))
print(len(set(Vid)), "videos;", len(Yt), "ventanas;", int(Yt.sum()), "calientes")

# --- matriz de confusión (filas = clase real, columnas = clase predicha), estilo notebook
cm = confusion_matrix(Yt, Yp, labels=[True, False])
clases_real, clases_pred = ["caliente", "no caliente"], ["elegida", "no elegida"]
fig, ax = plt.subplots(figsize=(5.4, 4.4), dpi=200)
im = ax.imshow(cm, cmap="Blues")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]:,}".replace(",", " "), ha="center", va="center", fontweight="bold", fontsize=12,
                color="white" if cm[i, j] > cm.max() * 0.5 else "black")
ax.set_xticks([0, 1]); ax.set_xticklabels(clases_pred)
ax.set_yticks([0, 1]); ax.set_yticklabels(clases_real, rotation=90, va="center")
ax.set_xlabel("Clase predicha"); ax.set_ylabel("Clase real")
ax.set_title(f"Matriz de confusión | {len(set(Vid))} videos | fórmula V1")
fig.colorbar(im, ax=ax)
fig.tight_layout()
fig.savefig(ROOT / "reports" / "matriz_confusion_azul_D099.png")
plt.close(fig)
print("matriz:", cm.tolist())

# --- ROC y precisión-exhaustividad
fpr, tpr, _ = roc_curve(Yt, Ys)
roc_auc = auc(fpr, tpr)
pr, rc, _ = precision_recall_curve(Yt, Ys)
ap = average_precision_score(Yt, Ys)
base = Yt.mean()
fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.6), dpi=200)
axs[0].plot(fpr, tpr, color="#1f4e79", lw=2, label=f"Fórmula V1 (AUC = {roc_auc:.3f})")
axs[0].plot([0, 1], [0, 1], "--", color="gray", label="Azar (AUC = 0.500)")
axs[0].set_xlabel("Tasa de falsos positivos"); axs[0].set_ylabel("Tasa de verdaderos positivos"); axs[0].set_title("Curva ROC")
axs[0].legend(loc="lower right", frameon=False); axs[0].grid(alpha=0.25)
axs[1].plot(rc, pr, color="#e8710a", lw=2, label=f"Fórmula V1 (AP = {ap:.3f})")
axs[1].axhline(base, ls="--", color="gray", label=f"Azar (AP = {base:.3f})")
axs[1].set_xlabel("Exhaustividad"); axs[1].set_ylabel("Precisión"); axs[1].set_title("Curva precisión-exhaustividad")
axs[1].legend(loc="upper right", frameon=False); axs[1].grid(alpha=0.25)
for a in axs:
    for sp in ("top", "right"):
        a.spines[sp].set_visible(False)
fig.tight_layout()
fig.savefig(ROOT / "reports" / "roc_pr_D099.png")
plt.close(fig)
json.dump({"videos": len(set(Vid)), "ventanas": int(len(Yt)), "calientes": int(Yt.sum()), "matriz": cm.tolist(), "auc": float(roc_auc), "ap": float(ap), "tasa_base": float(base)},
          open(ROOT / "reports" / "roc_pr_D099.json", "w", encoding="utf-8"), indent=1)
print(f"AUC={roc_auc:.3f}  AP={ap:.3f}  tasa base={base:.3f}")
