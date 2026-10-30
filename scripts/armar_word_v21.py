"""v21 = v20 + sección 6.7 "Las redes neuronales en el sistema" (Tabla 10, Figura 8) y menciones en introducción, discusión y conclusiones."""
import copy, sys
from pathlib import Path
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from docx.text.paragraph import Paragraph
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v20.docx")
def P(s, contains=False):
    for p in d.paragraphs:
        if (s in p.text) if contains else p.text.strip().startswith(s): return p
    raise KeyError(s)
def st(p, t):
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = t
def clone_after(anchor_el, tpl, text):
    el = copy.deepcopy(tpl._p); anchor_el.addprevious(el)
    q = Paragraph(el, tpl._parent); st(q, text); return q
HEAD = P("6.6 Ciclo"); BODY = P("El minero reunió"); CAP9 = P("Tabla 9. "); CAPF = P("Figura 7. ")
disc = P("7. DISCUSIÓN")
a = disc._p
clone_after(a, HEAD, "6.7 Las redes neuronales en el sistema")
clone_after(a, BODY, "Las redes neuronales participan en cada etapa del sistema, desde la transcripción hasta el ranking, y no solo en el modelo de aprendizaje profundo de la sección 4.9. La Tabla 10 las reúne. La transcripción usa Whisper, un transformador de codificador y decodificador (Radford et al., 2023); los eventos de audio (risa, aplausos y música) los etiqueta PANNs CNN14, una red convolucional (Kong et al., 2020); la similitud de palabras clave sale de embeddings multilingües de tipo BERT (Grootendorst, 2020); y los embeddings de habla, de HuBERT (Hsu et al., 2021). Tres de las 17 variables de la fórmula final provienen de estas redes: la música máxima y media de PANNs y la similitud de KeyBERT.")
clone_after(a, BODY, "En el ranking se probaron cuatro familias de redes. Un perceptrón multicapa (RankNet) sirvió de línea base desde el inicio del proyecto; tres modelos de secuencia (BiGRU, TCN y transformador) leyeron la línea de tiempo completa del video con 12 configuraciones sobre 444 videos; una red de ecuaciones (EQL) aprendió fórmulas legibles; y un agente neuronal en GPU evoluciona esa red y propone variables nuevas (sección 4.10). El resultado es consistente: las redes acompañan y a veces igualan al modelo de árboles, pero con unos 400 videos de entrenamiento ninguna lo supera de forma confirmada, por lo que el puntaje de producción sigue siendo LightGBM y las redes funcionan como extractores de variables y como exploradoras de mejoras (Figura 8).")
cap = clone_after(a, CAP9, "Tabla 10. Redes neuronales del sistema: función, resultado y papel final")
rows = [
 ("Componente (tipo de red)", "Función", "Resultado y papel final"),
 ("Whisper (transformador codificador-decodificador)", "Transcripción con tiempo por palabra", "Base de todas las variables de texto"),
 ("PANNs CNN14 (red convolucional)", "Risa, aplausos y música por tramo", "Grupo E; la música máxima y media entran a la fórmula de 17 variables"),
 ("KeyBERT (embeddings multilingües)", "Similitud de palabras clave con el pasaje", "Entra a la fórmula de 17 variables"),
 ("HuBERT (transformador autosupervisado)", "Embeddings de habla (grupo U)", "LightGBM + HuBERT: 59.5 % frente a 58.8 % (p del F1 = 0.109); BiGRU + HuBERT: 60.1 % frente a 54.7 % (p = 0.028, no alcanza el umbral de 0.0125); no se adopta"),
 ("RankNet (perceptrón multicapa)", "Línea base de ranking", "Parte de las 12 configuraciones de secuencia (el perceptrón por tramo)"),
 ("BiGRU, TCN y transformador de secuencia", "Contexto temporal del video completo", "Mejor red (BiGRU 128): 54.7 % y F1 0.121 frente a 58.8 % y 0.130 de LightGBM; ninguna de las 12 supera a la fórmula en F1"),
 ("EQL (red de ecuaciones)", "Ecuación legible de 17 o 68 variables", "17 variables: F1 0.1337 frente a 0.1335 de LightGBM (empate con ecuación legible); 68 variables: 0.1124 (p = 0.90)"),
 ("Agente neuronal 24/7 (EQL en GPU)", "Muta la arquitectura e inventa variables", "En curso; ninguna variable ni arquitectura promovida hasta ahora"),
]
tbl = copy.deepcopy(d.tables[13]._tbl); a.addprevious(tbl)
from docx.table import Table
T = Table(tbl, disc._parent)
tpl_row = copy.deepcopy(T.rows[1]._tr)
for r in list(T.rows)[1:]: tbl.remove(r._tr)
def setcell(c, t):
    p = c.paragraphs[0]
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    if p.runs: p.runs[0].text = t
    else: p.add_run(t)
for j, t in enumerate(rows[0]): setcell(T.rows[0].cells[j], t)
for row in rows[1:]:
    tr = copy.deepcopy(tpl_row); tbl.append(tr)
    for j, t in enumerate(row): setcell(T.rows[-1].cells[j], t)
clone_after(a, BODY, "")
pic = d.add_paragraph(); pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
pic.add_run().add_picture(str(ROOT / "reports" / "redes_vs_base.png"), width=Inches(6.4)); pic.paragraph_format.keep_with_next = True
a.addprevious(pic._p)
fc = copy.deepcopy(CAPF._p); a.addprevious(fc); c8 = Paragraph(fc, CAPF._parent)
for r in c8.runs[1:]: r._r.getparent().remove(r._r)
c8.runs[0].text = "Figura 8. "; c8.runs[0].bold = True
rr = c8.add_run("Redes neuronales de secuencia frente a la fórmula y a LightGBM (444 videos, validación cruzada por canal)."); rr.bold = False; rr.italic = True
# el rótulo de la figura 7 comparte párrafo con la imagen: el nuevo va aparte, con el mismo estilo
# ---- menciones en otras secciones
q = P("Para cerrar esta brecha")
st(q, q.text.rstrip() + " Las redes neuronales intervienen desde el inicio: transcripción, eventos de audio, embeddings, modelos de secuencia, una red de ecuaciones y un agente neuronal que se mejora solo (sección 6.7).")
q = P("En síntesis, con solo audio y texto")
q._p.addprevious(copy.deepcopy(BODY._p)); n = Paragraph(q._p.getprevious(), q._parent)
st(n, "Sobre las redes neuronales, el patrón fue el mismo en todas las familias: con unos 400 videos de entrenamiento, los modelos de secuencia no superaron a la fórmula en F1 y la red de ecuaciones solo igualó a LightGBM. La ventaja de una red como la EQL no fue ganar precisión sino entregar una ecuación legible y servir de base para explorar variables nuevas de forma automática; que no ganen aquí no implica que no puedan hacerlo con más datos, como los de Rhapsody.")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v21.docx"); print("ok")
