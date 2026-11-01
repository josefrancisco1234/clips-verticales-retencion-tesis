"""Paso 3: las celdas que el texto no cubre se llenan con lo que dicen los resúmenes de los artículos (marcado «según el resumen»); nada se inventa."""
import sys

import openpyxl
from openpyxl.styles import PatternFill

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUTA = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\7_Excel_resumenes_26_articulos\Planilla_ESTADO_DEL_ARTE_26_articulos.xlsx"
wb = openpyxl.load_workbook(RUTA)
ws = wb.active
sin = PatternFill(fill_type=None)
COL = {"var": 5, "pre": 7, "fut": 11, "con": 12}
DATOS = {
    "Badamdorj": {
        "pre": "Según el resumen, el audio y la imagen se modelan por separado y se fusionan con atención bimodal; el detalle de la extracción de características no se informa en el resumen.",
        "fut": "El resumen no menciona trabajo futuro; destaca que la mayoría de los trabajos previos usa solo la imagen y que modelar juntos audio e imagen es la dirección que propone."},
    "Kwak": {
        "pre": "Según el resumen, se usan videos de YT-8M y del conjunto MR.Hisum, que trae los momentos destacados organizados, agrupados por nivel de complejidad; el modelo hace una regresión de la curva de interés.",
        "fut": "Según el resumen, el modelo tiene potencial para resumen de video, recomendación de contenido y edición automática, y se espera que sirva de base para sistemas de inteligencia artificial basados en video."},
    "Wang, E. W.": {
        "pre": "Según el resumen: 40 adultos (15 de 18 a 30 años, 13 de 31 a 40 y 12 de 41 a 50) hicieron una tarea de habla conectada a tres velocidades (habitual, rápida y lenta) con registro cinemático del labio inferior y acústico; se midieron duración y variabilidad.",
        "fut": "El resumen no menciona trabajo futuro; indica que el tiempo influye en la variabilidad motora del habla pero no es su único factor."},
    "Cho": {
        "var": "Según el título del artículo: señales multimodales de videos cortos de marketing en redes sociales; el texto del artículo es de acceso restringido y no se pudo consultar para detallarlas.",
        "pre": "Según el título, el modelo AMPS procesa señales multimodales con mecanismos de atención; el detalle del preprocesamiento no se pudo consultar (artículo de acceso restringido).",
        "fut": "No se pudo consultar (artículo de acceso restringido).",
        "con": "Según el título, propone AMPS, un modelo con mecanismos de atención multimodal para predecir la popularidad de videos cortos en entornos de marketing en redes sociales."},
    "Javed": {
        "fut": "El resumen no menciona trabajo futuro; destaca que el análisis de sentimiento mejora la predicción de popularidad en contextos culturalmente distintos y poco estudiados, como Pakistán."},
    "Tseng": {
        "pre": "Según el resumen: 42 estudiantes de pregrado se dividieron al azar en un grupo de control (video sin anotaciones) y uno experimental (con anotaciones del docente); se recogieron una encuesta de engagement, conductas de visualización y entrevistas.",
        "fut": "El resumen no menciona trabajo futuro; concluye que las anotaciones y el engagement se correlacionan positivamente y que los estudiantes sintieron mayor retención y comprensión del contenido."},
    "Parker": {
        "pre": "Según el resumen: se usaron datos detallados de 3.1 millones de visualizaciones de cursos en línea de ciencias biomédicas; el engagement se midió sobre todas las sesiones de cada estudiante y no solo en una, y se ajustaron modelos lineales con elementos del contexto del curso.",
        "fut": "Según el resumen, los resultados sugieren factores que educadores y diseñadores de cursos pueden usar para aumentar el engagement con el video; no menciona trabajo futuro."},
    "Cao": {
        "pre": "Según el resumen: se reunieron datos de más de 90 000 campañas de video publicitario (1 billón de impresiones, más de 20 segmentos de industria y seis plataformas sociales); se armó una taxonomía de rasgos del video basada en el modelo de probabilidad de elaboración y se exploró con agrupamiento no supervisado."},
}
hechas = 0
for pref, cambios in DATOS.items():
    r = next(x for x in range(7, 33) if str(ws.cell(x, 2).value).startswith(pref))
    for k, txt in cambios.items():
        c = ws.cell(r, COL[k])
        assert str(c.value).startswith(("No se informa", "Pendiente")), (pref, k, c.value)
        c.value = txt
        c.fill = sin
        hechas += 1
wb.save(RUTA)
filas = range(7, 33)
print("celdas llenadas con el resumen o el título:", hechas)
print("quedan 'No se informa' o 'Pendiente':", sum(1 for r in filas for c in range(2, 15) if str(ws.cell(r, c).value).startswith(("No se informa", "Pendiente"))))
print("vacías:", sum(1 for r in filas for c in range(2, 15) if not ws.cell(r, c).value))
