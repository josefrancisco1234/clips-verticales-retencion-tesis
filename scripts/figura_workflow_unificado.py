"""Workflow unificado: ETL -> BD -> ranking -> clips, calificación con el heatmap y ciclo de mejora automática con red neuronal."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
AZ, NA, VE, MO, GR, TE = "#1F4E79", "#E8590C", "#2F7D32", "#6A3D9A", "#555555", "#0B7285"
fig, ax = plt.subplots(figsize=(15, 9.2), dpi=170)
ax.set_xlim(0, 150)
ax.set_ylim(0, 92)
ax.axis("off")
ax.text(75, 90, "Workflow unificado del sistema", ha="center", fontsize=18, fontweight="bold", color="#14213D")


def caja(x, y, w, h, c, t, s="", tsz=8.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.0", fc=c, ec="none"))
    ax.text(x + w / 2, y + h - 2.2 if s else y + h / 2, t, ha="center", va="center", color="white", fontsize=tsz, fontweight="bold")
    if s:
        ax.text(x + w / 2, y + (h - 4.6) / 2, s, ha="center", va="center", color="white", fontsize=7.8, linespacing=1.25)


def fl(a, b, c=GR, rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=13, lw=1.5, color=c, connectionstyle=f"arc3,rad={rad}", linestyle=ls))


def banda(y, h, t):
    ax.add_patch(FancyBboxPatch((1, y), 148, h, boxstyle="round,pad=0.2,rounding_size=1.5", fc="#F3F5F9", ec="#D5DAE3", lw=1))
    ax.text(3, y + h - 2.3, t, fontsize=10, fontweight="bold", color=GR, va="center")


# Banda 1: ETL y BD (construcción de datos)
banda(64, 24, "A · CONSTRUIR LOS DATOS (ETL → base de datos)")
x0, w, g = 4, 21, 3.5
b1 = [("Búsqueda en YouTube", "50+ consultas ES/EN\nfiltros de idioma y duración"), ("Descarga (yt-dlp)", "audio wav 16 kHz\ncurva Most Replayed"),
      ("Transcripción", "Whisper por palabra\ncon marcas de tiempo"), ("Variables", "71 por ventana: audio,\ntexto, gancho, fluidez"), ("BD_TESIS", "1 021 videos en carpetas\ncohortes congeladas")]
for i, (t, s) in enumerate(b1):
    caja(x0 + i * (w + g), 67, w, 15, AZ if i < 4 else TE, t, s)
    if i < 4:
        fl((x0 + i * (w + g) + w + .2, 74.5), (x0 + (i + 1) * (w + g) - .2, 74.5))

# Banda 2: producción
banda(37, 25, "B · USAR EL SISTEMA (un video nuevo → clips con puntaje)")
b2 = [("Video largo", "archivo o URL"), ("Transcripción + variables", "mismo ETL, sin curva"), ("Ranking del campeón", "red EQL (o V0 / LightGBM)\npercentiles por video"),
      ("Top-5 sin solape", "NMS 30 %, ventanas 15–90 s"), ("Clips 9:16", "puntaje 0–99, SHAP,\nsubtítulos con palabras clave")]
for i, (t, s) in enumerate(b2):
    caja(x0 + i * (w + g), 40, w, 15, NA if i == 2 else AZ, t, s)
    if i < 4:
        fl((x0 + i * (w + g) + w + .2, 47.5), (x0 + (i + 1) * (w + g) - .2, 47.5))

# Banda 3: mejora automática
banda(2, 33, "C · MEJORAR SOLO (24/7, GPU, red neuronal)")
caja(4, 6, 21, 22, MO, "Minero de papers", "OpenAlex: 1 339 trabajos\nseñales que faltan\n(cada 10 rondas)")
caja(28.5, 6, 21, 22, MO, "Inventor de variables\ny arquitecturas", "5 variables nuevas\n(producto, razón, suavizado…)\n5 mutaciones de la red")
caja(53, 6, 21, 22, NA, "Entrenar la red EQL", "GPU, validación por canal\nen desarrollo (354 videos)")
caja(77.5, 6, 21, 22, VE, "Campeón / retador", "reservado 89 videos\nWilcoxon p < 0.05/50\n(Bonferroni)")
caja(102, 6, 21, 22, VE, "Confirmación", "una vez, cohorte fresca\nhipótesis escrita antes")
caja(126.5, 6, 19.5, 22, GR, "Bitácora", "DECISIONES.md\nrondas.jsonl\n(también negativos)")
for xa, xb in ((25.2, 28.3), (49.7, 52.8), (74.2, 77.3), (98.7, 101.8), (123.2, 126.3)):
    fl((xa, 17), (xb, 17))
fl((88, 28.4), (68, 39.8), VE)  # nuevo campeón vuelve al ranking
ax.text(83, 33.5, "si se confirma:\nnuevo campeón", fontsize=7.8, color=VE, ha="left", va="center")
fl((60, 28.4), (60, 39.8), MO)
ax.text(46, 33.5, "lee BD_TESIS", fontsize=7.8, color=MO)

# Heatmap: califica
ax.add_patch(FancyBboxPatch((127, 40), 21, 15, boxstyle="round,pad=0.25,rounding_size=1.0", fc="white", ec=NA, lw=1.8))
ax.text(137.5, 51, "Heatmap\nMost Replayed", ha="center", va="center", fontsize=9, fontweight="bold", color=NA)
ax.text(137.5, 44.3, "solo califica:\netiquetas y métricas", ha="center", va="center", fontsize=7.8, color=NA)
fl((113, 66.8), (136, 55.6), NA, rad=-0.25, ls=":")
ax.text(75, 0.1, "La curva nunca entra como variable del sistema; el reservado y la cohorte fresca no se mezclan con el entrenamiento.", ha="center", fontsize=8.5, color=GR, style="italic")
fig.savefig(ROOT / "reports" / "workflow_unificado.png", bbox_inches="tight", facecolor="white")
print("ok")
