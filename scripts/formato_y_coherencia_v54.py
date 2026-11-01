"""Word v54: tipografía uniforme (párrafo de la ecuación y todas las tablas de datos), rondas del agente neuronal actualizadas con el registro real
(reports/auto_mejora_nn/rondas.jsonl) y explicación de las fórmulas propias y del sistema de creación de fórmulas."""
import copy
import json
import re
import sys

import docx
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v53.docx")
P = d.paragraphs
rows = [json.loads(x) for x in open(r"F:\TESISJF\tesis\desarrollo\reports\auto_mejora_nn\rondas.jsonl", encoding="utf-8") if x.strip()]
usadas = [r for r in rows if r.get("p_wilcoxon") is not None]
N_NN = f"{len(rows):,}".replace(",", " ")
print("rondas del agente neuronal:", N_NN, "| pruebas:", len(usadas), "| promovidas:", sum(1 for r in rows if r["promovido"]), "| p mínimo:", round(min(r["p_wilcoxon"] for r in usadas), 3))

# 1) párrafo con tipografía distinta (ecuación): mismo formato que el cuerpo
cuerpo = next(p for p in P if p.text.startswith("Las limitaciones del estudio son tres"))
ec = next(p for p in P if p.text.startswith("La ecuación aprendida por la red de ecuaciones"))
ec._p.remove(ec._p.pPr) if ec._p.pPr is not None else None
ec._p.insert(0, copy.deepcopy(cuerpo._p.pPr))
for r in ec.runs:
    r.font.size = Pt(12)
    r.font.name = None

# 2) tablas de datos: 9 pt y bordes iguales a la Tabla 1
ref_borders = d.tables[0]._tbl.tblPr.find(qn("w:tblBorders"))
n_fmt = 0
for t in d.tables:
    h = t.cell(0, 0).text.strip()
    if h.startswith("Algoritmo") or h.startswith("Variable") and len(t.rows) > 40:
        continue
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    if t._tbl.tblPr.find(qn("w:tblBorders")) is None and ref_borders is not None:
        t._tbl.tblPr.append(copy.deepcopy(ref_borders))
        n_fmt += 1
print("tablas a las que se agregaron bordes:", n_fmt)

# 3) rondas del agente neuronal
cambios = 0
for p in d.paragraphs:
    for r in p.runs:
        if "9 158" in r.text:
            r.text = r.text.replace("9 158", N_NN)
            cambios += 1
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if "9 158" in r.text:
                        r.text = r.text.replace("9 158", N_NN)
                        cambios += 1
print("cifras de rondas actualizadas:", cambios)

# 4) fórmulas propias y sistema de creación de fórmulas (al final de 4.5)
ult = next(p for p in d.paragraphs if p.text.startswith("Qué sale del audio y qué de la transcripción"))
sig = Paragraph(ult._p.getnext(), ult._parent)   # segundo párrafo de esa explicación
ancla = sig if sig.text.startswith("Por su peso en la fórmula") else ult


def despues(ref, texto):
    el = copy.deepcopy(cuerpo._p)
    ref._p.addnext(el)
    q = Paragraph(el, ref._parent)
    for r in q.runs[1:]:
        r._r.getparent().remove(r._r)
    q.runs[0].text = texto
    return q


q1 = despues(ancla, "Variables sin respaldo en la literatura y sistema de creación de fórmulas. De las 71 variables, 45 tienen un trabajo de 2021 en adelante que relaciona la señal con engagement o atención; las otras 26 son fórmulas propias de los autores, definidas a partir de la señal (por ejemplo, la proporción de pausa, el silencio total, el peso KVSUM de las palabras o el rango de tono) y descritas con su fórmula en la Tabla 2. "
         "Sobre esas variables, el sistema crea y evalúa fórmulas nuevas por sí mismo, sin tomarlas de ningún artículo: la red de ecuaciones (EQL) aprende ecuaciones legibles con penalización L1 y el inventor del agente propone variables derivadas (productos, razones, máximos, diferencias, suavizados y derivadas temporales) que se calculan con el audio y la transcripción ya existentes.")
q2 = despues(q1, "Cada fórmula nueva, sin importar su origen, se somete al mismo protocolo: se criba por validación cruzada por canal en desarrollo, gasta como máximo una de las 25 pruebas del conjunto reservado y solo se promueve si supera al campeón con Wilcoxon unilateral y corrección de Bonferroni. "
         "Así, las variables sin literatura quedan justificadas por evidencia propia y no por una cita. Con este procedimiento se evaluaron, en la sección 6.9, miles de fórmulas candidatas y ninguna superó al campeón de forma confirmada, de modo que las fórmulas propias que sí usa el modelo final (17 variables) son las que resultaron de la selección fijada antes de mirar los datos de confirmación.")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v54.docx")
print("ok", len(d.element.body.xpath(".//w:drawing")), "dibujos")
