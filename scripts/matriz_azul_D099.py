"""D-099: matriz de confusión de la Figura 6 en estilo notebook (imshow, Blues). Cifras de reports/tabla_clases_D099.json (557 videos)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
TP, FP, FN, TN = 468, 2317, 4039, 48876
cm = np.array([[TP, FN], [FP, TN]])
fig, ax = plt.subplots(figsize=(5.2, 4.2), dpi=200)
im = ax.imshow(cm, cmap="Blues")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]:,}".replace(",", " "), ha="center", va="center", fontweight="bold", fontsize=13, color="white" if cm[i, j] > cm.max() / 2 else "black")
ax.set_xticks([0, 1]); ax.set_xticklabels(["Elegida", "No elegida"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Caliente", "No caliente"], rotation=90, va="center")
ax.set_xlabel("Clase predicha"); ax.set_ylabel("Clase real")
ax.set_title("Matriz de confusión (557 videos, fórmula V1)")
fig.colorbar(im, ax=ax); fig.tight_layout()
fig.savefig(ROOT / "reports" / "matriz_confusion_azul_D099.png"); print("ok")
