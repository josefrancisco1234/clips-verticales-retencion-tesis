"""Word v35: agrega 5.8 (Experimentación) con el análisis comparativo de las cuatro formas de puntuar (azar, V0, V1, R0), con su tabla de métricas.
Cifras: docs/DECISIONES.md D-064 (cohorte fresca 1), reports/confirmacion_D048 (352 videos), D-063/D-065 (R0)."""
import copy
import re
import sys

import docx
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v34.docx")
P = lambda s: next(p for p in d.paragraphs if p.text.strip().startswith(s))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


def clone_after(tpl, text, after_el):
    el = copy.deepcopy(tpl._p); after_el.addnext(el)
    q = Paragraph(el, tpl._parent); st(q, text); return q


# tabla modelo (Tabla 6 actual) antes de renumerar
t6 = next(t for t in d.tables if t.cell(0, 0).text.strip().startswith("Método"))
new_tbl = copy.deepcopy(t6._tbl)
# renumerar Tabla 6..14 -> 7..15 (de mayor a menor)
def renum(old):
    pat = re.compile(rf"Tabla {old}\b")
    for p in d.paragraphs:
        for r in p.runs:
            if pat.search(r.text):   # solo los runs con texto coincidente: asignar r.text a un run con imagen la borra
                r.text = pat.sub(f"Tabla {old + 1}", r.text)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if pat.search(r.text):   # solo los runs con texto coincidente: asignar r.text a un run con imagen la borra
                            r.text = pat.sub(f"Tabla {old + 1}", r.text)
for old in range(14, 5, -1):
    renum(old)

head = P("5.7 Reproducibilidad")
body_tpl = P("El procedimiento siguió siete pasos")
cap_tpl = P("Tabla 5. Partición")
anchor = P("6. RESULTADOS")._p.getprevious()   # último elemento de 5.7

h58 = clone_after(head, "5.8 Análisis comparativo de las cuatro formas de puntuar", anchor)
p1 = clone_after(body_tpl, "Se compararon cuatro formas de puntuar los clips candidatos, de la que menos información usa a la que más: (1) el azar, que elige cinco clips sin criterio y es la referencia mínima; (2) V0, la suma de las 17 variables con pesos fijos, sin entrenamiento y explicable variable por variable; (3) V1, que es V0 restringida a clips de hasta 45 s; y (4) R0, LightGBM con objetivo LambdaRank sobre las 71 variables en percentiles, entrenado con 444 videos. Cada paso cambia una sola cosa respecto del anterior, de modo que la diferencia se puede atribuir a ese cambio. Se reportan el acierto@5, el F1 temporal y el calor del clip frente al promedio del video (definiciones en la sección 4.10) en la cohorte fresca 1 (93 videos, una sola corrida con pesos y modelos congelados) y, para las tres primeras formas, en el conjunto de confirmación (352 videos de 290 canales) (Tabla 6).", h58._p)
cap = clone_after(cap_tpl, "Tabla 6. Métricas de las cuatro formas de puntuar en la cohorte fresca 1 y en el conjunto de confirmación", p1._p)
cap._p.addnext(new_tbl)
# 3 -> 5 columnas
grid = new_tbl.find(qn("w:tblGrid"))
rows = new_tbl.findall(qn("w:tr"))
for tr in rows:
    tcs = tr.findall(qn("w:tc"))
    for _ in range(2):
        tcs[-1].addnext(copy.deepcopy(tcs[-1]))
if grid is not None:
    cols = grid.findall(qn("w:gridCol"))
    tot = sum(int(c.get(qn("w:w"))) for c in cols) or 9000
    ws = [int(tot * f) for f in (0.30, 0.17, 0.14, 0.16, 0.23)]
    for c in list(cols[1:]):
        grid.remove(c)
    cols[0].set(qn("w:w"), str(ws[0]))
    for w_ in ws[1:]:
        gc = copy.deepcopy(cols[0]); gc.set(qn("w:w"), str(w_)); grid.append(gc)
else:
    ws = None
for tr in rows:
    for n, tc in enumerate(tr.findall(qn("w:tc"))):
        pr = tc.find(qn("w:tcPr"))
        tw = pr.find(qn("w:tcW")) if pr is not None else None
        if tw is not None and ws:
            tw.set(qn("w:w"), str(ws[n])); tw.set(qn("w:type"), "dxa")
from docx.table import Table
tb = Table(new_tbl, cap._parent)
DATA = [["Forma de puntuar", "Acierto@5 (cohorte 1, 93)", "F1 temporal (cohorte 1)", "Calor del clip frente al video", "Acierto@5 y F1 (confirmación, 352)"],
        ["1 · Azar", "26.9 %", "0.072", "1.00x", "29.1 % y 0.070"],
        ["2 · V0 (fórmula de 17 variables)", "47.3 %", "0.149", "1.35x", "49.4 % y 0.131"],
        ["3 · V1 (V0 con clips de hasta 45 s)", "54.8 %", "0.141", "1.43x", "53.4 % y 0.118"],
        ["4 · R0 (LightGBM LambdaRank)", "62.4 %", "0.142", "1.52x", "no evaluado"]]
for r, vals in zip(tb.rows, DATA):
    for c, v in zip(r.cells, vals):
        p = c.paragraphs[0]
        if p.runs:
            for x in p.runs[1:]:
                x._r.getparent().remove(x._r)
            p.runs[0].text = v
        else:
            p.add_run(v)
last = new_tbl
texts = [
 "De azar a V0. El acierto@5 sube de 26.9 % a 47.3 % (20.4 puntos) y el F1 temporal de 0.072 a 0.149; V0 supera al azar en F1 (Wilcoxon unilateral, p = 3e-9). El conjunto de confirmación lo replica (49.4 % frente a 29.1 % y F1 de 0.131 frente a 0.070). Es el mayor salto de la serie y viene de las señales de pausas, silencio y prosodia, no de ningún aprendizaje.",
 "De V0 a V1. Limitar los clips a 45 s sube el acierto@5 a 54.8 % (7.5 puntos) y el calor del clip de 1.35x a 1.43x. Frente a V0, V1 acertó solo en 11 videos y V0 solo en 4 (p = 0.12) en la cohorte 1, y en la confirmación fueron 30 contra 16 (McNemar unilateral, p = 0.027); frente al azar restringido a clips de hasta 45 s (30.6 %) la diferencia es significativa (p = 4e-6). El F1 temporal, en cambio, no mejora (0.149 a 0.141 en la cohorte 1 y 0.131 a 0.118 en la confirmación, p = 0.016 bilateral): los clips cortos tocan más veces un pico, pero cubren menos tiempo caliente. V1 acierta más a costa de cubrir menos.",
 "De V1 a R0. El modelo de aprendizaje llega a 62.4 % (7.6 puntos sobre V1), con un F1 de 0.142 igual al de V1 (0.141) y menor que el de V0 (0.149): aprende a acertar más veces, no a cubrir más tiempo caliente. La comparación directa exige cautela porque R0 puntúa ventanas por tramo de la curva, cuyo azar es 31.9 %, mientras que V0 y V1 puntúan candidatos alineados a oración, con azar de 26.9 %. Medido contra su propio azar, R0 acierta 1.96 veces el azar y V1 2.04 veces, de modo que buena parte de la ventaja aparente de R0 se debe al azar más alto de sus ventanas. Fuera de la cohorte 1 la ventaja de R0 es menor: en la cohorte 2 acertó 49.2 % frente a 30.0 % del azar (1.64 veces) y en validación cruzada en el desarrollo, 58.8 % con F1 de 0.130.",
 "Lectura conjunta. Los tres pasos aportan, pero con rendimientos decrecientes y costos distintos: V0 pasa del azar a casi el doble de acierto sin entrenar nada; V1 suma 7.5 puntos con una sola regla de duración; R0 suma otros 7.6 puntos en la cohorte 1, pero necesita 444 videos de entrenamiento y no explica por qué elige un clip. V1 conserva el 88 % del acierto de R0 (54.8 frente a 62.4) y se explica variable por variable, por lo que se adoptó como modelo final del sistema, en banderas 0/1, y R0 queda como referencia de aprendizaje. Todas las formas quedan lejos del techo de usar la curva real de YouTube (94.6 % de acierto, que solo sirve para calificar y nunca entra al sistema), lo que acota lo que se puede lograr con solo audio y texto.",
]
prev = last
for t in texts:
    q = clone_after(body_tpl, t, prev); prev = q._p
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v35.docx")
print("ok")
