"""Word v44: cambia las tres imágenes que decían «cohorte» (pipeline, ciclo de mejora y metodología completa) y quita las imágenes que ya no se usan."""
import os
import re
import sys
import zipfile

import docx
from docx.oxml.ns import qn
from lxml import etree
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = r"F:\TESISJF\tesis\desarrollo\reports"
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v43.docx")
MAP = {"pipeline_metodologia_D099.png": "image14.png", "ciclo_automejora.png": "image7.png", "workflow_horizontal_D099.png": "image9.png"}
par = d.part
for drw in d.element.body.xpath(".//w:drawing"):
    blip = drw.xpath('.//*[local-name()="blip"]')[0]
    part = par.related_parts[blip.get(qn("r:embed"))]
    nm = part.partname.split("/")[-1]
    for src, tgt in MAP.items():
        if nm == tgt:
            ruta = os.path.join(R, src)
            part._blob = open(ruta, "rb").read()
            w, h = Image.open(ruta).size
            ext = drw.xpath('.//*[local-name()="extent"]')[0]
            cx = int(ext.get("cx")); cy = int(cx * h / w)
            ext.set("cy", str(cy))
            for e in drw.xpath('.//*[local-name()="ext"]'):
                if e.get("cx"):
                    e.set("cx", str(cx)); e.set("cy", str(cy))
            print("reemplazada", nm, "<-", src)
xml = etree.tostring(par.element).decode()
usados = set(re.findall(r'(?:embed|id|link)="(rId\d+)"', xml))
quitadas = []
for rid, rel in list(par.rels.items()):
    if rel.reltype.endswith("/image") and rid not in usados:
        quitadas.append(rel.target_part.partname.split("/")[-1])
        del par.rels[rid]
print("imágenes sin uso quitadas:", quitadas)
SAL = r"F:\TESISJF\Articulo_Investigacion_CIS2026_v44.docx"
d.save(SAL)
d2 = docx.Document(SAL)
print("dibujos:", len(d2.element.body.xpath(".//w:drawing")))
print("media en el paquete:", sorted(n.split("/")[-1] for n in zipfile.ZipFile(SAL).namelist() if n.startswith("word/media")))
