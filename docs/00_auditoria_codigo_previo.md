# 00 — Auditoría del código y material previo

- **Fecha:** 2026-09-21
- **Autor de la tesis:** Núñez del Prado Vega, José Francisco (ULima, Ingeniería de Sistemas)
- **Carpeta auditada:** `ulima/tesisOFICIAL/desarrollo/` (y, como contexto, `ulima/tesisOFICIAL/` y `ulima/`)
- **Alcance:** inventario de archivos, lenguajes, dependencias y estado del software. Durante la auditoría no se borró, modificó ni movió ningún archivo.

---

## 1. Resultado principal

**No existe código previo.** La carpeta `desarrollo/` estaba vacía (0 archivos, sin archivos ocultos) y no hay ningún archivo `.py`, `.ipynb`, `requirements.txt` ni configuración de proyecto en `tesisOFICIAL/` ni en el resto de `ulima/`.

Por eso:

- No hay módulos que evaluar como "funciona" o "roto".
- No hace falta mover nada a `legacy/`; esa carpeta se creará solo si en una fase posterior hay algo que reemplazar.
- La Fase 2 empieza desde cero (*greenfield*). Lo que sí existe es **material de investigación** (ficha, papers, presentaciones y matrices) que define requisitos y restricciones. Se inventaría abajo.

---

## 2. Inventario de `tesisOFICIAL/` (material de investigación, no código)

| Archivo | Tipo | Contenido | Observación |
|---|---|---|---|
| `Ficha_Investigacion_Oficial_20221730_resuelta.docx` | Word | Ficha oficial de investigación (título, problema, objetivos, metodología) | **Fuente de requisitos.** Idéntico byte a byte a `…Oficial_20221730.docx` y `…COMPLETA.docx` (mismo MD5 `650f0c56…`) |
| `Ficha_Investigacion_Oficial_20221730.docx` | Word | Duplicado exacto | — |
| `Ficha_Investigacion_COMPLETA.docx` | Word | Duplicado exacto | — |
| `Ficha_Investigacion_Oficial_20221730_BACKUP.docx` | Word | Versión anterior de la ficha (MD5 distinto) | Respaldo |
| `FINAL.pptx` | PowerPoint | Exposición del paper SPOT (Kwak et al., 2025, *Electronics* 14(18) 3640): arquitectura CNN+TimeSformer, CAFGL, resultados y limitaciones | Base de la técnica 3 (Most Replayed) |
| `Plantilla_1.2.pptx` | PowerPoint | Plantilla de la exposición | — |
| `electronics-14-03640-v2.pdf` | PDF, 20 pp. | Paper SPOT | Técnica 3 |
| `SVHighlights_2606.06926.pdf` | PDF, 12 pp. | Lee et al. (2026), *SVHighlights: Towards Extremely Long Sport Video Highlight Detection*, KDD 2026 | Referencia de benchmark para videos largos |
| `final.xlsx` / `revisar_excel.xlsx` | Excel | Matriz grupal del Seminario (Avance 1.1 y 1.2). Filas del autor: SVHighlights, SPOT y Cresci (2020, bots) | Duplicados exactos entre sí |
| `revisar_excel_COMPLETO.xlsx` | Excel | Otra versión de la matriz | — |
| `unpacked/`, `pptunpacked/`, `finalunpacked/` | XML | Contenido descomprimido de los .docx/.pptx (restos de edición) | Pueden ignorarse |

### Material relacionado en `ulima/` (fuera de la carpeta de la tesis)

| Archivo | Relevancia |
|---|---|
| `KVSUM_Explicacion.md` | Explica KVSUM (2011): fórmula de peso de términos por pasaje, una variante de TF-IDF con *passage frequency*. **Base directa de la técnica 5.** |
| `Peso_Palabras_Clave_Papers.pptx` | Compara Summarize-Pro (TF-IDF + embeddings/KeyBERT) con KVSUM y propone combinarlos. **Técnicas 5 y 6.** |
| `MKT360_Motor_Clips_Peso_Palabras.pptx` | Propuesta de un "motor de clips tipo Opus Clip": pasa de palabras clave a momentos clave, con una fórmula de scoring de segmentos. **Antecedente conceptual directo del sistema.** |
| `A_Keyword-based_Video_Summarization_…pdf` | Paper KVSUM |
| `Summarize-Pro_…pdf` | Paper Summarize-Pro |

Estos archivos se consultaron como referencia y no se modificaron.

---

## 3. Requisitos implícitos extraídos de la ficha oficial

| Aspecto | Lo que dice la ficha |
|---|---|
| Título | *"A Deep Learning Approach for Automated Highlight Detection and Virality Scoring in Short-Form Video Clip Generation"* |
| Objetivo general | Recibir un video largo y generar clips verticales 9:16, **cada uno con un puntaje de viralidad** |
| Dominio | Podcasts, entrevistas y contenido conversacional; **español e inglés**; de 20 min a 3 h; al menos un hablante visible |
| Herramientas | Whisper con marcas de tiempo por palabra, **pyannote-audio** (diarización), MediaPipe/YOLO (hablante activo) |
| Modelo de scoring | Transformer con *pairwise ranking loss* (según VideoLights y SVHighlights) |
| Datasets de evaluación | TVSum, SumMe, Mr. HiSum, SVHighlights y un conjunto propio con métricas reales de engagement |
| Métricas | F1, mAP, Kendall/Spearman (highlights); RMSE y Pearson (viralidad vs engagement) |

---

## 4. Discrepancias y riesgos detectados (a resolver antes de la Fase 1)

### 4.1 La ficha y el encargo actual no coinciden en el modelo
- La **ficha** promete un modelo de *deep learning* (transformer con ranking por pares) y un **score de viralidad** validado con engagement real (RMSE y Pearson).
- El **encargo actual** propone un ranker **LightGBM** con etiquetas débiles (Most Replayed y selección por LLM), evaluado con precision@K, F1 vs Most Replayed y MRR.

**Riesgo:** en la sustentación pueden observar que el título dice "Deep Learning" y el modelo central es gradient boosting. Hay dos salidas razonables:
1. **Ajustar el título y los objetivos** con la asesora (por ejemplo, "enfoque híbrido multimodal").
2. **Mantener el título** y justificar que el componente profundo está en los extractores: faster-whisper, embeddings de KeyBERT/sentence-transformers, LLM y MediaPipe. LightGBM con objetivo **LambdaRank** sigue siendo *learning-to-rank* por pares/listas, coherente con la ficha. Se podría añadir un baseline neuronal (MLP o transformer ligero sobre las mismas features) para comparar.

Además, **Most Replayed mide re-reproducción dentro de YouTube, no viralidad en TikTok/Reels.** Si se mantiene "virality score", hay que declararlo como *proxy* o incluir el conjunto propio con engagement real.

### 4.2 Falta la técnica 2
La lista del encargo salta de la técnica 1 (Lotus) a la 3 (SPOT). **La técnica 2 no está definida.** El diseño pide que "1–2" aporten contexto, así que hay que confirmarla. Candidatos coherentes con el material existente:
- **Summarize-Pro:** resumen con transformer + BERTopic para tópicos. Ya aparece en tus presentaciones.
- **KVSUM:** surrogates verbales y visuales, y segmentación por pasajes. Ya está documentado en `KVSUM_Explicacion.md`.
- **Diarización con pyannote**, que figura en la ficha y aporta turnos de habla como contexto.

### 4.3 Entorno de ejecución

| Elemento | Estado | Implicancia |
|---|---|---|
| Python | Solo **3.12.10** instalado | El encargo pide 3.11. Hay que instalar 3.11 (recomendado por la compatibilidad de wheels de mediapipe, spaCy y pyannote) o justificar 3.12 en `DECISIONES.md` |
| GPU | **AMD Radeon integrada, sin CUDA** | faster-whisper correrá en CPU (`int8`). Con un video de 1–3 h, el modelo `medium` o `large-v3` tomará mucho tiempo. Conviene usar `small`/`medium` por defecto y configurable |
| CPU / RAM | Ryzen 7 7735HS, 13.7 GB | Suficiente para LightGBM, librosa y PySceneDetect. Justo para modelos grandes |
| ffmpeg | 8.1.2 instalado | OK para cortes y render |
| Paquetes presentes | faster-whisper 1.2.1, openai-whisper, torch 2.13, anthropic 0.118, openai 2.48, pandas 3.0.5, numpy 2.5.1, PyYAML | Están en el Python global. Se usará un **entorno virtual propio** con versiones pinneadas |
| Paquetes ausentes | spaCy, KeyBERT, sentence-transformers, LightGBM, librosa, PySceneDetect, MediaPipe, OpenCV, scikit-learn, pytest, **yt-dlp** | Se instalarán en la Fase 2 |
| Control de versiones | `desarrollo/` **no es un repositorio git** | Recomendado `git init` para trazabilidad y para respaldar `DECISIONES.md` |
| OneDrive | El proyecto vive dentro de OneDrive | Los videos, modelos y `.venv` pesados saturarán la sincronización. Conviene excluir `data/raw`, `models/` y `.venv` (o ubicarlos fuera de OneDrive) |

### 4.4 Riesgos de datos
- **Most Replayed** no está en la YouTube Data API oficial. Se obtiene del campo `heatmap` de `yt-dlp` y solo existe en videos con audiencia suficiente (limitación que ya señala SPOT). Hay que revisar los Términos de Servicio de YouTube y usarlo con fines académicos. El dataset **Mr. HiSum** trae estas curvas ya recolectadas, pero para videos de YT-8M, que no son conversacionales.
- **TVSum y SumMe** son videos cortos y visuales, sin habla dominante. Sirven como referencia, pero no representan el dominio podcast. Hay que declararlo como limitación.
- No hay todavía un **conjunto propio** de podcasts con curva Most Replayed. Construirlo (por ejemplo, 50–150 videos en español e inglés) es una tarea crítica de la Fase 2.

---

## 5. Estado de partida para la Fase 2

- Código reutilizable: **ninguno**.
- Conocimiento reutilizable: la fórmula KVSUM (TF-IDF por pasaje), el esquema híbrido TF-IDF + embeddings (Summarize-Pro) y la idea de scoring de segmentos (MKT360). Se trasladan como diseño a `docs/01_diseno_metodologico.md`.
- Estructura a crear: `src/{ingest,transcribe,keywords,features,ranking,context,render}`, `data/`, `models/`, `notebooks/`, `tests/`, `docs/`, `configs/`, además de `requirements.txt`, `run_all.py` y `docs/DECISIONES.md`.

## 6. Decisiones pendientes del autor

1. **Técnica 2:** ¿cuál es? (ver §4.2)
2. **Enfoque frente a la ficha:** ¿se ajusta el título y los objetivos, o se mantiene "Deep Learning" con la justificación de §4.1? ¿Se incluye un baseline neuronal?
3. **Python 3.11 o 3.12:** ¿instalar 3.11?
4. **Idioma del dataset propio:** ¿español, inglés o ambos?, y ¿cuántos videos?
5. **LLM por defecto** para desarrollo y experimentos (Anthropic, OpenAI o local).
6. **git init** en `desarrollo/` y ubicación de los datos pesados fuera de OneDrive.
