"""v22 = v21 + modelo final con variables 0/1 (D-098): ecuación 4b en 4.6, sección 6.8 con la Tabla 11 y conclusión."""
import copy, json, sys
from pathlib import Path
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v21.docx")
C = json.loads((ROOT / "reports" / "costo_binario_D098.json").read_text(encoding="utf-8"))
def P(s):
    for p in d.paragraphs:
        if p.text.strip().startswith(s): return p
    raise KeyError(s)
def st(p, t):
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = t
def clone(tpl, text, before=None, after=None):
    el = copy.deepcopy(tpl._p)
    (before._p.addprevious(el) if before is not None else after._p.addnext(el))
    q = Paragraph(el, tpl._parent); st(q, text); return q
BODY = P("El minero reunió"); HEAD = P("6.7 Las redes"); CAP10 = P("Tabla 10. "); eq = P("puntaje(w) = Σᵢ")
# 4.6: ecuación 4b y texto del modelo final
t1 = clone(BODY, "Modelo final adoptado (D-098). Para que el sistema sea más fácil de sustentar y de explicar, la versión del producto convierte cada variable en una bandera 0/1: vale 1 si su percentil dentro del video está en el 25 % más alto (0.75 o más) y 0 en caso contrario (Ecuación 4b). El umbral lo fijó el autor y no se eligió mirando resultados. Los empates se rompen con el percentil continuo con un peso de 1e-4, de modo que la posición del clip en el video no decide, y el puntaje de 0 a 99 es el percentil del puntaje dentro del video.", after=eq)
e2 = copy.deepcopy(eq._p); eq._p.addnext(e2); q = Paragraph(e2, eq._parent)
st(q, "puntaje_bin(w) = Σᵢ  pesoᵢ × 1[percentilᵢ(w) ≥ 0.75]          (4b)")
# la ecuación 4b queda antes del texto: reordena (ecuación, texto)
eq._p.addnext(e2); e2.addnext(t1._p)
# 6.8
disc = P("7. DISCUSIÓN")
clone(HEAD, "6.8 Modelo final con variables 0/1: el costo medido", before=disc)
clone(BODY, "El modelo final del producto es la fórmula de 17 variables en su versión 0/1. Se adoptó por explicabilidad y no por precisión: cada clip se explica con banderas que el lector entiende de inmediato (por ejemplo, «la variación de volumen está en el 25 % más alto de este video»). Para medir lo que se pierde se comparó, con el mismo procedimiento y en una sola corrida, la fórmula con percentiles continuos y la fórmula 0/1 sobre las 100 ventanas de cada video (la Tabla 11). Las cifras absolutas difieren de las de la Tabla 6, que evalúa clips candidatos de 15 a 90 s.", before=disc)
clone(CAP10, "Tabla 11. Costo de usar variables 0/1: acierto@5 y F1 temporal de la fórmula de 17 variables", before=disc)
src_tbl = next(t for t in d.tables if t.cell(0, 0).text.startswith("Componente (tipo de red)"))
tbl = copy.deepcopy(src_tbl._tbl); disc._p.addprevious(tbl)
T = Table(tbl, disc._parent); tpl = copy.deepcopy(T.rows[1]._tr)
for r in list(T.rows)[1:]: tbl.remove(r._tr)
def setcell(c, t):
    p = c.paragraphs[0]
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    (p.runs[0].__setattr__("text", t) if p.runs else p.add_run(t))
f = lambda x: f"{x['hit5'] * 100:.1f} % / {x['F1']:.3f}"
rows = [("Conjunto (videos)", "Percentil continuo", "Variables 0/1 (diferencia de F1; p de Wilcoxon)")]
for k, nom in (("cohorte fresca 1", "Cohorte fresca 1"), ("cohorte fresca 2", "Cohorte fresca 2"), ("desarrollo (443)", "Desarrollo")):
    g = C[k]; rows.append((f"{nom} ({g['n']})", f(g["continuo"]), f"{f(g['binario'])} ({g['dif_F1_bin_menos_cont']:+.4f}; p = {g['p_wilcoxon']:.3g})"))
rows.append(("Azar (referencia)", "; ".join(f"{f(C[k]['azar'])}" for k in ("cohorte fresca 1", "cohorte fresca 2", "desarrollo (443)")), "mismo azar, por conjunto"))
for j, t in enumerate(rows[0]): setcell(T.rows[0].cells[j], t)
for row in rows[1:]:
    tr = copy.deepcopy(tpl); tbl.append(tr)
    for j, t in enumerate(row): setcell(T.rows[-1].cells[j], t)
clone(BODY, "", before=disc)
g1, g2 = C["cohorte fresca 1"], C["cohorte fresca 2"]
clone(BODY, f"La versión 0/1 no se distinguió de la continua en ninguna comparación (p de 0.59, 0.145 y 0.39), pero quedó por debajo en las tres: en la cohorte 2 el acierto bajó de {g2['continuo']['hit5'] * 100:.1f} % a {g2['binario']['hit5'] * 100:.1f} % y el F1 en {abs(g2['dif_F1_bin_menos_cont']):.4f}. En todos los conjuntos siguió claramente por encima del azar. Por ello se adopta como modelo final por su interpretabilidad, con un costo de precisión acotado y medido, y no como el modelo de mayor precisión: ese lugar lo conserva el ranker aprendido R0 (62.4 % en la cohorte fresca 1).", before=disc)
# conclusión
c = P("Este trabajo propuso y evaluó"); st(c, c.text.rstrip() + " El modelo final adoptado para el producto es la fórmula de 17 variables en versión 0/1, elegida por su explicabilidad; frente a los percentiles continuos perdió entre 0.005 y 0.020 de F1 sin diferencia significativa, y el modelo de mayor precisión sigue siendo el ranker aprendido R0.")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v22.docx"); print("ok")
