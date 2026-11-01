"""Word v48: agrega en 4.3 cómo creció el conjunto de videos (473 → 526 → 557 → unos 770) y que la base sigue ampliándose; y en trabajos futuros la ampliación continua.
Cifras de docs/DECISIONES.md (D-046, D-080, D-064) y del propio artículo."""
import copy
import sys

import docx
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v47.docx")
base = next(p for p in d.paragraphs if p.text.strip().startswith("Siguiendo la receta de Rhapsody"))
el = copy.deepcopy(base._p)
base._p.addnext(el)
q = Paragraph(el, base._parent)
for r in q.runs[1:]:
    r._r.getparent().remove(r._r)
q.runs[0].text = ("Crecimiento del conjunto. La base de datos se fue ampliando a medida que avanzó el trabajo, y cada resultado se reporta con el tamaño que tenía en ese momento. "
                  "El análisis empezó con unos 470 videos (473: 121 de desarrollo y 352 de confirmación), pasó a 526 videos de desarrollo al ampliar el conjunto (419 de entrenamiento y 107 reservados), llegó a 557 videos que no se usaron para fijar la fórmula y a unos 770 videos con curva al cierre de esta versión. "
                  "Es un conjunto pequeño frente a los 13 000 episodios de Rhapsody (Park et al., 2025), pero no está cerrado: la descarga y el cálculo de variables continúan, y el número final se reportará con los videos que se hayan analizado hasta el último momento.")
fut = next(p for p in d.paragraphs if p.text.strip().startswith("9. TRABAJOS FUTUROS"))
sig = Paragraph(fut._p.getnext(), fut._parent)
sig.runs[-1].text += " Seguir ampliando la base de videos, pues en la curva de aprendizaje cada duplicación de los datos suma cerca de un punto de acierto@5 y los modelos de aprendizaje profundo podrían aprovechar un volumen mayor."
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v48.docx")
print("ok", len(d.element.body.xpath(".//w:drawing")), "dibujos")
