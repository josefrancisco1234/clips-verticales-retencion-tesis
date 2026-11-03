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
SALIDA = __import__("os").environ.get("PPT_SALIDA") or r"F:\TESISJF\ENTREGA_NOTA2_FINAL_Diapositivas\PPT_Nota2_Nunez_del_Prado.pptx"
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

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR


def caja(slide, x, y, w, h, color, titulo, cuerpo, tam=12, tam_titulo=13):
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor.from_string(color); sh.line.fill.background(); sh.shadow.inherit = False
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(0.15); tf.margin_top = Inches(0.1)
    items = ([titulo] if titulo else []) + list(cuerpo)
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        etiqueta = t.split(":")[0] + ":" if (not titulo and t.startswith("Brecha identificada:")) else None
        if etiqueta:   # la etiqueta va en negrita y el resto en texto normal
            r0 = p.add_run(); r0.text = etiqueta; r0.font.size = Pt(tam); r0.font.bold = True; r0.font.color.rgb = RGBColor(0, 0, 0)
            t = t[len(etiqueta):]
        r = p.add_run(); r.text = t; r.font.size = Pt(tam_titulo if (titulo and i == 0) else tam)
        r.font.bold = bool(titulo and i == 0); r.font.color.rgb = RGBColor(0, 0, 0)
        p.space_after = Pt(5)
    return sh


bo = prs.slides.add_slide(L["CUSTOM_8"])
_t = bo.shapes.title; _t.left, _t.top, _t.width, _t.height = Inches(0.4), Inches(0.35), Inches(9.2), Inches(0.6)
txt(bo.shapes.title, "Brecha y Objetivos de la Investigación", size=22)
for r in bo.shapes.title.text_frame.paragraphs[0].runs:
    r.font.color.rgb = RGBColor(0, 0, 0)
caja(bo, 0.4, 1.1, 9.2, 1.25, "EEEEEE", "Objetivo General:",
     ["Desarrollar un pipeline basado en aprendizaje profundo y de ranking que, con solo el audio y la transcripción de un video conversacional, seleccione y puntúe de 0 a 99 clips verticales (9:16) con alto potencial de retención, de forma abierta y explicable."], 12.5, 14)
caja(bo, 0.4, 2.55, 3.8, 2.75, "FDE9D9", "",
     ["Brecha identificada: Inexistencia de un sistema abierto y explicable que, usando solo audio y texto en contenido conversacional, puntúe cada clip y contraste su elección con una medida objetiva de retención bajo un protocolo estricto de validación."], 13)
caja(bo, 4.35, 2.55, 5.25, 2.75, "FDE9D9", "Objetivos Específicos:",
     ["1) Datos: construir el conjunto propio (más de 500 videos en español e inglés, con la curva Most Replayed) y preprocesar con Whisper, candidatos de 15 a 90 s y 71 variables de audio y texto.",
      "2) Modelos: entrenar y comparar la fórmula de variables ponderadas y el ranker LightGBM frente a modelos de secuencia y red de ecuaciones, con validación cruzada por canal.",
      "3) Evaluación y producto: medir con acierto@5, F1 temporal y NDCG@10 frente al azar, integrar la web (5 clips con puntaje y explicación) y validar con 5 creadores (utilidad y SUS)."], 10.5, 13)
notas(bo, "1 minuto para objetivos. Los 7 objetivos específicos del artículo se agrupan en tres: datos, modelos, y evaluación y producto. La curva de YouTube solo califica el sistema, nunca entra como variable.")


def tabla_literatura():
    sl = prs.slides.add_slide(L["CUSTOM_8"])
    t = sl.shapes.title; t.left, t.top, t.width, t.height = Inches(0.4), Inches(0.3), Inches(9.2), Inches(0.55)
    txt(sl.shapes.title, "Trabajos Relacionados", size=22)
    for r in sl.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    enc = ["Autor (Año)", "Dataset utilizado", "Técnicas de preprocesamiento", "Algoritmos evaluados", "Principales hallazgos y limitaciones"]
    filas = [
        ("Sul et al. (2023), Mr. HiSum", "31 892 videos de YouTube con la etiqueta Most Replayed (≥ 50 000 vistas, hasta 300 s)",
         "Etiqueta agregada de re-reproducción; estudio con usuarios", "Detección de momentos destacados; transferencia entre conjuntos",
         "64.8 % de acuerdo de los usuarios con la etiqueta; sesgo autocumplido; videos cortos y no conversacionales"),
        ("Park et al. (2025), Rhapsody", "≈ 13 000 episodios de podcast, 100 segmentos por episodio",
         "Transcripción dividida en 100 segmentos alineados a la curva; rasgos de audio", "GPT-4o y Gemini sin ajuste; Llama de 1B ajustado",
         "GPT-4o rinde como heurísticas simples; el modelo ajustado con voz y texto mejora, pero el desempeño absoluto sigue bajo"),
        ("Liu et al. (2022), UMT", "QVHighlights, Charades-STA, YouTube Highlights y TVSum",
         "Codificadores unimodales de audio e imagen antes de fusionar", "Transformer multimodal (UMT)",
         "Fusionar audio e imagen supera a los modelos visuales; parte de consultas de texto; sin puntaje explicable"),
        ("Barua et al. (2025), Lotus", "Videos largos de creadores; estudio con usuarios",
         "Frases nominales de la transcripción (spaCy) en la instrucción al modelo de lenguaje", "Guion abstractivo + clips extractivos con LLM",
         "Videos comparables a los de herramientas tradicionales; se valida con personas, sin medida objetiva de retención"),
        ("Este trabajo (2026)", "Más de 500 videos analizados (≈ 770 con curva), español e inglés",
         "Percentil dentro del video; bandera 0/1 sobre el 25 % superior; 17 a 23 variables por segmento", "Fórmula V0/V1, LightGBM LambdaRank, BiGRU, TCN, Transformer y red de ecuaciones",
         "Acierto@5: V1 54.8 % y R0 62.4 % frente a 26.9 % del azar; abierto y explicable; solo audio y texto"),
    ]
    gt = sl.shapes.add_table(len(filas) + 1, 5, Inches(0.3), Inches(0.95), Inches(9.4), Inches(4.4))
    tb = gt.table
    for j, w in enumerate((1.45, 1.75, 2.0, 1.7, 2.5)):
        tb.columns[j].width = Inches(w)
    def celda(c, texto, size, bold, fondo, color):
        c.fill.solid(); c.fill.fore_color.rgb = RGBColor.from_string(fondo)
        c.margin_left = c.margin_right = Inches(0.06); c.margin_top = c.margin_bottom = Inches(0.04)
        tf = c.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; r = p.add_run(); r.text = texto; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = RGBColor.from_string(color)
    for j, h in enumerate(enc):
        celda(tb.cell(0, j), h, 10, True, "1F3A6E", "FFFFFF")
    for i, f in enumerate(filas, 1):
        ultimo = i == len(filas)
        for j, v in enumerate(f):
            celda(tb.cell(i, j), v, 8.5, j == 0, "FDE9D9" if ultimo else ("FFFFFF" if i % 2 else "F2F2F2"), "000000")
    notas(sl, "Cuatro trabajos representativos de los 26 revisados (detalle en el Excel de estado del arte) frente a este trabajo. Ninguno reúne las tres condiciones: habla como señal principal, puntaje explicable y validación contra una medida objetiva de retención.")
    return sl


tr_lit = tabla_literatura()


def problematica():
    sl = prs.slides.add_slide(L["CUSTOM_8"])
    t = sl.shapes.title; t.left, t.top, t.width, t.height = Inches(0.4), Inches(0.3), Inches(9.2), Inches(0.7)
    txt(sl.shapes.title, "Problemática: Selección Manual, Herramientas Cerradas y Falta de Evidencia", size=20)
    for r in sl.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    cards = [
        ("Selección manual y subjetiva", "Planificar, extraer y ordenar clips de un video largo es difícil y consume mucho tiempo de quien edita (Barua et al., 2025; Wang et al., 2024)."),
        ("Herramientas cerradas", "Opus Clip y Vizard automatizan parte del flujo, pero no publican los criterios con los que puntúan un segmento (Opus.pro, 2024; Vizard.ai, 2024)."),
        ("El habla como señal secundaria", "La literatura de momentos destacados se apoya sobre todo en la imagen, aunque en contenido conversacional la información está en el habla (Liu et al., 2022; Kwak et al., 2025)."),
        ("Validación sin medida objetiva", "Falta evidencia, bajo un protocolo estricto, de cuánto se logra solo con el contenido frente al azar y frente a la curva real de retención (Sul et al., 2023)."),
    ]
    pos = [(0.4, 1.2), (5.1, 1.2), (0.4, 3.3), (5.1, 3.3)]
    for (x, y), (h, d) in zip(pos, cards):
        c = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(4.5), Inches(1.95))
        c.adjustments[0] = 0.06
        c.fill.solid(); c.fill.fore_color.rgb = RGBColor.from_string("FDE9D9"); c.line.fill.background(); c.shadow.inherit = False
        ic = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.2), Inches(y + 0.18), Inches(0.3), Inches(0.3))
        ic.fill.solid(); ic.fill.fore_color.rgb = RGBColor.from_string("FF3A00"); ic.line.fill.background(); ic.shadow.inherit = False
        tb = sl.shapes.add_textbox(Inches(x + 0.15), Inches(y + 0.55), Inches(4.2), Inches(1.35))
        tf = tb.text_frame; tf.word_wrap = True
        p1 = tf.paragraphs[0]; r1 = p1.add_run(); r1.text = h; r1.font.size = Pt(15); r1.font.bold = True; r1.font.color.rgb = RGBColor(0x1F, 0x1F, 0x1F)
        p2 = tf.add_paragraph(); r2 = p2.add_run(); r2.text = d; r2.font.size = Pt(11); r2.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    notas(sl, "1 minuto. Cuatro problemas: la selección manual y subjetiva, las herramientas comerciales cerradas, el habla tratada como señal secundaria y la falta de validación con una medida objetiva de retención.")
    return sl


s_prob2 = problematica()

from pptx.enum.text import PP_ALIGN

def marco_teorico_3col():
    sl = prs.slides.add_slide(L["CUSTOM_8"])
    t = sl.shapes.title; t.left, t.top, t.width, t.height = Inches(0.4), Inches(0.3), Inches(9.2), Inches(0.55)
    txt(sl.shapes.title, "Marco teórico", size=22)
    for r in sl.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0)

    def col(x, w, color, titulo, items, tam=10.5, formula=False):
        sh = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(1.0), Inches(w), Inches(4.35))
        sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor.from_string(color); sh.line.fill.background(); sh.shadow.inherit = False
        tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.margin_left = tf.margin_right = Inches(0.14); tf.margin_top = Inches(0.1)
        p0 = tf.paragraphs[0]; p0.alignment = PP_ALIGN.CENTER
        r0 = p0.add_run(); r0.text = titulo; r0.font.size = Pt(13); r0.font.bold = True; r0.font.color.rgb = RGBColor(0, 0, 0)
        p0.space_after = Pt(8)
        for it in items:
            p = tf.add_paragraph(); p.space_after = Pt(7 if not formula else 9)
            if formula:
                p.alignment = PP_ALIGN.CENTER
                r = p.add_run(); r.text = it; r.font.size = Pt(tam); r.font.italic = True; r.font.name = "Cambria Math"
            else:
                r = p.add_run(); r.text = "•  " + it; r.font.size = Pt(tam)
            r.font.color.rgb = RGBColor(0, 0, 0)

    col(0.3, 3.05, "FDE9D9", "Preprocesamiento de audio y texto:", [
        "Whisper: transcripción con tiempos por palabra (Radford et al., 2023).",
        "PANNs: eventos de sonido como risa, aplausos y música (Kong et al., 2020).",
        "Candidatos de 15 a 90 s alineados a oración; 71 variables como percentil dentro del propio video.",
        "Bandera 0/1: por segmento se escanean 17 a 23 variables y solo cuentan las del 25 % superior, para evitar ruido."])
    col(3.5, 2.9, "EEEEEE", "Modelos de ranking e interpretabilidad:", [
        "LightGBM LambdaRank (Burges, 2010; Ke et al., 2017): cada video es un grupo y los árboles corrigen el orden de los clips.",
        "BiGRU, TCN y Transformer, y red de ecuaciones EQL (Sahoo et al., 2018), como alternativas.",
        "Aporte aditivo por variable, tipo SHAP (Lundberg & Lee, 2017): explica cada puntaje."])
    col(6.55, 3.15, "FDE9D9", "Métricas y puntaje:", [
        "Acierto@5 = videos con ≥ 1 clip en tramo caliente ÷ videos",
        "Precisión = tiempo de clips en zona caliente ÷ tiempo de clips",
        "Cobertura = tiempo caliente cubierto ÷ tiempo caliente total",
        "F1 = 2 · Precisión · Cobertura ÷ (Precisión + Cobertura)",
        "NDCG@10 = DCG@10 ÷ DCG ideal",
        "Puntaje = (raw − mín) ÷ (máx − mín) × 99"], 10, True)
    notas(sl, "2 minutos. Tres bloques: cómo se prepara el audio y el texto, qué modelos ordenan los clips y cómo se explican, y cómo se miden y se calcula el puntaje. Un tramo caliente es un tramo de la curva Most Replayed con valor mayor a 0.5.")
    return sl


mt3 = marco_teorico_3col()


def metodologia_fases():
    sl = prs.slides.add_slide(L["CUSTOM_8"])
    t = sl.shapes.title; t.left, t.top, t.width, t.height = Inches(0.4), Inches(0.25), Inches(3.0), Inches(0.55)
    txt(sl.shapes.title, "Metodología", size=22)
    for r in sl.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    tb = sl.shapes.add_textbox(Inches(0.4), Inches(1.4), Inches(3.1), Inches(3.4)); tf = tb.text_frame; tf.word_wrap = True
    for i, (a, b) in enumerate((("Enfoque: ", "cuantitativo."), ("Diseño: ", "no experimental de tipo descriptivo (Hernández-Sampieri & Mendoza, 2018)."),
                                ("Población: ", "más de 500 videos analizados (≈ 770 con curva) de YouTube, en español e inglés, con máximo 2 por canal."),
                                ("Unidad de análisis: ", "el video con sus ventanas de 15 a 90 s."))):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.space_after = Pt(9)
        r1 = p.add_run(); r1.text = "•  " + a; r1.font.size = Pt(13); r1.font.bold = True
        r2 = p.add_run(); r2.text = b; r2.font.size = Pt(13)
    fases = [
        ("Fase de Preparación", "0E7A6B", "D5EFEA", [("Búsqueda", "50 consultas ES y EN; máx. 2 por canal"), ("Descarga", "yt-dlp: audio y curva Most Replayed"), ("Transcripción", "Whisper en GPU, tiempos por palabra")]),
        ("Fase de Preprocesamiento", "E8C233", "FBF3CC", [("Candidatos", "ventanas de 15 a 90 s por oración"), ("71 variables", "audio, texto, gancho y eventos"), ("Percentil y bandera", "17 a 23 por segmento; umbral del 25 %")]),
        ("Fase de Modelado", "6C63C9", "E3E1F6", [("Fórmula V0 y V1", "pesos por correlación parcial"), ("LightGBM", "LambdaRank, un video por grupo"), ("Redes y EQL", "ciclo campeón / retador")]),
        ("Fase de Validación e Interpretación", "BFE0DA", "EAF5F2", [("Selección", "top 5 y mejor clip por capítulo"), ("Explicación", "puntaje 0–99 y aporte por variable"), ("Métricas y usuarios", "acierto@5, F1, NDCG; SUS 75")]),
    ]
    y0, h, gap = 0.45, 1.18, 0.1
    for i, (nom, fuerte, suave, pasos) in enumerate(fases):
        y = y0 + i * (h + gap)
        band = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3.65), Inches(y), Inches(6.15), Inches(h))
        band.fill.solid(); band.fill.fore_color.rgb = RGBColor.from_string(suave); band.line.fill.background(); band.shadow.inherit = False
        lab = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3.65), Inches(y), Inches(1.05), Inches(h))
        lab.fill.solid(); lab.fill.fore_color.rgb = RGBColor.from_string(fuerte); lab.line.fill.background(); lab.shadow.inherit = False
        lf = lab.text_frame; lf.word_wrap = True; lf.vertical_anchor = MSO_ANCHOR.MIDDLE
        lf.margin_left = lf.margin_right = Inches(0.05)
        lp = lf.paragraphs[0]; lp.alignment = PP_ALIGN.CENTER
        lr = lp.add_run(); lr.text = nom; lr.font.size = Pt(8 if len(nom) > 22 else 9.5); lr.font.bold = True
        lr.font.color.rgb = RGBColor(255, 255, 255) if fuerte not in ("E8C233", "BFE0DA") else RGBColor(0x33, 0x33, 0x33)
        for j, (a, b) in enumerate(pasos):
            x = 4.85 + j * 1.66
            bx = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y + 0.14), Inches(1.4), Inches(h - 0.28))
            bx.adjustments[0] = 0.08
            bx.fill.solid(); bx.fill.fore_color.rgb = RGBColor(255, 255, 255); bx.line.color.rgb = RGBColor.from_string(fuerte); bx.line.width = Pt(1.2); bx.shadow.inherit = False
            f = bx.text_frame; f.word_wrap = True; f.vertical_anchor = MSO_ANCHOR.MIDDLE
            f.margin_left = f.margin_right = Inches(0.05); f.margin_top = f.margin_bottom = Inches(0.03)
            p1 = f.paragraphs[0]; p1.alignment = PP_ALIGN.CENTER
            r1 = p1.add_run(); r1.text = a; r1.font.size = Pt(9.5); r1.font.bold = True; r1.font.color.rgb = RGBColor(0x1F, 0x1F, 0x1F)
            p2 = f.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run(); r2.text = b; r2.font.size = Pt(8); r2.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            if j < len(pasos) - 1:
                ar = sl.shapes.add_textbox(Inches(x + 1.4), Inches(y + h / 2 - 0.17), Inches(0.26), Inches(0.3))
                ap = ar.text_frame.paragraphs[0]; ap.alignment = PP_ALIGN.CENTER
                arr = ap.add_run(); arr.text = "→"; arr.font.size = Pt(13); arr.font.bold = True; arr.font.color.rgb = RGBColor.from_string(fuerte if fuerte != "BFE0DA" else "5A9A8F")
    notas(sl, "4 minutos para la metodología completa. Cuatro fases: preparación del dataset, preprocesamiento, modelado y validación con interpretación. Las figuras detalladas siguen en las diapositivas siguientes: pipeline, creación del clip, puntaje y mejora continua.")
    return sl


met_fases = metodologia_fases()

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
m1 = nueva_imagen("Metodología 4.2: pipeline de la metodología", REP / "pipeline_metodologia_D099.png",
                  "4 minutos para toda la metodología. Del video largo al clip: preprocesamiento (Whisper y PANNs), 71 variables como percentiles dentro de su video, modelo final de 17 variables en banderas 0/1, modelos de comparación, evaluación y selección con recorte 9:16.", 9.3, 3.9)
m2 = nueva_imagen("Metodología 4.6: creación del clip", REP / "pipeline_clip_D099.png",
                  "Cada candidato (ventana de 15 a 90 s armada con oraciones) se mide en tres bloques: Hook, Flow y Value. Luego se ordena con la fórmula o con LightGBM, se eligen cinco clips sin traslape mayor a 30 % y se recorta a 9:16.", 9.3, 3.9)
m3 = nueva_imagen("Metodología 4.7: cómo se calcula el puntaje", REP / "scoring_horizontal_D099.png",
                  "Ejemplo real de un video de 400 candidatos. Variable a percentil dentro del video; bandera 1 si está en el 25 % más alto; raw = suma de peso por bandera (+1.0118); puntaje = (raw − mín)/(máx − mín) × 99, con mín = −0.4851 y máx = +1.2400, da 86.", 9.4, 3.9)
m4 = nueva_imagen("Metodología 4.9: mejora continua del sistema", REP / "ciclo_automejora.png",
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
             "Modelo final: V1 en banderas 0/1 (17 a 23 variables escaneadas por segmento), por explicabilidad."], 11)
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

m5 = nueva_imagen("Metodología: el flujo completo del sistema (todo es backend)", REP / "workflow_horizontal_D099.png",
                  "Vista completa: A construir los datos, B modelar y evaluar, C usar el sistema con un video nuevo y validar con creadores, D mejorar solo. Todo es backend: la página web solo hace llamadas al servidor y este ejecuta el proceso.", 9.4, 3.95, 1.2)
m6 = nueva_imagen("Metodología 4.5: qué sale del audio y qué de la transcripción", REP / "audio_vs_transcripcion_D099.png",
                  "De las 17 variables de la fórmula, 8 salen solo del audio (44 % del peso), 4 de los tiempos de las palabras (34 %) y 5 del contenido del texto (22 %): 78 % del peso no lee lo que se dice.", 9.3, 3.6)
m7 = nuevo_texto("Metodología 4.6: capítulos, umbral y cortes del clip", [
    "Capítulos: el video se divide por los capítulos que YouTube muestra sobre la barra; cada capítulo recibe su mejor clip y el top 5 general se elige sobre todo el video (sin capítulos, bloques de 10 minutos).",
    "Umbral: para cada segmento se escanean entre 17 y 23 variables y solo cuentan las que superan el umbral (el 25 % más alto de su video), para evitar ruido; en los clips elegidos, 7.6 de las 17 de la fórmula lo superan en promedio.",
    "Cortes: cada clip empieza y termina en límites de oración con un margen de 0.15 s antes y hasta 0.35 s después que nunca invade la palabra vecina; así no se corta al hablante.",
], "Detalle en las secciones 4.6 y 4.7 del artículo. El mejor clip por capítulo es descriptivo: toca un pico real en 17.2 % de los casos frente a 13.5 % de una ventana al azar del capítulo.", 12)
m8 = nuevo_texto("Metodología 4.10: cómo se calcula cada métrica", [
    "Acierto@5: por video vale 1 si al menos uno de los 5 clips tiene 50 % o más de su duración en tramos calientes (valor mayor a 0.5, máximo 20 por video); la cifra es la suma entre el número de videos. Ej.: V1 acertó en 51 de 93 videos = 54.8 %.",
    "F1 temporal: precisión = tiempo de clips en zona caliente ÷ tiempo de clips; cobertura = tiempo caliente cubierto ÷ tiempo caliente total; F1 = 2·P·R / (P + R).",
    "Calor del clip: promedio de la curva en el clip ÷ calor medio del video (1.43x = 43 % más).",
    "Puntaje 0–99 = (raw − mín) / (máx − mín) × 99, con mín = −0.4851 y máx = +1.2400. Ej.: (1.0118 + 0.4851) / 1.7251 × 99 = 86.",
], "Todas las cifras de los conteos salen de los archivos por video; el azar se sortea 100 veces por video. Pruebas: Wilcoxon unilateral, McNemar y Bonferroni.", 11)
r3 = nuevo_texto("Resultados: R0 en confirmación y exploración automática", [
    "R0 (LightGBM LambdaRank) en los 352 videos de confirmación, con predicciones fuera de pliegue: 60.2 % de acierto@5 (212 de 352), F1 0.136; V0 56.2 % y azar 32.7 % sobre los mismos tramos.",
    "Mejora progresiva: azar → V0 → V1 → R0, confirmada paso a paso. Después se estancó: 73 rondas del agente con LightGBM y más de 12 000 del agente neuronal (EQL), 25 pruebas cada uno, 0 promociones (p mínimo 0.068).",
    "Fórmulas sin literatura: 26 de las 71 variables son fórmulas propias; el sistema crea y prueba fórmulas derivadas (productos, razones, suavizados) con el mismo protocolo.",
], "La base creció durante el trabajo: 526 videos de desarrollo, 557 de evaluación y unos 770 con curva; siempre más de 500 analizados.", 12)
r4 = nuevo_texto("Resultados: validación con 5 creadores de podcast", [
    "Utilidad percibida (6 afirmaciones, 1 a 5): mediana 4 (4–4) en todas, incluida la calificación de los clips. Cumple el criterio (mediana mayor o igual a 4).",
    "SUS (usabilidad): 75 (75–75) con 4 en las afirmaciones positivas y 2 en las negativas. Cumple la meta (mayor a 70; Bangor, 2008).",
    "Comentario común: los clips son muy buenos; el único problema es el seguimiento de la cámara al hablante, que falla con cabezas giradas o lejanas.",
], "Tabla 13 y 14 del artículo. Consentimientos firmados por los cinco participantes.", 13)
lim = nuevo_texto("Limitaciones y trabajos futuros", [
    "Limitaciones: solo YouTube y dos idiomas; los grupos de videos nuevos son pequeños (93, 63 y 83 videos); la señal visual se probó de forma gruesa; el reencuadre falla con cabezas giradas.",
    "Futuro: reencuadre con YOLO (personas y pose) y seguimiento entre cuadros; ampliar la base de videos (cada duplicación suma cerca de 1 punto de acierto@5); repetir la validación con más creadores.",
], "El YOLO no se incluyó por limitaciones de GPU y tiempo.", 14)

m_etl = nueva_imagen("Metodología 4.3: creación del dataset (ETL)", REP / "etl_horizontal_D099.png",
                     "Del video a la base de datos: búsqueda con 50 consultas, descarga del audio y de la curva Most Replayed, transcripción con Whisper, 71 variables por ventana, etiquetas solo para entrenar y calificar, y partición por canal en desarrollo, confirmación y grupos de videos nuevos.", 9.3, 3.9, 1.2)


def tabla_f1():
    sl = prs.slides.add_slide(L["CUSTOM_8"])
    t = sl.shapes.title; t.left, t.top, t.width, t.height = Inches(0.4), Inches(0.25), Inches(9.2), Inches(0.55)
    txt(sl.shapes.title, "Resultados: F1 temporal y qué usa cada propuesta", size=20)
    for r in sl.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0)
    enc = ["Propuesta", "Qué usa y cómo puntúa", "F1 grupo nuevo 1 (93)", "F1 confirmación (352)", "F1 val. cruzada (444)"]
    filas = [
        ("Azar", "Elige 5 clips sin criterio; se sortea 100 veces por video", "0.072", "0.070", "0.055"),
        ("V0: fórmula", "17 variables en percentil continuo con pesos fijos (correlación parcial con el calor, 121 videos); sin entrenamiento", "0.149", "0.131", "0.121"),
        ("V1: fórmula + clips cortos", "V0 solo con ventanas de hasta 45 s; el modelo final la usa con banderas 0/1 (17 a 23 variables por segmento, umbral del 25 %)", "0.141", "0.118", "—"),
        ("R0: LightGBM LambdaRank", "71 variables en percentil; un video es un grupo; árboles que corrigen el orden; entrenado con 444 videos", "0.142", "0.136 (fuera de pliegue)", "0.130"),
        ("BiGRU 128 (red de secuencia)", "Lee la línea de tiempo de 100 tramos con las variables en percentil; pérdida MSE o ListNet", "0.129", "—", "0.121"),
        ("EQL: red de ecuaciones", "Aprende una ecuación legible sobre las 17 variables (penalización L1); explorador automático", "—", "—", "0.134 (reservado, 107 videos)"),
        ("Calor real (solo califica)", "Usa la propia curva Most Replayed: techo de referencia, nunca entra al sistema", "0.555", "0.542", "—"),
    ]
    gt = sl.shapes.add_table(len(filas) + 1, 5, Inches(0.3), Inches(0.9), Inches(9.4), Inches(3.85))
    tb = gt.table
    for j, w in enumerate((1.65, 3.6, 1.2, 1.5, 1.45)):
        tb.columns[j].width = Inches(w)
    def celda(c, texto, size, bold, fondo, color, centro=False):
        c.fill.solid(); c.fill.fore_color.rgb = RGBColor.from_string(fondo)
        c.margin_left = c.margin_right = Inches(0.06); c.margin_top = c.margin_bottom = Inches(0.015)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = c.text_frame; tf.word_wrap = True
        pp = tf.paragraphs[0]
        if centro:
            pp.alignment = PP_ALIGN.CENTER
        r = pp.add_run(); r.text = texto; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = RGBColor.from_string(color)
    for j, h in enumerate(enc):
        celda(tb.cell(0, j), h, 9.5, True, "1F3A6E", "FFFFFF", j >= 2)
    for i, f in enumerate(filas, 1):
        fondo = "FDE9D9" if i == 3 else ("FFFFFF" if i % 2 else "F2F2F2")
        for j, v in enumerate(f):
            celda(tb.cell(i, j), v, 8 if j == 1 else 9, j == 0 or (j >= 2 and i == 3), fondo, "000000", j >= 2)
    nb = sl.shapes.add_textbox(Inches(0.3), Inches(5.0), Inches(9.4), Inches(0.5)); nt = nb.text_frame; nt.word_wrap = True
    rr = nt.paragraphs[0].add_run(); rr.text = "F1 temporal = 2·P·R / (P + R), con P = tiempo de los 5 clips en zona caliente ÷ tiempo de los clips y R = tiempo caliente cubierto ÷ tiempo caliente total; promedio por video. El modelo final adoptado es V1 con banderas 0/1, por su explicabilidad."
    rr.font.size = Pt(8); rr.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    notas(sl, "Todas las propuestas se comparan con el mismo F1 temporal sobre los mismos videos. V0 tiene el F1 más alto en el grupo nuevo 1, pero V1 acierta más veces; R0 acierta más pero cubre el mismo tiempo caliente que V1. Se adopta V1 por explicabilidad. Los F1 de las columnas no son comparables entre sí: cada columna es un conjunto distinto de videos.")
    return sl


tabla_f1_sl = tabla_f1()

# ---- diapositivas de resultados con el estilo de la profe: tabla azul marino, cifras grandes en naranja, tarjetas grises
AZM, NAR, GRIS = "1F3A6E", "E8661A", "F2F2F2"


def lamina(titulo):
    sl = prs.slides.add_slide(L["CUSTOM_8"])
    t = sl.shapes.title; t.left, t.top, t.width, t.height = Inches(0.4), Inches(0.25), Inches(9.2), Inches(0.6)
    txt(sl.shapes.title, titulo, size=22)
    for r in sl.shapes.title.text_frame.paragraphs[0].runs:
        r.font.color.rgb = RGBColor(0, 0, 0); r.font.bold = True
    sl.shapes.title.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
    return sl


def tabla_estilo(sl, enc, filas, x, y, w, colw, alto_fila=0.46, resaltar_col=None, resaltar_fila=None, size=11):
    gt = sl.shapes.add_table(len(filas) + 1, len(enc), Inches(x), Inches(y), Inches(w), Inches(alto_fila * (len(filas) + 1)))
    tb = gt.table
    for j, cw in enumerate(colw):
        tb.columns[j].width = Inches(cw)
    for i in range(len(filas) + 1):
        tb.rows[i].height = Inches(alto_fila)
    def cel(c, texto, bold, fondo, color, centro):
        c.fill.solid(); c.fill.fore_color.rgb = RGBColor.from_string(fondo)
        c.margin_left = c.margin_right = Inches(0.08); c.margin_top = c.margin_bottom = Inches(0.02)
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        pp = c.text_frame.paragraphs[0]; c.text_frame.word_wrap = True
        if centro:
            pp.alignment = PP_ALIGN.CENTER
        r = pp.add_run(); r.text = texto; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = RGBColor.from_string(color)
    for j, h in enumerate(enc):
        cel(tb.cell(0, j), h, True, AZM, "FFFFFF", j > 0)
    for i, f in enumerate(filas, 1):
        for j, v in enumerate(f):
            hl = (resaltar_col == j) or (resaltar_fila == i)
            cel(tb.cell(i, j), v, j == 0 or hl, "FDEFE6" if hl else ("FFFFFF" if i % 2 else GRIS), NAR if (hl and j > 0) else "000000", j > 0)
    return tb


def tarjeta(sl, x, y, w, h, titulo, cuerpo, size=11):
    sh = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor.from_string(GRIS); sh.line.fill.background(); sh.shadow.inherit = False
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = Inches(0.15); tf.margin_top = Inches(0.08)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT; r = p.add_run(); r.text = titulo; r.font.bold = True; r.font.size = Pt(size + 1); r.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.LEFT; r2_ = p2.add_run(); r2_.text = cuerpo; r2_.font.size = Pt(size); r2_.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def cifras(sl, items, y=1.0):
    n = len(items); ancho = 9.2 / n
    for i, (grande, chico) in enumerate(items):
        b = sl.shapes.add_textbox(Inches(0.4 + i * ancho), Inches(y), Inches(ancho - 0.15), Inches(1.1)); tf = b.text_frame; tf.word_wrap = True
        r = tf.paragraphs[0].add_run(); r.text = grande; r.font.size = Pt(26); r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(NAR if i == 0 else "111111")
        p = tf.add_paragraph(); r = p.add_run(); r.text = chico; r.font.size = Pt(11); r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


# 1) conjuntos de videos (como la tabla de balanceo de clases)
rs1 = lamina("Datos y Configuración de la Evaluación")
tabla_estilo(rs1, ["Fase / conjunto de videos", "Videos", "Para qué se usa", "Regla"], [
    ("Desarrollo inicial", "121", "Pesos de la fórmula V0", "Partición por canal"),
    ("Desarrollo ampliado", "444", "Validación cruzada de 10 particiones y entrenamiento de R0", "Partición por canal"),
    ("Confirmación", "352", "Confirmar V1 y R0 (fuera de pliegue)", "Congelado antes de mirar"),
    ("Grupo de videos nuevos 1", "93", "Una sola corrida preregistrada", "Hipótesis escrita antes"),
    ("Grupo de videos nuevos 2", "63", "Segunda confirmación independiente", "Hipótesis escrita antes"),
], 0.4, 1.15, 9.2, (2.5, 0.9, 3.7, 2.1), 0.5, resaltar_fila=None, size=11)
tarjeta(rs1, 0.4, 4.45, 4.5, 1.0, "Qué es un acierto", "El clip acierta si al menos 50 % de su duración cae en tramos calientes (curva mayor a 0.5). La curva solo califica.", 10.5)
tarjeta(rs1, 5.1, 4.45, 4.5, 1.0, "Clase minoritaria", "Solo 8.1 % de las ventanas son calientes; por eso se reporta acierto@5 y F1, no solo exactitud.", 10.5)
notas(rs1, "Los conjuntos se agrupan por canal para que ningún canal aparezca en entrenamiento y prueba. Los grupos de videos nuevos se congelan antes de mirar los resultados.")

# 2) cifras clave + gráfico de las cuatro formas
rs2 = lamina("Resultados: Las Cuatro Formas de Puntuar")
cifras(rs2, [("54.8 %", "acierto@5 de V1 (modelo final) en el grupo nuevo 1"), ("26.9 %", "acierto@5 del azar en los mismos videos"), ("+27.9", "puntos sobre el azar, solo con audio y texto")])
rs2.shapes.add_picture(str(REP / "ppt_acierto_cohorte1.png"), Inches(0.5), Inches(2.2), Inches(5.0))
tarjeta(rs2, 5.8, 2.3, 3.8, 1.35, "Sin entrenar nada", "De azar a V0 (fórmula de 17 variables) sube de 26.9 % a 47.3 %: +20.4 puntos.", 11)
tarjeta(rs2, 5.8, 3.8, 3.8, 1.35, "Clips cortos y banderas 0/1", "V1 limita los clips a 45 s y llega a 54.8 %; R0 (LightGBM) alcanza 62.4 %.", 11)
notas(rs2, "Acierto@5: al menos uno de los 5 clips toca un pico real. Grupo de videos nuevos 1, 93 videos: azar 26.9, V0 47.3, V1 54.8, R0 62.4.")

# 3) tabla de resultados por propuesta + confirmación
rs3 = lamina("Resultados en Videos Nuevos y en Confirmación")
tabla_estilo(rs3, ["Métrica (grupo nuevo 1, 93 videos)", "Azar", "V0", "V1 (final)", "R0"], [
    ("Acierto@5 (%)", "26.9", "47.3", "54.8", "62.4"),
    ("F1 temporal", "0.072", "0.149", "0.141", "0.142"),
    ("Veces sobre su propio azar", "1.00", "1.76", "2.04", "1.96"),
    ("Explicable por variable", "—", "Sí", "Sí", "No"),
], 0.4, 1.1, 9.2, (3.4, 1.3, 1.3, 1.6, 1.6), 0.5, resaltar_col=3, size=11.5)
tarjeta(rs3, 0.4, 3.9, 4.5, 1.5, "Confirmación (352 videos)", "V1 acierta 53.4 % frente a 29.1 % del azar. R0, con predicciones fuera de pliegue: 60.2 % (212 de 352), F1 0.136; V0 56.2 % y azar 32.7 % en esos tramos.", 11)
tarjeta(rs3, 5.1, 3.9, 4.5, 1.5, "Grupo nuevo 2 (63 videos)", "R0 acierta 49.2 % frente a 30.0 % del azar: la ventaja se mantiene, pero es menor que en el grupo 1. Por eso se adopta V1, que se explica variable por variable.", 11)
notas(rs3, "R0 puntúa por tramos con azar propio más alto (31.9 %): frente a su azar acierta 1.96 veces y V1 2.04 veces. El F1 no mejora de V0 a V1 porque los clips cortos tocan más picos pero cubren menos tiempo.")

# 4) matriz de confusión
rs4 = lamina("Resultados: Matriz de Confusión por Ventana")
rs4.shapes.add_picture(str(REP / "matriz_confusion_azul_D099.png"), Inches(0.4), Inches(1.1), Inches(4.4))
tabla_estilo(rs4, ["Métrica (557 videos, V1)", "Valor"], [
    ("Aciertos (calientes elegidas)", "468"), ("Falsas elegidas", "2 317"), ("Calientes no elegidas", "4 039"),
    ("Exactitud", "88.6 %"), ("Precisión / Cobertura", "16.8 % / 10.4 %")], 5.1, 1.1, 4.5, (3.0, 1.5), 0.42, resaltar_fila=None, size=11)
tarjeta(rs4, 5.1, 3.85, 4.5, 1.4, "Techo del contenido", "Solo con audio y texto el techo es de 50 a 69 %; con la curva real, 85 a 95 %, que no existe en un video aún no publicado.", 10.5)
notas(rs4, "La exactitud global no basta porque 92 % de las ventanas no son calientes; por eso se reportan también precisión y cobertura.")

# 5) mejora automática
rs5 = lamina("Resultados: Exploración Automática de Mejoras")
tabla_estilo(rs5, ["Agente de mejora", "Rondas", "Pruebas confirmatorias", "Promovidos"], [
    ("LightGBM (campeón / retador)", "73", "25", "0"),
    ("Red de ecuaciones neuronal (EQL)", "más de 12 000", "25", "0"),
], 0.4, 1.1, 9.2, (3.8, 1.5, 2.4, 1.5), 0.55, size=11.5)
tarjeta(rs5, 0.4, 3.0, 4.5, 1.6, "Resultado negativo documentado", "Ninguna variante superó de forma confirmada a la fórmula (p mínimo 0.068; umbral 0.05 con Bonferroni). Se reporta igual que los positivos.", 11)
tarjeta(rs5, 5.1, 3.0, 4.5, 1.6, "Fórmulas sin literatura", "26 de las 71 variables son fórmulas propias; el sistema crea y prueba productos, razones y suavizados con el mismo protocolo de validación.", 11)
notas(rs5, "Mejora progresiva azar, V0, V1, R0 confirmada paso a paso; después se estancó. La base creció durante el trabajo: siempre más de 500 videos analizados.")

# 6) validación con creadores
rs6 = lamina("Resultados: Validación con 5 Creadores de Podcast")
cifras(rs6, [("75", "puntaje SUS (meta mayor a 70)"), ("4 de 5", "mediana de utilidad percibida"), ("5", "creadores con consentimiento firmado")])
tabla_estilo(rs6, ["Instrumento", "Resultado", "Criterio", "¿Cumple?"], [
    ("Utilidad percibida (6 afirmaciones, Likert 1 a 5)", "Mediana 4 (4–4)", "Mediana ≥ 4", "Sí"),
    ("SUS (usabilidad)", "75 (75–75)", "Mayor a 70 (Bangor, 2008)", "Sí"),
    ("SUS: afirmaciones positivas / negativas", "4 / 2", "—", "—"),
], 0.4, 2.2, 9.2, (4.0, 1.9, 2.2, 1.1), 0.5, size=11)
tarjeta(rs6, 0.4, 4.35, 9.2, 0.95, "Comentario común", "Los clips son muy buenos; el único problema es el seguimiento de la cámara al hablante, que falla con cabezas giradas o lejanas (trabajo futuro: YOLO).", 11)
notas(rs6, "Tablas 13 y 14 del artículo. SUS = ((impares − 1) + (5 − pares)) × 2.5.")

concl = nuevo_texto("Conclusiones", [
    "Con solo audio y texto, la fórmula de 17 variables (17 a 23 escaneadas por segmento) más que duplica el acierto del azar (47.3 % frente a 26.9 %).",
    "Limitar los clips a 45 s sube el acierto a 54.8 %, a costa de cubrir menos tiempo caliente.",
    "El ranking aprendido (R0) llega a 62.4 % en el grupo de videos nuevos 1, pero rinde menos en el grupo de videos nuevos 2 y no se explica por variable.",
    "Se adoptó V1 en banderas 0/1 por su explicabilidad. La validación con cinco creadores cumplió utilidad (mediana 4) y SUS (75).",
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
usar = [slides[0], slides[1], s_prob2, bo, tr_lit, tl, mt3, met_fases, m5, m1, m_etl, m6, m2, m7, m3, m4, m8, e1, rs1, rs2, rs3, tabla_f1_sl, rs4, rs5, rs6, lim, concl, ref]
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
