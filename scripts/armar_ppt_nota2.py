"""PPT de la Nota 2 en la plantilla oficial (SI1_20262_NOTA 2_PLANTILLA.pptx): índice obligatorio, línea de tiempo de la literatura,
metodología con las figuras del artículo y resultados con las cifras del artículo v36. Salida: ENTREGA_NOTA2_FINAL/4_Diapositivas/."""
import copy
import re
import sys
from pathlib import Path

import docx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reports"
PLANT = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\SI1_20262_NOTA 2_PLANTILLA.pptx"
SALIDA = r"F:\TESISJF\ENTREGA_NOTA2_FINAL\4_Diapositivas\PPT_Nota2_Nunez_del_Prado.pptx"
ART = r"F:\TESISJF\Articulo_Investigacion_CIS2026_v36.docx"
NARANJA, GRIS = "#FF3A00", "#535353"

# ---- gráfico de resultados (cifras del artículo: Tabla 5, grupo de videos nuevos 1, 93 videos)
fig, ax = plt.subplots(figsize=(5.6, 3.3), dpi=220)
nom = ["Azar", "V0\nfórmula", "V1\nclips ≤ 45 s", "R0\nLightGBM"]
val = [26.9, 47.3, 54.8, 62.4]
cols = ["#CECECE", GRIS, NARANJA, "#111111"]
b = ax.bar(nom, val, color=cols, width=0.62)
for r, v in zip(b, val):
    ax.text(r.get_x() + r.get_width() / 2, v + 1.2, f"{v:.1f} %", ha="center", fontsize=9, fontweight="bold")
ax.set_ylim(0, 75); ax.set_ylabel("Acierto@5 (% de videos)", fontsize=9)
ax.set_title("Grupo de videos nuevos 1 (93 videos)", fontsize=10, fontweight="bold")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.tick_params(labelsize=8.5)
fig.tight_layout(); fig.savefig(REP / "ppt_acierto_cohorte1.png", facecolor="white"); plt.close(fig)

prs = Presentation(PLANT)
L = {l.name: l for l in prs.slide_layouts}
slides = list(prs.slides)


def txt(shape, text, size=None, bold=None):
    tf = shape.text_frame
    p0 = tf.paragraphs[0]
    for r in p0.runs[1:]:
        r._r.getparent().remove(r._r)
    if p0.runs:
        p0.runs[0].text = text
    else:
        p0.add_run().text = text
    for p in tf.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    for r in tf.paragraphs[0].runs:
        if size:
            r.font.size = Pt(size)
        if bold is not None:
            r.font.bold = bold


def bullets(shape, items, size=14, plano=False):
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    if plano:   # columnas: un solo párrafo con saltos de línea, para que todas las líneas tengan la misma sangría
        p = tf.paragraphs[0]
        for i, it in enumerate(items):
            r = p.add_run(); r.text = it; r.font.size = Pt(size)
            if i < len(items) - 1:
                p.add_line_break(); p.add_line_break()
        return
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = it; r.font.size = Pt(size)
        p.space_after = Pt(6)


def notas(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto


def nuevo_texto(titulo, items, nota, size=14):
    s = prs.slides.add_slide(L["1_Text slide with title 1"])
    txt(s.shapes.title, titulo)
    body = s.placeholders[1]
    body.left, body.top, body.width, body.height = Inches(0.6), Inches(1.9), Inches(8.8), Inches(3.3)
    bullets(body, items, size)
    notas(s, nota)
    return s


def nueva_imagen(titulo, img, nota, ancho=9.2, alto=3.9, top=1.3):
    s = prs.slides.add_slide(L["CUSTOM_8"])
    txt(s.shapes.title, titulo)
    t = s.shapes.title
    t.left, t.top, t.width, t.height = Inches(0.33), Inches(0.5), Inches(9.34), Inches(0.6)
    from PIL import Image
    w, h = Image.open(img).size
    k = min(ancho / w, alto / h)
    pw, ph = w * k, h * k
    s.shapes.add_picture(str(img), Inches((10 - pw) / 2), Inches(top + (alto - ph) / 2), Inches(pw), Inches(ph))
    notas(s, nota)
    return s


def tres_columnas(titulo, cols, nota):
    s = prs.slides.add_slide(L["1_Slide with three columns"])
    txt(s.shapes.title, titulo)
    ph = {p.placeholder_format.idx: p for p in s.placeholders}
    lay = {p.placeholder_format.idx: p for p in s.slide_layout.placeholders}
    for n, (h, body) in enumerate(cols):
        for k in (1 + 2 * n, 2 + 2 * n):   # geometría explícita completa (si no, el cuadro queda con ancho 0)
            q = lay[k]
            ph[k].left, ph[k].top, ph[k].width, ph[k].height = q.left, q.top, q.width, (Inches(2.5) if k == 2 + 2 * n else q.height)
        txt(ph[1 + 2 * n], h, bold=True)
        bullets(ph[2 + 2 * n], body, 12, True)
    for r in s.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    notas(s, nota)
    return s


# ---- 1: portada
s1 = slides[0]
for sh in s1.shapes:
    if sh.name.endswith(";207;p1"):
        txt(sh, "Selección automática de clips verticales con alto potencial de retención en videos conversacionales a partir de señales de audio y texto", size=24)
    elif sh.name.endswith(";208;p1"):
        txt(sh, "Inteligencia artificial / Procesamiento de audio y lenguaje")
    elif sh.name.endswith(";212;p1"):
        ps = sh.text_frame.paragraphs
        ps[0].runs[-1].text = ps[0].runs[-1].text.rstrip() + " José Francisco Núñez del Prado Vega"
        ps[1].runs[-1].text = ps[1].runs[-1].text.rstrip() + " Angela Gabriela Mayhua Quispe"
notas(s1, "Presentación de 15 minutos. Trabajo individual: el tiempo completo es mío.")
notas(slides[1], "Seis bloques en 15 minutos: problema 1, objetivos 1, literatura 2, marco teórico 2, metodología 4 y experimentos y resultados 4, más referencias.")

# ---- contenido nuevo
s_prob = nuevo_texto("Problema", [
    "Elegir los mejores momentos de un video largo (podcast, entrevista, charla) para publicarlos como clips cortos es manual y subjetivo.",
    "Las herramientas comerciales (Opus Clip, Vizard) no publican cómo puntúan un segmento: no se pueden auditar.",
    "La literatura de momentos destacados se apoya sobre todo en la imagen; en contenido conversacional la información está en el habla.",
    "Falta evidencia, con un protocolo estricto, de cuánto se logra solo con audio y texto frente al azar.",
], "1 minuto. Contexto: los creadores reportan que planificar y extraer clips es difícil (Barua et al., 2025). Problema: seleccionar los momentos de mayor retención en videos conversacionales largos, con un método abierto y explicable.", 14)
s_obj = nuevo_texto("Objetivos", [
    "General: desarrollar un pipeline que, con el audio y la transcripción de un video conversacional, seleccione y puntúe de 0 a 99 clips verticales (9:16) con alto potencial de retención.",
    "Datos: construir un conjunto propio (español e inglés) y extraer 71 variables de audio y texto.",
    "Modelos: una fórmula de variables ponderadas y un modelo de ranking, comparados con el azar y con redes de secuencia.",
    "Evaluación y producto: acierto@5, F1 temporal y NDCG@10; página web validada con cinco creadores de podcast.",
], "1 minuto. Son siete objetivos específicos en el artículo; aquí se agrupan en datos, modelos, evaluación y producto. La curva de YouTube solo califica; nunca entra como variable.", 13)

# ---- línea de tiempo de la literatura (slide 20 de la plantilla)
tl = slides[19]
txt(tl.shapes.title, "Literatura revisada: principales hallazgos", size=22)
ph = {sh.name.split(";")[1]: sh for sh in tl.shapes if sh.is_placeholder}
chev = ["728", "724", "726", "723", "727", "725"]
desc = ["717", "718", "719", "721", "720", "722"]
anios = ["2021", "2022", "2023", "2024", "2025", "2026"]
hall = ["Badamdorj: audio + imagen supera a solo imagen. Reddy: el texto predice el engagement en podcasts.",
        "Liu (UMT): modelo unificado visual-audio para momentos y destacados.",
        "Sul (Mr. HiSum): la curva Most Replayed refleja la percepción humana (64.8 % de acuerdo).",
        "Li: engagement como retención (NAWP, ECR). Wang: PodReels baja la carga del editor.",
        "Park (Rhapsody): destacados en podcasts. Barua (Lotus) y Wang: edición con modelos de lenguaje.",
        "Suen: la prosodia predice el engagement afectivo (R² = 0.85)."]
for c, d_, a, h in zip(chev, desc, anios, hall):
    txt(ph[c], a)
    txt(ph[d_], h, size=8)
notas(tl, "2 minutos. De 2021 a 2026: se pasa de señales visuales a multimodales, se adopta la curva de re-reproducción como etiqueta a gran escala y se incorporan modelos de lenguaje a la edición. Son 26 artículos en el estado del arte; aquí se muestran los hitos.")

s_brecha = tres_columnas("Brecha: ningún trabajo reúne las tres condiciones", [
    ("1 · Habla como señal principal", ["En contenido conversacional, la información está en el audio y la transcripción.", "La mayoría parte de imagen o de consultas de texto."]),
    ("2 · Puntaje explicable", ["Un sistema abierto, del video al clip, con el aporte de cada variable.", "Las herramientas comerciales son cerradas."]),
    ("3 · Validación objetiva", ["Contrastar con la curva real de retención bajo un protocolo con hipótesis previa.", "Los sistemas de edición se validan solo con personas."]),
], "Cierre de la revisión: esta es la brecha que se aborda (sección 2.6 del artículo).")

# ---- marco teórico (slide 13 de la plantilla, ya con tres columnas)
mt = slides[12]
txt(mt.shapes.title, "Marco teórico")
ph = {p.placeholder_format.idx: p for p in mt.placeholders}
cols = [("Señales de audio y texto", ["Whisper: transcripción con tiempos.", "PANNs: eventos de sonido (risa, música).", "Pausas, tono y volumen; palabras clave."]),
        ("Aprendizaje de ranking", ["LightGBM con objetivo LambdaRank.", "Un video es un grupo; árboles que corrigen el orden.", "Métricas: acierto@5, F1 temporal, NDCG@10."]),
        ("Explicabilidad y validación", ["Aporte aditivo por variable (SHAP).", "Wilcoxon, McNemar, Bonferroni.", "SUS para usabilidad (meta > 70)."])]
for n, (h, body) in enumerate(cols):
    txt(ph[1 + 2 * n], h, bold=True)
    bullets(ph[2 + 2 * n], body, 12, True)
notas(mt, "2 minutos. Tres bloques: de dónde salen las señales, cómo se aprende o se calcula un orden de clips y cómo se explica y se valida estadísticamente.")

# ---- metodología
m1 = nueva_imagen("Metodología: pipeline completo", REP / "pipeline_metodologia_D099.png",
                  "4 minutos para toda la metodología. Del video largo al clip: preprocesamiento (Whisper y PANNs), 71 variables como percentiles dentro de su video, modelo final de 17 variables en banderas 0/1, modelos de comparación, evaluación y selección con recorte 9:16.", 9.3, 3.9)
m2 = nueva_imagen("Metodología: creación del clip", REP / "pipeline_clip_D099.png",
                  "Cada candidato (ventana de 15 a 90 s armada con oraciones) se mide en tres bloques: Hook, Flow y Value. Luego se ordena con la fórmula o con LightGBM, se eligen cinco clips sin traslape mayor a 30 % y se recorta a 9:16.", 9.3, 3.9)
m3 = nueva_imagen("Metodología: cómo se calcula el puntaje", REP / "scoring_horizontal_D099.png",
                  "Ejemplo real de un video de 400 candidatos. Variable a percentil dentro del video; bandera 1 si está en el 25 % más alto; raw = suma de peso por bandera (+1.0118); puntaje = (raw − mín)/(máx − mín) × 99, con mín = −0.4851 y máx = +1.2400, da 86.", 9.4, 3.9)
m4 = nueva_imagen("Metodología: mejora continua del sistema", REP / "ciclo_automejora.png",
                  "Ciclo campeón/retador: se suman videos, un minero de papers propone señales, un explorador de ecuaciones las prueba y solo se promueve un nuevo campeón si supera al actual en datos reservados y se confirma una sola vez en un grupo de videos nuevos.", 9.0, 3.9)

# ---- experimentos y resultados
e1 = tres_columnas("Experimentos: datos, entorno y protocolo", [
    ("Datos (YT-MR)", ["~770 videos en español e inglés.", "Desarrollo 121 y 444; confirmación 352.", "Grupos de videos nuevos: 93 y 63 videos."]),
    ("Entorno", ["Intel Core i5-10400, 15.9 GB de RAM.", "GPU GTX 1660 SUPER (6 GB).", "Python 3.11, faster-whisper, LightGBM."]),
    ("Protocolo", ["Validación cruzada de 10 particiones por canal.", "Hipótesis previa y una sola corrida por grupo de videos nuevos.", "Wilcoxon y McNemar; Bonferroni."]),
], "Parte de los 4 minutos de experimentos y resultados. Todo se agrupa por canal para evitar fuga de información y los grupos de videos nuevos se congelan antes de mirarlas.")
r1 = prs.slides.add_slide(L["CUSTOM_8"])
_t = r1.shapes.title; _t.left, _t.top, _t.width, _t.height = Inches(0.33), Inches(0.5), Inches(9.34), Inches(0.6)
txt(r1.shapes.title, "Resultados: las cuatro formas de puntuar")
r1.shapes.add_picture(str(REP / "ppt_acierto_cohorte1.png"), Inches(0.5), Inches(1.5), Inches(5.3))
tb = r1.shapes.add_textbox(Inches(6.0), Inches(1.7), Inches(3.6), Inches(3.4))
bullets(tb, ["Azar → V0: +20.4 puntos sin entrenar nada.",
             "V1 (clips ≤ 45 s): 54.8 %; en confirmación (352 videos) 53.4 % frente a 29.1 % del azar.",
             "R0: 62.4 %, pero con azar propio de 31.9 %; en el grupo de videos nuevos 2, 49.2 % frente a 30.0 %.",
             "Modelo final: V1 en banderas 0/1, por explicabilidad."], 11)
notas(r1, "Grupo de videos nuevos 1: azar 26.9, V0 47.3, V1 54.8 y R0 62.4 de acierto@5. F1 temporal: 0.072, 0.149, 0.141 y 0.142. El F1 no mejora de V0 a V1 porque los clips cortos tocan más picos pero cubren menos tiempo. R0 puntúa ventanas por tramo con azar más alto (31.9 %): frente a su propio azar acierta 1.96 veces y V1 2.04 veces.")
r2 = prs.slides.add_slide(L["CUSTOM_8"])
_t = r2.shapes.title; _t.left, _t.top, _t.width, _t.height = Inches(0.33), Inches(0.5), Inches(9.34), Inches(0.6)
txt(r2.shapes.title, "Resultados: matriz de confusión y techo")
r2.shapes.add_picture(str(REP / "matriz_confusion_azul_D099.png"), Inches(0.5), Inches(1.45), Inches(4.4))
tb = r2.shapes.add_textbox(Inches(5.2), Inches(1.7), Inches(4.4), Inches(3.4))
bullets(tb, ["557 videos, V1, solo contenido: 468 aciertos, 2 317 falsas elegidas, 4 039 calientes no elegidas.",
             "Exactitud 88.6 %, precisión 16.8 % y cobertura 10.4 %: la clase caliente es minoritaria (8.1 %).",
             "Techo con solo contenido: 50 a 69 %; con la curva real: 85–95 %.",
             "Redes de secuencia, texto, imagen y ensamble no superaron a la fórmula de forma confirmada."], 11)
notas(r2, "La exactitud global no basta porque 92 % de las ventanas no son calientes; por eso se reportan también precisión y cobertura. El techo con la curva real solo sirve para calificar, no existe en un video aún no publicado.")
demo = nuevo_texto("Demostración de la página web (video de hasta 60 s)", [
    "Insertar aquí el video de la web: subir un video o link, ver los cinco clips 9:16 con subtítulos, el puntaje 0–99 y el desglose por variable.",
    "Código: github.com/josefrancisco1234/clips-verticales-retencion-tesis",
], "Pendiente: grabar el video de máximo 60 segundos con la web en funcionamiento (Clips_Web.exe) e insertarlo en esta diapositiva.", 14)
concl = nuevo_texto("Conclusiones", [
    "Con solo audio y texto, la fórmula de 17 variables más que duplica el acierto del azar (47.3 % frente a 26.9 %).",
    "Limitar los clips a 45 s sube el acierto a 54.8 %, a costa de cubrir menos tiempo caliente.",
    "El ranking aprendido (R0) llega a 62.4 % en el grupo de videos nuevos 1, pero rinde menos en el grupo de videos nuevos 2 y no se explica por variable.",
    "Se adoptó V1 en banderas 0/1 por su explicabilidad. Pendiente: validación con cinco creadores y ampliar el conjunto.",
], "Cierre de la exposición. Resultado negativo documentado: modelos más complejos no mejoraron de forma confirmada a la fórmula sencilla.", 13)
# referencias desde el artículo
d = docx.Document(ART)
P = [p.text.strip() for p in d.paragraphs]
i = [n for n, t in enumerate(P) if t.upper().startswith("REFERENCIAS")][-1]
refs = [t for t in P[i + 1:] if t]
claves = ["Sul, J.", "Park, Y.", "Badamdorj", "Liu, Y.", "Barua", "Li, D.", "Wang, X.", "Ke, G.", "Radford", "Kong, Q."]
sel = []
for k in claves:
    m = next((r for r in refs if r.startswith(k)), None)
    if m:
        sel.append(re.sub(r"\s+https?://\S+$", "", m))
ref = nuevo_texto("Referencias", sel, "Lista completa en el artículo (sección Referencias, APA 7).", 8)

# ---- orden final y limpieza de las diapositivas de ejemplo de la plantilla
usar = [slides[0], slides[1], s_prob, s_obj, tl, s_brecha, mt, m1, m2, m3, m4, e1, r1, r2, demo, concl, ref]
ids = prs.slides._sldIdLst
por_slide = {}
for sid in list(ids):
    por_slide[prs.part.related_part(sid.rId).slide.slide_id] = sid
mantener = [por_slide[s.slide_id] for s in usar]
for sid in list(ids):
    if sid not in mantener:
        prs.part.drop_rel(sid.rId)
        ids.remove(sid)
for sid in mantener:
    ids.remove(sid)
for sid in mantener:
    ids.append(sid)
prs.save(SALIDA)
print("ok", len(prs.slides), "diapositivas")
