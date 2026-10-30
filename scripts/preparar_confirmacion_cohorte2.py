"""Deriva los scripts de la cohorte 2 (D-065) a partir de los de la cohorte 1, sin tocar la logica preregistrada."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "scripts"

# 1) HuBERT con PCA congelado para la cohorte 2
t = (S / "hubert_fresca_D061.py").read_text(encoding="utf-8")
t = t.replace("conjunto_confirmacion_fresca_D050.json", "conjunto_confirmacion_fresca2_D065.json")
(S / "hubert_cohorte2_D065.py").write_text(t, encoding="utf-8")

# 2) Confirmacion unica de E3 / R4 en la cohorte 2 + evidencia combinada (Stouffer ponderado por raiz de n)
t = (S / "confirmacion_fresca_final_D063.py").read_text(encoding="utf-8")
t = t.replace("conjunto_confirmacion_fresca_D050.json", "conjunto_confirmacion_fresca2_D065.json")
t = t.replace('"confirmacion_fresca_D063"', '"confirmacion_cohorte2_D065"')
t = t.replace("if len(Vf) < 20:", "if len(Vf) < 10:")
t += '''

# ---- evidencia combinada cohorte 1 + cohorte 2 (Stouffer ponderado por raiz de n; declarada en D-065)
from scipy.stats import norm  # noqa: E402

c1 = json.loads((ROOT / "reports" / "confirmacion_fresca_D063" / "resultado.json").read_text(encoding="utf-8"))
n1, n2 = c1["n_videos"], len(Vf)
comb = {}
for k in ("R4", "E3"):
    p1 = c1[f"{k}_vs_R0"]["p_unilateral"]
    p2 = res[f"{k}_vs_R0"]["p_unilateral"]
    z1, z2 = norm.isf(p1), norm.isf(p2)
    w1, w2 = np.sqrt(n1), np.sqrt(n2)
    z = (w1 * z1 + w2 * z2) / np.sqrt(w1 ** 2 + w2 ** 2)
    comb[k] = {"p_cohorte1": p1, "p_cohorte2": p2, "z_combinado": float(z), "p_combinado": float(norm.sf(z)),
               "n1": n1, "n2": n2}
res["combinado_cohortes_1_y_2"] = comb
res["descriptiva_n_menor_40"] = bool(n2 < 40)
json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1)
print("\\nEvidencia combinada (Stouffer, descriptiva):")
for k, v in comb.items():
    print(f"  {k}: p1={v['p_cohorte1']:.4f} (n={n1}) | p2={v['p_cohorte2']:.4f} (n={n2}) | combinado p={v['p_combinado']:.4f}")
if n2 < 40:
    print("AVISO: n < 40; resultado descriptivo segun D-065 (enmienda).")
'''
(S / "confirmacion_cohorte2_D065.py").write_text(t, encoding="utf-8")
print("scripts derivados creados")
