"""Figura 1 del artículo: pipeline de la metodología en el estilo de bloques verticales de izquierda a derecha (D-099).
Salida: reports/pipeline_metodologia_D099.png (se inserta en el Word con scripts/armar_word_v23.py)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
NL = chr(10)
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(7.6, 3.3), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
T = lambda s: s.replace("|", NL)


def panel(x, y, w, h, fc, ec, title, body="", tfs=5.6, bfs=4.7, ty=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, ty if ty is not None else y + h - 0.045, T(title), ha="center", va="top", fontsize=tfs, fontweight="bold", color="#1f2937", linespacing=1.15)
    if body:
        ax.text(x + w / 2, (ty if ty is not None else y + h - 0.045) - 0.085, T(body), ha="center", va="top", fontsize=bfs, color="#374151", linespacing=1.25)


def arr(a, b, c="#4b5563"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color=c))


ax.text(0.005, 0.975, "Pipeline de la metodología", fontsize=6.4, style="italic", va="top", color="#111827")
TOP, BOT = (0.55, 0.37), (0.07, 0.37)   # (y, alto) de las dos ramas
# --- entradas
panel(0.005, TOP[0], 0.085, TOP[1], "#ffffff", "#9ca3af", "Audio", "", ty=TOP[0] + TOP[1] - 0.03)
t = np.linspace(0, 1, 160)
wave = 0.5 * np.sin(2 * np.pi * 9 * t) * np.exp(-((t - 0.3) ** 2) / 0.04) + 0.35 * np.sin(2 * np.pi * 14 * t) * np.exp(-((t - 0.72) ** 2) / 0.03)
ax.plot(0.015 + 0.065 * t, TOP[0] + 0.15 + 0.07 * wave, color="#1f4e79", lw=0.6)
ax.text(0.0475, TOP[0] + 0.05, "wav 16 kHz mono", ha="center", fontsize=4.3, color="#6b7280")
panel(0.005, BOT[0], 0.085, BOT[1], "#ffffff", "#9ca3af", "Transcripción", "", ty=BOT[0] + BOT[1] - 0.03)
for i, wd in enumerate((0.065, 0.05, 0.062, 0.04, 0.058)):
    ax.add_patch(plt.Rectangle((0.015, BOT[0] + 0.24 - i * 0.04), wd, 0.014, fc="#9ca3af", ec="none"))
ax.text(0.0475, BOT[0] + 0.05, "texto con tiempo", ha="center", fontsize=4.3, color="#6b7280")
ax.text(0.0475, 0.51, "Video largo", ha="center", va="center", fontsize=5.0, fontweight="bold", color="#1f4e79")
ax.text(0.0475, 0.475, "(archivo o link)", ha="center", va="center", fontsize=4.2, color="#6b7280")
# --- preprocesamiento (azul)
for (y, h), body in ((TOP, "Eventos de sonido|(risa, aplausos,|música) con PANNs"), (BOT, "Whisper en GPU,|oraciones y|candidatos de|15 a 90 s")):
    panel(0.115, y, 0.095, h, "#dbe7f5", "#7aa0cf", "Preprocesamiento", body, ty=y + h - 0.04)
    arr((0.092, y + h / 2), (0.113, y + h / 2))
# --- extracción (verde)
for (y, h), body in ((TOP, "A y E: pausas,|volumen, tono,|ritmo, risa,|música"), (BOT, "K, S, H, F, L:|palabras clave,|preguntas, gancho,|fluidez")):
    panel(0.235, y, 0.095, h, "#dcefdc", "#7cb87c", "Extracción de|variables", body, ty=y + h - 0.04)
    arr((0.212, y + h / 2), (0.233, y + h / 2))
# --- percentil y división de datos (amarillo)
panel(0.355, 0.07, 0.105, 0.85, "#fbf0c8", "#d6b84e", "Percentil y|división de datos", "", ty=0.88)
ax.text(0.4075, 0.755, T("71 variables por|candidato, cada una|como percentil dentro|de su propio video"), ha="center", va="top", fontsize=4.7, color="#374151", linespacing=1.3)
ax.text(0.4075, 0.455, T("Conjuntos agrupados|por canal:"), ha="center", va="top", fontsize=4.7, color="#374151", linespacing=1.3)
for i, lab in enumerate(("Desarrollo", "Confirmación", "Videos nuevos")):
    ax.add_patch(FancyBboxPatch((0.367, 0.32 - i * 0.075), 0.081, 0.055, boxstyle="round,pad=0,rounding_size=0.006", fc="#fff8e1", ec="#d6b84e", lw=0.5))
    ax.text(0.4075, 0.3475 - i * 0.075, lab, ha="center", va="center", fontsize=4.5, color="#374151")
for y, h in (TOP, BOT):
    arr((0.332, y + h / 2), (0.353, y + h / 2))
# --- modelos (rosado)
panel(0.485, TOP[0], 0.215, TOP[1], "#f8dfe6", "#d489a2", "Modelo final del sistema", "", ty=TOP[0] + TOP[1] - 0.04)
ax.text(0.5925, TOP[0] + TOP[1] - 0.125, T("Fórmula de 17 variables en banderas 0/1"), ha="center", va="top", fontsize=4.7, color="#374151")
rng = np.random.default_rng(3)
vals = [0.9, 0.2, 0.8, 0.85, 0.3, 0.78, 0.4]
for i, v in enumerate(vals):
    on = v >= 0.75
    ax.add_patch(plt.Rectangle((0.505 + i * 0.0265, TOP[0] + 0.07), 0.018, 0.17 * v, fc="#2e7d32" if on else "#cbd5e1", ec="none"))
ax.plot([0.5, 0.69], [TOP[0] + 0.07 + 0.17 * 0.75] * 2, ls="--", lw=0.6, color="#e8710a")
ax.text(0.5925, TOP[0] + 0.035, T("suma de pesos x bandera, escala 0 a 99"), ha="center", fontsize=4.4, color="#374151")
panel(0.485, BOT[0], 0.215, BOT[1], "#f8dfe6", "#d489a2", "Modelos de comparación", "", ty=BOT[0] + BOT[1] - 0.04)
for i, lab in enumerate(("Azar", "Ranker LightGBM LambdaRank", "BiGRU · TCN · Transformer", "Red de ecuaciones (EQL)")):
    ax.add_patch(FancyBboxPatch((0.5, BOT[0] + 0.23 - i * 0.065), 0.185, 0.048, boxstyle="round,pad=0,rounding_size=0.006", fc="white", ec="#d489a2", lw=0.5))
    ax.text(0.5925, BOT[0] + 0.254 - i * 0.065, lab, ha="center", va="center", fontsize=4.5, color="#374151")
arr((0.462, 0.5), (0.483, TOP[0] + TOP[1] / 2 - 0.0), "#4b5563")
arr((0.462, 0.5), (0.483, BOT[0] + BOT[1] / 2), "#4b5563")
# --- evaluación (rojo)
panel(0.725, 0.07, 0.085, 0.85, "#f2d5d0", "#c9776c", "Evaluación", "", ty=0.88)
ax.text(0.7675, 0.745, T("acierto@5|F1 temporal|NDCG@10|y pruebas|estadísticas"), ha="center", va="top", fontsize=4.7, color="#374151", linespacing=1.3)
ax.add_patch(FancyBboxPatch((0.733, 0.28), 0.069, 0.19, boxstyle="round,pad=0,rounding_size=0.006", fc="#fff3e0", ec="#e8710a", lw=0.5))
ax.text(0.7675, 0.375, T("Calor real|(Most Replayed):|solo califica"), ha="center", va="center", fontsize=4.3, color="#7c2d12", linespacing=1.25)
arr((0.702, TOP[0] + TOP[1] / 2), (0.723, 0.7))
arr((0.702, BOT[0] + BOT[1] / 2), (0.723, 0.3))
# --- selección y clips (naranja)
panel(0.835, 0.07, 0.085, 0.85, "#fde6cf", "#e8a05a", "Selección|y clips", "", ty=0.88)
ax.text(0.8775, 0.72, T("Top 5: dos clips|no comparten más|del 30 % de su|duración|Recorte 9:16|con seguimiento|del hablante|y subtítulos"), ha="center", va="top", fontsize=4.7, color="#374151", linespacing=1.3)
arr((0.812, 0.5), (0.833, 0.5))
# --- validación y final (morado)
panel(0.945, 0.07, 0.05, 0.85, "#e6dcf3", "#9b7fc7", "", "", ty=0.88)
ax.text(0.97, 0.52, T("Validación con 5 creadores y comparación final"), ha="center", va="center", fontsize=4.9, fontweight="bold", color="#1f2937", rotation=90)
arr((0.922, 0.5), (0.943, 0.5))
fig.savefig(ROOT / "reports" / "pipeline_metodologia_D099.png", facecolor="white")
print("ok")
