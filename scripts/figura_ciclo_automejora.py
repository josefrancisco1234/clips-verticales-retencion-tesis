"""Figura del ciclo de mejora automática del sistema (para el artículo): datos -> ranking -> exploración automática -> promoción."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
AZUL, NARANJA, VERDE, MORADO, GRIS = "#1F4E79", "#E8590C", "#2F7D32", "#6A3D9A", "#555555"

fig, ax = plt.subplots(figsize=(13, 6.6), dpi=170)
ax.set_xlim(0, 100)
ax.set_ylim(0, 56)
ax.axis("off")
ax.text(50, 54.2, "Ciclo de mejora automática del sistema", ha="center", va="center", fontsize=15, fontweight="bold", color="#222")


def caja(x, y, w, h, color, num, titulo, lineas, tcolor="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=color, ec="none"))
    ax.text(x + 1.4, y + h - 1.9, f"{num}", fontsize=12, fontweight="bold", color=tcolor, va="center")
    ax.text(x + 4.2, y + h - 1.9, titulo, fontsize=10, fontweight="bold", color=tcolor, va="center")
    for i, ln in enumerate(lineas):
        ax.text(x + 1.6, y + h - 5.0 - i * 2.6, ln, fontsize=8.6, color=tcolor, va="center")


def flecha(a, b, color=GRIS, rad=0.0, estilo="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=estilo, mutation_scale=14, lw=1.6, color=color, connectionstyle=f"arc3,rad={rad}", linestyle=ls))


# fila 1: datos y ranking
ax.text(1, 49.2, "DATOS Y RANKING", fontsize=9.5, fontweight="bold", color=GRIS)
caja(1, 33.5, 29, 13.5, AZUL, "1", "Videos de YouTube", ["50+ consultas ES/EN, curva de retención", "ETL: yt-dlp → audio + curva", "cohortes frescas congeladas antes de mirar"])
caja(35.5, 33.5, 29, 13.5, AZUL, "2", "Base de datos (BD_TESIS)", ["Whisper: transcripción por palabra", "audio (librosa), eventos (PANNs), HuBERT", "71 variables por tramo y ventana"])
caja(70, 33.5, 29, 13.5, NARANJA, "3", "Ranking de clips", ["fórmula de 17 pesos (V0/V1)", "LightGBM LambdaRank (R0, campeón)", "5 clips con puntaje 0–99 y explicación"])
flecha((30.6, 40.2), (35.0, 40.2))
flecha((65.1, 40.2), (69.4, 40.2))

# fila 2: exploración automática
ax.text(1, 30.0, "EXPLORACIÓN AUTOMÁTICA", fontsize=9.5, fontweight="bold", color=GRIS)
caja(1, 12.5, 23, 15.5, MORADO, "4", "Minero de papers", ["OpenAlex: 1 339 trabajos 2020+", "señales medibles que mencionan", "las compara con las 71 variables", "→ variables candidatas nuevas"])
caja(27, 12.5, 23, 15.5, MORADO, "5", "Explorador de fórmulas", ["red de ecuaciones (EQL) con L1", "12 configuraciones por ronda", "validación interna por canal", "→ fórmulas legibles nuevas"])
caja(53, 12.5, 23, 15.5, VERDE, "6", "Campeón / retador", ["retador vs campeón en holdout", "Wilcoxon unilateral p < 0.05", "corrección por rondas múltiples", "→ ¿se promueve?"])
caja(79, 12.5, 20, 15.5, VERDE, "7", "Confirmación", ["una sola vez, cohorte fresca", "hipótesis escrita antes", "se reportan los negativos", "→ nuevo campeón o descarte"])
flecha((24.6, 20.2), (26.4, 20.2))
flecha((50.6, 20.2), (52.4, 20.2))
flecha((76.6, 20.2), (78.4, 20.2))

# conexiones entre filas
flecha((50, 33.0), (38, 28.9), MORADO, rad=-0.15)       # BD y ranking alimentan la exploración
flecha((82, 33.2), (62, 28.9), NARANJA, rad=0.2)      # campeón actual entra al retador
flecha((89, 12.0), (89, 6.2), VERDE)
flecha((89, 6.0), (15, 6.0), VERDE, estilo="-")
flecha((15, 6.0), (15, 32.8), VERDE, rad=0.0)
ax.text(52, 3.6, "si se confirma: nuevo campeón y reentrenamiento; siempre: más videos y una nueva ronda registrada en la bitácora (D-0NN)", ha="center", fontsize=9, color=VERDE, style="italic")
ax.text(1, 0.4, "La curva de retención solo califica; nunca entra como variable del sistema.", fontsize=8.5, color=GRIS)
out = ROOT / "reports" / "ciclo_automejora.png"
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("guardada:", out)
