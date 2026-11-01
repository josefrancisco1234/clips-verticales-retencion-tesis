"""Figura de la metodología centrada en la creación del clip (D-099): del video largo a los clips, con los tres bloques
Hook / Flow / Value, el ordenamiento (fórmula de 17 variables y LightGBM LambdaRank), la selección sin traslape y el recorte 9:16.
Salida: reports/pipeline_clip_D099.png"""
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
fig = plt.figure(figsize=(7.6, 3.6), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
T = lambda s: s.replace("|", NL)


def panel(x, y, w, h, fc, ec, title, ty=None, tfs=5.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, ty if ty is not None else y + h - 0.04, T(title), ha="center", va="top", fontsize=tfs, fontweight="bold", color="#1f2937", linespacing=1.15)


def txt(x, y, s, fs=4.6, c="#374151", **k):
    ax.text(x, y, T(s), ha="center", va=k.pop("va", "top"), fontsize=fs, color=c, linespacing=1.28, **k)


def arr(a, b, c="#4b5563"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color=c))


def box(x, y, w, h, fc, ec, s, fs=4.4, c="#374151"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.005", fc=fc, ec=ec, lw=0.5))
    ax.text(x + w / 2, y + h / 2, T(s), ha="center", va="center", fontsize=fs, color=c, linespacing=1.2)


ax.text(0.005, 0.98, "Pipeline de la creación del clip", fontsize=6.4, style="italic", va="top", color="#111827")
Y0, H = 0.06, 0.84
# 1) video largo
panel(0.005, Y0, 0.085, H, "#ffffff", "#9ca3af", "Video largo|(archivo o link)")
t = np.linspace(0, 1, 160)
wave = 0.5 * np.sin(2 * np.pi * 9 * t) * np.exp(-((t - 0.3) ** 2) / 0.04) + 0.35 * np.sin(2 * np.pi * 14 * t) * np.exp(-((t - 0.72) ** 2) / 0.03)
ax.plot(0.015 + 0.065 * t, 0.62 + 0.06 * wave, color="#1f4e79", lw=0.6)
txt(0.0475, 0.53, "audio wav|16 kHz mono", 4.2, "#6b7280")
for i, wd in enumerate((0.065, 0.05, 0.062, 0.04, 0.058)):
    ax.add_patch(plt.Rectangle((0.015, 0.40 - i * 0.04), wd, 0.014, fc="#9ca3af", ec="none"))
txt(0.0475, 0.16, "transcripción|con tiempo|(Whisper)", 4.2, "#6b7280")
# 2) candidatos
panel(0.115, Y0, 0.115, H, "#dbe7f5", "#7aa0cf", "Candidatos")
txt(0.1725, 0.80, "Se cortan por oraciones|ventanas de 15 a 90 s|que se solapan", 4.5)
ax.plot([0.125, 0.22], [0.58, 0.58], color="#9ca3af", lw=0.8)
for i, (a, b, c) in enumerate(((0.125, 0.17, "#7aa0cf"), (0.15, 0.2, "#9bb8de"), (0.18, 0.22, "#7aa0cf"))):
    ax.add_patch(plt.Rectangle((a, 0.52 - i * 0.045), b - a, 0.03, fc=c, ec="none"))
txt(0.1725, 0.36, "Cada candidato|es un posible clip", 4.5)
txt(0.1725, 0.22, "~ cientos por video", 4.2, "#6b7280")
arr((0.092, 0.5), (0.113, 0.5))
# 3) tres bloques Hook / Flow / Value
panel(0.255, Y0, 0.155, H, "#dcefdc", "#7cb87c", "Cada candidato se mide|en 3 bloques")
for i, (lab, body, fc) in enumerate((("HOOK", "inicio: gancho, pregunta,|primeras palabras", "#c7e6c7"),
                                     ("FLOW", "cuerpo: pausas, ritmo,|fluidez del habla", "#d5ecc9"),
                                     ("VALUE", "contenido: palabras clave,|sentimiento, volumen,|risa, aplausos, música", "#e3f3d0"))):
    y = 0.60 - i * 0.205
    box(0.266, y, 0.133, 0.17, fc, "#7cb87c", "", 4.4)
    ax.text(0.3325, y + 0.145, lab, ha="center", va="top", fontsize=5.0, fontweight="bold", color="#1b5e20")
    txt(0.3325, y + 0.105, body, 4.1, va="top")
    if i < 2:
        arr((0.3325, y - 0.002), (0.3325, y - 0.033), "#6b8e6b")
arr((0.232, 0.5), (0.253, 0.5))
# 4) variables y percentil
panel(0.435, Y0, 0.095, H, "#fbf0c8", "#d6b84e", "71 variables|y percentil")
txt(0.4825, 0.74, "cada variable pasa a|percentil dentro de|su propio video", 4.5)
vals = [0.9, 0.2, 0.8, 0.85, 0.3, 0.78, 0.4]
for i, v in enumerate(vals):
    ax.add_patch(plt.Rectangle((0.444 + i * 0.0115, 0.30), 0.008, 0.2 * v, fc="#2e7d32" if v >= 0.75 else "#cbd5e1", ec="none"))
ax.plot([0.442, 0.525], [0.30 + 0.2 * 0.75] * 2, ls="--", lw=0.6, color="#e8710a")
txt(0.4825, 0.25, "bandera 1 si está en|el 25 % superior", 4.2)
arr((0.412, 0.5), (0.433, 0.5))
# 5) ordenamiento
panel(0.555, Y0, 0.205, H, "#f8dfe6", "#d489a2", "Ordenamiento del clip")
box(0.565, 0.57, 0.185, 0.2, "white", "#d489a2", "Modelo final: fórmula de 17|banderas 0/1 con pesos|puntaje = suma de pesos x bandera|(17 a 23 variables por segmento)", 4.3)
box(0.565, 0.18, 0.185, 0.35, "white", "#d489a2", "", 4.3)
ax.text(0.6575, 0.515, "Referencia: LightGBM LambdaRank", ha="center", va="top", fontsize=4.5, fontweight="bold", color="#9d2b57")
txt(0.6575, 0.475, "grupo = un video|etiqueta 0 a 4 según Most Replayed|(solo para entrenar)|arboles que corrigen el orden|de los pares mal clasificados|salida: puntaje por candidato", 4.0, va="top")
txt(0.6575, 0.145, "se ordenan de mayor a menor puntaje", 4.3, va="top")
arr((0.532, 0.5), (0.553, 0.5))
# 6) selección
panel(0.785, Y0, 0.095, H, "#fde6cf", "#e8a05a", "Selección")
txt(0.8325, 0.78, "solo clips de 45 s|o menos", 4.5)
for i, (w, s) in enumerate(((0.07, "1"), (0.06, "2"), (0.065, "3"), (0.05, "4"), (0.055, "5"))):
    ax.add_patch(plt.Rectangle((0.795, 0.66 - i * 0.04), w, 0.026, fc="#e8a05a", ec="none"))
    ax.text(0.795 + w + 0.004, 0.673 - i * 0.04, s, fontsize=4.3, va="center", color="#7c2d12")
txt(0.8325, 0.44, "top 5: dos clips no|comparten más del|30 % de su duración", 4.4)
txt(0.8325, 0.27, "puntaje escalado|de 0 a 99", 4.4, "#7c2d12")
arr((0.762, 0.5), (0.783, 0.5))
# 7) render
panel(0.905, Y0, 0.09, H, "#e6dcf3", "#9b7fc7", "Clip final")
ax.add_patch(FancyBboxPatch((0.93, 0.42), 0.04, 0.3, boxstyle="round,pad=0,rounding_size=0.004", fc="#1f2937", ec="#9b7fc7", lw=0.6))
ax.text(0.95, 0.575, "9:16", color="white", fontsize=4.6, ha="center", va="center", fontweight="bold")
txt(0.95, 0.38, "recorte vertical|con seguimiento|del hablante|y subtítulos", 4.3)
txt(0.95, 0.19, "puntaje + desglose|Hook / Flow / Value|y palabras clave", 4.2, "#4b2e83")
arr((0.882, 0.5), (0.903, 0.5))
fig.savefig(ROOT / "reports" / "pipeline_clip_D099.png", facecolor="white")
print("ok")
