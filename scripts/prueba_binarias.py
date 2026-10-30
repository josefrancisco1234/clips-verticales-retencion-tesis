"""Prueba exploratoria (solo desarrollo, sin tocar el reservado): variables continuas (percentil) frente a variables 0/1 con distintos umbrales."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "scripts" / "auto_mejora.py").read_text(encoding="utf-8")
exec(compile(src[: src.index("# ---------------- generador de variables")], "auto_mejora_cargador", "exec"))
import numpy as np
res = {}
for nombre, X in (("percentil (hoy)", RK), ("0/1 mediana (>=0.5)", (RK >= 0.5).astype(np.float32)), ("0/1 cuartil alto (>=0.75)", (RK >= 0.75).astype(np.float32)),
                  ("0/1 decil alto (>=0.9)", (RK >= 0.9).astype(np.float32)), ("percentil + 0/1 cuartil", np.concatenate([RK, (RK >= 0.75).astype(np.float32)], 2))):
    m = cv_dev(X)
    res[nombre] = (m[:, 0].mean(), m[:, 1].mean())
    print(f"{nombre:28s} acierto@5 {m[:, 0].mean():.1%}  F1 {m[:, 1].mean():.4f}", flush=True)
# fórmula V0 con variables binarizadas (mismos 17 pesos)
import json
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
idx = [(feats.index(k), W[k]) for k in W if k in feats]
for nombre, X in (("fórmula V0 percentil", RK), ("fórmula V0 0/1 mediana", (RK >= 0.5).astype(np.float32)), ("fórmula V0 0/1 cuartil", (RK >= 0.75).astype(np.float32))):
    S = sum(w * X[:, :, i] for i, w in idx)
    m = metrica(S[dev_i], dev_i)
    print(f"{nombre:28s} acierto@5 {m[:, 0].mean():.1%}  F1 {m[:, 1].mean():.4f}")
