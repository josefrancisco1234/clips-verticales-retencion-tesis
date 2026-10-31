"""Word v32: agrega a 4.7 la figura del puntaje de un video (ejemplo real) con su explicación; renumera Figuras 5-10 a 6-11."""
import copy, re, sys
from pathlib import Path
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v31.docx")
P = lambda s: next(p for p in d.paragraphs if p.text.strip().startswith(s))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


def clone(tpl, text, after):
    el = copy.deepcopy(tpl._p); after._p.addnext(el)
    q = Paragraph(el, tpl._parent); st(q, text); return q


def renum(old):
    for p in d.paragraphs:
        for r in p.runs:
            r.text = re.sub(rf"Figura {old}\b", f"Figura {old + 1}", r.text)


for old in range(10, 4, -1):
    renum(old)
t3 = P("Selección y recorte.")
cap_t = P("Figura 4. ")
ip = clone(t3, "", after=t3)
ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
ip.paragraph_format.first_line_indent = 0
ip.add_run().add_picture(str(ROOT / "reports" / "scoring_horizontal_D099.png"), width=Cm(16.2))
cap = clone(cap_t, "Figura 5. Cómo un video recibe su puntaje, con un ejemplo real de 400 candidatos: variables, percentil dentro del video, bandera 0/1, suma ponderada, escala de 0 a 99 y selección de cinco clips.", after=ip)
txt = ("Cálculo del puntaje de un clip (Figura 5). Cada peso es la mediana, entre 121 videos de desarrollo, de la correlación parcial de Spearman de la variable con el calor real, controlando la posición del clip; se conservaron las 17 variables con |ρ| ≥ 0.05 y prueba de signos significativa con Bonferroni (0.05/68). Para un candidato, cada variable se convierte en su percentil dentro del video y pasa a bandera 1 si está en el 25 % más alto (percentil ≥ 0.75). El puntaje crudo es la suma de peso por bandera (los pesos negativos restan) y se lleva a la escala de 0 a 99 con (crudo − mín) / (máx − mín) × 99, donde mín es la suma de los pesos negativos (−0.4851) y máx la de los positivos (+1.2400); la escala es absoluta y no depende del número de candidatos. En el ejemplo, el mejor clip del video tiene nueve banderas en 1 que suman +1.0118 y recibe 86 puntos. Los cinco clips elegidos tras la supresión de no máximos reciben 86, 83, 81, 80 y 79.")
clone(t3, txt, after=cap)
_p4b = P("Modelo final adoptado (D-098)")
_old = "y el puntaje de 0 a 99 es el percentil del puntaje dentro del video."
assert _old in _p4b.text, "no se encontró la frase del percentil"
st(_p4b, _p4b.text.replace(_old, "y el puntaje de 0 a 99 resulta de llevar el puntaje crudo a una escala absoluta entre el mínimo y el máximo posibles de la fórmula (Figura 5)."))
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v33.docx")
print("ok")
