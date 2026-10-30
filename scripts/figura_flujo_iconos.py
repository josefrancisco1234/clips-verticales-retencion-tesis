"""Diagrama de flujo con íconos para la ficha (comentario de la profesora: 'diagrama de flujo con íconos')."""
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
EMO = "Segoe UI Emoji" if any("Segoe UI Emoji" in f.name for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
pasos = [("1", "Crear el dataset", "videos conversacionales\n+ curva de re-reproducción", "🎬", "#1F4E79"), ("2", "Preprocesar", "transcribir, segmentar y\ny extraer 71 variables", "🎙", "#1F4E79"),
         ("3", "Entrenar modelos", "fórmula, LightGBM,\nBiGRU / TCN / Transformer, EQL", "🧠", "#6A3D9A"), ("4", "Evaluar el sistema", "acierto@5, F1 temporal,\nNDCG@10 frente al azar", "📊", "#E8590C"),
         ("5", "Página web", "carga un video y entrega\n5 clips 9:16 con puntaje", "🌐", "#2F7D32"), ("6", "Validar con usuarios", "5 creadores de podcast:\ncuestionario de utilidad", "👥", "#555555")]
fig, ax = plt.subplots(figsize=(15, 4.6), dpi=170); ax.set_xlim(0, 150); ax.set_ylim(0, 46); ax.axis("off")
ax.text(75, 43, "Flujo de trabajo de la investigación", ha="center", fontsize=15, fontweight="bold", color="#14213D")
w, g = 20.5, 4.4
for i, (n, t, s, em, c) in enumerate(pasos):
    x = 2 + i * (w + g)
    ax.add_patch(FancyBboxPatch((x, 4), w, 31, boxstyle="round,pad=0.3,rounding_size=1.4", fc="#F3F5F9", ec=c, lw=2))
    ax.add_patch(Circle((x + w / 2, 26), 6.3, fc=c, ec="none"))
    ax.text(x + w / 2, 25.6, em, ha="center", va="center", fontsize=26, color="white", fontfamily=EMO)
    ax.text(x + 2.4, 33, n, ha="center", va="center", fontsize=11, fontweight="bold", color=c)
    ax.text(x + w / 2, 15.3, t, ha="center", va="center", fontsize=10.2, fontweight="bold", color="#14213D")
    ax.text(x + w / 2, 9, s, ha="center", va="center", fontsize=7.7, color="#444", linespacing=1.3)
    if i < len(pasos) - 1:
        ax.add_patch(FancyArrowPatch((x + w + .6, 20), (x + w + g - .6, 20), arrowstyle="-|>", mutation_scale=16, lw=2, color="#555"))
ax.text(75, 0.6, "La curva de re-reproducción de YouTube solo califica los resultados; nunca es entrada del sistema.", ha="center", fontsize=9, color="#555", style="italic")
fig.savefig(ROOT / "reports" / "flujo_ficha_iconos.png", bbox_inches="tight", facecolor="white"); print("ok", EMO)
