"""Paso 2 de la verificación de la planilla: Żygis (texto completo en PMC) y Li 2024a (texto completo en arXiv) con datos del texto, y redacción neutral
y verdadera («no se informa en el resumen») para lo que el resumen no dice. No se inventa contenido."""
import sys

import openpyxl
from openpyxl.styles import PatternFill

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUTA = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\7_Excel_resumenes_26_articulos\Planilla_ESTADO_DEL_ARTE_26_articulos.xlsx"
wb = openpyxl.load_workbook(RUTA)
ws = wb.active
sin = PatternFill(fill_type=None)


def fila(prefijo):
    return next(r for r in range(7, 33) if str(ws.cell(r, 2).value).startswith(prefijo))


# Żygis et al. (2025): texto completo (PMC12743243)
r = fila("Żygis")
ws.cell(r, 7).value = "Anotación y análisis en Praat 6.1.08 con segmentación semiautomática revisada a mano por dos anotadores; medidas de duración, amplitud RMS, F0 máximo y medio (ERB) y rango de F0; tasa de habla en sílabas por segundo dentro de unidades entre pausas de 2 s o más; duración y rango de F0 en log10."
ws.cell(r, 11).value = "El artículo no incluye una sección de trabajo futuro; señala como limitaciones el laboratorio controlado, que animar sin otras personas resulta poco natural y que la amplitud varía con la distancia al micrófono."
ws.cell(r, 12).value = "El aliento dirigido a corredores se caracteriza por mayor F0 y mayor rango de F0, más intensidad, mayor duración y menor tasa de habla que el habla neutra; se hallaron cuatro patrones de producción y se rechazó la hipótesis de que sería más breve y rápido."
ws.cell(r, 14).value = ws.cell(r, 14).value.replace("Lectura: solo el resumen", "Lectura: texto completo")
# Li et al. (2024a): texto completo (arXiv 2410.00289)
r = fila("Li et al. (2024a)")
ws.cell(r, 7).value = "El tiempo medio de visualización se normaliza por la duración del video (ajuste del 3 % superior de los tiempos): NAWP lo lleva a una escala entre un mínimo y un máximo según la duración, y ECR es la probabilidad de ver más de 5 s; los rasgos multimodales incluyen calidad, sonido de fondo, título y descripción, subtítulos del video, transcripciones y emoción visual."
ws.cell(r, 11).value = "El artículo no incluye una sección de trabajo futuro; la conclusión resume los aportes."
# resto: redacción neutral y verdadera
NEUTRO = "No se informa en el resumen del artículo."
SIN_ACCESO = "Pendiente: sin acceso al texto del artículo."
pend = []
for r in range(7, 33):
    for c in (4, 5, 7, 11, 12):
        v = str(ws.cell(r, c).value)
        if v.startswith("No verificable: solo se leyó el resumen"):
            ws.cell(r, c).value = NEUTRO
            ws.cell(r, c).fill = sin
            pend.append((ws.cell(r, 2).value, c))
        elif v.startswith("No verificable: no se obtuvo"):
            ws.cell(r, c).value = SIN_ACCESO
            ws.cell(r, c).fill = sin
            pend.append((ws.cell(r, 2).value, c))
wb.save(RUTA)
print("celdas con redacción neutral:", len(pend))
filas = range(7, 33)
print("lectura: texto completo", sum(1 for r in filas if "texto completo" in str(ws.cell(r, 14).value)),
      "| solo resumen", sum(1 for r in filas if "solo el resumen" in str(ws.cell(r, 14).value)),
      "| sin texto", sum(1 for r in filas if "no se obtuvo" in str(ws.cell(r, 14).value)))
print("celdas con 'No verificable':", sum(1 for r in filas for c in range(2, 15) if "No verificable" in str(ws.cell(r, c).value)))
