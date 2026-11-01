"""Word v36: ajusta el artículo a la plantilla A.3 (resumen de hasta 250 palabras sin citas, sin tabla en Trabajos relacionados,
introducción con párrafos de 5 a 6 oraciones con cita y párrafo de estructura del artículo)."""
import copy
import re
import sys

import docx
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v35.docx")
body = d.element.body


def P(prefix):
    return next(p for p in d.paragraphs if p.text.strip().startswith(prefix))


def st(p, t):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    p.runs[0].text = t


def after(tpl, text, anchor_el):
    el = copy.deepcopy(tpl._p)
    anchor_el.addnext(el)
    q = Paragraph(el, tpl._parent)
    st(q, text)
    return q


# ---- 1) resumen y abstract: hasta 250 palabras, sin citas
RES = ("La producción de clips cortos a partir de grabaciones largas depende de la edición manual y de herramientas comerciales que no documentan sus criterios. "
       "Este trabajo propone un sistema abierto y auditable que, solo con el audio y la transcripción de un video conversacional, elige cinco clips y los puntúa de 0 a 99 según su potencial de retención. "
       "La curva Most Replayed de YouTube califica el sistema y nunca es una entrada. "
       "Con un conjunto propio de unos 770 videos en español e inglés se calcularon 71 variables y, con una regla fijada antes de mirar los datos de confirmación, se conservaron 17, ponderadas por su correlación parcial mediana con el calor real; cada una se convierte en una bandera 0/1 y la suma se lleva a una escala de 0 a 99. "
       "Se compararon el azar, la fórmula (V0), la fórmula con clips de hasta 45 s (V1) y un modelo de ranking LightGBM (R0) con hipótesis previa. "
       "En una cohorte fresca de 93 videos, los cinco clips tocaron al menos un pico de retención en 47.3 %, 54.8 % y 62.4 % con V0, V1 y R0, frente a 26.9 % del azar; en una segunda cohorte, R0 alcanzó 49.2 % frente a 30.0 %. "
       "Otros modelos (redes de secuencia, texto, imagen, ensamble) no superaron a la fórmula de forma confirmada. "
       "Con solo contenido el techo fue de 50 a 69 %. "
       "Se adoptó V1 en banderas 0/1 por su explicabilidad.")
ABS = ("Abstract: The production of short clips from long recordings relies on manual editing and on commercial tools that do not disclose their criteria. "
       "This work proposes an open, auditable system that, using only the audio and transcript of a conversational video, selects five clips and scores them from 0 to 99 by their retention potential. "
       "The YouTube Most Replayed curve grades the system and is never an input. "
       "With a dataset of about 770 Spanish and English videos, 71 variables were computed and, with a rule fixed before looking at the confirmation data, 17 were kept, weighted by their median partial correlation with the real heat; each becomes a 0/1 flag and the sum is scaled to 0 to 99. "
       "Chance, the formula (V0), the formula with clips of up to 45 s (V1) and a LightGBM ranking model (R0) were compared with prior hypotheses. "
       "On a fresh cohort of 93 videos, the five clips hit at least one retention peak in 47.3 %, 54.8 % and 62.4 % with V0, V1 and R0, against 26.9 % for chance; on a second cohort, R0 reached 49.2 % against 30.0 %. "
       "Other models (sequence networks, text, image, ensemble) did not beat the formula in a confirmed way. "
       "With content alone the ceiling was 50 to 69 %. "
       "V1 with 0/1 flags was adopted for its interpretability.")
for t in (RES, ABS):
    assert len(t.split()) <= 250, len(t.split())
print("palabras resumen/abstract:", len(RES.split()), len(ABS.split()))
st(P("La producción de clips cortos a partir de grabaciones largas"), RES)
st(P("Abstract: The production"), ABS)

# ---- 2) quitar la Tabla 1 de Trabajos relacionados y renumerar las tablas siguientes
cap = P("Tabla 1. Comparación de los trabajos relacionados")
tbl = cap._p.getnext()
assert tbl.tag.endswith("}tbl")
body.remove(tbl)
cap._p.getparent().remove(cap._p)
p53 = P("La Tabla 1 compara los trabajos revisados")
st(p53, "Al comparar los trabajos revisados por su contexto y conjunto de datos, su técnica y su limitación frente al problema de este estudio, se observa que los conjuntos con etiqueta de re-reproducción (Mr. HiSum y Rhapsody) ampliaron la escala de evaluación, que los modelos de detección de highlights se concentraron en señales visuales o en consultas textuales, y que los sistemas de edición asistida se validaron con personas y no con una medida objetiva de retención (Sul et al., 2023; Park et al., 2025; Liu et al., 2022; Barua et al., 2025).")


def renum(old):
    pat = re.compile(rf"Tabla {old}\b")
    for p in d.paragraphs:
        for r in p.runs:
            if pat.search(r.text):   # solo los runs con texto coincidente: asignar r.text a un run con imagen la borra
                r.text = pat.sub(f"Tabla {old - 1}", r.text)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        if pat.search(r.text):   # solo los runs con texto coincidente: asignar r.text a un run con imagen la borra
                            r.text = pat.sub(f"Tabla {old - 1}", r.text)


for old in range(2, 16):
    renum(old)

# ---- 3) introducción: párrafos de 5 a 6 oraciones, cada uno con cita, y párrafo de estructura
p36 = P("Las limitaciones comunes de estos trabajos son tres.")
st(p36, "Los avances recientes en detección de momentos destacados parten de consultas textuales o de señales visuales (Lei et al., 2021; Lin et al., 2023). Las limitaciones comunes de estos trabajos son tres. "
   "Primero, la mayoría trata el habla como una señal secundaria, aunque en el contenido conversacional es la fuente principal de información (Liu et al., 2022; Kwak et al., 2025). "
   "Segundo, ningún enfoque entrega un sistema completo, abierto y explicable que vaya del video al clip con su puntaje, y los sistemas de edición asistida se validan con estudios de usuarios (Barua et al., 2025; Wang et al., 2024). "
   "Tercero, falta evidencia, bajo un protocolo estricto de validación, de cuánto se logra solo con el contenido frente al azar y frente a la curva real de retención (Sul et al., 2023). "
   "Estas tres limitaciones definen la brecha que este trabajo busca cerrar.")
p37 = P("Para cerrar esta brecha, este trabajo propone")
st(p37, "Para cerrar esta brecha, este trabajo propone un pipeline que recibe el audio y la transcripción de un video conversacional, extrae variables con modelos preentrenados de aprendizaje profundo (Whisper, PANNs, modelos de oraciones) y puntúa los candidatos con una fórmula de variables ponderadas que se compara con el azar y con un modelo de ranking aprendido (LightGBM LambdaRank) (Radford et al., 2023; Kong et al., 2020; Ke et al., 2017). "
   "El conjunto de datos propio, YT-MR, reúne unos 770 videos en español e inglés etiquetados con la curva Most Replayed de YouTube, siguiendo la receta de los conjuntos Mr. HiSum y Rhapsody (Sul et al., 2023; Park et al., 2025). "
   "Las contribuciones son: (i) un pipeline completo de video a clips verticales 9:16 con puntaje de 0 a 99 y explicación por clip; (ii) una fórmula abierta de 17 variables, explicable; (iii) un protocolo de desarrollo, confirmación y cohortes frescas con hipótesis previa; "
   "(iv) un resultado negativo documentado, pues modelos más complejos no mejoraron de forma confirmada a la fórmula sencilla; y (v) un ciclo de mejora automática que somete cada idea nueva al mismo protocolo de validación (Sul et al., 2023). "
   "El aporte incremental frente al estado del arte es medir cuánto se logra solo con audio y texto, de forma abierta y explicable, y no solo proponer un modelo (Barua et al., 2025).")
p38 = P("El objetivo general es desarrollar un pipeline")
st(p38, "El objetivo general es desarrollar un pipeline basado en modelos de aprendizaje profundo y de ranking que, a partir del audio y la transcripción de un video conversacional, seleccione y puntúe de 0 a 99 clips verticales (9:16) con alto potencial de retención. "
   "La retención se toma como la medida del interés de la audiencia (Li et al., 2024a). "
   "Los objetivos específicos son: (i) construir un conjunto de datos propio de videos conversacionales en español e inglés, etiquetado con la curva de re-reproducción de YouTube; (ii) preprocesar los videos con Whisper, segmentarlos en candidatos de 15 a 90 s y extraer 71 variables de audio y texto; "
   "(iii) entrenar un modelo de ranking y una fórmula de variables ponderadas como modelos base, con validación cruzada por canal; (iv) entrenar y comparar modelos de aprendizaje profundo frente al ranker de árboles; "
   "(v) evaluar el sistema con acierto@5, F1 temporal y NDCG@10 en cohortes frescas, frente al azar y a la curva real de retención; (vi) integrar el sistema en una página web que genere cinco clips verticales con puntaje y explicación; y (vii) validar la utilidad y la usabilidad de la página con cinco creadores de podcast. "
   "Los objetivos se agrupan en datos (i y ii), modelos (iii y iv), evaluación (v) y producto (vi y vii). "
   "La curva de YouTube solo califica el sistema y nunca entra como variable (Sul et al., 2023).")
p39 = P("Con ello se busca responder tres preguntas.")
st(p39, "Con ello se busca responder tres preguntas. "
   "La primera es si un modelo de ranking aprendido supera al azar y a una fórmula fija de variables ponderadas en el acierto de al menos un pico de retención entre cinco clips, bajo un protocolo con hipótesis previa (Sul et al., 2023). "
   "La segunda es si los modelos de aprendizaje profundo de secuencia (BiGRU, TCN y Transformer) mejoran de forma confirmada al ranker de árboles sobre las mismas variables (Ke et al., 2017). "
   "La tercera es si los creadores de podcast perciben la página web como útil y usable. "
   "Las diferencias entre métodos se contrastan con las pruebas de Wilcoxon y de McNemar, y con la corrección de Bonferroni cuando se prueba una familia de variantes (Wilcoxon, 1945; McNemar, 1947; Dunn, 1961). "
   "Responder estas preguntas permite acotar cuánto aporta el aprendizaje frente a una fórmula explicable.")
est = after(p39, "La estructura del artículo es la siguiente. En la sección de trabajos relacionados se discuten los estudios sobre detección de momentos destacados, edición asistida y engagement (Sul et al., 2023; Barua et al., 2025). "
            "En la sección de marco teórico se revisan la transcripción, las representaciones de audio y de texto, el aprendizaje de ranking y la explicabilidad (Radford et al., 2023; Ke et al., 2017). "
            "Luego, la metodología describe el pipeline, los datos, las variables y el protocolo, y la experimentación detalla el entorno, la configuración técnica y la partición de los datos. "
            "Después se presentan los resultados y su discusión frente a la literatura. "
            "Finalmente, se exponen las conclusiones y los trabajos futuros.", p39._p)
d.save(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v36.docx")
print("ok")
