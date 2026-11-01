"""Llena la planilla oficial (Cuadrado_ESTADOARTE.xlsx) con los 26 artículos: reemplaza las filas de ejemplo."""
import copy
import re
import sys

import openpyxl
from openpyxl.styles import PatternFill

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\7_Excel_resumenes_26_articulos"
src = openpyxl.load_workbook(DIR + r"\Resumenes_26_articulos_estado_del_arte.xlsx").active
rows = [r for r in src.iter_rows(min_row=2, values_only=True) if r[0]]
wb = openpyxl.load_workbook(DIR + r"\Cuadrado_ESTADOARTE.xlsx")
ws = wb.active
TODO = "POR COMPLETAR (leer el artículo)"
amarillo = PatternFill("solid", fgColor="FFF2CC")
ws["C2"] = "Selección automática de clips verticales con alto potencial de retención en videos conversacionales a partir de señales de audio y texto"
ws["C3"] = "Núñez del Prado Vega, José Francisco"
for r in range(7, 35):   # filas de ejemplo de la plantilla
    for c in range(2, 15):
        ws.cell(r, c).value = None


def partes(ref):
    m = re.search(r"\((\d{4}[a-z]?)\)\.\s*(.+?)(?<![A-Z])[.?]\s", ref)
    aut = ref[:ref.index("(" + m.group(1) + ")")].strip().rstrip(",")
    n = len(re.findall(r",\s(?:[A-ZÀ-Ž]\.-?\s?)+", aut + ","))
    ap = re.match(r"([^,]+)", aut).group(1)
    corto = aut if n <= 3 else f"{ap} et al."
    titulo = m.group(2).strip()
    if ref[m.end(2)] == "?":
        titulo += "?"
    return f"{corto} ({m.group(1)})", titulo


for i, r in enumerate(rows):
    n = 7 + i
    ref = r[1]
    ay, titulo = partes(ref)
    if ref.startswith("Sul"):   # el título lleva «Mr.» y el corte por punto lo trunca
        titulo = "Mr. HiSum: A large-scale dataset for video highlight detection and summarization"
    vals = {2: ay, 3: titulo, 4: TODO, 5: TODO, 6: r[5], 7: TODO, 8: r[6], 9: r[7], 10: r[7], 11: TODO, 12: TODO, 13: ref,
            14: "Limitación frente a este trabajo: " + r[8]}
    for c in range(2, 15):
        cell = ws.cell(n, c)
        cell.value = vals[c]
        tpl = ws.cell(7, c)
        cell.font = copy.copy(tpl.font); cell.alignment = copy.copy(tpl.alignment); cell.border = copy.copy(tpl.border); cell.fill = copy.copy(tpl.fill)
        if vals[c] == TODO:
            cell.fill = amarillo
    ws.row_dimensions[n].height = 90
wb.save(DIR + r"\Planilla_ESTADO_DEL_ARTE_26_articulos.xlsx")
print(len(rows), "filas")
for i in range(7, 33):
    print(ws.cell(i, 2).value, "|", ws.cell(i, 3).value[:70])
