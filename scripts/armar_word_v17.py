"""Arma Articulo_Investigacion_CIS2026_v17.docx desde la v16: explica el ciclo de mejora automática del modelo (minero de papers,
exploración de ecuaciones y variables, campeón/retador), con figura, Algoritmo 5, resultados D-092/D-093 y discusión. No toca versiones anteriores."""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v16.docx")
DST = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v17.docx")
d = docx.Document(str(SRC))


def find(start, after=0):
    for i, p in enumerate(d.paragraphs):
        if i >= after and p.text.strip().startswith(start):
            return i
    raise KeyError(start)


def P(start, after=0):
    return d.paragraphs[find(start, after)]


def set_text(p, text):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)


def clone(tpl, text):
    el = copy.deepcopy(tpl._p)
    q = docx.text.paragraph.Paragraph(el, tpl._parent)
    set_text(q, text)
    return q


def replace_in(p, a, b):
    assert a in p.text, f"no encontrado: {a[:70]}"
    set_text(p, p.text.replace(a, b, 1))


BODY = P("La creación de contenido audiovisual")
HEAD = P("3.7 ")
CAPS = [p for p in d.paragraphs if re.match(r"^Figura \d+\. ", p.text)]
CAP_TPL = CAPS[-1]

# ---------------------------------------------------------------- renumerar figuras >= 4 (en las partes con un solo formato por rótulo)
for p in d.paragraphs:
    if "<w:drawing" in p._p.xml:
        continue
    for r in p.runs:
        if re.search(r"Figura ([4-9])\b", r.text):
            r.text = re.sub(r"Figura ([4-9])\b", lambda m: f"Figura {int(m.group(1)) + 1}", r.text)

# ---------------------------------------------------------------- 1. Introducción
replace_in(P("Para cerrar esta brecha"),
           "; y (v) un explorador automático de ecuaciones basado en aprendizaje profundo que propone fórmulas legibles y las somete al mismo protocolo de validación.",
           "; y (v) un ciclo de mejora automática que combina un minero de literatura científica, un explorador de ecuaciones basado en aprendizaje profundo y un protocolo "
           "campeón/retador, y que somete cada idea al mismo protocolo de validación.")

# ---------------------------------------------------------------- 2. 4.9: opción de 68 variables
q = P("Para que el criterio de puntuación no dependa")
set_text(q, q.text + " La red puede recibir las 17 variables de la fórmula o las 68 variables de contenido, y dejar que la penalización L1 elija cuáles entran en la ecuación, "
         "lo que permite descubrir variables además de formas nuevas de combinarlas.")

# ---------------------------------------------------------------- 3. 4.10 Ciclo de mejora automática
anchor = P("5. EXPERIMENTACIÓN")
anchor._p.addprevious(clone(HEAD, "4.10 Ciclo de mejora automática del sistema")._p)
anchor._p.addprevious(clone(BODY, (
    "El sistema no es una fórmula fija: se diseñó como un ciclo que busca mejorar solo, siempre bajo el mismo protocolo de validación (Figura 4). Los videos entran por un proceso "
    "de extracción, transformación y carga (ETL) que descarga el audio y la curva con yt-dlp, transcribe con Whisper, calcula las variables de audio y de texto y guarda todo en una "
    "base de datos de archivos, una carpeta por tipo de dato y un índice por video (BD_TESIS). Sobre esa base, el ranking puntúa cada ventana con las variables y selecciona los "
    "cinco clips (secciones 4.5 y 4.6). Encima de ese flujo operan tres mecanismos automáticos."))._p)
anchor._p.addprevious(clone(BODY, (
    "El primero es un minero de literatura: consulta la API abierta de OpenAlex con 15 consultas sobre detección de momentos, retención de audiencia y habla en trabajos desde 2020, "
    "reúne los que tienen resumen, cuenta qué señales medibles mencionan (pausas, tono, risa, turnos de palabra, muletillas, entre otras) y las compara con las 71 variables que ya existen "
    "(OpenAlex, 2026). Las señales que no están cubiertas se convierten en variables candidatas. Esta minería es por patrones sobre título y resumen y no equivale a leer el trabajo "
    "completo, por lo que solo propone candidatos y no decide nada."))._p)
anchor._p.addprevious(clone(BODY, (
    "El segundo es el explorador de ecuaciones (sección 4.9), que prueba formas nuevas de combinar las variables, incluidas las candidatas, y entrega fórmulas legibles. El tercero es el "
    "protocolo campeón/retador: cada fórmula o variable nueva se enfrenta al modelo vigente en un conjunto reservado por canal y solo se promueve si mejora el F1 con una prueba de Wilcoxon "
    "unilateral de p menor que 0.05, con corrección cuando se repiten rondas sobre el mismo conjunto; después se confirma una sola vez en una cohorte fresca con la hipótesis escrita antes "
    "(Algoritmo 5). Cada ronda queda registrada en la bitácora, incluidos los resultados negativos, de modo que el ciclo mejora solo cuando hay evidencia y no por acumulación de variantes."))._p)
# imagen + rótulo
pic_p = d.add_paragraph()
pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
pic_p.add_run().add_picture(str(ROOT / "reports" / "ciclo_automejora.png"), width=Inches(6.4))
pic_p.paragraph_format.keep_with_next = True
cap = clone(CAP_TPL, "")
for r in cap.runs[1:]:
    r._r.getparent().remove(r._r)
cap.runs[0].text = "Figura 4. "
cap.runs[0].bold = True
cap.runs[0].italic = False
run = cap.add_run("Ciclo de mejora automática del sistema: de los videos a la promoción de un nuevo campeón.")
run.bold = False
run.italic = True
cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
anchor._p.addprevious(pic_p._p)
anchor._p.addprevious(cap._p)

# Algoritmo 5 en caja
lineas = [
    "Requiere: base de datos B, campeón C, número de rondas R.",
    "Asegura: campeón vigente y bitácora de rondas.",
    "1: para r = 1 hasta R hacer",
    "2:   B ← B ∪ videos nuevos        ▷ ETL: descarga, transcripción y variables; las cohortes frescas se congelan antes de mirarlas",
    "3:   S ← minero de papers(consultas)        ▷ señales medibles no cubiertas por las 71 variables",
    "4:   para cada señal s en S hacer",
    "5:     calcular las variables candidatas de s y preregistrar la prueba",
    "6:   fin para",
    "7:   E ← explorador de ecuaciones(B, variables candidatas)        ▷ Algoritmo 4",
    "8:   si E supera a C con Wilcoxon unilateral p < 0.05 en el conjunto reservado entonces",
    "9:     confirmar E en una cohorte fresca, una sola vez",
    "10:    si se confirma entonces C ← E fin si",
    "11:  fin si",
    "12:  registrar la ronda en la bitácora        ▷ también los resultados negativos",
    "13: fin para",
    "14: retornar C",
]
tbl = d.add_table(rows=1, cols=1)
tbl._tbl.tblPr.append(parse_xml('<w:tblBorders %s>' % nsdecls("w") + "".join(
    f'<w:{s} w:val="single" w:sz="8" w:space="0" w:color="000000"/>' for s in ("top", "left", "bottom", "right")) + "</w:tblBorders>"))
cell = tbl.cell(0, 0)
r0 = cell.paragraphs[0].add_run("Algoritmo 5 Ciclo de mejora automática (campeón/retador con minero de papers)")
r0.bold = True
r0.font.size = Pt(9)
for ln in lineas:
    pp = cell.add_paragraph()
    rr = pp.add_run(ln)
    rr.font.name = "Consolas"
    rr.font.size = Pt(8)
    pp.paragraph_format.space_after = Pt(0)
    pp.paragraph_format.space_before = Pt(0)
anchor._p.addprevious(tbl._tbl)
anchor._p.addprevious(clone(BODY, "")._p)
anchor._p.addprevious(clone(BODY, (
    "En el Algoritmo 5, las líneas 3 a 6 corresponden al minero, la línea 7 al explorador, las líneas 8 a 11 al campeón/retador con confirmación y la línea 12 al registro. "
    "Hasta ahora ninguna ronda promovió un nuevo campeón, y los resultados se informan en la sección 6.6."))._p)

# ---------------------------------------------------------------- 4. Experimentación 5.3
q = P("El modelo de aprendizaje de referencia (R0) es LightGBM")
set_text(q, q.text + " El minero de papers consulta OpenAlex con 15 consultas y trabajos desde 2020; las variables minadas se calculan con la transcripción y los cuadros de audio ya existentes, "
         "y el explorador de 68 variables usa la misma configuración y el mismo conjunto reservado que el de 17.")

# ---------------------------------------------------------------- 5. Resultados 6.6
disc = P("7. DISCUSIÓN")
disc._p.addprevious(clone(HEAD, "6.6 Ciclo de mejora automática: literatura y variables nuevas")._p)
disc._p.addprevious(clone(BODY, (
    "El minero reunió 1 339 trabajos con resumen. Las señales que más mencionaron y que el sistema no tenía fueron el cambio de hablante y los turnos de palabra (112 trabajos), las muletillas, "
    "las disfluencias y la repetición (84), el rol de anfitrión o invitado (41) y las entidades nombradas (5). Se calcularon cuatro variables nuevas con la transcripción y el audio: la tasa de "
    "repeticiones, la tasa de muletillas, un aproximado de los cambios de hablante por minuto y la proporción de nombres propios. En 443 videos de desarrollo, agregarlas a R0 cambió el F1 de "
    "0.1304 a 0.1324 (p = 0.56) y agregarlas al submodelo de 17 variables lo cambió de 0.1386 a 0.1328 (p = 0.07); ninguna cumplió el criterio preregistrado de p menor que 0.025. La correlación "
    "mediana con el calor fue de +0.077 para los cambios de hablante y de entre -0.033 y +0.033 para las otras tres."))._p)
disc._p.addprevious(clone(BODY, (
    "Cuando el explorador recibió las 68 variables en lugar de las 17, la ecuación aprendida alcanzó un F1 de 0.1124 y un acierto de 51.4 %, frente a 0.1335 y 52.3 % de LightGBM (p = 0.90) "
    "y a 0.1337 de la ecuación de 17 variables. Con 7 rondas del explorador de 17 variables sobre el mismo conjunto reservado, el F1 varió entre 0.128 y 0.137 y ninguna ronda superó al campeón."))._p)

# ---------------------------------------------------------------- 6. Discusión
fin = P("En síntesis, con solo audio y texto")
fin._p.addprevious(clone(BODY, (
    "El ciclo de mejora automática mostró que el sistema es capaz de proponer, probar y descartar ideas por sí solo, y que en esta vuelta no encontró mejoras. Las señales que la literatura "
    "menciona con más frecuencia ya están recogidas por alguna de las 71 variables o no aportaron sobre ellas con este tamaño de datos, y dejar que la red elija entre 68 variables empeoró el "
    "resultado, lo que es coherente con que más variables aumentan el ruido cuando hay unos 420 videos de entrenamiento. Esta explicación es una hipótesis: con más datos, como los de Rhapsody, "
    "el ciclo podría encontrar variables que aquí no alcanzaron a distinguirse del ruido."))._p)

# ---------------------------------------------------------------- 7. Conclusiones y trabajos futuros
q = P("Este trabajo propuso y evaluó un pipeline abierto")
replace_in(q, "y una red de ecuaciones solo igualó su F1 con una fórmula legible de 17 variables.",
           "y una red de ecuaciones solo igualó su F1 con una fórmula legible de 17 variables, mientras que el ciclo de mejora automática, con un minero de 1 339 trabajos y la exploración de 68 variables, no encontró mejoras confirmadas.")
q = P("Como trabajos futuros")
replace_in(q, "Cuarto, se evaluará la señal visual en géneros con más cambio de imagen que un podcast.",
           "Cuarto, se extenderá el minero para que lea los trabajos completos con un modelo de lenguaje y se evaluará la señal visual en géneros con más cambio de imagen que un podcast.")

# ---------------------------------------------------------------- 8. Referencia
ref = P("Opus.pro. (2024)", after=find("REFERENCIAS"))
ref._p.addprevious(clone(ref, "OpenAlex. (2026). OpenAlex technical documentation. https://docs.openalex.org")._p)

d.save(str(DST))
d2 = docx.Document(str(DST))
txt = "\n".join(p.text for p in d2.paragraphs)
print("guardado:", DST, "| párrafos:", len(d2.paragraphs), "| imágenes:", len(d2.inline_shapes))
for k in ("4.10 Ciclo", "6.6 Ciclo", "Algoritmo 5", "OpenAlex. (2026)", "Figura 4.", "Figura 5."):
    print(k, "->", k in txt)
