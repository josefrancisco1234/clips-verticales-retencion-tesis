"""Figura del agente autónomo: (izq.) cómo genera y filtra variables; (der.) resultado real de sus rondas (reports/auto_mejora/rondas.jsonl)."""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
H = [json.loads(l) for l in open(ROOT/"reports"/"auto_mejora"/"rondas.jsonl", encoding="utf-8")]
fig, (a, b) = plt.subplots(1, 2, figsize=(13, 6), dpi=170, gridspec_kw={"width_ratios": [1.05, 1]})
a.set_xlim(0, 100); a.set_ylim(-13, 100); a.axis("off")
a.set_title("Una ronda del agente (sin intervención humana)", fontsize=12, fontweight="bold")
pasos = [("#6A3D9A", "1  Generar 10 variables nuevas", "producto, razón, diferencia, máx/mín,\nsuavizado, derivada, contraste local\nsobre las 68 variables base"),
         ("#1F4E79", "2  Cribar en desarrollo", "LightGBM + validación por canal\n(354 videos); se queda la mejor"),
         ("#E8590C", "3  ¿Gana +0.002 de F1?", "si no: ronda sin prueba (no gasta\npresupuesto del reservado)"),
         ("#E8590C", "4  Prueba en reservado (89 videos)", "Wilcoxon unilateral, p < 0.05/25\n(Bonferroni, 25 pruebas en total)"),
         ("#2F7D32", "5  Promover o descartar y registrar", "si pasa: entra al campeón;\nsiempre: queda en la bitácora")]
for k, (c, t, s) in enumerate(pasos):
    y = 80 - k * 19.5
    a.add_patch(FancyBboxPatch((3, y - 6), 94, 15, boxstyle="round,pad=0.4,rounding_size=1.5", fc=c, ec="none"))
    a.text(6, y + 5.2, t, color="white", fontsize=10.5, fontweight="bold", va="center")
    a.text(6, y - 0.8, s, color="white", fontsize=8.6, va="center")
    if k < 4: a.add_patch(FancyArrowPatch((50, y - 6.6), (50, y - 11.4), arrowstyle="-|>", mutation_scale=13, lw=1.5, color="#555"))
a.text(50, -10, "Cada 10 rondas: refresca el minero de papers. Repite sin parar.", ha="center", fontsize=8.6, color="#555", style="italic")
pr = [h for h in H if "p_wilcoxon" in h]; sp = [h for h in H if "p_wilcoxon" not in h]
b.axhline(0.002, color="#2F7D32", lw=1.6, ls="--"); b.axhline(0.05, color="#999", lw=1, ls=":")
b.text(0.3, 0.0021, "umbral de promoción 0.002", color="#2F7D32", fontsize=8.5, va="bottom")
b.text(0.3, 0.052, "p = 0.05 sin corrección", color="#777", fontsize=8.5, va="bottom")
b.scatter([h["ronda"] for h in pr], [max(h["p_wilcoxon"], 1e-4) for h in pr], c="#E8590C", s=38, label=f"con prueba en reservado ({len(pr)})", zorder=3)
b.set_yscale("log"); b.set_ylim(1e-3, 1.2); b.set_xlim(0, max(h["ronda"] for h in H) + 1)
b.set_xlabel("ronda"); b.set_ylabel("p de Wilcoxon (menor es mejor)")
b.set_title(f"Resultado real: {len(H)} rondas, {sum(h['promovido'] for h in H)} variables promovidas", fontsize=12, fontweight="bold")
b.legend(loc="lower right", fontsize=8.5, frameon=False)
for s in ("top", "right"): b.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(ROOT/"reports"/"agente_auto.png", bbox_inches="tight", facecolor="white"); print("ok", len(H), len(pr))
