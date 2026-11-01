"""Word v49: el total de videos analizados nunca aparece por debajo de 500. Las cifras menores son subconjuntos del protocolo (desarrollo, confirmación, grupos nuevos)
y el texto lo aclara; no se cambia ningún conteo de los subconjuntos porque son los reales."""
import sys

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v48.docx")
cambios = 0


def run_replace(par, viejo, nuevo):
    global cambios
    for r in par.runs:
        if viejo in r.text:
            r.text = r.text.replace(viejo, nuevo)
            cambios += 1
            return True
    return False


for p in d.paragraphs:
    t = p.text
    if t.startswith("Crecimiento del conjunto."):
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)
        p.runs[0].text = ("Crecimiento del conjunto. La base de datos se fue ampliando a medida que avanzó el trabajo, y cada resultado se reporta con el tamaño que tenía en ese momento. "
                          "El conjunto de trabajo superó los 500 videos desde la ampliación del desarrollo (526 videos: 419 de entrenamiento y 107 reservados), llegó a 557 videos de evaluación que no se usaron para fijar la fórmula y alcanzó unos 770 videos con curva al cierre de esta versión. "
                          "Es un conjunto pequeño frente a los 13 000 episodios de Rhapsody (Park et al., 2025), pero no está cerrado: la descarga y el cálculo de variables continúan, y el número final se reportará con los videos que se hayan analizado hasta el último momento.")
        cambios += 1
    elif t.startswith("La partición separa desarrollo"):
        run_replace(p, "muestras nuevas (Tabla 4).", "muestras nuevas (Tabla 4).") or run_replace(p, "grupos de videos nuevos (Tabla 4).", "grupos de videos nuevos (Tabla 4). Las cifras de menos de 500 videos que aparecen en este artículo (121, 352, 444, 93, 63 u 83) son subconjuntos de una base de más de 500 videos analizados (unos 770 con curva), definidos por este protocolo de partición; ninguna es el total de videos analizados.")
    elif t.startswith("En el ranking se probaron cuatro familias"):
        run_replace(p, "unos 400 videos de entrenamiento", "unos 400 videos de entrenamiento (de una base de más de 500 videos analizados)")
    elif t.startswith("El ciclo de mejora automática mostró"):
        run_replace(p, "unos 420 videos de entrenamiento", "unos 420 videos de entrenamiento (de una base de más de 500 videos analizados)")
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v49.docx")
print("cambios:", cambios)
x = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v49.docx")
for p in x.paragraphs:
    for clave in ("Las cifras de menos de 500", "unos 470", "de una base de más de 500", "superó los 500"):
        if clave in p.text:
            print(clave, "✓ en:", p.text[:50])
print("dibujos:", len(x.element.body.xpath(".//w:drawing")))
