"""Arma Articulo_Investigacion_CIS2026_v15.docx desde la v14: introducción alineada con la ficha (párrafo de causas), trabajos relacionados
ampliados con una tabla comparativa, y cuatro referencias nuevas con DOI verificado en Crossref. No toca versiones anteriores."""
import copy
import re
import sys
from pathlib import Path

import docx
from docx.shared import Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v14.docx")
DST = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v15.docx")
FICHA = Path(r"F:\TESISJF\tesisOFICIAL_entrega\tesisOFICIAL\outputs\2026-10-17\Ficha_Investigacion_NUNEZDELPRADO_v6_plantilla.docx")
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


BODY = d.paragraphs[find("La creación de contenido audiovisual")]
HEAD = d.paragraphs[find("2.4 ")]

# ------------------------------------------------ 1. Introducción: párrafo de causas, como en la ficha
ficha = docx.Document(str(FICHA))
causas = next(p.text for p in ficha.paragraphs if p.text.startswith("La selección de momentos se hace de forma manual"))
BODY._p.addnext(clone(BODY, causas)._p)

# ------------------------------------------------ 2. Citas con las referencias nuevas
p = d.paragraphs[find("LightGBM construye un conjunto de árboles")]
t = p.text
t = t.replace("cada árbol corrige los errores del anterior.", "cada árbol corrige los errores del anterior, principio propio del boosting de gradiente (Friedman, 2001).", 1)
t = t.replace("por lo que vale 1 cuando el orden es perfecto.", "por lo que vale 1 cuando el orden es perfecto (Järvelin & Kekäläinen, 2002).", 1)
assert "Friedman, 2001" in t and "Järvelin" in t
set_text(p, t)
p = d.paragraphs[find("Las métricas siguen el protocolo de evaluación")]
pp = d.paragraphs[find("La explicabilidad del puntaje")]
set_text(pp, pp.text + " Para modelos de árboles como el ranker de este trabajo, esas contribuciones se calculan de forma exacta y eficiente (Lundberg et al., 2020).")
p = d.paragraphs[find("Badamdorj et al. (2021) y Liu et al. (2022) coincidieron")]
set_text(p, p.text + " En una línea cercana, Lin et al. (2023) propusieron UniVTG, un marco unificado de anclaje temporal video-lenguaje que reúne en un solo modelo la recuperación de momentos, la detección de highlights y el resumen de video a partir de consultas en lenguaje natural.")

# ------------------------------------------------ 3. Tablas existentes: Tabla N -> Tabla N+1 (la comparativa será la Tabla 1)
for p in d.paragraphs:
    if has_drawing(p):
        continue
    t = p.text
    t2 = re.sub(r"\bTabla (\d+)\b", lambda m: f"Tabla {int(m.group(1)) + 1}", t)
    if t2 != t:
        set_text(p, t2)

# ------------------------------------------------ 4. Sección 2.5 con tabla comparativa
anchor = d.paragraphs[find("3. MARCO TEÓRICO")]
CAP = d.paragraphs[find("Tabla 2")]          # plantilla de rótulo APA (número en negrita)
CAPT = d.paragraphs[find("Tabla 2") + 1]     # plantilla de título en cursiva
anchor._p.addprevious(clone(HEAD, "2.5 Comparación de los trabajos y brecha identificada")._p)
anchor._p.addprevious(clone(BODY, (
    "La Tabla 1 compara los trabajos revisados según su contexto y conjunto de datos, la técnica o el modelo, los resultados que reportaron y su principal limitación "
    "frente al problema de este estudio. Se observa que los conjuntos con etiqueta de re-reproducción (Mr. HiSum y Rhapsody) y los de clips de curación (Repurpose-10K) "
    "ampliaron la escala de evaluación, que los modelos de detección de highlights se concentraron en señales visuales o en consultas textuales, y que los sistemas de edición "
    "asistida se validaron con personas y no con una medida objetiva de retención (Sul et al., 2023; Park et al., 2025; Wu et al., 2025; Liu et al., 2022; Barua et al., 2025)."))._p)
anchor._p.addprevious(clone(CAP, "Tabla 1", bold=True, italic=False)._p)
anchor._p.addprevious(clone(CAPT, "Comparación de los trabajos relacionados", bold=False, italic=True)._p)
rows = [
    ("Trabajo", "Contexto y datos", "Técnica o modelo", "Resultado reportado", "Limitación frente a este estudio"),
    ("Sul et al. (2023)", "Mr. HiSum: 31 892 videos con etiqueta de re-reproducción de más de 50 000 usuarios por video", "Conjunto de datos; confiabilidad de la etiqueta por transferencia y estudio con usuarios", "Etiqueta confiable a gran escala", "Videos generalistas; no se centra en contenido conversacional"),
    ("Park et al. (2025)", "Rhapsody: unos 13 000 episodios de podcast, 100 segmentos por episodio", "Clasificación binaria por segmento; modelos de lenguaje sin ajuste y modelos ligeros ajustados", "Los modelos sin ajuste rinden mal; ajustados con habla y transcripción mejoran", "Etiqueta de re-reproducción; sin sistema completo hasta el clip"),
    ("Wu et al. (2025)", "Repurpose-10K: más de 10 000 videos de unos 32 min y más de 120 000 clips anotados", "Línea base que fusiona audio, visual y subtítulos", "Referencia para reproducir clips de editores", "Mide la curación humana, no la retención"),
    ("Liu et al. (2022)", "QVHighlights, Charades-STA, YouTube Highlights y TVSum", "UMT: transformer multimodal visual y audio", "Supera a métodos puramente visuales", "Señal principal visual o consulta; sin puntaje explicable"),
    ("Li et al. (2024b)", "Videos sin etiquetas o sin audio", "Modelo no supervisado con aprendizaje contrastivo visual-audio", "Detección de highlights sin etiquetas", "Entrada visual; sin explicación del puntaje"),
    ("Lin et al. (2023)", "Consultas en lenguaje natural sobre video", "UniVTG: marco unificado de anclaje temporal video-lenguaje", "Un modelo para recuperación de momentos, highlights y resumen", "Depende de consultas; no usa la retención"),
    ("Kwak et al. (2025)", "YT-8M y Mr. HiSum", "SPOT: codificador convolucional con TimeSformer", "Error cuadrático medio de 0.090 a 0.080 en el grupo de mayor complejidad", "No usa audio ni texto"),
    ("Um et al. (2025)", "QVHighlights, TVSum y Charades-STA", "Atención sobre palabras clave contextuales", "Mejora la recuperación de momentos y los highlights", "Requiere una consulta textual"),
    ("Barua et al. (2025)", "Estudio con usuarios sobre videos largos", "Lotus: guion abstractivo con clips extractivos", "Comparado con un método extractivo y con la práctica de los participantes", "Validación con personas; sistema cerrado"),
    ("Wang et al. (2024)", "Comentarios de audiencia y entrevistas a creadores de podcasts", "PodReels: herramienta de co-creación de teasers", "Reduce la demanda mental y mejora la eficiencia", "Validación con personas; sin medida objetiva de retención"),
    ("Wang et al. (2025)", "DramaAD: más de 2 500 episodios y 500 clips publicitarios", "HIVE: modelos de lenguaje multimodales", "Superó de forma consistente a las líneas base", "Depende de modelos de gran tamaño; material narrativo"),
]
tab = d.add_table(rows=len(rows), cols=5)
ref_style = d.tables[0].style
try:
    tab.style = ref_style
except Exception:  # noqa: BLE001
    tab.style = "Table Grid"
for r, row in enumerate(rows):
    for k, txt in enumerate(row):
        cell = tab.cell(r, k)
        cell.text = txt
        for par in cell.paragraphs:
            for run in par.runs:
                run.font.size = Pt(7.5)
                run.bold = True if r == 0 else None
anchor._p.addprevious(tab._tbl)
anchor._p.addprevious(clone(BODY, (
    "En conjunto, ningún trabajo reunió las tres condiciones que este estudio plantea: usar el habla y la transcripción como señal principal en contenido conversacional, entregar "
    "un puntaje explicable por clip y contrastar la selección con una medida objetiva de retención bajo un protocolo con hipótesis previa. Esa es la brecha que se aborda."))._p)

# ------------------------------------------------ 5. Referencias nuevas (orden alfabético APA)
NEW = [
    ("Grootendorst, M. (2020)", "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. The Annals of Statistics, 29(5), 1189–1232. https://doi.org/10.1214/aos/1013203451"),
    ("Javed, A.", "Järvelin, K., & Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR techniques. ACM Transactions on Information Systems, 20(4), 422–446. https://doi.org/10.1145/582415.582418"),
    ("Liu, Y., Li, S.", "Lin, K. Q., Zhang, P., Chen, J., Pramanick, S., Gao, D., Wang, A. J., Yan, R., & Shou, M. Z. (2023). UniVTG: Towards unified video-language temporal grounding. En Proceedings of the IEEE/CVF International Conference on Computer Vision (pp. 2782–2792). IEEE. https://doi.org/10.1109/ICCV51070.2023.00262"),
    ("Lundberg, S. M., & Lee", "Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., & Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. Nature Machine Intelligence, 2(1), 56–67. https://doi.org/10.1038/s42256-019-0138-9"),
]
REF = d.paragraphs[find("Grootendorst, M. (2020)")]
for before, text in NEW:
    tgt = d.paragraphs[find(before, after=find("REFERENCIAS"))]
    tgt._p.addprevious(clone(REF, text)._p)

d.save(str(DST))
d2 = docx.Document(str(DST))
txt = "\n".join(p.text for p in d2.paragraphs)
print("guardado:", DST, "| párrafos:", len(d2.paragraphs), "| tablas:", len(d2.tables))
print("Tablas rotuladas:", sorted(set(re.findall(r"^Tabla \d+$", txt, re.M)), key=lambda s: int(s.split()[1])))
for k in ("2.5 Comparación", "Friedman, J. H.", "Lin, K. Q.", "Järvelin, K.", "Lundberg, S. M., Erion", "La selección de momentos se hace de forma manual"):
    print(k, "->", k in txt)

# ------------------------------------------------ 6. Ficha v7: título en español y hardware actual (coherencia ficha-artículo)
fd = docx.Document(str(FICHA))
titulo_en = "A Deep Learning Approach for Automated Highlight Detection and Virality Scoring in Short-Form Video Clip Generation"
titulo_es = "Selección automática de clips verticales con alto potencial de retención en videos conversacionales a partir de señales de audio y texto"
n = 0


def replace_in(par, a, b):
    global n
    if a in par.text:
        set_text(par, par.text.replace(a, b))
        n += 1


def walk(paragraphs):
    for par in paragraphs:
        replace_in(par, titulo_en, titulo_es)
        replace_in(par, "es suficiente para la transcripción y el entrenamiento, con Google Colab como respaldo.",
                   "es suficiente para la transcripción y el entrenamiento; los experimentos posteriores se ejecutaron en una segunda computadora con GPU NVIDIA GeForce RTX 3060 de 12 GB, con Google Colab como respaldo.")


walk(fd.paragraphs)
for t in fd.tables:
    for row in t.rows:
        for c in row.cells:
            walk(c.paragraphs)
FICHA_OUT = Path(r"F:\TESISJF\Ficha_Investigacion_NUNEZDELPRADO_v7_plantilla.docx")
fd.save(str(FICHA_OUT))
print("ficha v7:", FICHA_OUT, "| reemplazos:", n)
