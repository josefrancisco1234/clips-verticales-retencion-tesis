"""Figura de la metodología: cómo se calculan los pesos, el puntaje y los KPI de evaluación (D-099).
Salida: reports/pipeline_kpis_D099.png"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
NL = chr(10)
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(7.6, 3.9), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
T = lambda s: s.replace("|", NL)


def panel(x, w, fc, ec, title):
    ax.add_patch(FancyBboxPatch((x, 0.05), w, 0.85, boxstyle="round,pad=0,rounding_size=0.008", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, 0.875, T(title), ha="center", va="top", fontsize=5.4, fontweight="bold", color="#1f2937", linespacing=1.15)


def box(x, y, w, h, title, body, ec, tc="#1f2937", fs=4.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.005", fc="white", ec=ec, lw=0.5))
    ax.text(x + w / 2, y + h - 0.012, title, ha="center", va="top", fontsize=4.6, fontweight="bold", color=tc)
    ax.text(x + w / 2, y + h - 0.047, T(body), ha="center", va="top", fontsize=fs, color="#374151", linespacing=1.28)


def arr(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color="#4b5563"))


ax.text(0.005, 0.985, "Cálculo de pesos, puntaje y KPI de evaluación", fontsize=6.4, style="italic", va="top", color="#111827")
# 1 pesos
X = [0.005, 0.145, 0.285, 0.425, 0.605, 0.775]
W = [0.125, 0.125, 0.125, 0.165, 0.155, 0.22]
panel(X[0], W[0], "#fbf0c8", "#d6b84e", "1. Pesos")
for i, (t, b) in enumerate((("Correlación", "Spearman parcial de|cada variable con el|calor, sin la posición"),
                            ("Mediana", "de 121 videos de|desarrollo"),
                            ("Filtro", "|ρ| ≥ 0.05 y prueba|de signos con|Bonferroni 0.05/68"),
                            ("Resultado", "17 pesos: peso = ρ|ej. pausas +0.1797|habla continua −0.1071"))):
    box(X[0] + 0.007, 0.70 - i * 0.16, W[0] - 0.014, 0.145, t, b, "#d6b84e", fs=3.9)
# 2 banderas y puntaje
panel(X[1], W[1], "#dcefdc", "#7cb87c", "2. Puntaje")
box(X[1] + 0.007, 0.665, W[1] - 0.014, 0.185, "Bandera", "1 si el percentil en|su video es ≥ 0.75,|si no, 0", "#7cb87c")
box(X[1] + 0.007, 0.43, W[1] - 0.014, 0.215, "Suma", "raw = Σ peso × bandera|ej. A: 0.1797 + 0.1478|+ 0.1022 + 0.0582|− 0.0976 = 0.3903", "#7cb87c", fs=3.8)
box(X[1] + 0.007, 0.15, W[1] - 0.014, 0.26, "Escala 0 a 99", "(raw − lo) / (hi − lo) × 99|lo = −0.4851|hi = +1.2399|ej. (0.3903 + 0.4851)|/ 1.7250 × 99 = 50", "#7cb87c", fs=3.8)
arr((X[0] + W[0] + 0.002, 0.5), (X[1] - 0.002, 0.5))
# 3 selección
panel(X[2], W[2], "#fde6cf", "#e8a05a", "3. Selección")
box(X[2] + 0.007, 0.665, W[2] - 0.014, 0.185, "Orden", "de mayor a menor|raw; solo ≤ 45 s", "#e8a05a")
box(X[2] + 0.007, 0.43, W[2] - 0.014, 0.215, "No máximos", "traslape ≤ 30 % del|clip más corto|(iomin 0.3)", "#e8a05a")
box(X[2] + 0.007, 0.15, W[2] - 0.014, 0.26, "Top 5", "los 5 clips con su|puntaje, aportes por|variable y desglose|Hook/Flow/Value", "#e8a05a")
arr((X[1] + W[1] + 0.002, 0.5), (X[2] - 0.002, 0.5))
# 4 etiquetas
panel(X[3], W[3], "#dbe7f5", "#7aa0cf", "4. Calificación con Most Replayed")
box(X[3] + 0.007, 0.665, W[3] - 0.014, 0.185, "Tramos calientes", "curva corregida > 0.5,|máximo 20 por video", "#7aa0cf")
box(X[3] + 0.007, 0.43, W[3] - 0.014, 0.215, "Grado 0 a 4", "cuantiles del calor de la|ventana dentro del video|(solo para NDCG y R0)", "#7aa0cf")
box(X[3] + 0.007, 0.15, W[3] - 0.014, 0.26, "Regla", "la curva solo califica,|nunca entra al sistema|ni a la fórmula", "#7aa0cf", tc="#7c2d12")
arr((X[2] + W[2] + 0.002, 0.5), (X[3] - 0.002, 0.5))
# 5 KPI
panel(X[4], W[4], "#f8dfe6", "#d489a2", "5. KPI por video")
box(X[4] + 0.007, 0.665, W[4] - 0.014, 0.185, "Acierto@5", "1 si algún clip toca un|tramo caliente, si no 0", "#d489a2")
box(X[4] + 0.007, 0.43, W[4] - 0.014, 0.215, "F1 temporal", "P = tiempo caliente ÷ tiempo|elegido; R = ÷ tiempo caliente|F1 = 2PR/(P+R), ej. 0.24", "#d489a2", fs=3.8)
box(X[4] + 0.007, 0.15, W[4] - 0.014, 0.26, "NDCG@10", "Σ grado/log₂(pos+1)|÷ el mejor orden posible", "#d489a2")
arr((X[3] + W[3] + 0.002, 0.5), (X[4] - 0.002, 0.5))
# 6 agregación y pruebas
panel(X[5], W[5], "#f2d5d0", "#c9776c", "6. Resultado e inferencia")
box(X[5] + 0.007, 0.665, 0.102, 0.185, "Promedio", "de los videos|vs azar 26.9 %", "#c9776c")
box(X[5] + 0.111, 0.665, 0.102, 0.185, "Pruebas", "Wilcoxon,|Bonferroni", "#c9776c")
box(X[5] + 0.007, 0.43, 0.206, 0.215, "Matriz de confusión (557 videos)", "TP 468 · FN 4039 · FP 2317 · TN 48 876|accuracy = (TP+TN)/total = 88.6 %|precision = TP/(TP+FP) = 16.8 %|recall = TP/(TP+FN) = 10.4 %", "#c9776c", fs=3.8)
box(X[5] + 0.007, 0.15, 0.206, 0.26, "Validación con 5 creadores", "SUS: impares (r − 1), pares (5 − r)|suma × 2.5, de 0 a 100|meta: mayor a 70 (Bangor, 2008)", "#c9776c", fs=3.8)
arr((X[4] + W[4] + 0.002, 0.5), (X[5] - 0.002, 0.5))
fig.savefig(ROOT / "reports" / "pipeline_kpis_D099.png", facecolor="white")
print("ok")
