"""Arma Articulo_Investigacion_CIS2026_v16.docx desde la v15 aplicando lo que enseña el curso Seminario de Investigación I (PPT del curso):
- pseudocódigo en el formato del ejemplo de la profesora (caja, Requiere/Asegura, líneas numeradas, ▷),
- rótulos: Tabla N. arriba y Figura N. abajo, alineados a la izquierda,
- objetivos y preguntas de investigación en la introducción (coherencia con la ficha),
- marco teórico con fórmulas, desbalance de clases y justificación de modelos,
- experimentación con versiones exactas y procedimiento,
- resultados sin interpretación ni citas, discusión con limitaciones ligadas a consecuencias,
- conclusiones y trabajos futuros en 5 a 6 oraciones. No toca versiones anteriores.
"""
import copy
import re
import sys
from importlib import metadata
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v15.docx")
DST = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v16.docx")
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
    assert a in p.text, f"no encontrado: {a[:60]}"
    set_text(p, p.text.replace(a, b, 1))


BODY = P("La creación de contenido audiovisual")
HEAD = P("3.6 ")
EQ = P("puntaje(w) = Σ")

# ------------------------------------------------ 1. Introducción: objetivos y preguntas (coherencia con la ficha)
org = P("El artículo se organiza así")
org._p.addprevious(clone(BODY, (
    "El objetivo general es desarrollar un pipeline basado en modelos de aprendizaje profundo y de ranking que, a partir del audio y la transcripción de un video "
    "conversacional, seleccione y puntúe de 0 a 99 clips verticales (9:16) con alto potencial de retención. Los objetivos específicos son: (i) construir un conjunto de "
    "datos propio de videos conversacionales en español e inglés, etiquetado con la curva de re-reproducción de YouTube; (ii) implementar un pipeline de preprocesamiento "
    "que transcriba el audio con Whisper, segmente el contenido en oraciones y genere clips candidatos de 15 a 90 s; (iii) extraer variables de audio, eventos de sonido, "
    "texto y fluidez por candidato; y (iv) definir líneas base y entrenar un modelo de ranking con validación por canal."))._p)
org._p.addprevious(clone(BODY, (
    "Con ello se busca responder dos preguntas. La primera es si un modelo de ranking aprendido supera al azar y a una fórmula fija de variables ponderadas en el acierto de "
    "al menos un pico de retención entre cinco clips. La segunda es si los modelos de aprendizaje profundo de secuencia (BiGRU, TCN y Transformer) mejoran de forma confirmada "
    "al ranker de árboles sobre las mismas variables."))._p)

# ------------------------------------------------ 2. Marco teórico: fórmulas, desbalance, justificación de modelos
p = P("LightGBM construye un conjunto de árboles")
e1 = clone(EQ, "DCG@k = Σᵢ₌₁ᵏ (2^relᵢ − 1) / log₂(i + 1)          (1)")
e2 = clone(EQ, "NDCG@k = DCG@k / IDCG@k          (2)")
p._p.addnext(e1._p)
e1._p.addnext(e2._p)
e2._p.addnext(clone(BODY, "En las ecuaciones (1) y (2), relᵢ es la relevancia del elemento que ocupa la posición i e IDCG@k es el DCG@k del orden ideal.")._p)
p6 = P("Las métricas siguen el protocolo de evaluación")
p6._p.addnext(clone(BODY, (
    "En la selección de ventanas la clase de interés es rara, pues cerca de 8 % de las ventanas son momentos destacados. En conjuntos desequilibrados la exactitud puede ser "
    "engañosa, porque un clasificador que nunca elige la clase minoritaria obtiene valores altos; por eso se usan la precisión P, la cobertura R y su media armónica, el "
    "F1 = 2 · P · R / (P + R) (ecuación 3), que dependen solo de la clase de interés (He & Garcia, 2009)."))._p)
i4 = find("4. METODOLOGÍA")
tgt = d.paragraphs[i4]
tgt._p.addprevious(clone(HEAD, "3.8 Justificación de los modelos elegidos")._p)
tgt._p.addprevious(clone(BODY, (
    "Se eligió LightGBM con objetivo LambdaRank porque el problema consiste en ordenar ventanas dentro de cada video y no en predecir un valor absoluto, lo que hace adecuado "
    "un objetivo de ranking por listas (Burges, 2010), y porque los árboles con histogramas se entrenan en una computadora personal (Ke et al., 2017). Los modelos de "
    "secuencia (BiGRU, TCN y Transformer) se incluyeron porque el contexto temporal podría aportar señal que los árboles, que puntúan cada ventana por separado, no capturan "
    "(Cho et al., 2014; Lea et al., 2017; Liu et al., 2022). La red de ecuaciones se eligió porque entrega una fórmula legible, requisito de un sistema auditable (Sahoo et al., 2018). "
    "Whisper se usa por su cobertura multilingüe sin entrenamiento adicional (Radford et al., 2023) y PANNs por reconocer eventos como la risa y el aplauso (Kong et al., 2020)."))._p)

# ecuación V0: (1) -> (4)
pe = P("puntaje(w) = Σ")
assert "(1)" in pe.text
set_text(pe, pe.text.replace("(1)", "(4)"))
for q in d.paragraphs:
    if "Ecuación 1" in q.text and not q.text.startswith("puntaje"):
        set_text(q, q.text.replace("Ecuación 1", "Ecuación 4"))

# ------------------------------------------------ 3. Metodología: diseño transeccional y referencias a líneas del pseudocódigo
replace_in(P("La investigación tiene un enfoque cuantitativo"), "diseño no experimental de alcance descriptivo", "diseño no experimental transeccional de alcance descriptivo")
replace_in(P("El audio se transcribe con Whisper"), "(Algoritmo 1)", "(líneas 2 a 11 del Algoritmo 1)")
replace_in(P("Las etiquetas se derivan de la curva"), "el Algoritmo 2", "las líneas 3 a 9 del Algoritmo 2")
replace_in(P("Como alternativa de aprendizaje profundo"), "(Algoritmo 3)", "(líneas 1 a 3 del Algoritmo 3)")
replace_in(P("Para que el criterio de puntuación"), "(Algoritmo 4)", "(líneas 2 a 9 del Algoritmo 4)")

# ------------------------------------------------ 4. Pseudocódigo en el formato del ejemplo de la profesora
ALG = {
    "Algoritmo 1": ("Algoritmo 1 Generación de candidatos", [
        "Requiere: oraciones O = (o₁, …, oₘ) con marcas de tiempo; duraciones objetivo T = {20, 40, 60} s; dmín = 15 s; dmáx = 90 s.",
        "Asegura: conjunto W de ventanas candidatas alineadas a los límites de oración.",
        "1: W ← ∅",
        "2: para i = 1 hasta m hacer",
        "3:   para cada t en T hacer",
        "4:     j ← primera oración con fin(oⱼ) − inicio(oᵢ) ≥ t        ▷ la ventana termina en un límite de oración",
        "5:     mientras fin(oⱼ) − inicio(oᵢ) > dmáx y j > i hacer j ← j − 1 fin mientras",
        "6:     d ← fin(oⱼ) − inicio(oᵢ)",
        "7:     si dmín ≤ d ≤ dmáx entonces",
        "8:       W ← W ∪ {(inicio(oᵢ), fin(oⱼ))}",
        "9:     fin si",
        "10:  fin para",
        "11: fin para",
        "12: retornar las ventanas únicas de W ordenadas por inicio"]),
    "Algoritmo 2": ("Algoritmo 2 Entrenamiento y evaluación del ranker R0 con validación cruzada agrupada por canal", [
        "Requiere: ventanas W con 71 variables, relevancia y ∈ {0, …, 4}, video v(w) y canal c(v).",
        "Asegura: puntaje por ventana, selección de los 5 mejores clips por video y métricas.",
        "1: para cada variable f y cada video v hacer x_f(w) ← percentil de f(w) entre las ventanas de v fin para",
        "2: dividir los videos en 10 particiones agrupadas por canal        ▷ ningún canal queda en dos particiones",
        "3: para k = 1 hasta 10 hacer",
        "4:   entrenar LightGBM(LambdaRank, grupo = video) con las particiones distintas de k",
        "5:   s(w) ← puntaje del modelo para las ventanas de los videos de la partición k",
        "6:   para cada video de la partición k hacer",
        "7:     ordenar por s(w); suprimir los candidatos con más de 30 % de tiempo en común; conservar los 5 primeros",
        "8:   fin para",
        "9: fin para",
        "10: calcular acierto@5, F1 temporal y NDCG@10 por video",
        "11: comparar con el azar (Wilcoxon, McNemar)",
        "12: retornar puntajes, clips y métricas"]),
    "Algoritmo 3": ("Algoritmo 3 Modelo de secuencia (BiGRU, TCN o Transformer)", [
        "Requiere: matriz X ∈ ℝ^(T×F) de percentiles (T = 40 tramos), calor y ∈ ℝᵀ y codificador E ∈ {BiGRU, TCN, Transformer}.",
        "Asegura: puntaje de calor ŷ ∈ ℝᵀ por tramo.",
        "1: H ← E(X)        ▷ codificador temporal",
        "2: ŷ ← W·H + b        ▷ capa lineal por tramo",
        "3: minimizar L(ŷ, y) con AdamW, lotes de 16 videos y 40 épocas",
        "4: evaluar con las mismas métricas y particiones que R0",
        "5: retornar ŷ"]),
    "Algoritmo 4": ("Algoritmo 4 Exploración automática de ecuaciones (campeón/retador)", [
        "Requiere: percentiles X de 17 variables por ventana, calor y por video, canal c(v) y campeón C.",
        "Asegura: ecuación aprendida y decisión de promoción.",
        "1: separar un conjunto reservado por canal; el resto es entrenamiento",
        "2: sortear 12 configuraciones θ        ▷ unidades, profundidad, λ de L1 y tasa de aprendizaje",
        "3: para cada θ hacer",
        "4:   F1interno(θ) ← F1 medio de la validación cruzada de 3 particiones por canal en el entrenamiento",
        "5: fin para",
        "6: θ* ← argmax F1interno; entrenar EQL(θ*) con 3 semillas",
        "7: podar los pesos pequeños y escribir la ecuación resultante",
        "8: evaluar EQL y C en el conjunto reservado",
        "9: si F1(EQL) > F1(C) y Wilcoxon unilateral p < 0.05 entonces C ← EQL fin si",
        "10: registrar la ronda; retornar la ecuación y C"]),
}
def sanitize(s):
    """Consolas no tiene algunos glifos (ℝ, ∅, subíndices): se usan equivalentes ASCII para que el pseudocódigo se vea igual en cualquier PC."""
    for a, b in (("ℝᵀ", "R^T"), ("ℝ^(T×F)", "R^(T×F)"), ("ℝ", "R"), ("∅", "{}"), ("oₘ", "o_m"), ("o₁", "o_1"), ("oⱼ", "o_j"), ("oᵢ", "o_i"), ("ᵀ", "^T")):
        s = s.replace(a, b)
    return s


for key, (titulo, lineas) in ALG.items():
    lineas = [sanitize(x) for x in lineas]
    i = find(key)
    tp = d.paragraphs[i]
    old = [tp]
    j = i + 1
    while j < len(d.paragraphs) and d.paragraphs[j].runs and d.paragraphs[j].runs[0].font.name == "Consolas":
        old.append(d.paragraphs[j])
        j += 1
    tbl = d.add_table(rows=1, cols=1)
    borders = parse_xml(
        '<w:tblBorders %s>' % nsdecls("w")
        + "".join(f'<w:{s} w:val="single" w:sz="8" w:space="0" w:color="000000"/>' for s in ("top", "left", "bottom", "right"))
        + "</w:tblBorders>")
    tbl._tbl.tblPr.append(borders)
    cell = tbl.cell(0, 0)
    c0 = cell.paragraphs[0]
    r0 = c0.add_run(titulo)
    r0.bold = True
    r0.font.size = Pt(9)
    for ln in lineas:
        q = cell.add_paragraph()
        r = q.add_run(ln)
        r.font.name = "Consolas"
        r.font.size = Pt(8)
        q.paragraph_format.space_after = Pt(0)
        q.paragraph_format.space_before = Pt(0)
    tp._p.addprevious(tbl._tbl)
    spacer = copy.deepcopy(BODY._p)
    sp = docx.text.paragraph.Paragraph(spacer, BODY._parent)
    set_text(sp, "")
    tp._p.addprevious(spacer)
    for q in old:
        q._p.getparent().remove(q._p)

# ------------------------------------------------ 5. Rótulos: Tabla N. (arriba) y Figura N. (debajo), a la izquierda
def merge_caption(a, b):
    label = a.text.strip()
    title = b.text.strip()
    for r in a.runs[1:]:
        r._r.getparent().remove(r._r)
    a.runs[0].text = label + ". "
    a.runs[0].bold = True
    a.runs[0].italic = False
    run = a.add_run(title)
    run.bold = False
    run.italic = True
    a.alignment = WD_ALIGN_PARAGRAPH.LEFT
    a.paragraph_format.keep_with_next = label.startswith("Tabla")  # el rótulo de tabla no se separa de su tabla
    b._p.getparent().remove(b._p)


for p in list(d.paragraphs):
    if re.fullmatch(r"Tabla \d+", p.text.strip()):
        nxt = docx.text.paragraph.Paragraph(p._p.getnext(), p._parent)
        merge_caption(p, nxt)
for p in list(d.paragraphs):
    if re.fullmatch(r"Figura \d+", p.text.strip()):
        b = docx.text.paragraph.Paragraph(p._p.getnext(), p._parent)
        c = docx.text.paragraph.Paragraph(b._p.getnext(), p._parent)  # párrafo con la imagen
        merge_caption(p, b)
        c.paragraph_format.keep_with_next = True  # la imagen no se separa de su rótulo
        c._p.addnext(p._p)

# ------------------------------------------------ 6. Experimentación: versiones exactas y procedimiento
def ver(pkg):
    try:
        return metadata.version(pkg)
    except Exception:  # noqa: BLE001
        return None


libs = [("PyTorch", "torch"), ("LightGBM", "lightgbm"), ("scikit-learn", "scikit-learn"), ("pandas", "pandas"), ("NumPy", "numpy"), ("SciPy", "scipy"),
        ("librosa", "librosa"), ("faster-whisper", "faster-whisper"), ("sentence-transformers", "sentence-transformers"), ("transformers", "transformers"),
        ("SHAP", "shap"), ("spaCy", "spacy"), ("yt-dlp", "yt-dlp")]
lista = ", ".join(f"{n} {ver(k)}" for n, k in libs if ver(k))
p = P("Los experimentos hasta las cohortes frescas")
p._p.addnext(clone(BODY, (
    "El entorno de software de la segunda computadora fue Windows 10 Pro, Python 3.11 y las librerías " + lista + ". La primera computadora usó Python 3.11.9 con las mismas "
    "librerías principales en versiones anteriores, y el código fija las semillas de los modelos para repetir las corridas.")) ._p)
rep = P("5.6 Reproducibilidad")
rep._p.addprevious(clone(HEAD, "5.6 Procedimiento experimental")._p)
rep._p.addprevious(clone(BODY, (
    "El procedimiento siguió siete pasos: (1) búsqueda de videos con 50 consultas y descarga del audio y de la curva con yt-dlp; (2) transcripción con faster-whisper y "
    "filtrado por idioma y longitud; (3) generación de candidatos alineados a oración (Algoritmo 1); (4) cálculo de las 71 variables y su transformación a percentiles por "
    "video; (5) entrenamiento del ranker R0 y de los modelos de secuencia con validación cruzada agrupada por canal (Algoritmos 2 y 3); (6) exploración de ecuaciones con el "
    "explorador automático (Algoritmo 4); y (7) evaluación con el acierto@5, el F1 temporal y el NDCG@10, con las pruebas de Wilcoxon y McNemar."))._p)
set_text(rep, "5.7 Reproducibilidad")

# ------------------------------------------------ 7. Resultados: sin interpretación ni citas
replace_in(P("El techo observado con solo contenido"), ", valor que no está disponible para un video aún no publicado", "")
q = P("El techo observado con solo contenido")
t = q.text
k = t.index("Por la fuerte asimetría de clases")
set_text(q, t[:k] + "El 92 % de las ventanas no fue caliente.")
q = P("Tras las cohortes frescas se amplió")
replace_in(q, "La mejora de +0.010 vista en desarrollo era ruido.", "En desarrollo, la mezcla había mostrado +0.010 de F1 (p = 0.015 sin corregir).")
q = P("Para atender la observación de explorar")
t = q.text
k = t.index(", así que no se adopta; su valor")
set_text(q, t[:k] + ". La ecuación aprendida suma un término lineal en la variación del volumen y dos cuadrados: uno sobre una combinación de variación y nivel del volumen y de similitud con el tema, y otro sobre una combinación de pausas, silencio, tono, ritmo y cantidad de oraciones. La Tabla 9 resume estas pruebas.")

# ------------------------------------------------ 8. Discusión: limitaciones ligadas a consecuencias, interpretación de la ecuación, implicaciones
q = P("Las limitaciones del estudio son las siguientes")
set_text(q, (
    "Las limitaciones del estudio son cuatro. Primero, el conjunto proviene solo de YouTube y de dos idiomas, por lo que los resultados no pueden generalizarse a otras plataformas ni "
    "a otros idiomas. Segundo, las cohortes frescas son pequeñas (93, 63 y 83 videos), de modo que sus contrastes tienen baja potencia y las diferencias de 0.01 a 0.02 de F1 no pueden "
    "distinguirse del ruido; este riesgo se mitigó con hipótesis previas y una sola corrida por prueba. Tercero, la señal visual se probó solo de forma gruesa y no se evaluó con "
    "usuarios reales, por lo que no se sabe si la imagen aporta en otros géneros; además, el contraste con la curación humana se apoya en 11 videos y es solo indicativo. Cuarto, la curva "
    "mide la re-reproducción de la audiencia general, de modo que un puntaje bien calibrado para ella puede no corresponder a la elección de un editor."))
q.insert_paragraph_before(
    "La ecuación aprendida por la red de ecuaciones muestra que la relación entre las pausas, el silencio, el tono y el volumen con el calor no es monótona: sus términos cuadráticos "
    "indican que los extremos de esas combinaciones puntúan alto, algo que la fórmula lineal no puede expresar. Esta lectura es una interpretación de los pesos aprendidos y no una "
    "relación causal comprobada, y como la diferencia con LightGBM no fue significativa, la ecuación se mantiene como hallazgo interpretable y no como reemplazo del ranker.")
disc_end = P("8. CONCLUSIONES")
disc_end._p.addprevious(clone(BODY, (
    "En síntesis, con solo audio y texto es posible proponer clips con una ventaja clara sobre el azar, pero la evidencia indica que ese enfoque tiene un techo cercano a 57 % de "
    "acierto en videos nuevos. Para un editor, el sistema ofrece una lista corta de candidatos con una explicación por clip; para la investigación, el resultado sugiere que "
    "superar ese techo requeriría una señal nueva y no solo más datos o modelos más complejos; para un producto, la curva real de retención seguiría siendo el complemento "
    "necesario cuando el video ya está publicado."))._p)

# ------------------------------------------------ 9. Conclusiones y trabajos futuros (5 a 6 oraciones, sin citas)
q = P("Este trabajo propuso un pipeline abierto")
set_text(q, (
    "Este trabajo propuso y evaluó un pipeline abierto que, a partir del audio y la transcripción de un video conversacional, selecciona cinco clips verticales y los puntúa de 0 a 99 "
    "con una explicación por clip. Respecto del objetivo general, el pipeline se construyó completo, desde un conjunto propio de unos 770 videos hasta la validación con cohortes "
    "frescas. Respecto de la primera pregunta, el modelo de ranking acertó al menos un pico de retención en 62.4 % de los videos de la cohorte fresca 1, frente a 26.9 % del azar y "
    "47.3 % de la fórmula de 17 variables, y en las pruebas posteriores con 83 videos nuevos el acierto fue de 55 a 58 %, frente a 32 % del azar. Respecto de la segunda pregunta, los "
    "modelos de secuencia no superaron al ranker de árboles, y una red de ecuaciones solo igualó su F1 con una fórmula legible de 17 variables. Con solo audio y texto, el techo observado "
    "fue de 50 a 69 %, por debajo del 85 a 95 % que se alcanza con la curva real de retención. Por tanto, el sistema propone clips con una ventaja clara sobre el azar, pero no reemplaza "
    "la señal real de la audiencia."))
q = P("Primero, se continuará ampliando el conjunto")
set_text(q, (
    "Como trabajos futuros, en Seminario de Investigación 2 se continuará la propuesta con cinco líneas. Primero, se ampliará el conjunto de podcasts con el conjunto Rhapsody, de unos "
    "13 000 episodios, para evaluar si los modelos de secuencia y las redes de ecuaciones superan al ranker de árboles con más datos. Segundo, se confirmará en una cohorte fresca la "
    "ecuación aprendida por el explorador y se repetirán sus rondas con otras configuraciones. Tercero, se entrenará el ranker con los clips de curación humana de Repurpose-10K para "
    "contrastar la retención con la preferencia editorial. Cuarto, se evaluará la señal visual en géneros con más cambio de imagen que un podcast. Quinto, se diseñará un prototipo del "
    "sistema como servicio para creadores y empresas de contenido, y se contrastará su selección con el mapa de calor de retención en cohortes nuevas."))

# ------------------------------------------------ 10. Referencia nueva
ref = P("Hernández-Sampieri, R.", after=find("REFERENCIAS"))
ref._p.addprevious(clone(ref, "He, H., & Garcia, E. A. (2009). Learning from imbalanced data. IEEE Transactions on Knowledge and Data Engineering, 21(9), 1263–1284. https://doi.org/10.1109/TKDE.2008.239")._p)

d.save(str(DST))
d2 = docx.Document(str(DST))
txt = "\n".join(p.text for p in d2.paragraphs)
print("guardado:", DST, "| párrafos:", len(d2.paragraphs), "| tablas:", len(d2.tables))
print("[COMPLETAR]:", txt.count("[COMPLETAR"), "| 'Algoritmo N.' viejos:", len(re.findall(r"^Algoritmo \d\.", txt, re.M)))
for k in ("El objetivo general es desarrollar", "3.8 Justificación", "5.6 Procedimiento", "5.7 Reproducibilidad", "Como trabajos futuros", "He, H., & Garcia"):
    print(k, "->", k in txt)
