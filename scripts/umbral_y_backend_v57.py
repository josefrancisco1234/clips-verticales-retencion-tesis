"""Word v57: (1) cada mención de la fórmula de 17 variables aclara que de las 17 variables que se escanean en cada clip solo cuentan las que superan el umbral
(percentil >= 0.75 de su video) para evitar ruido; en los clips elegidos son 7.6 de 17 en promedio (4 a 12; 6 a 9 en el 80 % de los casos; medido en 150 videos, 750 clips);
(2) la Figura 6 aclara que todo es el backend: la página web solo hace llamadas al servidor."""
import copy
import sys

import docx
from docx.oxml.ns import qn
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v56.docx")
CORTO = " Se escanean las 17 variables en cada clip y solo cuentan las que superan el umbral (el 25 % más alto de su video), para evitar ruido."
LARGO = (" En cada clip se escanean las 17 variables de la fórmula y solo se conservan las que superan el umbral (percentil de 0.75 o más dentro de su propio video), de modo que el ruido de las variables que no destacan no suma al puntaje; "
         "en los clips elegidos, 7.6 de las 17 variables superan el umbral en promedio (entre 6 y 9 en el 80 % de los casos; medido en 750 clips de 150 videos).")
INSERTAR = {
    "Las contribuciones son:": CORTO,                       # introducción
    "Por cada candidato se calculan 71 variables": None,
    "Los candidatos se ordenan por puntaje": CORTO,         # 4.6
    "Modelo final adoptado (D-098)": LARGO,                 # 4.7: definición completa
    "Se compararon cuatro formas de puntuar": CORTO,        # 5.8
    "El modelo final del producto es la fórmula de 17 variables": CORTO,   # 6.8
    "En síntesis, con solo audio y texto": None,
}
n = 0
for p in d.paragraphs:
    for clave, texto in INSERTAR.items():
        if texto and clave in p.text and len(p.runs) >= 1:
            p.runs[-1].text = p.runs[-1].text.rstrip() + texto
            n += 1
            break
# conclusiones: mención de la fórmula de 17 variables
for p in d.paragraphs:
    if p.text.startswith("El modelo final del producto es la fórmula de 17 variables"):
        pass
print("párrafos con la aclaración del umbral:", n)

# Figura 6: imagen nueva y leyenda
cap = next(p for p in d.paragraphs if p.text.strip().startswith("Figura 6. Metodología completa"))
dr = cap._p.getprevious().xpath(".//w:drawing")[0]
ruta = r"F:\TESISJF\tesis\desarrollo\reports\workflow_horizontal_D099.png"
rid = dr.xpath('.//*[local-name()="blip"]')[0].get(qn("r:embed"))
d.part.related_parts[rid]._blob = open(ruta, "rb").read()
w, h = Image.open(ruta).size
ext = dr.xpath('.//*[local-name()="extent"]')[0]
cx = int(ext.get("cx")); cy = int(cx * h / w)
ext.set("cy", str(cy))
for e in dr.xpath('.//*[local-name()="ext"]'):
    if e.get("cx"):
        e.set("cx", str(cx)); e.set("cy", str(cy))
cap.runs[-1].text = cap.runs[-1].text.rstrip().rstrip(".") + ". Todo este flujo es el backend: la página web solo hace llamadas (peticiones) al servidor y este ejecuta el proceso completo."
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v57.docx")
print("ok", len(d.element.body.xpath(".//w:drawing")), "dibujos |", cap.text[-170:])
