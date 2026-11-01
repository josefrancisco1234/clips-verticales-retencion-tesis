"""Mapa de fuentes: en qué secciones del artículo se cita cada referencia (y cuáles son los 26 artículos del Excel del estado del arte)."""
import re
import sys

import docx
import openpyxl

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORD = sys.argv[1] if len(sys.argv) > 1 else r"F:\TESISJF\Articulo_Investigacion_CIS2026_v44.docx"
XLSX = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\7_Excel_resumenes_26_articulos\Planilla_ESTADO_DEL_ARTE_26_articulos.xlsx"
SAL = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\MAPA_FUENTES_EN_EL_ARTICULO.txt"
d = docx.Document(WORD)
P = [p.text.strip() for p in d.paragraphs]
i_ref = [n for n, t in enumerate(P) if t.upper().startswith("REFERENCIAS")][-1]
REFS = [t for t in P[i_ref + 1:] if t]
HEAD = re.compile(r"^(\d{1,2}(?:\.\d{1,2})?)[ .]+(\S.{2,90})$")
sec, cuerpo = "Portada y resumen", []
for t in P[:i_ref]:
    m = HEAD.match(t)
    if m and len(t) < 95 and not re.search(r"[.;]$", t) and (m.group(1).count(".") == 1 or t.isupper()):
        sec = f"{m.group(1)} {m.group(2).title() if t.isupper() else m.group(2)}"
        continue
    if t:
        cuerpo.append((sec, t))
for tb in d.tables:
    for row in tb.rows:
        for c in row.cells:
            if c.text.strip():
                cuerpo.append(("Tablas (Tabla 2 y otras)", c.text.strip()))


def clave(ref):
    ap = re.match(r"([^,(]+)", ref).group(1).strip()
    ap1 = ap.split()[0] if ap else ap
    y = re.search(r"\((\d{4})[a-z]?\)", ref)
    return ap1, y.group(1) if y else ""


def donde(ref):
    ap, y = clave(ref)
    if not y:
        return []
    pat = re.compile(re.escape(ap) + r"[^()]{0,70}?" + y + r"|" + re.escape(ap) + r".{0,60}?" + y)
    res = {}
    for s, t in cuerpo:
        for m in pat.finditer(t):
            res.setdefault(s, []).append(re.sub(r"\s+", " ", t[max(0, m.start() - 70):m.end() + 40]))
    return res


ws = openpyxl.load_workbook(XLSX).active
lista26 = [(r - 6, ws.cell(r, 13).value) for r in range(7, 33)]
lineas = ["MAPA DE FUENTES: dónde se usa cada referencia en el artículo (" + WORD.split("\\")[-1] + ")", "",
          "PARTE 1. LOS 26 ARTÍCULOS DEL EXCEL DEL ESTADO DEL ARTE", ""]
faltan = []
for n, ref in lista26:
    w = donde(ref)
    ap, y = clave(ref)
    lineas.append(f"{n}. {ap} ({y}) — Excel fila {n + 6}")
    if not w:
        faltan.append(ref[:60])
        lineas.append("   (no se encontró la cita en el cuerpo)")
    for s, frases in w.items():
        lineas.append(f"   - {s}: «…{frases[0]}…»" + (f" (+{len(frases) - 1} más)" if len(frases) > 1 else ""))
    lineas.append("")
en26 = {r[:45] for _, r in lista26}
lineas += ["PARTE 2. LAS DEMÁS REFERENCIAS (métodos, estadística, herramientas y fuentes de la Tabla 2)", ""]
for ref in REFS:
    if ref[:45] in en26:
        continue
    w = donde(ref)
    ap, y = clave(ref)
    lineas.append(f"{ap} ({y})" + ("" if w else " — solo aparece en la lista de referencias o con otro formato de cita"))
    for s, frases in w.items():
        lineas.append(f"   - {s}: «…{frases[0]}…»")
lineas.append("")
open(SAL, "w", encoding="utf-8").write("\n".join(lineas))
print("26 del Excel sin cita encontrada:", faltan)
print("referencias en el Word:", len(REFS), "| líneas del mapa:", len(lineas))
