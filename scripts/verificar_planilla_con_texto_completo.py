"""Actualiza la planilla del estado del arte con cinco artículos cuyo texto completo se pudo leer en arXiv (Um 2025, Barua 2025, Suen y Su 2026, Pei 2024, Banzina y Niebuhr 2023)."""
import sys

import openpyxl
from openpyxl.styles import PatternFill

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUTA = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\7_Excel_resumenes_26_articulos\Planilla_ESTADO_DEL_ARTE_26_articulos.xlsx"
# n -> (preprocesamiento, sugerencias futuras, conclusiones), todo leído en el texto completo
ACT = {
    7: ("Las características de los clips se agrupan (clustering) para resumir el contexto del video; se usan codificaciones posicionales aprendibles, normalización previa, 8 cabezas de atención y dropout de 0.1.",
        "Desarrollar una integración audio-visual más sofisticada.",
        "El módulo de atención a palabras clave con el contexto de todo el video mejora la precisión, y las pérdidas contrastivas alinean mejor el texto de la consulta con los clips."),
    9: ("Se extraen las frases nominales de la transcripción larga (spaCy) y se incluyen en la instrucción al modelo de lenguaje; las sesiones del estudio se grabaron, transcribieron y analizaron con codificación temática.",
        "Integrar Lotus a las herramientas de edición existentes para aprovechar la edición con línea de tiempo.",
        "Los participantes crearon videos cortos comparables a los de herramientas tradicionales; la preferencia por el modo extractivo o el abstractivo dependió de la composición del video (por ejemplo, si había un hablante frente a cámara) y valoraron el borrador inicial y la flexibilidad."),
    17: ("Cada video se transcribe; las palabras se segmentan con Jieba-tw y se cruzan con la base de emociones Chinese EmoBank; se usaron 210 videos válidos de profesores distintos, transcritos y analizados con aprendizaje profundo.",
         "Diversificar la muestra y los sujetos para generalizar mejor; usar herramientas computacionales de reconocimiento emocional para evaluaciones más objetivas.",
         "Las emociones vocales no verbales (felicidad y sorpresa suben el engagement afectivo; el enojo lo baja) importan más que el contenido verbal; pesa más la activación emocional que la valencia, y sumar las expresiones no verbales aumentó 25.6 % el poder explicativo (R² ajustado)."),
    22: ("No se usan técnicas de aumento de datos; los videos se procesan con la herramienta LiveLabel a una tasa de cuadros ajustable.",
         "No hay una sección de trabajo futuro; los autores presentan GPE como línea base para futuras investigaciones y esperan inspirar otros trabajos sobre esta tarea.",
         "Introducen la tarea de detección incremental de momentos destacados, el conjunto LiveFood (cuatro dominios) y el modelo GPE; los experimentos muestran la eficacia del método."),
    24: ("El video del discurso de Obama (COP26, 30 cuadros por segundo) se analizó cuadro por cuadro en cada pausa, distinguiendo pausas intermedias y pausas posteriores al mensaje.",
         "Explorar el uso de pausas en hablantes principalmente de inglés en situaciones de oratoria planificada, centradas en pausas planificadas.",
         "Estudio piloto: Obama usa pausas excepcionalmente largas, con cambios abruptos de tono e intensidad justo antes y después, sobre todo en pausas posteriores al mensaje, y usa más expresiones faciales mientras más larga es la pausa."),
}
wb = openpyxl.load_workbook(RUTA)
ws = wb.active
sin_relleno = PatternFill(fill_type=None)
for n, (pre, fut, con) in ACT.items():
    r = 6 + n
    for col, v in ((7, pre), (11, fut), (12, con)):
        c = ws.cell(r, col)
        c.value = v
        c.fill = sin_relleno
    ws.cell(r, 14).value = ws.cell(r, 14).value.replace("Lectura: solo el resumen", "Lectura: texto completo")
wb.save(RUTA)
filas = range(7, 33)
nv = {r: [c for c in (4, 5, 7, 11, 12) if str(ws.cell(r, c).value).startswith("No verificable")] for r in filas}
nv = {r: v for r, v in nv.items() if v}
print("artículos con celdas no verificables:", len(nv), "| celdas:", sum(len(v) for v in nv.values()))
print("lectura: texto completo", sum(1 for r in filas if "texto completo" in str(ws.cell(r, 14).value)),
      "| solo resumen", sum(1 for r in filas if "solo el resumen" in str(ws.cell(r, 14).value)),
      "| sin texto", sum(1 for r in filas if "no se obtuvo" in str(ws.cell(r, 14).value)))
for r in nv:
    print(" -", ws.cell(r, 2).value, "|", ws.cell(r, 14).value.split(chr(10))[-1])
