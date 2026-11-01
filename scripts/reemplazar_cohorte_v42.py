"""Word v42: reemplaza la palabra «cohorte» por «muestra nueva» y la define una vez en 5.4. Solo toca los runs de texto que coinciden (los runs con imagen no se tocan)."""
import re
import sys

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v41.docx")


def cap(m, nuevo):
    return nuevo[0].upper() + nuevo[1:] if m.group(0)[0].isupper() else nuevo


REG = [
    (r"[Cc]ohortes frescas", lambda m: cap(m, "muestras nuevas")),
    (r"[Cc]ohortes nuevas", lambda m: cap(m, "muestras nuevas")),
    (r"[Cc]ohorte fresca (\d)", lambda m: cap(m, "muestra nueva") + " " + m.group(1)),
    (r"[Cc]ohorte (\d)", lambda m: cap(m, "muestra nueva") + " " + m.group(1)),
    (r"[Cc]ohorte fresca", lambda m: cap(m, "muestra nueva")),
    (r"segunda cohorte", lambda m: "segunda muestra nueva"),
    (r"[Cc]ohortes", lambda m: cap(m, "muestras")),
    (r"[Cc]ohorte", lambda m: cap(m, "muestra")),
    (r"fresh cohorts", lambda m: "new samples"),
    (r"fresh cohort", lambda m: "new sample"),
    (r"second cohort", lambda m: "second new sample"),
    (r"[Cc]ohorts?", lambda m: "samples" if m.group(0).endswith("s") else "sample"),
]


def arreglar(r):
    t = r.text
    for pat, fn in REG:
        t = re.sub(pat, fn, t)
    if t != r.text:
        r.text = t
        return 1
    return 0


n = 0
for p in d.paragraphs:
    for r in p.runs:
        if re.search(r"(?i)cohort", r.text):
            n += arreglar(r)
for t in d.tables:
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    if re.search(r"(?i)cohort", r.text):
                        n += arreglar(r)
print("runs cambiados:", n)
# definición en 5.4 y precisión en el resumen
for p in d.paragraphs:
    for r in p.runs:
        if "muestras nuevas (Tabla 4)." in r.text:
            r.text = r.text.replace("muestras nuevas (Tabla 4).", "muestras nuevas (Tabla 4). Una muestra nueva es un grupo de videos buscado con consultas distintas después de fijar la fórmula y los modelos; no se usó para ajustar nada y se evalúa una sola vez.")
            print("definición insertada")
        if "En una muestra nueva de 93 videos," in r.text:
            r.text = r.text.replace("En una muestra nueva de 93 videos,", "En una muestra nueva de 93 videos (no usados para ajustar nada),")
        if "On a new sample of 93 videos," in r.text:
            r.text = r.text.replace("On a new sample of 93 videos,", "On a new sample of 93 videos (not used to fit anything),")
res = next(p for p in d.paragraphs if p.text.startswith("La producción de clips cortos"))
ab = next(p for p in d.paragraphs if p.text.startswith("Abstract:"))
print("palabras resumen/abstract:", len(res.text.split()), len(ab.text.split()) - 1)
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v42.docx")
resto = [p.text[:80] for p in d.paragraphs if re.search(r"(?i)cohort", p.text)] + [c.text[:60] for t in d.tables for r_ in t.rows for c in r_.cells if re.search(r"(?i)cohort", c.text)]
print("quedan con cohorte:", resto)
