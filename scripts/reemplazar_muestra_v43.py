"""Word v43: «muestra nueva» pasa a «grupo de videos nuevos» (más específico: son grupos de videos, no de clips). Solo toca runs con texto."""
import re
import sys

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v42.docx")
S = [
    ("Una muestra nueva es un grupo de videos buscado con consultas distintas después de fijar la fórmula y los modelos; no se usó para ajustar nada y se evalúa una sola vez.",
     "Un grupo de videos nuevos es un conjunto de videos buscado con consultas distintas después de fijar la fórmula y los modelos; no se usó para ajustar nada y se evalúa una sola vez."),
    ("En una muestra nueva de 93 videos", "En un grupo de 93 videos nuevos"),
    ("en una segunda muestra nueva,", "en un segundo grupo,"),
    ("(muestra nueva 1, 93)", "(grupo nuevo 1, 93)"),
    ("On a new sample of 93 videos", "On a new group of 93 videos"),
    ("on a second new sample", "on a second group"),
    ("de la primera muestra nueva", "del primer grupo de videos nuevos"),
    ("en la primera muestra nueva", "en el primer grupo de videos nuevos"),
    ("la primera muestra nueva", "el primer grupo de videos nuevos"),
    ("una segunda muestra nueva", "un segundo grupo de videos nuevos"),
    ("La segunda muestra nueva", "El segundo grupo de videos nuevos"),
    ("la segunda muestra nueva", "el segundo grupo de videos nuevos"),
    ("de la muestra nueva", "del grupo de videos nuevos"),
    ("a la muestra nueva", "al grupo de videos nuevos"),
    ("La muestra nueva", "El grupo de videos nuevos"),
    ("la muestra nueva", "el grupo de videos nuevos"),
    ("Una muestra nueva", "Un grupo de videos nuevos"),
    ("una muestra nueva", "un grupo de videos nuevos"),
    ("de las muestras nuevas", "de los grupos de videos nuevos"),
    ("a las muestras nuevas", "a los grupos de videos nuevos"),
    ("Las muestras nuevas", "Los grupos de videos nuevos"),
    ("las muestras nuevas", "los grupos de videos nuevos"),
    ("Muestras nuevas", "Grupos de videos nuevos"),
    ("muestras nuevas", "grupos de videos nuevos"),
    ("Muestra nueva", "Grupo de videos nuevos"),
    ("muestra nueva", "grupo de videos nuevos"),
    ("cada muestra", "cada grupo"),
    ("entre muestras", "entre grupos"),
    ("new samples", "new groups of videos"),
    ("new sample", "new group of videos"),
]
n = 0


def arreglar(r):
    t = r.text
    for a, b in S:
        t = t.replace(a, b)
    if t != r.text:
        r.text = t
        return 1
    return 0


for p in d.paragraphs:
    for r in p.runs:
        if re.search(r"(?i)muestra|sample", r.text):
            n += arreglar(r)
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if re.search(r"(?i)muestra|sample", r.text):
                        n += arreglar(r)
print("runs cambiados:", n)
res = next(p for p in d.paragraphs if p.text.startswith("La producción de clips cortos"))
ab = next(p for p in d.paragraphs if p.text.startswith("Abstract:"))
print("palabras resumen/abstract:", len(res.text.split()), len(ab.text.split()) - 1)
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v43.docx")
resto = [p.text[:90] for p in d.paragraphs if re.search(r"(?i)muestra nueva|muestras nuevas|cohort", p.text)]
print("restos:", resto)
print("dibujos", len(d.element.body.xpath(".//w:drawing")))
