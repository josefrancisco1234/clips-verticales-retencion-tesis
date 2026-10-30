"""Instancias por clase y métricas por clase (tabla tipo classification_report de scikit-learn) para la matriz de confusión por ventana
de los 557 videos de evaluación (TP, FP, FN, TN tomados de la Tabla 8 del artículo v22). Salida: reports/tabla_clases_D099.json."""
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import classification_report

ROOT = Path(__file__).resolve().parent.parent
TP, FP, FN, TN = 468, 2317, 4039, 48876
y = np.r_[np.ones(TP + FN, int), np.zeros(FP + TN, int)]
p = np.r_[np.ones(TP, int), np.zeros(FN, int), np.ones(FP, int), np.zeros(TN, int)]
r = classification_report(y, p, target_names=["No caliente", "Caliente"], output_dict=True, digits=3)
out = {k: {m: float(v) for m, v in r[k].items()} for k in ("No caliente", "Caliente", "macro avg")}
out["exactitud"] = float(r["accuracy"])
out["pct_caliente"] = float((TP + FN) / len(y))
Path(ROOT / "reports" / "tabla_clases_D099.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))

# salida de Python como imagen (tipo celda de Jupyter) para pegarla en el informe
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
txt = classification_report(y, p, target_names=["No caliente", "Caliente"], digits=3)
fig = plt.figure(figsize=(5.4, 1.75), dpi=200)
fig.patch.set_facecolor("#f7f7f7")
fig.text(0.03, 0.93, txt, family="monospace", fontsize=9.5, va="top", ha="left", color="#222222")
fig.savefig(ROOT / "reports" / "tabla_clases_D099.png", facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.15)
