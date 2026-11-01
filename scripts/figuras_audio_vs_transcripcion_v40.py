"""Word v40: quita las figuras repetitivas ETL (Figura 2) y de video a clips (Figura 3) y agrega en 4.5 la figura de qué sale del audio y qué de la transcripción,
con su explicación; renumera el resto de las figuras. Los runs con imagen no se tocan al renumerar."""
import copy
import re
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"F:\TESISJF\tesis\desarrollo\reports"
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v39.docx")
P = lambda s: next(p for p in d.paragraphs if p.text.strip().startswith(s))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


# 1) quitar Figuras 2 (ETL) y 3 (video a clips): imagen + leyenda
for pref in ("Figura 2. ", "Figura 3. "):
    cap = P(pref)
    prev = cap._p.getprevious()
    assert prev.xpath(".//w:drawing"), pref
    prev.getparent().remove(prev)
    cap._p.getparent().remove(cap._p)

# 2) referencias a las figuras quitadas
for p in d.paragraphs:
    for r in p.runs:
        if "(Figura 2 y Tabla" in r.text:
            r.text = r.text.replace("(Figura 2 y Tabla", "(Tabla")
        if " (Figura 3)" in r.text:
            r.text = r.text.replace(" (Figura 3)", "")

# 3) renumerar: antes 4..11 -> 3..10 (el hueco 2 queda para la figura nueva)
for old in range(4, 12):
    pat = re.compile(rf"Figura {old}\b")
    for p in d.paragraphs:
        for r in p.runs:
            if pat.search(r.text):
                r.text = pat.sub(f"Figura {old - 1}", r.text)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if pat.search(r.text):
                            r.text = pat.sub(f"Figura {old - 1}", r.text)

# 4) figura nueva al final de 4.5
ult = P("Las variables se calculan con herramientas abiertas")
cap_tpl = P("Figura 1. ")
body_tpl = ult


def clone_after(tpl, text, anchor_el):
    el = copy.deepcopy(tpl._p)
    anchor_el.addnext(el)
    q = Paragraph(el, tpl._parent)
    st(q, text)
    return q


ip = clone_after(body_tpl, "", ult._p)
ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
ip.paragraph_format.first_line_indent = 0
ip.add_run().add_picture(ROOT + r"\audio_vs_transcripcion_D099.png", width=Cm(16.2))
cap = clone_after(cap_tpl, "Figura 2. Qué se obtiene solo del audio, qué de los tiempos de las palabras y qué del contenido del texto, y su parte del peso de la fórmula.", ip._p)
t1 = clone_after(body_tpl, "Qué sale del audio y qué de la transcripción (Figura 2). De las 17 variables de la fórmula, 8 salen solo de la señal de audio y no necesitan la transcripción: el volumen (RMS) y su variación, el rango y la variación del tono (f0), la proporción de voz continua y las probabilidades de habla y de música que entrega PANNs. "
                 "Otras 4 usan los tiempos de las palabras que marca Whisper, sin leer su contenido: la proporción de pausa (huecos de más de 0.3 s), las pausas largas por minuto, el silencio total del tramo y las palabras por segundo. "
                 "Las 5 restantes sí dependen del contenido del texto: la cercanía al tema del video, la densidad de sustantivos, el número de oraciones, las preguntas por minuto y el uso de la segunda persona.", cap._p)
t2 = clone_after(body_tpl, "Por su peso en la fórmula, las variables de audio puro aportan 44 %, las de tiempos de las palabras 34 % y las de contenido del texto 22 %. "
                 "Es decir, 78 % del peso descansa en señales que no leen lo que se dice, y las dos variables de mayor peso (la proporción de pausa y el silencio) vienen de los tiempos de las palabras. "
                 "La transcripción, además, es indispensable para armar los candidatos alineados a oración, los subtítulos y las palabras clave que se muestran con cada clip.", t1._p)
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v40.docx")
print("ok")
