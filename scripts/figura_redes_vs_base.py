"""Figura 8: redes neuronales de secuencia frente a la fórmula y LightGBM (D-054/D-055: 444 videos, 10 particiones por canal)."""
import sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
N = ["Azar", "Fórmula V0", "BiGRU 128", "BiGRU 64\n+ contraste", "TCN / Transformer\n(mejores)", "LightGBM\npor ventana"]
HIT = [32.8, 53.4, 54.7, 55.2, 54.0, 58.8]
F1 = [0.055, 0.121, 0.121, 0.117, 0.114, 0.130]
C = ["#999999", "#1F4E79", "#6A3D9A", "#6A3D9A", "#6A3D9A", "#E8590C"]
fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.4), dpi=170)
for ax, v, t, fmt in ((a, HIT, "Acierto@5 (%)", "{:.1f}"), (b, F1, "F1 temporal", "{:.3f}")):
    bars = ax.bar(range(6), v, color=C)
    for k, (r, x) in enumerate(zip(bars, v)):
        s = fmt.format(x) + ("*" if k == 4 and ax is a else "")
        ax.text(r.get_x() + r.get_width() / 2, x, s, ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(6)); ax.set_xticklabels(N, fontsize=8)
    ax.set_title(t, fontsize=11, fontweight="bold"); ax.set_ylim(0, max(v) * 1.18)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.text(0.5, -0.02, "Violeta: redes neuronales de secuencia. *rango 53–55 %. 444 videos, validación cruzada de 10 particiones por canal. Ninguna red supera a la fórmula en F1.", ha="center", fontsize=8.5, color="#555")
fig.tight_layout(); fig.savefig(ROOT / "reports" / "redes_vs_base.png", bbox_inches="tight", facecolor="white"); print("ok")
