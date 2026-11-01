"""Word v45: completa la sección 6.10 y las Tablas 13 y 14 con los datos de las 5 sesiones reportados por el autor (4 en todas las respuestas;
comentario común: el seguimiento de la cámara al hablante falla), agrega capítulos y cortes en 4.6 y el seguimiento de cámara como limitación y trabajo futuro."""
import copy
import sys

import docx
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v44.docx")
P = lambda s: next(p for p in d.paragraphs if p.text.strip().startswith(s))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t
    p.runs[0].font.highlight_color = None


# 6.10: texto y tablas
st(P("[COMPLETAR TRAS LAS CINCO SESIONES] Participaron"),
   "Participaron cinco creadores de podcast (P1 a P5), que vieron los cinco clips de un episodio, revisaron la explicación del puntaje en la página web y respondieron el cuestionario de utilidad (seis afirmaciones) y el SUS. "
   "La Tabla 13 reúne la calificación de los clips, las seis afirmaciones y el puntaje SUS; cada valor es la mediana (mínimo–máximo) de los cinco participantes y el SUS se reporta como media y rango. "
   "Las cinco personas respondieron 4 en la calificación de los clips y en cada afirmación de utilidad, de modo que todas las medianas son 4 (4–4). También respondieron 4 en los diez ítems del SUS, lo que da 50 puntos por persona (media 50, rango 50–50). "
   "La uniformidad de las respuestas sugiere cierta tendencia a asentir y limita la lectura de diferencias entre ítems. En los comentarios abiertos, los cinco calificaron los clips como muy buenos y señalaron un problema principal: el seguimiento de la cámara a la persona que habla en el podcast, que no siempre sigue al hablante activo en el reencuadre vertical.")
st(P("[COMPLETAR TRAS LAS CINCO SESIONES] La Tabla 14"),
   "La Tabla 14 contrasta la métrica final con su criterio. En los 352 videos de confirmación que no se usaron para fijar la fórmula, la variante V1 acertó al menos un pico en 53.4 % de los videos frente a 31.7 % del azar con clips cortos (Wilcoxon unilateral, p < 0.001). "
   "La utilidad percibida cumple el criterio (mediana de 4 de 5), pero el SUS (50) queda por debajo de la meta de 70, por lo que la usabilidad no alcanzó el criterio fijado.")
t13 = next(t for t in d.tables if t.cell(0, 0).text.startswith("Medida"))
for r in t13.rows[1:]:
    c = r.cells[1]
    txt = "50.0 (50.0–50.0)" if r.cells[0].text.startswith("Puntaje SUS") else "4 (4–4)"
    p = c.paragraphs[0]
    if p.runs:
        for x in p.runs[1:]:
            x._r.getparent().remove(x._r)
        p.runs[0].text = txt
    else:
        p.add_run(txt)
t14 = next(t for t in d.tables if t.cell(0, 0).text.startswith("Métrica final"))
for r, txt in ((t14.rows[2], "50.0 (50.0–50.0); no alcanza la meta"), (t14.rows[3], "mediana 4 (4–4); cumple")):
    p = r.cells[2].paragraphs[0]
    for x in p.runs[1:]:
        x._r.getparent().remove(x._r)
    p.runs[0].text = txt

# 4.6: capítulos y cortes
base = P("Los candidatos se ordenan por puntaje y se descartan")
el = copy.deepcopy(base._p)
base._p.addnext(el)
nuevo = Paragraph(el, base._parent)
st(nuevo, "Capítulos y cortes. El video se divide por los capítulos que YouTube muestra sobre la barra de reproducción; en cada capítulo se elige su mejor clip con el mismo puntaje, y el top 5 general se sigue eligiendo sobre todo el video (si el video no trae capítulos, se usan bloques de 10 minutos). "
          "Cada clip empieza y termina en límites de oración y con un pequeño margen de respiración (0.15 s antes y hasta 0.35 s después) que nunca invade la palabra vecina, de modo que el hablante no quede cortado a media palabra ni a media frase.")

# limitación y trabajo futuro: seguimiento de cámara
lim = P("Los hallazgos tienen una implicancia")
lim_par = next(p for p in d.paragraphs if "los grupos de videos nuevos son pequeños" in p.text)
lim_par.runs[-1].text += " Además, en la validación los cinco creadores señalaron que el reencuadre vertical no siempre sigue a la persona que habla en el podcast, porque el detector de rostros falla con cabezas giradas o lejanas."
fut = next(p for p in d.paragraphs if p.text.strip().startswith("9. TRABAJOS FUTUROS"))
sig = fut._p.getnext()
sp = Paragraph(sig, fut._parent)
sp.runs[-1].text += " Para el reencuadre, sustituir el detector de rostros por detección de personas y de pose con YOLO y seguimiento entre cuadros, de modo que la cámara siga al hablante activo aun con la cabeza girada; no se incluyó en esta versión por limitaciones de GPU y de tiempo."
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v45.docx")
print("ok", len(d.element.body.xpath(".//w:drawing")), "dibujos")
