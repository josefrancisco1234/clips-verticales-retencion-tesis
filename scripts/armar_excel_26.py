"""Excel de resúmenes de los 26 artículos del estado del arte (sección 2 del artículo v23)."""
import re
import sys

import docx
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v23.docx")
P = d.paragraphs
iref = [i for i, p in enumerate(P) if p.text.strip().upper().startswith("REFERENCIAS")][-1]
REFS = [p.text.strip() for p in P[iref + 1:] if p.text.strip()]
T1 = {}
for r in d.tables[0].rows[1:]:
    c = [x.text.strip() for x in r.cells]
    m = re.match(r"([^\s(]+).*\((\d{4}[ab]?)\)", c[0])
    if m:
        T1[(m.group(1), m.group(2))] = c


def ref(sur, yr):
    y4 = yr[:4]
    suen_b = yr == "2026b"
    if suen_b:
        yr = "2026"
    for t in REFS:
        if sur == "Suen" and suen_b != t.startswith("Suen, H.-Y., & Su"):
            continue
        if t.lower().startswith(sur.lower()) and (f"({yr}" in t[:250] or (yr[-1] not in "ab" and f"({y4}" in t[:250])):
            return t
    raise KeyError((sur, yr))


N = {  # (apellido, año): (contexto y datos, técnica, resultado, limitación)
    ("Badamdorj", "2021"): ("Detección de momentos destacados en video con audio y visual", "Aprendizaje conjunto audio-visual con atención bimodal y un mecanismo que descuenta la modalidad ruidosa", "Fusionar audio y video superó a los modelos puramente visuales", "Entrada principal visual; sin puntaje explicable"),
    ("Cho", "2024"): ("Predicción de popularidad de videos cortos en redes sociales", "Mecanismos de atención multimodal (AMPS)", "Predice la popularidad del video completo", "No identifica qué segmento retuvo a la audiencia"),
    ("Javed", "2025"): ("Calidad del video antes de publicarlo para anticipar su popularidad", "Marco de predicción de la calidad del video", "Estima la popularidad esperada del video completo", "No selecciona segmentos ni mide retención"),
    ("Li", "2024a"): ("Predicción de engagement de videos cortos", "Define el compromiso del espectador como retención con las métricas NAWP y ECR", "Definición de engagement como retención, adoptada aquí para llamar al puntaje indicador de retención", "Trabaja con videos cortos completos, no con clips de videos largos"),
    ("Banzina", "2023"): ("Discursos carismáticos (estudio de caso de Barack Obama)", "Análisis de cómo se pausa en el discurso", "Describe el uso de pausas en discursos carismáticos", "Estudio de caso; no mide la retención de la audiencia"),
    ("Tseng", "2021"): ("42 estudiantes de pregrado en Taiwán: un grupo vio un video del curso con anotaciones del docente y otro sin ellas", "Experimento controlado con encuesta de engagement, comportamiento de visualización y entrevistas", "Las anotaciones del docente se asociaron con el engagement y con el comportamiento de visualización", "Muestra pequeña de un solo curso; no selecciona clips"),
    ("Parker", "2024"): ("Engagement con video educativo", "Marco motivacional de múltiples factores", "Propone un marco para explicar el engagement con el video educativo", "Marco conceptual en video educativo; no propone un selector de clips"),
    ("Suen", "2026b"): ("210 videos de cursos masivos de cuatro plataformas y 738 estudiantes", "Análisis acústico y de sentimiento de las expresiones vocales del docente frente al compromiso afectivo autoinformado", "La expresión verbal positiva y de alta activación no afectó por sí sola el compromiso afectivo; sí importaron las emociones vocales no verbales", "Video educativo; mide el compromiso del estudiante, no la retención por clip"),
    ("Reddy", "2021"): ("Podcasts con descripciones de los creadores y transcripciones del audio", "Rasgos de vocabulario, emoción y sintaxis, y modelos con distintas representaciones del texto", "Los rasgos identificados predicen el engagement de los oyentes", "Engagement por podcast completo; no selecciona clips"),
    ("Sun", "2025"): ("Videos cortos generados por usuarios en plataformas de video corto", "Modelos multimodales grandes (VideoLLaMA2 con audio, imagen y lenguaje; Qwen2.5-VL con imagen y lenguaje)", "Explora el uso de modelos multimodales grandes para predecir el engagement de videos cortos", "Predice el engagement del video completo, sin explicación del puntaje"),
    ("Cao", "2025"): ("Más de 90 000 campañas de video publicitario en seis plataformas sociales", "Taxonomía de características del video y su relación con el engagement", "Relaciona características del video publicitario con el engagement de la audiencia", "Videos publicitarios; no conversacionales ni de formato largo"),
    ("Lei", "2021"): ("Más de 10 000 videos de YouTube con consultas en lenguaje natural", "Conjunto QVHighlights con momentos relevantes y puntajes de saliencia de cinco niveles por clip", "Ofrece un banco de pruebas para detectar momentos y highlights", "Requiere una consulta en texto y usa señales visuales"),
    ("Pei", "2024"): ("Más de 5 100 videos de transmisiones en vivo de comida (LiveFood)", "Global Prototype Encoding para detección incremental de highlights", "Detecta highlights y se adapta a nuevos dominios sin reentrenar desde cero", "Dominio específico y entrada visual; sin explicación del puntaje"),
    ("Żygis", "2025"): ("Grabaciones de laboratorio de 30 hablantes nativos de alemán que animan a un corredor", "Estudio de producción que compara la prosodia de los gritos de aliento con el habla neutra", "Caracteriza las propiedades acústicas de los gritos de aliento en eventos deportivos", "Estudio fonético; no mide la retención de audiencia"),
    ("Patel", "2023"): ("Oyentes con y sin pérdida auditiva que evalúan habla con y sin pausas", "Experimento perceptivo sobre pausas y tono", "El habla con pausas suena más engañosa a los oyentes", "Percepción de engaño; no mide engagement"),
    ("Suen", "2026"): ("Video educativo con valoraciones de compromiso afectivo", "Regresión que combina expresiones faciales, rasgos oculomotores y prosodia", "Predice el compromiso afectivo del aprendiz y el atractivo de la voz", "Video educativo con señales faciales; no selecciona clips"),
}
ORDEN = [("Sul", "2023", "2.1"), ("Park", "2025", "2.1"), ("Badamdorj", "2021", "2.2"), ("Liu", "2022", "2.2"), ("Li", "2024b", "2.2"), ("Kwak", "2025", "2.2"),
         ("Um", "2025", "2.2"), ("Lin", "2023", "2.2"), ("Barua", "2025", "2.3"), ("Wang", "2024", "2.3"), ("Wang", "2025", "2.3"), ("Li", "2024a", "2.4"),
         ("Cho", "2024", "2.4"), ("Javed", "2025", "2.4"), ("Tseng", "2021", "2.5"), ("Parker", "2024", "2.5"), ("Suen", "2026b", "2.5"), ("Reddy", "2021", "2.5"),
         ("Sun", "2025", "2.5"), ("Cao", "2025", "2.5"), ("Lei", "2021", "2.5"), ("Pei", "2024", "2.5"), ("Żygis", "2025", "2.5"), ("Banzina", "2023", "2.5"),
         ("Patel", "2023", "2.5"), ("Suen", "2026", "2.5")]
assert len(ORDEN) == 26
CONGRESO = re.compile(r"Proceedings|Conference|Congress|ECCV|Computer Vision|Interspeech|ICASSP|ICME|Advances in Neural|International Conference|Learning @", re.I)
wb = Workbook()
ws = wb.active
ws.title = "Resumen de 26 artículos"
ws.append(["N.º", "Referencia (APA 7)", "DOI o enlace", "Año", "Tipo", "Contexto y datos", "Técnica o modelo", "Resultado reportado", "Limitación frente a este trabajo", "Sección del artículo"])
for i, (sur, yr, sec) in enumerate(ORDEN, 1):
    r = ref(sur, yr)
    m = re.search(r"https?://\S+", r)
    link = m.group(0).rstrip(".") if m else ""
    if (sur, yr) in N:
        ctx, tec, res, lim = N[(sur, yr)]
    else:
        c = next(v for (a, y), v in T1.items() if a.startswith(sur) and y == yr)
        ctx, tec, res, lim = c[1], c[2], c[3], c[4]
    tipo = "Preprint" if "arXiv" in r else ("Artículo de congreso" if CONGRESO.search(r) else "Artículo de revista")
    ws.append([i, r, link, int(yr[:4]), tipo, ctx, tec, res, lim, sec])
for c, w in zip("ABCDEFGHIJ", [5, 60, 38, 7, 18, 38, 38, 38, 36, 10]):
    ws.column_dimensions[c].width = w
thin = Side(style="thin", color="BBBBBB")
for row in ws.iter_rows():
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="1F4E79")
ws.freeze_panes = "C2"
n = wb.create_sheet("Notas")
for t in ("Resumen de los 26 artículos citados en el estado del arte (sección 2) del artículo v23.",
          "Los DOI se verificaron en Crossref, arXiv o DataCite.",
          "Las columnas de contexto, técnica, resultado y limitación de los trabajos de la Tabla 1 salen de esa tabla; las de los demás, de los resúmenes de los artículos.",
          "Si la plantilla oficial de la Nota 2 tiene otras columnas, copiar estas columnas a esa plantilla."):
    n.append([t])
n.column_dimensions["A"].width = 120
wb.save(r"F:\TESISJF\Resumenes_26_articulos_estado_del_arte.xlsx")
print("ok", len(ORDEN))
