"""PPT: los 3 flujos (ETL, BD, ranking con heatmap) y cómo el modelo se mejora de forma automática."""
import json, sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
H = [json.loads(l) for l in open(ROOT/"reports"/"auto_mejora"/"rondas.jsonl", encoding="utf-8")]
HN = [json.loads(l) for l in open(ROOT/"reports"/"auto_mejora_nn"/"rondas.jsonl", encoding="utf-8")]
NRN = len(HN); NPN = sum("p_wilcoxon" in h for h in HN); NPROMN = sum(h["promovido"] for h in HN)
pminN = min([h["p_wilcoxon"] for h in HN if "p_wilcoxon" in h] or [1.0])
NR = len(H); NP = sum("p_wilcoxon" in h for h in H); NPROM = sum(h["promovido"] for h in H)
pmin = min(h["p_wilcoxon"] for h in H if "p_wilcoxon" in h)
NAVY, AZUL, NAR, VERDE, MOR, GRIS = (RGBColor.from_string(c) for c in ("14213D", "1F4E79", "E8590C", "2F7D32", "6A3D9A", "555555"))
BL = RGBColor(255, 255, 255)
pr = Presentation(); pr.slide_width, pr.slide_height = Inches(13.333), Inches(7.5)
blank = pr.slide_layouts[6]


def tx(s, x, y, w, h, t, sz=16, b=False, c=GRIS, al=PP_ALIGN.LEFT, anc=MSO_ANCHOR.TOP, font="Calibri"):
    bx = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = bx.text_frame; tf.word_wrap = True; tf.vertical_anchor = anc
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, ln in enumerate(t if isinstance(t, list) else [t]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = al; r = p.add_run(); r.text = ln
        r.font.size = Pt(sz); r.font.bold = b; r.font.color.rgb = c; r.font.name = font; p.space_after = Pt(6)
    return bx


def box(s, x, y, w, h, color, titulo, lineas, tsz=16, lsz=13):
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)); sh.fill.solid(); sh.fill.fore_color.rgb = color
    sh.line.fill.background(); sh.adjustments[0] = 0.06; sh.shadow.inherit = False
    tx(s, x + .1, y + .08, w - .2, .6, titulo, tsz, True, BL)
    tx(s, x + .1, y + .7, w - .2, h - .8, lineas, lsz, False, BL)


def arrow(s, x, y, w=0.3):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(.4)); a.fill.solid(); a.fill.fore_color.rgb = GRIS; a.line.fill.background()


def slide(titulo):
    s = pr.slides.add_slide(blank); s.background.fill.solid(); s.background.fill.fore_color.rgb = BL
    tx(s, .6, .35, 12.1, .9, titulo, 32, True, NAVY, font="Cambria"); return s


def nota(s, t): tx(s, .6, 6.85, 12.1, .45, t, 12, False, GRIS)


# 1 portada
s = pr.slides.add_slide(blank); s.background.fill.solid(); s.background.fill.fore_color.rgb = NAVY
tx(s, .8, 2.0, 11.7, 1.6, "Cómo el sistema elige clips y se mejora solo", 44, True, BL, font="Cambria")
tx(s, .8, 3.9, 11.7, 1.0, "Tres flujos: ETL de videos, base de datos y ranking con el heatmap, más el ciclo de mejora automática", 20, False, RGBColor(0xCA, 0xDC, 0xFC))
tx(s, .8, 6.2, 11.7, .8, "José Francisco Núñez del Prado Vega · Ingeniería de Sistemas · Universidad de Lima", 14, False, RGBColor(0xCA, 0xDC, 0xFC))

# 2b workflow unificado
s = slide("Workflow unificado: cómo se conecta todo")
s.shapes.add_picture(str(ROOT/"reports"/"workflow_unificado.png"), Inches(1.25), Inches(1.15), height=Inches(6.0))

# 2 resumen
s = slide("Los tres flujos y el ciclo que los mejora")
for i, (c, t, l) in enumerate([(AZUL, "1 · ETL", ["De la URL de YouTube a audio, texto y curva"]), (AZUL, "2 · Base de datos", ["Una carpeta por tipo de dato; BD_TESIS con 1 021 videos"]),
                              (NAR, "3 · Ranking", ["71 variables, fórmula y LightGBM; 5 clips con puntaje 0–99"]), (MOR, "4 · Mejora automática", ["Agente que crea variables, las prueba y se corrige solo"])]):
    box(s, .6 + i * 3.1, 1.7, 2.9, 2.6, c, t, l, 20, 15)
tx(s, .6, 4.8, 12.1, 1.8, ["El heatmap de YouTube (Most Replayed) solo sirve para calificar y entrenar: nunca es una entrada del sistema.",
                          "El sistema decide con audio y texto, y el heatmap dice después si acertó."], 20, False, NAVY)
nota(s, "Entrada: video largo. Salida: clips verticales 9:16 con puntaje 0–99 y explicación.")

# 3 ETL
s = slide("Flujo 1 · ETL: del video a las ventanas con variables")
pasos = [("Buscar", "50+ consultas ES/EN; filtros de idioma y duración"), ("Descargar", "yt-dlp: audio y curva Most Replayed"), ("Transcribir", "Whisper por palabra, con marcas de tiempo"),
         ("Segmentar", "oraciones y candidatos de 15 a 90 segundos"), ("Calcular", "71 variables por ventana (audio y texto)"), ("Etiquetar", "calor real a relevancia 0–4 por video")]
for i, (t, l) in enumerate(pasos):
    x = .6 + i * 2.05
    box(s, x, 1.7, 1.85, 3.0, AZUL if i < 5 else NAR, f"{i + 1} {t}", [l], 15, 13)
    if i < 5: arrow(s, x + 1.84, 3.0, .2)
tx(s, .6, 5.1, 12.1, 1.6, ["Se descartan videos sin curva, sin habla suficiente o fuera de idioma (43 de 51 'libres' cayeron por idioma).", "Las cohortes frescas se congelan antes de mirarlas; los splits se agrupan por canal para evitar fugas."], 16, False, GRIS)

# 4 BD
s = slide("Flujo 2 · Base de datos en una carpeta (BD_TESIS)")
cols = [("audios/", "wav 16 kHz por video"), ("transcripciones/", "texto y palabras con tiempos"), ("variables/", "71 variables por ventana"), ("curvas/", "heatmap Most Replayed (solo etiqueta)"), ("indice_videos.csv", "un registro por video, 1 021")]
for i, (t, l) in enumerate(cols):
    box(s, .6 + i * 2.45, 1.7, 2.3, 2.3, MOR if i == 3 else AZUL, t, [l], 15, 13)
tx(s, .6, 4.4, 12.1, 2.3, ["Todo queda en disco: se puede reconstruir cualquier resultado sin volver a YouTube.",
                          "Las cohortes (desarrollo, reservado y frescas) quedan listadas en reports/ y no se mezclan.",
                          "El agente de mejora lee de aquí y escribe su bitácora en reports/auto_mejora/."], 17, False, GRIS)
nota(s, "BD_TESIS pesa 1.91 GB sin los audios completos; los 765 wav (65 GB) viven en tesis_data.")

# 5 ranking
s = slide("Flujo 3 · Ranking con 71 variables y heatmap")
pasos = [("Variables", "pausas, tono, energía, risa, palabras clave, gancho, fluidez"), ("Banderas 0/1", "cada variable vale 1 si está en el 25 % más alto de su video, y 0 si no"),
         ("Puntaje", "Modelo final: suma de peso × bandera de 17 variables. R0 (LightGBM) como referencia"), ("Top-5", "NMS: 5 clips con solape menor a 30 %"), ("Explicación", "SHAP: qué palabras y variables pesaron")]
for i, (t, l) in enumerate(pasos):
    x = .6 + i * 2.48
    box(s, x, 1.7, 2.25, 2.7, NAR if i == 2 else AZUL, t, [l], 17, 13)
    if i < 4: arrow(s, x + 2.26, 2.9, .2)
tx(s, .6, 4.8, 12.1, 2.0, ["Calificación: acierto = al menos uno de los 5 clips toca un pico real del heatmap.", "En videos nuevos: azar 32 %, fórmula V0 47 %, R0 (LightGBM) 52–62 % según cohorte.", "Con solo audio y texto el techo medido ronda 55–58 %; el 80 % solo se logra usando la curva, que está prohibida como entrada."], 16, False, GRIS)

# 5b modelo final 0/1
CB = json.load(open(ROOT/"reports"/"costo_binario_D098.json", encoding="utf-8"))
s = slide("Modelo final: 17 variables en 0/1")
box(s, .6, 1.5, 4.0, 2.7, AZUL, "Cómo puntúa", ["Cada variable vale 1 si está en el 25 % más alto de su video y 0 si no", "Puntaje = suma de pesos × banderas", "Se explica con una frase: «esta variable está en el top 25 % del video»"], 18, 14)
rows_ = [("Cohorte fresca 1 (93)", "cohorte fresca 1"), ("Cohorte fresca 2 (84)", "cohorte fresca 2"), ("Desarrollo (583)", "desarrollo (443)")]
tb = s.shapes.add_table(4, 3, Inches(4.9), Inches(1.5), Inches(7.8), Inches(2.7)).table
for j, (h, w) in enumerate((("Conjunto", 2.8), ("Percentil continuo", 2.4), ("Variables 0/1", 2.6))):
    tb.columns[j].width = Inches(w); c = tb.cell(0, j); c.text = h; c.text_frame.paragraphs[0].runs[0].font.size = Pt(13); c.text_frame.paragraphs[0].runs[0].font.bold = True
for i, (n, k) in enumerate(rows_, 1):
    g = CB[k]
    for j, t in enumerate((n, f"{g['continuo']['hit5']*100:.1f} % · F1 {g['continuo']['F1']:.3f}", f"{g['binario']['hit5']*100:.1f} % · F1 {g['binario']['F1']:.3f}")):
        c = tb.cell(i, j); c.text = t; c.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
tx(s, .6, 4.6, 12.1, 2.2, ["Costo medido: sin diferencia significativa (p = 0.59, 0.145 y 0.39), pero el 0/1 queda por debajo en las tres comparaciones; en la cohorte 2 baja de 48.8 % a 44.0 %.", "Se adopta por explicabilidad, no por precisión: el modelo más preciso sigue siendo el ranker aprendido R0 (62.4 % en la cohorte 1). Todo sigue por encima del azar."], 16, False, GRIS)
nota(s, "Acierto@5 y F1 sobre las 100 ventanas de cada video; difiere de la tabla de clips candidatos de 15 a 90 s.")

# 6 heatmap ejemplo
s = slide("Así se ve: puntaje del sistema frente al heatmap real")
s.shapes.add_picture(str(ROOT/"reports"/"ejemplo_heatmap_ranking.png"), Inches(1.4), Inches(1.4), width=Inches(10.5))
tx(s, .6, 6.15, 12.1, 1.1, ["Ejemplo ilustrativo: es el mejor de 300 videos (correlación 0.61); la correlación mediana de la fórmula en esos 300 es 0.14.", "Por eso se mide el acierto de los 5 clips en videos nuevos y no un caso favorable."], 14, False, GRIS)

# 7 mejora DL
s = slide("Cómo mejora el modelo de deep learning")
box(s, .6, 1.6, 3.9, 3.4, MOR, "Explorador de ecuaciones", ["Red EQL (Equation Learner): unidades identidad, tanh, producto y cuadrado", "Penalización L1 que deja una ecuación legible", "12 configuraciones por ronda"], 18, 14)
box(s, 4.7, 1.6, 3.9, 3.4, VERDE, "Campeón / retador", ["El retador compite con el modelo vigente en un conjunto reservado", "Se promueve solo con Wilcoxon p < 0.05", "Luego se confirma una vez en una cohorte fresca"], 18, 14)
box(s, 8.8, 1.6, 3.9, 3.4, AZUL, "Resultado hasta hoy", ["La red de 17 variables empata a LightGBM (F1 0.134) con una ecuación legible", "Con 68 variables empeora (0.112)", "Las redes de secuencia pierden"], 18, 14)
tx(s, .6, 5.4, 12.1, 1.3, ["Es el modelo propio que pidió la profesora: aprende fórmulas, no solo pesos, y su historial queda registrado también cuando pierde."], 18, False, NAVY)

# 8 agente autónomo
s = slide("Mejora automática: nadie le pide qué probar")
s.shapes.add_picture(str(ROOT/"reports"/"agente_auto.png"), Inches(1.9), Inches(1.3), width=Inches(9.5))
tx(s, .6, 6.05, 12.1, 1.2, ["Resultados del primer agente (LightGBM, D-095). El agente actual (auto_mejora_nn.py) entrena una red EQL en GPU, muta su arquitectura e inventa variables, con Bonferroni sobre 50 pruebas.", "Cada 10 rondas refresca el minero de papers (OpenAlex)."], 14, False, GRIS)

# 9 minero
s = slide("El minero de papers aporta ideas de variables")
box(s, .6, 1.6, 3.9, 3.3, MOR, "1 · Busca", ["OpenAlex, 15 consultas, trabajos 2020+", "1 339 trabajos con resumen"], 18, 14)
box(s, 4.7, 1.6, 3.9, 3.3, AZUL, "2 · Compara", ["Cuenta las señales que mencionan y las cruza con las 71 variables actuales"], 18, 14)
box(s, 8.8, 1.6, 3.9, 3.3, NAR, "3 · Propone", ["Cambios de hablante, muletillas, repeticiones, nombres propios", "Se probaron 4 variables: ninguna mejoró (p = 0.56 y 0.07)"], 18, 14)
tx(s, .6, 5.4, 12.1, 1.3, ["Limitación: lee título y resumen por patrones, no el trabajo completo. Siguiente paso: lectura con un modelo de lenguaje."], 17, False, GRIS)

# 10 camino
s = slide("Cómo llegamos hasta aquí")
hitos = [("1", "Fórmula V0", "17 pesos sobre audio y texto: 47 % de acierto frente a 27 % del azar (cohorte 1)", AZUL),
         ("2", "LightGBM R0", "aprende el ranking: 62 % en la cohorte 1 y 49 % contra 30 % de azar en la cohorte 2", NAR),
         ("3", "Lo que no funcionó", "redes de secuencia, juez LLM, señal visual, texto semántico, fronteras de tema, más datos", GRIS),
         ("4", "Red EQL", "deep learning que aprende una ecuación legible: empata a R0 con 17 variables", MOR),
         ("5", "Agente neuronal 24/7", "red EQL en GPU que muta su arquitectura e inventa variables; el agente previo (LightGBM) no promovió nada en 70+ rondas", VERDE)]
for i, (n, t, l, c) in enumerate(hitos):
    box(s, .6 + i * 2.48, 1.6, 2.3, 2.9, c, f"{n} · {t}", [l], 17, 13)
tx(s, .6, 4.9, 12.1, 1.2, ["Deep learning hoy: la red EQL y las de secuencia. El campeón que rankea sigue siendo LightGBM, y el agente neuronal 24/7 ya entrena y evoluciona la red EQL en GPU."], 16, False, NAVY)

# 11 estado
s = slide("Qué lleva el agente neuronal y qué falta")
for i, (n, l) in enumerate([(str(NRN), "rondas del agente neuronal"), (str(NPN), "pruebas gastadas de 25"), (str(NPROMN), "variables o arquitecturas promovidas"), (f"{pminN:.3f}", "mejor p (umbral 0.001)")]):
    tx(s, .6 + i * 3.1, 1.5, 2.9, 1.2, n, 54, True, MOR, PP_ALIGN.LEFT, font="Cambria")
    tx(s, .6 + i * 3.1, 2.75, 2.9, .6, l, 16, False, GRIS)
tx(s, .6, 3.7, 12.1, 3.1, [f"El primer agente (LightGBM) hizo {NR} rondas y no promovió nada; el agente neuronal sigue la misma regla, con Bonferroni sobre 50 pruebas.", "Hasta hoy ninguna variable nueva ni arquitectura superó la prueba: el sistema ya recoge casi todo lo que el contenido aporta.", "Las mejores candidatas quedan en cola para una sola confirmación en la cohorte fresca 3.", "Pendiente: Rhapsody (más datos y audio), que requiere login en Hugging Face, y la lectura completa de papers.", "No se promete 80 %: con solo audio y texto el techo medido es 55–58 %."], 16, False, GRIS)

# 11b producto final
s = slide("Producto final: tu podcast, 5 clips")
for i, (c, t, l) in enumerate([(AZUL, "1 · Pones el video", ["Copias tu podcast a la carpeta MIS_VIDEOS (mp4, mkv, mov…)"]), (NAR, "2 · Un botón", ["En la interfaz local pulsas «Generar mis 5 clips»"]),
                              (MOR, "3 · El sistema trabaja", ["Transcribe, calcula las variables, puntúa y elige 5 tramos sin solape"]), (VERDE, "4 · Recibes 5 clips", ["Verticales 9:16 con puntaje 0–99, subtítulos y reporte, en CLIPS_GENERADOS"])]):
    box(s, .6 + i * 3.1, 1.6, 2.9, 3.0, c, t, l, 18, 15)
tx(s, .6, 5.0, 12.1, 1.8, ["Elige solo con audio y texto y puntúa con las 17 variables en 0/1; la curva de YouTube nunca interviene. Un podcast de 12 min tardó unos 22 min con la GPU compartida con el agente.", "Corre en el PC con GPU de la tesis; la demo de 3 videos (Demo_Tesis_Clips.exe) funciona en cualquier Windows sin instalar nada."], 16, False, GRIS)

# 12 fuentes
import csv
M = [r for r in csv.DictReader(open(r"F:\TESISJF\FUENTES\MAPA_IDEAS_FUENTES.csv", encoding="utf-8-sig")) if r["paginas_pdf_donde_aparece"] not in ("", "verificar en la fuente")]
ELEG = ["Park_2025", "Radford_2023", "Burges_2010", "Ke_2017", "Lundberg_2017", "Kong_2020", "Sahoo_2018", "Cho_2014", "Lea_2017", "Liu_2022"]
sel = []
for k in ELEG:
    for r in M:
        if r["clave"] == k and r not in sel:
            sel.append(r); break
s = slide("En qué papers se apoya cada idea")
tb = s.shapes.add_table(len(sel) + 1, 3, Inches(.6), Inches(1.3), Inches(12.1), Inches(5.0)).table
for j, (h, w) in enumerate((("Idea de nuestro trabajo", 6.3), ("Fuente", 3.9), ("Páginas del PDF", 1.9))):
    tb.columns[j].width = Inches(w); c = tb.cell(0, j); c.text = h
    c.text_frame.paragraphs[0].runs[0].font.size = Pt(13); c.text_frame.paragraphs[0].runs[0].font.bold = True
for i, r in enumerate(sel, 1):
    au = r["fuente"].split(",")[0] + (" et al." if r["fuente"].split("(")[0].count(",") >= 3 else "")
    an = r["fuente"].split("(")[1][:4]
    for j, t in enumerate((r["idea_de_nuestro_trabajo"], f"{au} ({an})", r["paginas_pdf_donde_aparece"])):
        c = tb.cell(i, j); c.text = t; c.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
tx(s, .6, 6.55, 12.1, .7, ["Carpeta FUENTES: 21 PDF de acceso abierto verificados, FUENTES.csv (DOI verificado en Crossref) y MAPA_IDEAS_FUENTES.csv con todas las ideas. Páginas = número de página del PDF."], 12, False, GRIS)
pr.save(r"F:\TESISJF\PPT_Flujos_y_Mejora_Automatica.pptx"); print("ok", NR, NP, NPROM, pmin)
