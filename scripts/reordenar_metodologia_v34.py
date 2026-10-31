"""Word v34: reordena la metodología en tres etapas (flujo completo, funcionamiento del flujo, scoring, mejora continua).
Orden nuevo: 4.2 flujo completo; 4.3-4.6 flujo (dataset, preprocesamiento, extracción, creación del clip);
4.7 scoring; 4.8-4.9 mejora continua; 4.10 protocolo y métricas; 4.11 web. Actualiza referencias cruzadas."""
import copy
import re
import sys

import docx
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v33.docx")
body = d.element.body
kids = list(body)


def hidx(prefix):
    for n, e in enumerate(kids):
        if e.tag.endswith("}p") and "".join(e.itertext()).strip().startswith(prefix):
            return n
    raise KeyError(prefix)


h = {k: hidx(f"4.{k} ") for k in (6, 7, 8, 9, 10, 11)}
blk = {k: kids[h[k]:h[k + 1]] for k in (6, 7, 8, 9, 10)}
# Figura 5 (imagen, título y párrafo explicativo) vive al final del bloque 4.7: pasa al final del bloque de scoring (antes del párrafo de modelos de secuencia)
cap5 = next(e for e in blk[7] if "".join(e.itertext()).startswith("Figura 5. "))
n5 = blk[7].index(cap5)
fig5 = blk[7][n5 - 1:n5 + 2]
assert fig5[0].xpath(".//w:drawing") and "Cálculo del puntaje" in "".join(fig5[2].itertext())
blk[7] = [e for e in blk[7] if e not in fig5]
ante = next(e for e in blk[6] if "".join(e.itertext()).startswith("Como alternativa de aprendizaje profundo"))
for e in fig5:
    ante.addprevious(e)
kids = list(body)   # se recalcula con la figura ya movida
h = {k: hidx(f"4.{k} ") for k in (6, 7, 8, 9, 10, 11)}
blk = {k: kids[h[k]:h[k + 1]] for k in (6, 7, 8, 9, 10)}
# reordenar: 4.7 -> 4.6, 4.6 -> 4.7, 4.9 -> 4.8, 4.10 -> 4.9, 4.8 -> 4.10
orden = [blk[7], blk[6], blk[9], blk[10], blk[8]]
anchor = kids[h[6]].getprevious()
todos = [e for b in orden for e in b]
for e in todos:
    body.remove(e)
for e in reversed(todos):
    anchor.addnext(e)


def P(prefix):
    return next(p for p in d.paragraphs if p.text.strip().startswith(prefix))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


# títulos y numeración
st(P("4.7 Selección y generación de clips"), "4.6 Creación del clip: del video al clip final")
st(P("4.6 Modelos de ranking"), "4.7 Scoring: modelos de ranking y cálculo del puntaje")
st(P("4.9 Exploración automática"), "4.8 Exploración automática de ecuaciones con aprendizaje profundo")
st(P("4.10 Ciclo de mejora"), "4.9 Proceso de mejora continua: ciclo de mejora automática del sistema")
st(P("4.8 Protocolo experimental"), "4.10 Protocolo experimental y métricas")
# referencias cruzadas
for p in d.paragraphs:
    t = p.text
    n = t
    n = n.replace("métricas de la sección 4.8", "métricas de la sección 4.10")
    n = n.replace("aprendizaje profundo de la sección 4.9", "aprendizaje profundo de la sección 4.8")
    n = n.replace("(secciones 4.5 y 4.6)", "(secciones 4.5 a 4.7)")
    n = n.replace("(sección 4.10)", "(sección 4.9)")
    if n != t:
        st(p, n)
# párrafo de la sección 4.2: las etapas de la explicación
p42 = P("La Figura 1 resume el pipeline")
el = copy.deepcopy(p42._p)
p42._p.addnext(el)
q = Paragraph(el, p42._parent)
st(q, "La explicación sigue tres etapas. Primero se presenta el flujo completo (Figura 1). Luego se disecciona cómo funciona: el flujo que lleva del video al clip (secciones 4.3 a 4.6), el scoring con el que se calcula el puntaje y se ordenan los clips (sección 4.7) y el proceso de mejora continua que propone y evalúa cambios del sistema (secciones 4.8 y 4.9). Al final se describen el protocolo experimental y las métricas (sección 4.10) y la página web con la validación con usuarios (sección 4.11).")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v34.docx")
print("ok")
