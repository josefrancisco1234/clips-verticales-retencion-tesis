"""Figura: cómo un video recibe su puntaje, con un ejemplo real (D-099). Toma un video del conjunto de desarrollo ya procesado,
muestra los pasos y, para su mejor clip de 45 s o menos, las 17 variables con valor, percentil, bandera, peso y aporte.
Salida: reports/scoring_video_D099.png"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config  # noqa: E402
from src.ranking.retention import BANDERA_P, formula_raw, load_formula  # noqa: E402
from src.segment.candidates import Window, nms  # noqa: E402

VID = "-6rWqJhDv7M"
cfg = load_config("configs/gpu.yaml")
Wt = load_formula(ROOT / "models")["weights"]
df = pd.read_parquet(cfg.path("processed") / "features" / "sentence" / f"{VID}.parquet")
raw = formula_raw(df, Wt, True)
ok = ((df.end - df.start) <= 45).to_numpy()
raw = np.where(ok, raw, raw.min() - 10)
lo = sum(v for v in Wt.values() if v < 0); hi = sum(v for v in Wt.values() if v > 0)
score = np.clip(np.round((raw - lo) / (hi - lo) * 99), 0, 99).astype(int)
wins = [Window(r.start, r.end, int(r.s0), int(r.s1)) for r in df.itertuples()]
keep = nms(wins, raw, 0.3, 5, mode="iomin")
i = keep[0]
rows = []
for k, w in Wt.items():
    pct = float(df[k].rank(pct=True).fillna(0.5).iloc[i]); val = df[k].iloc[i]
    flag = 1 if pct >= BANDERA_P else 0
    rows.append((k, float(val), pct, flag, w, w * flag))
rows.sort(key=lambda r: (-r[3], -abs(r[5]), -abs(r[4])))
raw_i = sum(r[5] for r in rows)
print(VID, len(df), "candidatos; elegido", i, "dur", round(df.end[i] - df.start[i], 1), "raw", round(raw_i, 4), "score", score[i], "top5", [int(score[j]) for j in keep])

fig = plt.figure(figsize=(7.6, 6.0), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
NL = chr(10)


def block(x, y, w, h, fc, ec, title, body, fs=4.3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.006", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, y + h - 0.012, title, ha="center", va="top", fontsize=5.0, fontweight="bold", color="#1f2937")
    ax.text(x + w / 2, y + h - 0.045, body.replace("|", NL), ha="center", va="top", fontsize=fs, color="#374151", linespacing=1.28)


def arr(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color="#4b5563"))


ax.text(0.005, 0.99, f"Cómo un video recibe su puntaje (ejemplo real: video {VID}, {len(df)} candidatos)", fontsize=6.4, style="italic", va="top", color="#111827")
steps = [("#ffffff", "#9ca3af", "1. Candidatos", f"{len(df)} ventanas de|15 a 90 s armadas|con oraciones"),
         ("#dbe7f5", "#7aa0cf", "2. Variables", "17 variables de la|fórmula, medidas|en cada ventana"),
         ("#fbf0c8", "#d6b84e", "3. Percentil", "cada variable se|ordena dentro de|este video, de 0 a 1"),
         ("#dcefdc", "#7cb87c", "4. Bandera", "1 si percentil ≥ 0.75,|si no 0 (el 25 %|más alto)"),
         ("#f8dfe6", "#d489a2", "5. Suma", "raw = Σ peso × bandera|los pesos negativos|restan"),
         ("#fde6cf", "#e8a05a", "6. Escala 0-99", f"(raw − lo)/(hi − lo)|× 99, con lo = {lo:.4f}|y hi = {hi:.4f}")]
bw = 0.1495; gap = 0.0195
for n, (fc, ec, t, b) in enumerate(steps):
    x = 0.005 + n * (bw + gap)
    block(x, 0.855, bw, 0.105, fc, ec, t, b, 4.1)
    if n:
        arr((x - gap + 0.001, 0.907), (x - 0.001, 0.907))
# tabla de las 17 variables del mejor clip
tx, ty, tw = 0.005, 0.835, 0.62
ax.text(tx, ty, f"Mejor clip ({df.start[i]:.0f}–{df.end[i]:.0f} s, {df.end[i] - df.start[i]:.0f} s): las 17 variables", fontsize=5.3, fontweight="bold", va="top", color="#1f2937")
cols = [("Variable", 0.0, "left"), ("Valor", 0.235, "right"), ("Percentil", 0.31, "right"), ("Bandera", 0.385, "right"), ("Peso", 0.455, "right"), ("Aporte", 0.535, "right")]
y0 = ty - 0.032
for name, dx, ha in cols:
    ax.text(tx + dx + (0 if ha == "left" else 0.0), y0, name, fontsize=4.5, fontweight="bold", va="top", ha=ha, color="#111827")
ax.plot([tx, tx + 0.545], [y0 - 0.012, y0 - 0.012], color="#9ca3af", lw=0.5)
rh = 0.0355
for n, (k, val, pct, flag, w, ct) in enumerate(rows):
    y = y0 - 0.02 - n * rh
    if flag:
        ax.add_patch(plt.Rectangle((tx - 0.004, y - rh + 0.004), 0.553, rh - 0.002, fc="#e3f3d0" if w > 0 else "#fbdcdc", ec="none"))
    for (name, dx, ha), s in zip(cols, (k, f"{val:.3g}", f"{pct:.2f}", str(flag), f"{w:+.4f}", f"{ct:+.4f}" if flag else "0")):
        ax.text(tx + dx, y, s, fontsize=4.4, va="top", ha=ha, color="#111827" if flag else "#6b7280")
yb = y0 - 0.02 - len(rows) * rh
ax.plot([tx, tx + 0.545], [yb + 0.004, yb + 0.004], color="#9ca3af", lw=0.5)
ax.text(tx + 0.455, yb - 0.003, "Suma (raw)", fontsize=4.6, fontweight="bold", va="top", ha="right")
ax.text(tx + 0.535, yb - 0.003, f"{raw_i:+.4f}", fontsize=4.6, fontweight="bold", va="top", ha="right")
ax.text(tx, yb - 0.027, f"score = ({raw_i:.4f} − ({lo:.4f})) / ({hi:.4f} − ({lo:.4f})) × 99 = {score[i]}",
        fontsize=5.0, fontweight="bold", va="top", color="#7c2d12")
ax.text(tx, yb - 0.052, "Verde: bandera 1 con peso positivo (suma). Rojo: bandera 1 con peso negativo (resta).", fontsize=4.0, va="top", color="#6b7280")
# histograma de puntajes de todos los candidatos
hx = fig.add_axes([0.68, 0.53, 0.30, 0.24])
hx.hist(score[ok], bins=range(0, 100, 5), color="#cbd5e1", ec="white")
hx.axvline(score[i], color="#e8710a", lw=1.2)
hx.text(score[i] - 2, hx.get_ylim()[1] * 0.92, f"mejor clip: {score[i]}", color="#e8710a", fontsize=5.0, ha="right", va="top")
hx.set_title("Puntajes de los candidatos de 45 s o menos", fontsize=5.2)
hx.set_xlabel("puntaje 0-99", fontsize=4.6); hx.set_ylabel("candidatos", fontsize=4.6)
hx.tick_params(labelsize=4.4)
for s in ("top", "right"):
    hx.spines[s].set_visible(False)
# top 5 tras supresión de no máximos
ax.text(0.68, 0.455, "7. Orden y selección de 5 clips", fontsize=5.3, fontweight="bold", va="top", color="#1f2937")
ax.text(0.68, 0.43, "Se ordena por raw y se descartan los que comparten más del 30 %|de su duración con uno ya elegido (no máximos).".replace("|", NL), fontsize=4.2, va="top", color="#374151", linespacing=1.28)
for dx, h in ((0.0, "#"), (0.03, "inicio–fin (s)"), (0.14, "duración"), (0.23, "puntaje")):
    ax.text(0.68 + dx, 0.385, h, fontsize=4.4, fontweight="bold", va="top")
for n, j in enumerate(keep):
    for dx, v in ((0.0, str(n + 1)), (0.03, f"{df.start[j]:.0f}–{df.end[j]:.0f}"), (0.14, f"{df.end[j] - df.start[j]:.0f} s"), (0.23, str(score[j]))):
        ax.text(0.68 + dx, 0.36 - n * 0.026, v, fontsize=4.4, va="top")
block(0.68, 0.07, 0.315, 0.12, "#e6dcf3", "#9b7fc7", "8. Clip final",
      "recorte 9:16 con seguimiento del hablante,|subtítulos, puntaje, aporte de cada variable|y desglose Hook / Flow / Value", 4.1)
fig.savefig(ROOT / "reports" / "scoring_video_D099.png", facecolor="white")
