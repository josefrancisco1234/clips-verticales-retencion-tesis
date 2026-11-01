"""Consentimiento informado (5 participantes) y cuestionario de utilidad percibida para la validación con creadores de podcast."""
import sys
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document()
st = d.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(10)
from docx.shared import Cm
for _s in d.sections: _s.top_margin = _s.bottom_margin = Cm(1.6); _s.left_margin = _s.right_margin = Cm(2.0)
def H(t, n=1):
    p = d.add_heading(t, n)
    for r in p.runs: r.font.name = "Arial"
    return p
def borde(tb):
    tb._tbl.tblPr.append(parse_xml('<w:tblBorders %s>' % nsdecls("w") + "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="888888"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>"))
TIT = "Selección automática de clips verticales con alto potencial de retención en videos conversacionales a partir de señales de audio y texto"
for k in range(1, 6):
    if k > 1: d.add_page_break()
    H("Universidad de Lima · Facultad de Ingeniería · Ingeniería de Sistemas", 3)
    H("Consentimiento informado para participar en una validación", 1)
    d.add_paragraph().add_run(f"Participante N.º {k} de 5").bold = True
    d.add_paragraph(f"Estudio: {TIT}.")
    d.add_paragraph("Investigador: José Francisco Núñez del Prado Vega, estudiante de Ingeniería de Sistemas, Universidad de Lima. Asesora: Angela Mayhua Quispe. Curso: Seminario de Investigación.")
    H("¿De qué trata el estudio?", 2)
    d.add_paragraph("El estudio evalúa un sistema que, a partir del audio y la transcripción de un video conversacional (por ejemplo, un episodio de podcast), elige cinco clips verticales y les asigna un puntaje de 0 a 99 con una explicación. Se le pide su opinión como creador o creadora de contenido sobre la utilidad de esos clips y de la página web del sistema.")
    H("¿Qué se le pedirá?", 2)
    d.add_paragraph("Ver los cinco clips generados a partir de un episodio (suyo o de ejemplo), revisar la explicación de cada puntaje en la página web y calificar cada clip, responder 6 afirmaciones de utilidad, el cuestionario de usabilidad de 10 preguntas (SUS) y 2 comentarios abiertos. Tomará unos 20 minutos.")
    H("Participación voluntaria, confidencialidad y riesgos", 2)
    for t in ("Su participación es voluntaria; puede retirarse en cualquier momento sin consecuencia alguna.",
              "Sus respuestas serán anónimas y se usarán solo con fines académicos, reportadas de forma agregada (mediana y rango). No se publicará su nombre.",
              "No hay riesgos previstos más allá de los de una actividad cotidiana frente a una computadora. No hay pago por participar; si usó su propio episodio, recibirá los clips generados.",
              "Si el video es suyo, usted autoriza su procesamiento automático para el estudio; el video original no se redistribuye."):
        d.add_paragraph(t, style="List Bullet")
    H("Contacto", 2)
    d.add_paragraph("Ante cualquier duda puede escribir al investigador: 20221730@aloe.ulima.edu.pe.")
    H("Declaración", 2)
    d.add_paragraph("He leído y entendido la información anterior, he podido hacer preguntas y acepto participar voluntariamente.")
    tb = d.add_table(rows=4, cols=2); borde(tb)
    for i, (a, b) in enumerate((("Nombre y apellidos", ""), ("Documento de identidad", ""), ("Firma", ""), ("Fecha", ""))):
        tb.cell(i, 0).text = a; tb.cell(i, 1).text = b
        tb.rows[i].height = Pt(30)
d.add_page_break()
H("Cuestionario de utilidad percibida", 1)
d.add_paragraph("Marque de 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo). Es anónimo.")
ITEMS = ["Los cinco clips elegidos me parecen momentos interesantes del episodio.", "Publicaría estos clips en mis redes con poca o ninguna edición.",
         "La explicación del puntaje (banderas 0/1 por variable) es fácil de entender.", "El puntaje de 0 a 99 me ayuda a decidir qué clip publicar primero.",
         "La página web es fácil de usar.", "Este sistema me ahorraría tiempo frente a elegir los clips manualmente."]
tb = d.add_table(rows=len(ITEMS) + 1, cols=6); borde(tb)
for j, t in enumerate(["Afirmación", "1", "2", "3", "4", "5"]): tb.cell(0, j).text = t
for i, t in enumerate(ITEMS, 1):
    tb.cell(i, 0).text = f"{i}. {t}"
    for j in range(1, 6): tb.cell(i, j).text = "☐"; tb.cell(i, j).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
d.add_paragraph()
H("Cuestionario de usabilidad (SUS)", 2)
d.add_paragraph("Marque de 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo).")
SUS = ["Creo que me gustaría usar este sistema con frecuencia.", "Encontré el sistema innecesariamente complejo.", "Pensé que el sistema era fácil de usar.",
       "Creo que necesitaría el apoyo de un técnico para poder usar este sistema.", "Encontré que las diversas funciones del sistema estaban bien integradas.",
       "Pensé que había demasiada inconsistencia en este sistema.", "Imagino que la mayoría de las personas aprendería a usar este sistema muy rápidamente.",
       "Encontré el sistema muy incómodo de usar.", "Me sentí muy seguro/a usando el sistema.", "Necesité aprender muchas cosas antes de poder usar el sistema."]
ts = d.add_table(rows=len(SUS) + 1, cols=6); borde(ts)
for j, t in enumerate(["Afirmación", "1", "2", "3", "4", "5"]): ts.cell(0, j).text = t
for i, t in enumerate(SUS, 1):
    ts.cell(i, 0).text = f"S{i}. {t}"
    for j in range(1, 6): ts.cell(i, j).text = "☐"; ts.cell(i, j).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
d.add_paragraph()
d.add_paragraph("7. ¿Qué clip cambiaría o descartaría, y por qué?")
d.add_paragraph("_" * 90)
d.add_paragraph("8. ¿Qué mejoraría de la página web o de la explicación del puntaje?")
d.add_paragraph("_" * 90)
d.add_paragraph("Datos opcionales: años creando contenido: ____   Plataformas que usa: ____________________")
d.save(r"F:\TESISJF\Consentimiento_informado_y_cuestionario_5_creadores.docx"); print("ok")
