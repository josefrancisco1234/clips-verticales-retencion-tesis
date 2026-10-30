"""MAPA_IDEAS_FUENTES: para cada idea de nuestro trabajo, la fuente externa que la sustenta, la(s) página(s) del PDF donde aparece
(buscadas por palabras clave en el texto del propio PDF) y la sección del artículo donde se cita."""
import csv
import re
import sys
from pathlib import Path

import docx
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
F = Path(r"F:\TESISJF\FUENTES")
fuentes = {r["clave"]: r for r in csv.DictReader(open(F / "FUENTES.csv", encoding="utf-8-sig"))}
d = docx.Document(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v19.docx")
ps = [p.text.strip() for p in d.paragraphs if p.text.strip()]
i0 = max(k for k, t in enumerate(ps) if t.startswith("REFERENCIAS"))
cuerpo = ps[:i0]

# (idea de nuestro trabajo, clave de la fuente, palabras clave a ubicar en el PDF, apoyo propio / decisión, qué tomamos)
IDEAS = [
    ("Usar la curva Most Replayed como etiqueta de relevancia de cada tramo (protocolo de podcasts)", "Park_2025", ["most replayed", "replay"], "etiquetas de relevancia 0-4 por video; la curva nunca es entrada (D-018, D-021)", "Rhapsody usa la curva de re-reproducción como etiqueta y define el protocolo de evaluación"),
    ("Clips curados por humanos como referencia alternativa (Repurpose-10K)", "Wu_2025", ["human", "editor", "repurpos"], "pendiente: entrenar con clips humanos", "Conjunto de clips editados por personas, no usa la curva de re-reproducción"),
    ("Conjunto de podcasts con ~13 mil episodios y momentos destacados (escala de referencia)", "Park_2025", ["13,364", "podcast", "highlight"], "Rhapsody pendiente por login en Hugging Face", "Define la tarea de detección de momentos destacados en podcasts"),
    ("Transcripción robusta con marcas de tiempo por palabra", "Radford_2023", ["word-level", "timestamp", "long-form"], "faster-whisper small/medium en GPU", "Modelo Whisper entrenado con supervisión débil a gran escala"),
    ("Aprender a ordenar ventanas con LambdaRank", "Burges_2010", ["lambdarank", "ndcg"], "R0 = LightGBM LambdaRank (campeón de producción)", "Deducción de LambdaRank/LambdaMART a partir de RankNet"),
    ("Árboles de gradiente con histogramas (LightGBM)", "Ke_2017", ["histogram", "gradient-based one-side", "leaf-wise"], "R0", "Eficiencia de LightGBM, base del modelo R0"),
    ("Explicar el puntaje con valores SHAP (palabras y variables que pesan)", "Lundberg_2017", ["shapley", "additive feature attribution"], "explicación por clip", "Marco de atribución aditiva SHAP"),
    ("SHAP exacto para árboles", "Lundberg_2020", ["treeexplainer", "tree explainer", "shapley"], "explicación por clip", "Algoritmo TreeExplainer para modelos de árboles"),
    ("Eventos de audio (risa, aplausos, música) con PANNs", "Kong_2020", ["audioset", "laughter", "pretrained audio neural networks"], "grupo E de variables", "Redes de audio preentrenadas para etiquetar eventos sonoros"),
    ("Embeddings de habla con HuBERT (grupo U, descartado en CPU)", "Hsu_2021", ["masked prediction", "hidden units"], "grupo U de variables", "Representación de habla autosupervisada"),
    ("Red recurrente bidireccional con GRU (modelo de secuencia comparado)", "Cho_2014", ["gated", "gru", "update gate", "reset gate"], "BiGRU perdió contra LightGBM (D-054)", "Definición de la unidad recurrente con compuertas"),
    ("Red convolucional temporal TCN (modelo de secuencia comparado)", "Lea_2017", ["dilated", "temporal convolutional"], "TCN perdió contra LightGBM (D-054)", "Convoluciones dilatadas causales sobre secuencias"),
    ("Red de ecuaciones EQL: red neuronal que entrega una ecuación legible", "Sahoo_2018", ["equation learner", "multiplication", "regulariz", "l1", "identity"], "explorador de ecuaciones y agente neuronal (D-086, D-096)", "Capas con unidades identidad, seno y producto, y regularización L1 para ecuaciones"),
    ("Detección de momentos destacados multimodal (comparación con el estado del arte)", "Liu_2022", ["highlight detection", "audio", "multi-modal"], "contexto del estado del arte", "UMT: transformadores multimodales para recuperación de momentos y destacados"),
    ("Marco unificado de anclaje temporal video-lenguaje", "Lin_2023", ["highlight detection", "temporal grounding", "unified"], "contexto del estado del arte", "UniVTG: preentrenamiento unificado para anclaje temporal"),
    ("Audio y visual conjuntos para destacados", "Badamdorj_2021", ["audio", "highlight", "joint"], "justifica incluir audio como señal", "Aprendizaje conjunto de audio y visual"),
    ("Destacados con transferencia entre modalidades", "Li_2024b", ["highlight", "modality"], "contexto del estado del arte", "Detección no supervisada con transferencia de modalidad"),
    ("Palabras clave con atención de contexto para destacados", "Um_2025", ["keyword", "highlight", "moment retrieval"], "grupo K de variables (palabras clave)", "El texto y las palabras clave aportan a la detección de destacados"),
    ("Predicción de engagement de videos cortos", "Li_2024a", ["engagement", "short video"], "motivación del problema", "Modelos de engagement de video corto"),
    ("Teasers de podcast con IA (caso de uso con humanos)", "Wang_2024", ["podcast", "teaser"], "evaluación humana con la rúbrica PodReels (pendiente)", "Flujo de co-creación de teasers de podcast"),
    ("Resumen abstractivo y extractivo para videos cortos desde largos", "Barua_2025", ["abstractive", "extractive", "short video"], "contexto de herramientas de clipping", "Lotus: creación de videos cortos desde largos"),
    ("Edición de videos largos a clips con comprensión narrativa", "Wang_2025", ["clip", "narrative", "long video"], "contexto de herramientas de clipping", "Marco de edición inspirado en humanos"),
]
SIN_PDF = [
    ("Etiquetas de interés desde la curva de re-reproducción y protocolo de métricas (Mr. HiSum)", "Sul_2023", "metricas de acierto@5, F1 temporal; curva solo califica", "Conjunto grande con la curva de re-reproducción de YouTube"),
    ("Métrica NDCG para ordenar clips", "Jrvelin_2002", "NDCG@10", "Definición de ganancia acumulada descontada"),
    ("Aprendizaje de ranking por ganancia (GBM de Friedman)", "Friedman_2001", "base teórica de LightGBM", "Aproximación voraz de funciones con ganancia de gradiente"),
    ("Prueba de rangos con signo de Wilcoxon", "Wilcoxon_1945", "comparaciones pareadas por video (todas las rondas)", "Prueba no paramétrica para muestras pareadas"),
    ("Prueba de McNemar para aciertos pareados", "McNemar_1947", "comparación de aciertos@5 entre métodos", "Prueba para proporciones correlacionadas"),
    ("Desbalance de clases (pocos picos frente a muchos tramos)", "He_2009", "etiquetas por quintiles dentro del video", "Revisión de aprendizaje con datos desbalanceados"),
    ("Redes recurrentes bidireccionales", "Schuster_1997", "BiGRU (D-054)", "Definición de la red recurrente bidireccional"),
    ("Palabras clave con embeddings (KeyBERT)", "Grootendorst_2020", "grupo K de variables", "Extracción de palabras clave con BERT"),
    ("Predicción de popularidad de videos cortos con atención multimodal", "Cho_2024", "motivación del problema", "Modelo multimodal de popularidad"),
    ("Marco de calidad y popularidad de videos", "Javed_2025", "motivación del problema", "Marco para predecir calidad de video"),
    ("Detección de destacados con perceptual espacial", "Kwak_2025", "contexto del estado del arte", "Modelo de destacados para clips de video"),
    ("Metodología de la investigación (rutas cuantitativa y mixta)", "HernndezSampieri_2018", "diseño del estudio", "Libro de texto: rutas de investigación"),
]


def paginas(clave, kws):
    p = F / "pdfs" / f"{clave}.pdf"
    if not p.exists():
        return None
    out = []
    doc = fitz.open(p)
    for i, pg in enumerate(doc, 1):
        t = pg.get_text().lower()
        n = sum(t.count(k) for k in kws)
        if n:
            out.append((n, i))
    out.sort(reverse=True)
    return sorted(i for _, i in out[:4]), len(doc)


def seccion(clave):
    f = fuentes[clave]
    sur = re.sub(r"[^A-Za-zÀ-ÿ ]", "", f["autor"]).split()[-1]
    sec = None
    pats = []
    for k, t in enumerate(cuerpo):
        if re.match(r"^\d+(\.\d+)*\.?\s+[A-ZÁÉÍÓÚ]", t) and len(t) < 120:
            sec = t
        if re.search(sur + r".{0,40}" + f["anio"][:4], t):
            pats.append(sec or "Introducción")
    return "; ".join(dict.fromkeys(pats)) or "no se cita en el cuerpo"


filas = []
for idea, k, kws, propio, toma in IDEAS:
    f = fuentes[k]
    r = paginas(k, kws)
    filas.append({"idea_de_nuestro_trabajo": idea, "fuente": f["cita_APA"][:170], "clave": k, "doi_o_enlace": f["doi"] or f["url"],
                  "pdf_local": f["pdf_local"] if f["pdf_local"].endswith(".pdf") else "sin PDF abierto: abrir por DOI",
                  "paginas_pdf_donde_aparece": ", ".join(map(str, r[0])) if r else "", "total_paginas_pdf": r[1] if r else "",
                  "palabras_clave_buscadas": " | ".join(kws), "que_tomamos": toma, "donde_se_usa_en_nuestro_trabajo": propio, "seccion_del_articulo_donde_se_cita": seccion(k)})
for idea, k, propio, toma in SIN_PDF:
    f = fuentes[k]
    filas.append({"idea_de_nuestro_trabajo": idea, "fuente": f["cita_APA"][:170], "clave": k, "doi_o_enlace": f["doi"] or f["url"] or "libro: sin enlace",
                  "pdf_local": "sin PDF abierto: abrir por DOI" if f["doi"] else "sin PDF", "paginas_pdf_donde_aparece": "verificar en la fuente", "total_paginas_pdf": "",
                  "palabras_clave_buscadas": "", "que_tomamos": toma, "donde_se_usa_en_nuestro_trabajo": propio, "seccion_del_articulo_donde_se_cita": seccion(k)})
with open(F / "MAPA_IDEAS_FUENTES.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0]))
    w.writeheader()
    w.writerows(filas)
for r in filas:
    print(f"{r['clave']:15s} págs {r['paginas_pdf_donde_aparece']:12s} | {r['seccion_del_articulo_donde_se_cita'][:70]}")
