"""Word v62: cada mención de las 17 variables aclara que por segmento se escanean entre 17 y 23; se reemplazan las figuras regeneradas con la misma nota."""
import os
import re
import sys

import docx
from docx.oxml.ns import qn
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = r"F:\TESISJF\tesis\desarrollo\reports"
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v61.docx")
NOTA = " (entre 17 y 23 escaneadas por segmento)"
PAT = re.compile(r"(17 variables|17 banderas)(?! \(entre 17 y 23)")
n_par = n_tab = 0


def poner(par):
    global n_par
    if "entre 17 y 23" in par.text or par.text.strip().startswith(("Tabla 2.", "Tabla 3.")):
        return False
    for r in par.runs:
        if PAT.search(r.text):
            r.text = PAT.sub(lambda m: m.group(1) + NOTA, r.text, count=1)
            return True
    return False


for p in d.paragraphs:
    if poner(p):
        n_par += 1
for t in d.tables[2:]:
    h = t.cell(0, 0).text
    if h.startswith(("Algoritmo", "Variable")):
        continue
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                if "17 variables" in p.text and "entre 17" not in p.text:
                    for r in p.runs:
                        if PAT.search(r.text):
                            r.text = PAT.sub(lambda m: m.group(1) + NOTA, r.text, count=1)
                            n_tab += 1
                            break
print("párrafos:", n_par, "| celdas de tabla:", n_tab)
FIG = {"Figura 1.": "pipeline_metodologia_D099.png", "Figura 2.": "audio_vs_transcripcion_D099.png", "Figura 3.": "pipeline_clip_D099.png",
       "Figura 4.": "scoring_horizontal_D099.png", "Figura 5.": "ciclo_automejora.png", "Figura 6.": "workflow_horizontal_D099.png"}
for p in d.paragraphs:
    for k, img in FIG.items():
        if p.text.strip().startswith(k):
            prev = p._p.getprevious()
            dr = prev.xpath(".//w:drawing")
            if not dr:
                continue
            dr = dr[0]
            ruta = os.path.join(R, img)
            rid = dr.xpath('.//*[local-name()="blip"]')[0].get(qn("r:embed"))
            d.part.related_parts[rid]._blob = open(ruta, "rb").read()
            w, h = Image.open(ruta).size
            ext = dr.xpath('.//*[local-name()="extent"]')[0]
            cx = int(ext.get("cx")); cy = int(cx * h / w)
            ext.set("cy", str(cy))
            for e in dr.xpath('.//*[local-name()="ext"]'):
                if e.get("cx"):
                    e.set("cx", str(cx)); e.set("cy", str(cy))
            print("figura actualizada:", k, img)
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v62.docx")
print("dibujos:", len(d.element.body.xpath(".//w:drawing")))
