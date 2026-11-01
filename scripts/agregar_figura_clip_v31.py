"""Word v31: agrega a la sección 4.7 la figura de la creación del clip (tres bloques Hook/Flow/Value, ordenamiento con la
fórmula y con LightGBM LambdaRank, selección y recorte 9:16) y su explicación; renumera Figuras 4-9 a 5-10."""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v30.docx")


def P(s):
    return next(p for p in d.paragraphs if p.text.strip().startswith(s))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


def clone(tpl, text, after):
    el = copy.deepcopy(tpl._p)
    after._p.addnext(el)
    q = Paragraph(el, tpl._parent)
    st(q, text)
    return q


# renumerar de mayor a menor para no chocar
for old in range(9, 3, -1):
    for p in d.paragraphs:
        for r in p.runs:
            if re.search(rf"Figura {old}\b", r.text):   # asignar r.text a un run con imagen la borra
                r.text = re.sub(rf"Figura {old}\b", f"Figura {old + 1}", r.text)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if re.search(rf"Figura {old}\b", r.text):   # asignar r.text a un run con imagen la borra
                            r.text = re.sub(rf"Figura {old}\b", f"Figura {old + 1}", r.text)

cap3 = P("Figura 3. ")
BODY = P("Los candidatos se ordenan por puntaje")
CAP = cap3
ip = clone(BODY, "", after=cap3)
ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
ip.paragraph_format.first_line_indent = 0
ip.add_run().add_picture(str(ROOT / "reports" / "pipeline_clip_D099.png"), width=Cm(16.2))
cap4 = clone(CAP, "Figura 4. Creación de un clip: candidatos, medición en tres bloques (Hook, Flow y Value), ordenamiento con la fórmula de 17 variables y con LightGBM LambdaRank, selección de cinco clips y recorte vertical.", after=ip)
t1 = clone(BODY, "Creación de un clip (Figura 4). Cada clip sale de un candidato: una ventana de 15 a 90 s armada con oraciones completas de la transcripción, de modo que empiece y termine en una frase. Cada candidato se mide en tres bloques, que son las tres dimensiones del puntaje. El bloque Hook reúne las variables del grupo H (gancho); el bloque Flow, las del grupo F (fluidez del habla: pausas y ritmo); y el bloque Value, las de los grupos K, S, A, E y L (palabras clave, sentimiento, volumen y tono, eventos de sonido como risa, aplausos o música, y rasgos lingüísticos). Los tres bloques no son tres cortes del video en el tiempo: son tres lecturas del mismo clip, y de ellas salen el puntaje y el desglose que se muestra al usuario.", after=cap4)
t2 = clone(BODY, "Ordenamiento. Las 71 variables de cada candidato se convierten en percentiles dentro de su propio video. El sistema final marca con 1 las 17 variables de la fórmula que quedan en el 25 % más alto, suma sus pesos (Ecuación 4b) y ordena los candidatos de mayor a menor puntaje. Como referencia de aprendizaje se usa LightGBM con objetivo LambdaRank (R0), que recibe las mismas variables en percentiles y trata cada video como un grupo. Su etiqueta de 0 a 4 sale de la curva Most Replayed del video y solo se usa para entrenar esta referencia; el sistema final no la usa. LightGBM construye árboles de decisión en secuencia: cada árbol corrige el orden de los pares de candidatos que los anteriores ordenaron mal, y pesa cada par por cuánto cambiaría la métrica NDCG si se intercambiaran. Al terminar entrega un puntaje por candidato y los candidatos se ordenan igual que con la fórmula.", after=t1)
t3 = clone(BODY, "Selección y recorte. Con la variante V1 solo compiten los candidatos de hasta 45 s. Se eligen cinco con supresión de no máximos (dos clips no comparten más del 30 % de su duración), el puntaje se expresa en una escala de 0 a 99 y cada clip se recorta a 9:16 con seguimiento del hablante y subtítulos. Cada clip se entrega con su puntaje, el desglose Hook, Flow y Value y las palabras de mayor peso.", after=t2)
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v31.docx")
print("ok")
