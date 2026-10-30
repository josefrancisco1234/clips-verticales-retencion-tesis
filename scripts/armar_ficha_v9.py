"""Ficha v9: aplica los 28 comentarios de la profesora (ficha_ofi) a la ficha de la tesis de clips. Parte de la v8."""
import copy
import re
import sys
import unicodedata
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
d = docx.Document(r"F:\TESISJF\Ficha_Investigacion_NUNEZDELPRADO_v8_plantilla.docx")
art = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v22.docx")
P = list(d.paragraphs)


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = t
    else:
        p.add_run(t)
    return p


def clone_after(p, text):
    el = copy.deepcopy(p._p)
    p._p.addnext(el)
    return st(Paragraph(el, p._parent), text)


def drop(p):
    p._p.getparent().remove(p._p)


# ---- C0: apellido de la asesora
st(P[7], "Mayhua Quispe, Angela")

# ---- C2, C3, C4, C5: discusion y comparacion de 9 papers (2021-2026) con hallazgos y limitaciones
cap = clone_after(P[28], "Tabla 1. Comparación de nueve trabajos revisados: hallazgo y lo que les faltó")
for r in cap.runs:
    r.bold = True
    r.font.size = Pt(10)
FILAS = [("Trabajo", "Qué hicieron y qué hallaron", "Lo que les faltó (limitación)"),
         ("Sul et al. (2023), Mr. HiSum", "31 892 videos con etiquetas agregadas de más de 50 000 usuarios por video.", "No se centra en videos conversacionales ni evalúa solo con audio y texto."),
         ("Wu et al. (2025), Repurpose-10K", "Más de 10 000 videos largos y más de 120 000 clips anotados en etapas con retroalimentación de usuarios.", "Reproduce clips elegidos por editores y no la retención de la audiencia; no aísla audio y texto."),
         ("Liu et al. (2022), UMT", "Transformer multimodal visual y de audio, evaluado en QVHighlights, Charades-STA, YouTube Highlights y TVSum.", "Parte de señales visuales o de consultas textuales; no entrega un puntaje explicable por clip."),
         ("Li et al. (2024b)", "Modelo no supervisado con aprendizaje contrastivo visual-audio que no requiere etiquetas.", "Depende de señales visuales y no explica el puntaje de cada clip."),
         ("Kwak et al. (2025), SPOT", "Entrenado con YT-8M y Mr. HiSum; redujo el error cuadrático medio de 0.090 a 0.080 frente a TimeSformer en el grupo de alta complejidad.", "Usa solo señales visuales, sin audio ni texto, y sin explicación del puntaje."),
         ("Um et al. (2025)", "Atención sobre palabras clave en QVHighlights, TVSum y Charades-STA.", "Parte de consultas textuales y no explica el puntaje de cada clip."),
         ("Barua et al. (2025), Lotus", "Guiones abstractivos y clips extractivos; contrastado con un método extractivo y con la práctica de los participantes.", "Se valida con usuarios, sin una medida objetiva de retención, y depende de modelos de lenguaje de gran tamaño."),
         ("Wang et al. (2024), PodReels", "Reduce la demanda mental y mejora la eficiencia de los podcasters, según su estudio con creadores.", "Se valida con usuarios y no contrasta su elección con la retención de la audiencia."),
         ("Wang et al. (2025), HIVE", "Marco con modelos de lenguaje multimodales; superó a las líneas base en DramaAD (más de 2 500 episodios y 500 clips editados por profesionales).", "Trabaja con dramas cortos y modelos de lenguaje grandes; no mide retención ni explica el puntaje.")]
tb = d.add_table(rows=len(FILAS), cols=3)
tb._tbl.tblPr.append(parse_xml('<w:tblBorders %s>' % nsdecls("w") + "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="888888"/>' for s in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>"))
for i, fila in enumerate(FILAS):
    for j, t in enumerate(fila):
        c = tb.cell(i, j)
        c.width = Inches((1.6, 2.7, 2.4)[j])
        p_ = c.paragraphs[0]
        r_ = p_.add_run(t)
        r_.font.size = Pt(8.5)
        r_.bold = i == 0
cap._p.addnext(tb._tbl)
tail = copy.deepcopy(P[28]._p)
tb._tbl.addnext(tail)
st(Paragraph(tail, P[28]._parent), "Al comparar los nueve trabajos (Tabla 1) se observa un hallazgo común y tres limitaciones comunes. El hallazgo común es que automatizar parte de la selección de momentos es viable, ya sea con modelos de detección (Liu et al., 2022; Li et al., 2024b; Kwak et al., 2025; Um et al., 2025) o con sistemas de edición asistida (Barua et al., 2025; Wang et al., 2024; Wang et al., 2025). Las limitaciones comunes son que los conjuntos grandes amplían la escala pero no aíslan el contenido conversacional (Sul et al., 2023; Wu et al., 2025), que los modelos parten de señales visuales o de consultas textuales, y que los sistemas de edición se validan con usuarios o con material narrativo, sin contrastar su elección con una medida objetiva de retención.")

# ---- C6: la brecha es lo que les falto a los autores
st(P[30], "Lo que les faltó a los autores revisados es explicar el puntaje de cada clip, evaluar solo con audio y texto en contenido conversacional y contrastar la elección con una medida objetiva de retención bajo un protocolo estricto (Sul et al., 2023; Wu et al., 2025). La brecha que aborda esta investigación es, por tanto, doble: faltan sistemas abiertos que elijan y puntúen momentos de videos conversacionales con señales de audio y texto auditables, y falta evidencia validada sobre cuánto se puede predecir con solo el contenido. Esta investigación propone un pipeline que recibe el audio y la transcripción de un video, extrae variables con modelos preentrenados de aprendizaje profundo, y puntúa y ordena los candidatos con un modelo de ranking aprendido, de modo que cada clip se acompañe de una explicación de su puntaje (Lundberg & Lee, 2017). La curva de re-reproducción de YouTube se usa únicamente para entrenar y calificar, nunca como entrada del sistema (Sul et al., 2023). Finalmente, el estudio compara la propuesta con el azar, con una fórmula de variables ponderadas y con modelos de aprendizaje profundo de secuencia, de modo que la elección del mejor enfoque se demuestre con evidencia.")

# ---- C1: todas las preguntas (una por objetivo especifico)
st(P[31], "Preguntas de investigación")
PE = ["¿Es posible construir un conjunto de datos propio de videos conversacionales, etiquetado con la curva de re-reproducción, que permita evaluar sin fuga de información entre canales?",
      "¿Qué variables de audio y texto, extraídas con modelos preentrenados, pueden calcularse por candidato y qué relación tienen con la retención de la audiencia?",
      "¿Un modelo de ranking aprendido supera al azar y a una fórmula fija de variables ponderadas en el acierto de al menos un pico de retención entre cinco clips?",
      "¿Los modelos de aprendizaje profundo de secuencia (BiGRU, TCN y Transformer) y una red de ecuaciones mejoran de forma confirmada al ranker de árboles sobre las mismas variables?",
      "¿Qué desempeño alcanza el sistema automático, medido con acierto@5, F1 temporal y NDCG@10 en cohortes frescas, frente al azar y a la curva real de retención?",
      "¿Es posible integrar el sistema en una página web que entregue, a partir de un video, cinco clips verticales con puntaje y explicación?",
      "¿Cómo valoran la utilidad de la página web cinco creadores de podcast?"]
def pregunta(p, n, texto):   # etiqueta en negrita y texto normal, como en el original
    p.runs[0].text = f"Pregunta específica {n}: "
    p.runs[1].text = texto
pregunta(P[33], 1, PE[0])
pregunta(P[34], 2, PE[1])
prev = P[34]
for k in range(2, 7):
    el = copy.deepcopy(prev._p)
    prev._p.addnext(el)
    prev = Paragraph(el, prev._parent)
    pregunta(prev, k + 1, PE[k])

# ---- C7: objetivo general de maximo 15 palabras
OG = "Desarrollar un sistema de aprendizaje profundo que seleccione y puntúe clips verticales de podcasts."
assert len(OG.split()) <= 15, len(OG.split())
st(P[37], OG)

# ---- C9-C13: objetivos especificos en el orden pedido (dataset, preprocesar, modelos, evaluar el sistema, pagina web, validar)
OE = ["Construir un conjunto de datos de videos conversacionales en español e inglés, etiquetado con la curva de re-reproducción de YouTube.",
      "Preprocesar los videos transcribiendo el audio con Whisper, segmentando en candidatos de 15 a 90 s y extrayendo 71 variables de audio y texto por candidato.",
      "Entrenar un modelo de ranking LightGBM con objetivo LambdaRank y una fórmula de variables ponderadas como modelos base, con validación cruzada por canal.",
      "Entrenar y comparar modelos de aprendizaje profundo (BiGRU, TCN, Transformer y red de ecuaciones) frente al ranker de árboles.",
      "Evaluar el sistema automático con acierto@5, F1 temporal y NDCG@10 en cohortes frescas, frente al azar y a la curva real de retención.",
      "Integrar el sistema en una página web que genere cinco clips verticales con puntaje y explicación a partir de un video.",
      "Validar la utilidad percibida de la página web con cinco creadores de podcast, mediante un cuestionario de escala Likert y estadística descriptiva."]
for p_, t in zip((P[40], P[41], P[42], P[43], P[45], P[46], P[47]), OE):
    st(p_, t)
for i in (39, 44, 48):
    drop(P[i])

# ---- C16: justificacion directa y SIN citas
st(P[50], "Si esta propuesta estuviera en funcionamiento, su aporte sería social, educativo y práctico. En lo social, un creador independiente, un medio local o una radio universitaria podría convertir una conversación larga en cinco clips listos para redes sin pagar una agencia ni depender de herramientas cerradas, lo que reduce la brecha entre quienes tienen equipos de edición y quienes no. En lo educativo, cada clip se explica con banderas simples (por ejemplo, «el volumen varía mucho» o «hay una pausa larga antes de la idea»), de modo que estudiantes y creadores aprenden qué señales del contenido suelen acompañar los momentos que la audiencia vuelve a ver, y el sistema sirve como caso de estudio en cursos de ciencia de datos y comunicación. En lo práctico, elegir y recortar clips de un episodio largo deja de ser un trabajo manual de varias horas y pasa a ser un procesamiento automático, repetible y auditable, y el código y la base de datos quedan abiertos para que otros investigadores reproduzcan o mejoren los resultados. La propuesta se alinea con el ODS 9 al promover la innovación tecnológica abierta aplicada a la industria de contenidos digitales.")
# ---- C17: viabilidad (aqui si van citas)
st(P[51], P[51].text.replace("el plazo de dos seminarios es adecuado", "el plazo del proyecto es adecuado"))

# ---- C18, C19: contribucion academica (originalidad, valor anadido, brechas, lineas futuras), con referencias, una pagina
st(P[54], "El aporte principal es un sistema abierto, reproducible y explicable que va del video al clip vertical con puntaje (Barua et al., 2025). Su originalidad es doble. En lo teórico, trata el audio y el texto como eje del modelo para contenido conversacional, un frente menos explorado que el visual (Kwak et al., 2025; Liu et al., 2022), y reporta cuánto se logra solo con el contenido frente al azar y frente a la curva real de retención (Sul et al., 2023). En lo metodológico, aplica un protocolo de desarrollo, confirmación y cohortes frescas con la hipótesis escrita antes de probar, que limita la sobreestimación por exploración múltiple (Dunn, 1961), y propone una red de ecuaciones que entrega una fórmula legible (Sahoo et al., 2018), junto con un agente que prueba variables y arquitecturas nuevas y solo las promueve con evidencia. El valor añadido frente al estado del arte (Tabla 1) es un puntaje explicable por clip, con banderas 0/1 que indican si cada variable está en el 25 % más alto de su video (Lundberg & Lee, 2017), y la documentación de los resultados negativos. Las brechas que aborda son la falta de sistemas abiertos para contenido conversacional y de evidencia validada sobre el techo del contenido (Wu et al., 2025). Como líneas futuras se identifican el entrenamiento con más datos, como los de Rhapsody (Park et al., 2025), el entrenamiento directo con clips de curación humana (Wu et al., 2025) y la lectura automática de literatura para proponer variables nuevas.")

# ---- C20, C21: tecnicas, modelos y algoritmos explicitos y justificados
t1 = ("Datos y preprocesamiento. La adquisición usa yt-dlp para el audio y la curva de re-reproducción, la misma estrategia con que se construyen conjuntos de datos a gran escala (Sul et al., 2023). La transcripción con marcas de tiempo por palabra usa faster-whisper, basado en Whisper (Radford et al., 2023), elegido por su robustez multilingüe. El texto se agrupa en oraciones y se generan candidatos de 15 a 90 s.")
t2 = ("Variables. Las variables de audio se calculan con librosa y los eventos de sonido (risa, aplausos, música) con la red convolucional preentrenada PANNs CNN14 (Kong et al., 2020). Las variables de texto usan sentimiento con DistilBERT multilingüe, embeddings de oraciones MiniLM, palabras clave con KeyBERT (Grootendorst, 2020) y sintagmas nominales con spaCy; los embeddings de habla usan HuBERT (Hsu et al., 2021). Cada variable se transforma en un percentil dentro de su video y, en el modelo final, en una bandera 0/1.")
t3 = ("Modelos y algoritmos. Se comparan el azar; una fórmula de 17 variables ponderadas, con pesos fijados por la correlación parcial de Spearman con el calor real; LightGBM con objetivo LambdaRank (Burges, 2010; Ke et al., 2017), elegido porque el problema consiste en ordenar ventanas dentro de cada video; modelos de aprendizaje profundo de secuencia, BiGRU (Cho et al., 2014; Schuster & Paliwal, 1997), TCN (Lea et al., 2017) y Transformer (Liu et al., 2022), que leen la línea de tiempo completa; y una red de ecuaciones (Sahoo et al., 2018), que entrega una fórmula legible. El modelo final adoptado es la fórmula de 17 variables en versión 0/1, por su explicabilidad. La explicación usa contribuciones aditivas de tipo SHAP (Lundberg & Lee, 2017) y la selección de los cinco clips usa supresión de no máximos (Neubeck & Van Gool, 2006).")
t4 = ("Integración. Una página web local, con servidor en Python, recibe un video y devuelve cinco clips verticales 9:16 con subtítulos (FFmpeg), puntaje de 0 a 99 y la explicación de cada clip. No se fija de antemano ningún modelo: se elige el mejor con las métricas definidas.")
st(P[58], t1)
q = clone_after(P[58], t2)
q = clone_after(q, t3)
q = clone_after(q, t4)

# ---- C22, C23: metricas cuantitativas y de validacion del modelo de deep learning
m1 = ("Para el sistema automático, la métrica primaria es el acierto@5: que al menos uno de los cinco clips elegidos caiga sobre un pico real de retención. Se complementa con el F1 temporal entre el tiempo cubierto por los clips y el de los picos, el NDCG@10 (Järvelin & Kekäläinen, 2002), la precisión@5 y el cociente entre el calor del clip y el calor medio del video (Sul et al., 2023), todos comparados con el azar calculado por video. Se reporta además la matriz de confusión por ventana para describir la selección como clasificador.")
m2 = ("Para los modelos de aprendizaje profundo se registra la pérdida de entrenamiento (error cuadrático medio o entropía cruzada de ranking por listas, ListNet; Cao et al., 2007) y se evalúan con las mismas métricas mediante validación cruzada de 10 particiones agrupada por canal, para detectar sobreajuste. Las diferencias entre métodos se contrastan con la prueba de rangos con signo de Wilcoxon (1945) para las métricas continuas y con la prueba exacta de McNemar (1947) para el acierto binario, con umbral de Bonferroni (Dunn, 1961) cuando se prueban varias variantes. Para la validación con usuarios se usa un cuestionario de utilidad percibida con escala Likert de cinco puntos aplicado a cinco creadores de podcast; con n = 5 se reporta estadística descriptiva (mediana y rango) y no se hacen inferencias.")
st(P[60], m1)
clone_after(P[60], m2)

# ---- C24, C25: metodologia segun Hernandez-Sampieri (enfoque, alcance, diseno, poblacion, instrumentos, analisis)
g1 = ("Siguiendo a Hernández-Sampieri y Mendoza (2018), la investigación tiene un enfoque cuantitativo, porque mide variables con instrumentos objetivos (variables de audio y texto, y métricas de acierto) y contrasta hipótesis con pruebas estadísticas. Su alcance es correlacional con fines predictivos: relaciona las variables del contenido con la retención de la audiencia y evalúa qué tan bien las ordenan. El diseño es no experimental y transeccional, porque no se manipulan variables y los videos y sus curvas se observan tal como existen; a esto se suma una validación descriptiva con usuarios.")
g2 = ("La población son los videos de YouTube de contenido conversacional en español e inglés con curva de re-reproducción; la muestra, de unos 770 videos, se obtuvo por muestreo no probabilístico dirigido con 50 consultas, y la unidad de análisis es el video con sus ventanas de 15 a 90 s. Los instrumentos son la tabla de variables por ventana, la curva Most Replayed como regla de calificación y un cuestionario de utilidad para cinco creadores de podcast, con consentimiento informado. La recolección es automatizada (yt-dlp y Whisper); el procesamiento calcula las 71 variables como percentiles dentro del video; y el análisis compara el sistema con el azar mediante las métricas y pruebas descritas.")
g3 = ("Para cuidar la validez, los pesos de la fórmula se fijan solo con los videos de desarrollo y se congelan antes de evaluar, la posición del clip se excluye de las variables para evitar fugas de información, las particiones se agrupan por canal y la hipótesis se escribe antes de mirar los datos de confirmación y de las cohortes frescas.")
st(P[62], g1)
q = clone_after(P[62], g2)
clone_after(q, g3)

# ---- C26: diagrama de flujo con iconos
st(P[64], "La Figura 1 resume el flujo de trabajo con un ícono por fase; los pasos siguen ese mismo orden en la metodología y en los objetivos.")
fig_p = P[65]
for r in list(fig_p.runs):
    r._r.getparent().remove(r._r)
fig_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fig_p.add_run().add_picture(str(ROOT / "reports" / "flujo_ficha_iconos.png"), width=Inches(6.5))
st(P[66], "Figura 1. Flujo de trabajo de la investigación, de la creación del dataset a la validación con usuarios.")
PASOS = ["1. Creación del dataset: búsqueda de videos con 50 consultas (ES y EN), descarga de audio y de la curva de re-reproducción con yt-dlp, y partición en desarrollo, confirmación y cohortes frescas.",
         "2. Preprocesamiento: transcripción con Whisper, agrupación en oraciones y generación de candidatos de 15 a 90 s; extracción de 71 variables por ventana (audio, eventos de sonido, texto, gancho y fluidez) transformadas a percentiles dentro del propio video.",
         "3. Entrenamiento de modelos: azar, fórmula de 17 variables ponderadas, LightGBM LambdaRank, modelos de aprendizaje profundo de secuencia y red de ecuaciones; el modelo final adoptado es la fórmula de 17 variables en versión 0/1, elegida por su explicabilidad.",
         "4. Evaluación del sistema automático: cohortes frescas con hipótesis previa, contrastando los clips elegidos con el mapa de calor de retención mediante acierto@5, F1 temporal y NDCG@10, y pruebas estadísticas pareadas.",
         "5. Página web: carga del video, elección de cinco clips que no compartan más de 30 % de su duración, ajuste a cortes de escena, recorte vertical 9:16 con seguimiento del hablante, subtítulos y explicación del puntaje.",
         "6. Validación con usuarios: cuestionario de utilidad percibida con cinco creadores de podcast, con consentimiento informado, y análisis descriptivo."]
for p_, t in zip(P[67:73], PASOS):
    st(p_, t)

# ---- referencias: agregar las nuevas, quitar las que ya no se citan (C27) y ordenar
art_refs = [p.text.strip() for p in art.paragraphs[[i for i, p in enumerate(art.paragraphs) if p.text.strip().startswith("REFERENCIAS")][-1] + 1:] if p.text.strip()]
def ref(prefix):
    return next(r for r in art_refs if r.startswith(prefix))
NUEVAS = [ref(p_) for p_ in ("Cao, Z.", "Cho, K.", "Dunn, O.", "Järvelin", "Lea, C.", "McNemar", "Neubeck", "Park, Y.", "Sahoo", "Schuster", "Wilcoxon")]
ref_ps = P[74:94]
todas = [p.text.strip() for p in ref_ps] + NUEVAS
fold = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
cuerpo = "\n".join(p.text for p in d.paragraphs if p not in ref_ps)
cuerpo += "\n" + "\n".join(c.text for c in tb._tbl.xpath(".//w:t") if False)  # la tabla cita por nombre, ya cubierto en el texto
cuerpo += "\n" + "\n".join(t.text for t in tb._tbl.iter() if t.tag.endswith("}t") and t.text)
def citada(r):
    m = re.match(r"^([^,]+),.*?\((\d{4})", r)
    if not m:
        return True
    ap = fold(m.group(1)).split()[-1]
    return bool(re.search(ap + r".{0,80}" + m.group(2), fold(cuerpo), re.S))
sin_cita = [r for r in todas if not citada(r)]
print("referencias sin cita en el texto (se quitan):", [r[:40] for r in sin_cita])
finales = sorted([r for r in todas if r not in sin_cita], key=fold)
last = ref_ps[-1]
for k, t in enumerate(finales):
    if k < len(ref_ps):
        st(ref_ps[k], t)
    else:
        last = clone_after(last, t)
for p_ in ref_ps[len(finales):]:
    drop(p_)
d.save(r"F:\TESISJF\Ficha_Investigacion_NUNEZDELPRADO_v9_clips.docx")
print("ok | OG palabras:", len(OG.split()), "| referencias:", len(finales))
