"""Figura horizontal (estilo de la Figura 1): cómo un video recibe su puntaje, con un ejemplo real (D-099).
Salida: reports/scoring_horizontal_D099.png"""
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
keep = nms([Window(r.start, r.end, int(r.s0), int(r.s1)) for r in df.itertuples()], raw, 0.3, 5, mode="iomin")
i = keep[0]
rows = []
for k, w in Wt.items():
    pct = float(df[k].rank(pct=True).fillna(0.5).iloc[i])
    rows.append((k, pct, int(pct >= BANDERA_P), w))
rows.sort(key=lambda r: (-r[2], -abs(r[3]), -abs(r[3])))
act = [r for r in rows if r[2]]
raw_i = round(sum(r[3] for r in act), 4)
lo, hi = round(lo, 4), round(hi, 4)
n_corto = int(ok.sum())
assert score[i] == int(np.clip(round((raw_i - lo) / (hi - lo) * 99), 0, 99)), "el puntaje mostrado no coincide"
NL = chr(10)
T = lambda s: s.replace("|", NL)
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(7.6, 3.5), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
Y0, H = 0.06, 0.84


def panel(x, w, fc, ec, title):
    ax.add_patch(FancyBboxPatch((x, Y0), w, H, boxstyle="round,pad=0,rounding_size=0.008", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, Y0 + H - 0.035, T(title), ha="center", va="top", fontsize=5.4, fontweight="bold", color="#1f2937", linespacing=1.15)


def txt(x, y, s, fs=4.5, c="#374151", **k):
    ax.text(x, y, T(s), ha=k.pop("ha", "center"), va=k.pop("va", "top"), fontsize=fs, color=c, linespacing=1.28, **k)


def arr(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color="#4b5563"))


ax.text(0.005, 0.985, f"Cómo un video recibe su puntaje (ejemplo real: {len(df)} candidatos)", fontsize=6.4, style="italic", va="top", color="#111827")
# 1 video y candidatos
panel(0.005, 0.075, "#ffffff", "#9ca3af", "Video|largo")
txt(0.0425, 0.74, f"{len(df)}|candidatos|de 15 a 90 s|armados con|oraciones", 4.3)
for n, (a, b, c) in enumerate(((0.012, 0.050, "#7aa0cf"), (0.022, 0.062, "#9bb8de"), (0.032, 0.073, "#7aa0cf"))):
    ax.add_patch(plt.Rectangle((a, 0.46 - n * 0.05), b - a, 0.032, fc=c, ec="none"))
txt(0.0425, 0.26, f"{n_corto} de {len(df)} duran|45 s o menos;|se mide el mejor", 4.0, "#6b7280")
# 2 variables
panel(0.10, 0.08, "#dbe7f5", "#7aa0cf", "17 a 23|variables")
txt(0.14, 0.74, "pausas y|silencios|volumen|y tono|música|y habla|palabras|clave|preguntas|nº de|oraciones", 4.0)
arr((0.082, 0.5), (0.098, 0.5))
# 3 percentil y bandera
panel(0.20, 0.15, "#dcefdc", "#7cb87c", "Percentil y|bandera")
bx0, bw, sp, base, hmax = 0.2075, 0.0058, 0.0082, 0.22, 0.34
for n, (k, pct, flag, w) in enumerate(rows):
    ax.add_patch(plt.Rectangle((bx0 + n * sp, base), bw, hmax * pct, fc=("#2e7d32" if flag and w > 0 else ("#c62828" if flag else "#cbd5e1")), ec="none"))
ax.plot([0.205, 0.345], [base + hmax * 0.75] * 2, ls="--", lw=0.6, color="#e8710a")
ax.text(0.345, base + hmax * 0.75 + 0.012, "0.75", fontsize=3.9, color="#e8710a", ha="right", va="bottom")
txt(0.275, 0.76, "cada variable se ordena|dentro de este video|(0 a 1)", 4.0)
txt(0.275, 0.17, f"bandera 1 en {len(act)} de 17|si percentil ≥ 0.75|(se escanean 17 a 23|por segmento)", 4.0)
arr((0.182, 0.5), (0.198, 0.5))
# 4 peso x bandera, con el flujo por variable
X4, W4 = 0.37, 0.245
panel(X4, W4, "#fbf0c8", "#d6b84e", "Peso × bandera|(aporte de cada variable)")
cx = {"var": X4 + 0.008, "pct": X4 + 0.116, "flag": X4 + 0.150, "w": X4 + 0.190, "ct": X4 + 0.238}
for key, h in (("var", "variable"), ("pct", "percentil"), ("flag", "bandera"), ("w", "× peso"), ("ct", "= aporte")):
    ax.text(cx[key], 0.775, h, fontsize=3.7, fontweight="bold", va="top", ha="left" if key == "var" else "right", color="#111827")
ax.plot([X4 + 0.006, X4 + W4 - 0.006], [0.757, 0.757], color="#9ca3af", lw=0.5)
RH = 0.047
for n, (k, pct, flag, w) in enumerate(act):
    y = 0.745 - n * RH
    ax.text(cx["var"], y, k, fontsize=4.0, va="top", color="#111827")
    ax.text(cx["pct"], y, f"{pct:.4f}", fontsize=4.0, va="top", ha="right")
    ax.text(cx["flag"], y, "1", fontsize=4.0, va="top", ha="right", fontweight="bold", color="#2e7d32")
    ax.text(cx["w"], y, f"{w:+.4f}", fontsize=4.0, va="top", ha="right")
    ax.text(cx["ct"], y, f"{w:+.4f}", fontsize=4.0, va="top", ha="right", color="#111827")
yb = 0.745 - len(act) * RH
ax.plot([X4 + 0.006, X4 + W4 - 0.006], [yb + 0.005, yb + 0.005], color="#9ca3af", lw=0.5)
ax.text(cx["var"], yb - 0.003, "raw = suma de aportes", fontsize=4.4, fontweight="bold", va="top")
ax.text(cx["ct"], yb - 0.003, f"{raw_i:+.4f}", fontsize=4.4, fontweight="bold", va="top", ha="right")
ax.text(X4 + W4 / 2, yb - 0.045, "aporte = peso × bandera. Con bandera 0 el aporte es 0,|y si el peso es negativo y la bandera 1, resta.|Las otras 8 variables tienen bandera 0 y no suman.".replace("|", NL),
        fontsize=3.7, va="top", ha="center", color="#6b7280", linespacing=1.3)
arr((0.352, 0.5), (0.368, 0.5))
# 5 escala, con el flujo paso a paso
X5, W5 = 0.635, 0.165
panel(X5, W5, "#f8dfe6", "#d489a2", "Escala 0 a 99|(5 pasos)")
neg = sorted(v for v in Wt.values() if v < 0)
pos = sorted((v for v in Wt.values() if v > 0), reverse=True)
BH, SP = 0.108, 0.126
tx = X5 + W5 / 2
rng = hi - lo
frac = round((raw_i - lo) / rng, 4)
for n in range(5):
    y = 0.680 - n * SP
    ax.add_patch(FancyBboxPatch((X5 + 0.008, y), W5 - 0.016, BH, boxstyle="round,pad=0,rounding_size=0.005", fc="white", ec="#d489a2", lw=0.5))
    if n < 4:
        arr((tx, y - 0.001), (tx, y - 0.017))
    T_ = lambda dy, t, fs=3.6, **k: ax.text(tx, y + BH - dy, t, ha="center", va="top", fontsize=fs, color=k.pop("c", "#374151"), linespacing=1.25, **k)
    ttl = ("1. Entrada", "2. Mínimo posible", "3. Máximo posible", "4. Posición entre mín y máx", "5. Pasar a 99 y redondear")[n]
    T_(0.007, ttl, 4.1, c="#9d2b57", fontweight="bold")
    if n == 0:
        T_(0.034, f"raw = {raw_i:+.4f}", 5.0, c="#e8710a", fontweight="bold")
        T_(0.066, "suma de aportes del" + NL + "bloque amarillo", 3.6)
        y2 = y
    elif n == 1:
        T_(0.030, f"suma de los {len(neg)} pesos negativos" + NL + " ".join(f"{v:.4f}" for v in neg[:3]) + NL + " ".join(f"{v:.4f}" for v in neg[3:]) + f"  =  {lo:.4f}", 3.4)
        T_(0.084, "(peor clip posible: solo ellos en 1; vale 0)", 3.2, c="#6b7280")
    elif n == 2:
        T_(0.030, f"suma de los {len(pos)} pesos positivos" + NL + f"{pos[0]:.4f} + {pos[1]:.4f} + … + {pos[-1]:.4f}" + NL + f"=  {hi:+.4f}", 3.4)
        T_(0.084, "(mejor clip posible: solo ellos en 1; vale 99)", 3.2, c="#6b7280")
    elif n == 3:
        T_(0.028, f"(raw − mín) / (máx − mín)", 3.6, fontweight="bold")
        T_(0.046, f"({raw_i:.4f} + {-lo:.4f}) / ({hi:.4f} + {-lo:.4f})", 3.5)
        T_(0.062, f"= {raw_i - lo:.4f} / {rng:.4f} = {frac:.4f}", 3.5, fontweight="bold")
        bx1, bx2, by = X5 + 0.034, X5 + W5 - 0.034, y + 0.016
        ax.plot([bx1, bx2], [by, by], color="#9ca3af", lw=1.2)
        ax.plot([bx1, bx1], [by - 0.006, by + 0.006], color="#9ca3af", lw=0.8); ax.plot([bx2, bx2], [by - 0.006, by + 0.006], color="#9ca3af", lw=0.8)
        ax.plot([bx1, bx1 + (bx2 - bx1) * frac], [by, by], color="#9d2b57", lw=1.8)
        ax.plot([bx1 + (bx2 - bx1) * frac], [by], marker="v", color="#e8710a", ms=3.2, mec="none", ls="none", zorder=6)
        ax.text(bx1 - 0.004, by, "0", fontsize=3.4, ha="right", va="center", color="#6b7280")
        ax.text(bx2 + 0.004, by, "99", fontsize=3.4, ha="left", va="center", color="#6b7280")
    else:
        T_(0.034, f"{frac:.4f} × 99 = {frac * 99:.1f}", 4.2, fontweight="bold")
        T_(0.060, f"al entero más cercano:", 3.6)
        T_(0.076, f"{score[i]}", 5.0, c="#9d2b57", fontweight="bold")
ax.add_patch(FancyBboxPatch((X5 + 0.045, 0.072), W5 - 0.09, 0.09, boxstyle="round,pad=0,rounding_size=0.006", fc="white", ec="#d489a2", lw=0.8))
ax.text(tx, 0.130, str(score[i]), ha="center", va="center", fontsize=12, fontweight="bold", color="#9d2b57")
ax.text(tx, 0.087, "puntaje", ha="center", va="center", fontsize=3.9, color="#6b7280")
# el valor raw del bloque amarillo pasa al paso 2 del bloque rojo
ax.add_patch(FancyBboxPatch((X4 + W4 - 0.052, yb - 0.026), 0.046, 0.026, boxstyle="round,pad=0,rounding_size=0.004", fc="none", ec="#e8710a", lw=1.0))
ya, yt, xg = yb - 0.008, y2 + BH - 0.042, 0.625
ax.plot([X4 + W4 - 0.006, xg, xg], [ya, ya, yt], color="#e8710a", lw=1.3, zorder=5, solid_capstyle="round")
ax.add_patch(FancyArrowPatch((xg, yt), (X5 + 0.009, yt), arrowstyle="-|>", mutation_scale=8, lw=1.3, color="#e8710a", zorder=5))
# 6 orden y selección
panel(0.82, 0.085, "#fde6cf", "#e8a05a", "Orden y|selección")
txt(0.8625, 0.76, "se ordena|por raw y se|quitan clips|con más de|30 % de|traslape", 3.9)
for n, j in enumerate(keep):
    y = 0.46 - n * 0.075
    ax.add_patch(plt.Rectangle((0.828, y - 0.045), 0.04 * score[j] / 100 + 0.01, 0.04, fc="#e8a05a", ec="none"))
    ax.text(0.8745, y - 0.025, f"{n + 1}: {score[j]}", fontsize=4.0, va="center", color="#7c2d12")
arr((0.802, 0.5), (0.818, 0.5))
# 7 clip final
panel(0.925, 0.07, "#e6dcf3", "#9b7fc7", "Clip|final")
ax.add_patch(FancyBboxPatch((0.9425, 0.46), 0.035, 0.24, boxstyle="round,pad=0,rounding_size=0.004", fc="#1f2937", ec="#9b7fc7", lw=0.6))
ax.text(0.96, 0.58, "9:16", color="white", fontsize=4.2, ha="center", va="center", fontweight="bold")
txt(0.96, 0.40, "con puntaje,|aporte de|cada variable|y desglose|Hook/Flow/|Value", 3.8)
arr((0.907, 0.5), (0.923, 0.5))
fig.savefig(ROOT / "reports" / "scoring_horizontal_D099.png", facecolor="white")
print("ok", score[i], round(raw_i, 4), len(act))
