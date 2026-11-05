"""Figura didáctica: un árbol de decisión de ejemplo (ilustrativo, no es un árbol real entrenado) y cómo LightGBM suma muchos árboles.
Salida: reports/arbol_decision_ejemplo.png"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
fig = plt.figure(figsize=(9.6, 5.6), dpi=200)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
AZ, VE, AM, RO = ("#dbe7f5", "#7aa0cf"), ("#dcefdc", "#7cb87c"), ("#fbf0c8", "#d6b84e"), ("#f8dfe6", "#d489a2")


def caja(x, y, w, h, col, t, fs=8, bold=True):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.01", fc=col[0], ec=col[1], lw=1))
    ax.text(x, y, t, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", color="#1f2937", linespacing=1.25)


def flecha(a, b, et, dx=0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=8, lw=1, color="#4b5563"))
    ax.text((a[0] + b[0]) / 2 + dx, (a[1] + b[1]) / 2, et, fontsize=8, fontweight="bold", color="#9d2b57", ha="center", va="center",
            bbox=dict(fc="white", ec="none", pad=1))


ax.text(0.01, 0.975, "Un árbol de decisión: una cadena de preguntas de sí / no (ejemplo ilustrativo)", fontsize=11, fontweight="bold", va="top")
ax.text(0.01, 0.935, "Cada clip candidato baja por el árbol según sus variables y cae en una hoja con un número.", fontsize=8.5, color="#555", va="top")
# raíz
caja(0.30, 0.82, 0.30, 0.09, AZ, "¿Tiene muchas pausas?\n(a_pause_ratio, percentil ≥ 0.75)")
# nivel 2
caja(0.15, 0.58, 0.26, 0.09, AZ, "¿Hace preguntas?\n(s_questions_pm ≥ 0.75)")
caja(0.45, 0.58, 0.26, 0.09, AZ, "¿Varía el volumen?\n(a_rms_std ≥ 0.75)")
flecha((0.24, 0.775), (0.17, 0.625), "SÍ", -0.02)
flecha((0.36, 0.775), (0.43, 0.625), "NO", 0.02)
# hojas
hojas = [(0.07, "+0.9\nmuy buen clip", VE), (0.23, "+0.4\nbueno", AM), (0.37, "+0.2\nregular", AM), (0.53, "-0.3\nmalo", RO)]
caja(0.07, 0.34, 0.13, 0.11, VE, hojas[0][1], 8); caja(0.23, 0.34, 0.13, 0.11, AM, hojas[1][1], 8)
caja(0.37, 0.34, 0.13, 0.11, AM, hojas[2][1], 8); caja(0.53, 0.34, 0.13, 0.11, RO, hojas[3][1], 8)
flecha((0.11, 0.535), (0.075, 0.395), "SÍ", -0.015); flecha((0.19, 0.535), (0.225, 0.395), "NO", 0.015)
flecha((0.41, 0.535), (0.375, 0.395), "SÍ", -0.015); flecha((0.49, 0.535), (0.525, 0.395), "NO", 0.015)
ax.text(0.30, 0.235, "HOJA = el valor que ese árbol le da al clip", fontsize=8, style="italic", color="#555", ha="center")
# ejemplo de un clip
ax.add_patch(FancyBboxPatch((0.02, 0.04), 0.56, 0.15, boxstyle="round,pad=0,rounding_size=0.01", fc="#f3f4f6", ec="#9ca3af", lw=1))
ax.text(0.30, 0.115, "Ejemplo: un clip con muchas pausas (SÍ) y que hace preguntas (SÍ)\ncae en la hoja de la izquierda y recibe +0.9 de este árbol.",
        fontsize=8.5, ha="center", va="center", color="#1f2937", linespacing=1.4)
# derecha: boosting
ax.text(0.80, 0.86, "LightGBM no usa uno, usa cientos", fontsize=10, fontweight="bold", ha="center")
y = 0.74
for t, v in (("Árbol 1", "+0.9"), ("Árbol 2 (corrige los errores del 1)", "+0.3"), ("Árbol 3 (corrige los errores de 1 y 2)", "-0.1"), ("… hasta cientos de árboles", "+…")):
    caja(0.775, y, 0.32, 0.07, VE if "1" in t[:7] else AZ, t, 7.5, False)
    ax.text(0.97, y, v, fontsize=10, fontweight="bold", color="#9d2b57", ha="right", va="center")
    y -= 0.095
ax.add_patch(FancyArrowPatch((0.80, 0.40), (0.80, 0.33), arrowstyle="-|>", mutation_scale=9, lw=1, color="#4b5563"))
caja(0.80, 0.25, 0.34, 0.12, AM, "puntaje del clip =\nsuma de todas las hojas", 9)
ax.text(0.80, 0.14, "El puntaje final ordena los clips\ny se eligen los 5 mejores.", fontsize=8.5, ha="center", va="center", color="#444", linespacing=1.4)
ax.text(0.80, 0.05, "Los números son ilustrativos, no un árbol real entrenado.", fontsize=7, style="italic", color="#888", ha="center")
fig.savefig(ROOT / "reports" / "arbol_decision_ejemplo.png", facecolor="white")
print("ok")
