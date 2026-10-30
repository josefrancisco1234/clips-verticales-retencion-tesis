"""Arma Articulo_Investigacion_CIS2026_v14.docx desde la v13: referencias con DOI o URL verificada, tablas y figuras en estilo APA 7,
parámetros de candidatos buscados automáticamente (D-088/D-089). No toca v11, v12 ni v13."""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v13.docx")
DST = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v14.docx")
d = docx.Document(str(SRC))


def find(start, after=0):
    for i, p in enumerate(d.paragraphs):
        if i >= after and p.text.strip().startswith(start):
            return i
    raise KeyError(start)


def set_text(p, text):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)


def has_drawing(p):
    x = p._p.xml
    return "<w:drawing" in x or "<w:pict" in x or "<w:object" in x


def clone(tpl, text, bold=None, italic=None):
    el = copy.deepcopy(tpl._p)
    q = docx.text.paragraph.Paragraph(el, tpl._parent)
    set_text(q, text)
    for r in q.runs:
        if bold is not None:
            r.bold = bold
        if italic is not None:
            r.italic = italic
    return q


# ------------------------------------------------------------ referencias (DOI o URL verificada)
URLS = {
    "Burges, C. J. C. (2010)": "https://www.microsoft.com/en-us/research/publication/from-ranknet-to-lambdarank-to-lambdamart-an-overview/",
    "Ke, G., Meng, Q.": "https://papers.nips.cc/paper_files/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html",
    "Lundberg, S. M.": "https://papers.nips.cc/paper_files/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html",
}
for k, url in URLS.items():
    p = d.paragraphs[find(k)]
    if "http" not in p.text:
        set_text(p, p.text.rstrip() + " " + url)
p = d.paragraphs[find("Park, Y., Diwan, A.")]
set_text(p, "Park, Y., Diwan, A., Harwath, D., & Choi, E. (2025). Rhapsody: A dataset for highlight detection in podcasts. arXiv. https://doi.org/10.48550/arXiv.2505.19429")

# ------------------------------------------------------------ candidatos automáticos (D-088/D-089)
p = d.paragraphs[find("El audio se transcribe con Whisper")]
nuevo = clone(p, (
    "Los parámetros que controlan esta etapa no se fijaron a mano. La duración máxima del clip y el solapamiento permitido entre clips se buscaron de forma automática entre 12 "
    "combinaciones, con validación cruzada interna por canal y con el exceso de acierto sobre un azar restringido a las mismas ventanas como criterio, para que los clips más "
    "largos no ganen solo por cubrir más tiempo. La búsqueda eligió un solapamiento de 30 % y una duración máxima de entre 45 y 60 s, y en un conjunto reservado no hubo "
    "diferencia significativa entre ambas duraciones (p = 0.49), por lo que se mantuvo el límite de 45 s (variante V1). Los límites de oración provienen de la transcripción de "
    "Whisper (Radford et al., 2023), un modelo profundo, y el modelo que ordena los candidatos se aprende de los datos."))
p._p.addnext(nuevo._p)
p6 = d.paragraphs[find("Para atender la observación de explorar nuevas formas")]
p6._p.addnext(clone(p6, (
    "La búsqueda automática de los parámetros de generación de candidatos coincidió con la regla fijada: con 526 videos, el solapamiento de 30 % resultó óptimo en tres de las "
    "cuatro duraciones probadas y las duraciones máximas de 45 s y 60 s no se distinguieron en el conjunto reservado (exceso de acierto sobre el azar restringido de +0.214 y +0.175, "
    "p = 0.49)."))._p)

# ------------------------------------------------------------ estilo APA 7: tablas y figuras
ROM = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}
TITLES = {
    1: "Composición del conjunto de datos",
    2: "Las 71 variables, su fórmula y su peso en la fórmula de puntuación (— = no entra a la fórmula)",
    3: "Variables de la fórmula y su peso",
    4: "Partición del conjunto de datos",
    5: "Desempeño de cada paso en la cohorte fresca 1 (93 videos)",
    6: "Réplica en la cohorte 2 y evaluación conjunta",
    7: "Matriz de confusión por ventana (557 videos, solo contenido)",
    8: "Resumen de las pruebas posteriores (todas sin mejora confirmada)",
}
caps = [p for p in d.paragraphs if re.match(r"^TABLA [IVX]+\.", p.text.strip())]
for p in caps:
    n = ROM[re.match(r"^TABLA ([IVX]+)\.", p.text.strip()).group(1)]
    num = clone(p, f"Tabla {n}", bold=True, italic=False)
    ttl = clone(p, TITLES[n], bold=False, italic=True)
    p._p.addprevious(num._p)
    p._p.addprevious(ttl._p)
    p._p.getparent().remove(p._p)
figs = [p for p in d.paragraphs if re.match(r"^Fig\. \d+\.", p.text.strip())]
for p in figs:
    m = re.match(r"^Fig\. (\d+)\.\s*(.*)$", p.text.strip(), re.S)
    n, ttl = m.group(1), m.group(2).strip()
    prev = p._p.getprevious()
    pp = docx.text.paragraph.Paragraph(prev, p._parent)
    target = prev if has_drawing(pp) else p._p
    a = clone(p, f"Figura {n}", bold=True, italic=False)
    b = clone(p, ttl, bold=False, italic=True)
    target.addprevious(a._p)
    target.addprevious(b._p)
    p._p.getparent().remove(p._p)

# referencias cruzadas en el texto (no se editan párrafos con dibujos)
rx_t = re.compile(r"\bTabla (VIII|VII|VI|IV|V|III|II|I)\b")
for p in d.paragraphs:
    if has_drawing(p):
        continue
    t = p.text
    t2 = rx_t.sub(lambda m: f"Tabla {ROM[m.group(1)]}", t)
    t2 = re.sub(r"\bFig\. (\d+)", r"Figura \1", t2)
    if t2 != t and not re.match(r"^(Tabla|Figura) \d+$", t.strip()):
        set_text(p, t2)

d.save(str(DST))
d2 = docx.Document(str(DST))
txt = "\n".join(p.text for p in d2.paragraphs)
print("guardado:", DST, "| párrafos:", len(d2.paragraphs))
print("TABLA romanas restantes:", len(re.findall(r"TABLA [IVX]+", txt)), "| 'Fig.' restantes:", len(re.findall(r"Fig\. \d", txt)))
print("Tablas:", sorted(set(re.findall(r"^Tabla \d+$", txt, re.M))), "| Figuras:", sorted(set(re.findall(r"^Figura \d+$", txt, re.M))))
