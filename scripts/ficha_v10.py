"""Ficha de investigación v10: actualiza la v9 con el estado actual del trabajo (grupos de videos nuevos, base de más de 500 videos, rango de 17 a 23 variables
por segmento, capítulos, backend, validación con SUS, resultados a la fecha, actas y exposición). Solo modifica texto de runs; la figura y la tabla no se tocan."""
import copy
import sys

import docx
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\ENTREGA_NOTA2_FINAL\2_Ficha_de_investigacion\Ficha_Investigacion_NUNEZDELPRADO_v9_clips.docx")
P = d.paragraphs
n = 0


def run_sub(par, pares):
    global n
    for r in par.runs:
        for a, b in pares:
            if a in r.text:
                r.text = r.text.replace(a, b)
                n += 1


G = [("en cohortes frescas", "en grupos de videos nuevos"), ("cohortes frescas", "grupos de videos nuevos"), ("dos cohortes frescas (93 y 63 videos)", "dos grupos de videos nuevos (93 y 63 videos)")]
for p in P:
    if "ohorte" in p.text:
        run_sub(p, [("dos cohortes frescas (93 y 63 videos)", "dos grupos de videos nuevos (93 y 63 videos)"), ("de las cohortes frescas", "de los grupos de videos nuevos"),
                    ("en cohortes frescas", "en grupos de videos nuevos"), ("cohortes frescas", "grupos de videos nuevos")])
for p in P:
    t = p.text
    if t.startswith("Pregunta específica 7"):
        run_sub(p, [("valoran la utilidad de la página web", "valoran la utilidad y la usabilidad de la página web")])
    elif t.startswith("Validar la utilidad percibida"):
        run_sub(p, [("Validar la utilidad percibida de la página web con cinco creadores de podcast, mediante un cuestionario de escala Likert y estadística descriptiva.",
                     "Validar la utilidad percibida y la usabilidad de la página web con cinco creadores de podcast, mediante un cuestionario de escala Likert (6 afirmaciones), el cuestionario SUS y estadística descriptiva.")])
    elif t.startswith("El sistema se aplica a videos de YouTube"):
        run_sub(p, [("La población está formada por unos 770 videos y se organiza",
                     "La población está formada por unos 770 videos (siempre más de 500 analizados; la base sigue creciendo) y se organiza")])
    elif t.startswith("Modelos y algoritmos."):
        run_sub(p, [("una fórmula de 17 variables ponderadas, con pesos",
                     "una fórmula de 17 variables ponderadas (para cada segmento se escanean entre 17 y 23 variables y solo cuentan las que superan el umbral del 25 % más alto de su video, para evitar ruido), con pesos"),
                    ("y una red de ecuaciones (Sahoo et al., 2018), que entrega una fórmula legible.",
                     "y una red de ecuaciones (Sahoo et al., 2018), que entrega una fórmula legible. Un ciclo campeón/retador propone y prueba variables y fórmulas nuevas, incluidas las que no tienen respaldo en la literatura, bajo el mismo protocolo de validación.")])
    elif t.startswith("Integración. Una página web local"):
        run_sub(p, [("Una página web local, con servidor en Python, recibe un video",
                     "Una página web (la página solo hace llamadas al servidor; todo el procesamiento es backend en Python) recibe un video"),
                    ("y la explicación de cada clip.", "y la explicación de cada clip. El video se divide por los capítulos de YouTube: se elige el mejor clip de cada capítulo además del top 5 general.")])
    elif t.startswith("La población son los videos de YouTube"):
        run_sub(p, [("un cuestionario de utilidad para cinco creadores de podcast", "un cuestionario de utilidad y el SUS para cinco creadores de podcast")])
    elif t.startswith("3. Entrenamiento de modelos"):
        run_sub(p, [("la fórmula de 17 variables en versión 0/1,", "la fórmula de 17 variables en versión 0/1 (17 a 23 escaneadas por segmento),")])
    elif t.startswith("5. Página web"):
        run_sub(p, [("recorte vertical 9:16 con seguimiento del hablante, subtítulos y explicación del puntaje.",
                     "recorte vertical 9:16 con seguimiento del hablante, subtítulos y explicación del puntaje; mejor clip por capítulo de YouTube; todo se ejecuta en el backend.")])
    elif t.startswith("6. Validación con usuarios"):
        run_sub(p, [("cuestionario de utilidad percibida con cinco creadores de podcast", "cuestionario de utilidad percibida y SUS con cinco creadores de podcast")])
# Wu et al. (2025) está en la Tabla 1 de la ficha y en las referencias: se conserva (es una fuente real de la ficha).
# párrafo nuevo con el estado y los resultados a la fecha, antes de Referencias
ref = next(p for p in d.paragraphs if p.text.strip() == "Referencias")
tit = copy.deepcopy(next(p for p in d.paragraphs if p.text.strip().startswith("Flujo de trabajo"))._p)
ref._p.addprevious(tit)
q = Paragraph(tit, ref._parent)
for r in q.runs[1:]:
    r._r.getparent().remove(r._r)
q.runs[0].text = "Estado actual y resultados a la fecha: "
cuerpo = copy.deepcopy(next(p for p in d.paragraphs if p.text.startswith("Para cuidar la validez"))._p)
ref._p.addprevious(cuerpo)
c = Paragraph(cuerpo, ref._parent)
for r in c.runs[1:]:
    r._r.getparent().remove(r._r)
c.runs[0].text = ("El sistema está implementado de punta a punta (descarga, transcripción, 71 variables, puntaje de 0 a 99, selección de cinco clips y de un clip por capítulo, recorte 9:16 con subtítulos y explicación) y funciona como página web. "
                  "En el primer grupo de videos nuevos (93 videos) el acierto@5 fue de 26.9 % para el azar, 47.3 % para la fórmula V0, 54.8 % para V1 (clips de hasta 45 s) y 62.4 % para el ranker LightGBM (R0); en los 352 videos de confirmación, V1 acertó en 53.4 % frente a 29.1 % del azar. "
                  "Los modelos de secuencia, la red de ecuaciones y los dos agentes de mejora automática (más de 12 000 rondas) no superaron de forma confirmada a la fórmula. "
                  "La validación con cinco creadores de podcast dio una utilidad percibida con mediana de 4 sobre 5 y un SUS de 75; el problema señalado fue el seguimiento de la cámara al hablante. "
                  "Se cuenta con dos actas de asesoría (N.° 2 y N.° 3) y con el artículo hasta la sección de resultados.")
d.save(r"F:\TESISJF\Ficha_Investigacion_NUNEZDELPRADO_v10.docx")
print("sustituciones:", n, "| quedan 'cohorte':", sum("ohorte" in p.text for p in d.paragraphs), "| dibujos:", len(d.element.body.xpath(".//w:drawing")), "| tablas:", len(d.tables))
