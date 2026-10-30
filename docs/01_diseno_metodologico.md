# 01 — Diseño metodológico del modelo híbrido

- **Fecha:** 2026-09-22
- **Estado:** propuesta para aprobación (Fase 1)
- **Objetivo del sistema:** recibir un video largo de cualquier tipo y devolver clips cortos verticales (9:16). Cada clip lleva un **score de 0 a 99** con su desglose, las palabras de mayor peso con su contexto y subtítulos que las resaltan. La referencia funcional es Opus Clip, pero con un modelo entrenado sobre un dataset público y **auditable** en cada decisión.

> **Leyenda de verificación:** todas las referencias se comprobaron en arXiv, ACL Anthology, CVF, NeurIPS, ACM DL, MDPI o Springer. ⚠️ marca lo que falta confirmar leyendo el PDF completo.

---

## 1. Visión general del pipeline

```
video (cualquier tipo, 20 min – 3 h)
 │
 ├─[ingest]      ffmpeg → audio 16 kHz mono + video proxy de baja resolución; metadatos
 ├─[transcribe]  faster-whisper (int8, CPU) → palabras con timestamps; detección de idioma
 ├─[segment]     oraciones (PodReels) ∪ cortes de escena (PySceneDetect) → candidatos de 15–90 s
 │               + ventanas fijas de 20 s (Minimal Clips) como línea base
 ├─[keywords]    TF-IDF por pasaje (KVSUM) + KeyBERT multilingüe + frases nominales spaCy (Lotus)
 ├─[features]    léxico-semánticas · sentimiento/energía léxica · audio (librosa) · estructura tipo Opus (hook/flow)
 ├─[ranking]     LightGBM LambdaRank (grupo = video) → score 0–99 calibrado + desglose SHAP
 ├─[context]     LLM solo sobre el top-N: título, hook, “¿se entiende solo?”, ajuste de bordes
 └─[render]      ajuste a cortes naturales → reencuadre 9:16 (MediaPipe + Light-ASD) → subtítulos ASS con keywords resaltadas
```

**Principio de diseño:** lo caro (LLM y visión) solo trabaja sobre pocos candidatos; lo barato (texto y audio) ordena todos. Así el sistema corre en la laptop del autor, que solo tiene CPU y 13.7 GB de RAM.

---

## 2. Los 10 papers: qué aporta cada uno, qué tomo y qué descarto

### P1 — Lotus · *contexto: hook y conceptos*
Barua, A., Benharrak, K., Chen, M., Huh, M., & Pavel, A. (2025). *Lotus: Creating short videos from long videos with abstractive and extractive summarization.* **IUI '25**, 967–981. https://doi.org/10.1145/3708359.3712090
- **Aporta:** un LLM redacta un guion corto (parte abstractiva) y luego se le emparejan clips del video original (parte extractiva).
- **Tomo:**
  - El LLM genera el hook y el título sobre clips extractivos.
  - Extraigo "conceptos" con frases nominales de spaCy (`noun_chunks`) para describir cada clip y para las keywords de los subtítulos.
- **Descarto:** la narración sintética (TTS) y el emparejamiento abstractivo, porque rompen la sincronía entre audio y video y no producen un score por clip.
- ⚠️ La venue es IUI 2025, no CHI como se había dicho. Queda por confirmar en el PDF el uso exacto de spaCy.

### P2 — PodReels · *contexto: candidatos por oración y criterios de hook*
Wang, S., Ning, Z., Truong, A., Dontcheva, M., Li, D., & Chilton, L. B. (2024). *PodReels: Human-AI co-creation of video podcast teasers.* **DIS '24**, 958–974. https://doi.org/10.1145/3643834.3661591
- **Aporta:** un estudio formativo sobre qué hace bueno a un teaser. Sus cuatro ingredientes: unos 30 s, hook fuerte, contexto claro y buena producción. Además, selección por oraciones y limpieza de muletillas.
- **Tomo:**
  - Candidatos **alineados a oraciones** y eliminación de muletillas ("eh", "este", "o sea").
  - Su taxonomía de estilos (informativo, curiosidad, gracioso, emotivo) como salida del LLM.
  - Los cuatro ingredientes como **rúbrica de evaluación humana**.
- **Descarto:** mandar la transcripción completa a GPT-4 (caro y no reproducible) y la integración con Premiere.
- **Es la técnica 2** que faltaba en la lista original.

### P3 — SPOT · *etiquetas débiles: Most Replayed*
Kwak, S., Lee, J., & Park, S. (2025). *The effective highlight-detection model for video clips using spatial—perceptual.* **Electronics, 14**(18), 3640. https://doi.org/10.3390/electronics14183640
- **Aporta:** trata el puntaje de highlight como una **regresión supervisada con la curva Most Replayed** de YouTube, usando los datos de Mr. HiSum (Sul et al., NeurIPS 2023).
- **Tomo:**
  - La formulación "Most Replayed = etiqueta débil de highlight".
  - La receta para convertir la curva en una etiqueta por segmento.
  - MSE y F1 como métricas de referencia.
- **Descarto:** el backbone TimeSformer + CNN (94.5 M de parámetros y 825 G MACs), inviable sin GPU CUDA. Además, SPOT **solo usa visión**; sus propios autores dejan el audio y el texto como trabajo futuro. Esa limitación es justo el hueco que cubre esta tesis.

### P4 — Minimal Clips, Maximum Salience · *etiquetas débiles con LLM y línea base*
Pennec, G., Liu, Z., Asher, N., Muller, P., & Chen, N. F. (2026). *Minimal clips, maximum salience: Long video summarization via key moment extraction.* **IWSDS 2026** (ACL Anthology), 205–221. https://aclanthology.org/2026.iwsds-1.22/
- **Aporta:** divide el video en clips de **20 s**, les pone *captions* ligeros y arma un documento tipo guion (transcripción más descripción visual). Un LLM elige los **top-K**.
- **Tomo:**
  1. Las ventanas de 20 s como segmentación **línea base**.
  2. El formato de guion como entrada al LLM.
  3. "LLM elige top-K" en dos usos: como **fuente de etiqueta secundaria** (sirve en videos sin curva Most Replayed, como el set en español) y como **línea base** contra la que compito.
- **Descarto:** Qwen2.5-Omni 7B para los captions (muy lento en CPU) y el dominio de películas. Uso captions solo del texto, o captions visuales opcionales sobre el top-N.
- Es un **workshop**; así debe citarse.

### P5 — Rhapsody · *dataset de entrenamiento en el dominio*
Park, Y., Diwan, A., Harwath, D., & Choi, E. (2025). *Rhapsody: A dataset for highlight detection in podcasts.* **COLM 2025.** https://arxiv.org/abs/2505.19429
- **Aporta:**
  - **13 364 episodios** de podcast de YouTube (unas 6 060 h) con su curva Most Replayed dividida en 100 segmentos.
  - Transcripciones WhisperX alineadas por palabra.
  - Una definición de highlight: segmento con score > 0.5, como máximo 20 por episodio, con corrección del sesgo del primer segmento.
- **Tomo:** es el **dataset principal de entrenamiento**, junto con su definición de highlight binario para calcular P, R y F1 y compararme con el paper.
- **Descarto:** las features HuBERT precomputadas (el dataset pesa 65.8 GB) y bajar el dataset completo. Descargo solo IDs, curvas y transcripciones, más el audio de un subconjunto.
- ⚠️ Queda por confirmar en el PDF: idioma (probablemente solo inglés) y los resultados de sus líneas base.

### P6 — Keyword-DETR · *peso de palabras en highlight detection*
Um, S. J., Kim, D., Lee, S., & Kim, J. U. (2025). *Watch video, catch keyword: Context-aware keyword attention for moment retrieval and highlight detection.* **AAAI 2025.** https://arxiv.org/abs/2501.02504
- **Aporta:** evidencia de que ponderar **keywords según su contexto** en el video mejora la detección de highlights.
- **Tomo:** la justificación teórica del bloque de keywords. Lo implemento con dos señales complementarias:
  - **TF-IDF por pasaje** con la fórmula de KVSUM (Ecuación 1, ya documentada en el material previo del autor): `w_ij = log(tf_ij+1)·log(N/PF_i) / ‖·‖`.
  - **KeyBERT** con embeddings multilingües (`paraphrase-multilingual-MiniLM-L12-v2`) para medir la similitud semántica de cada clip con el tema global del video.

  Esta combinación es la métrica híbrida que describe Summarize-Pro sin publicar la fórmula; aquí la fórmula sí queda explícita.
- **Descarto:** la arquitectura DETR, que necesita una consulta de texto y features SlowFast/CLIP pesados.

### P7 — UMT · *audio como señal de énfasis*
Liu, Y., Li, S., Wu, Y., Chen, C. W., Shan, Y., & Qie, X. (2022). *UMT: Unified multi-modal transformers for joint video moment retrieval and highlight detection.* **CVPR 2022**, 3032–3041. https://doi.org/10.1109/CVPR52688.2022.00305
- **Aporta:** muestra de forma empírica que **agregar audio mejora de forma consistente** la detección de highlights (YouTube Highlights, TVSum), incluso sin consulta.
- **Tomo:**
  - La justificación del bloque de audio y su diseño de ablación (audio frente a sin audio).
  - Features con librosa: RMS (media, máximo y z-score respecto al video), variación de pitch (pyin), proporción de pausas, velocidad de habla (palabras/s) y picos de energía.
- **Descarto:** el transformer y los features PANNs/I3D. Los reemplazo por features de librosa y un modelo de árboles.

### P8 — SVHighlights / TF-SELECTOR · *videos muy largos y segmentación antes de puntuar*
Lee, D., Ki, Y., Kang, J., & Kim, T. (2026). *SVHighlights: Towards extremely long sport video highlight detection.* **KDD 2026** (D&B). https://arxiv.org/abs/2606.06926
- **Aporta:**
  - En videos de unas 2 h, **segmentar en unidades coherentes antes de puntuar** supera a los modelos de grounding.
  - El **volumen de audio** es una señal barata y útil.
  - Cubre el caso "cualquier video" en deportes.
- **Tomo:**
  - Segmentar primero y puntuar después, lo que respalda los candidatos por oración y por escena con PySceneDetect.
  - HIT@K como métrica.
  - Su dataset como **evaluación fuera de dominio** en videos largos.
- **Descarto:** puntuar todos los segmentos con un LLM, inviable en CPU para 2 h de video.
- ⚠️ Se cita como arXiv hasta que salga el DOI de ACM.

### P9 — Engagement prediction de videos cortos · *qué significa "score de viralidad"*
Li, D., Li, W., Lu, B., Li, H., Ma, S., Krishnan, G., & Wang, J. (2024). *Delving deep into engagement prediction of short videos.* **ECCV 2024**, LNCS 13666, 289–306. https://doi.org/10.1007/978-3-031-72949-2_17
- **Aporta:**
  - Define el engagement como **retención**: NAWP (porcentaje medio de visionado normalizado) y ECR (tasa de continuación). No lo mide con vistas ni likes.
  - Muestra que la calidad visual correlaciona poco con el engagement y que **el texto y el contenido sí importan**.
- **Tomo:**
  - El sustento conceptual del score: Most Replayed también es una señal de **retención y re-reproducción**, así que el score se define como "potencial de retención" y no como "vistas".
  - La justificación del bloque de **sentimiento y energía léxica**. Implementación:
    - Un modelo multilingüe de sentimiento: `cardiffnlp/twitter-xlm-roberta-base-sentiment`.
    - Intensidad emocional, exclamaciones, preguntas, primera y segunda persona, y números.
- **Descarto:** los encoders de video y el dataset SnapUGC como fuente de entrenamiento (clips ya cortos, sin video de origen, licencia no declarada).

### P10 — Light-ASD · *reencuadre 9:16 con hablante activo*
Liao, J., Duan, H., Feng, K., Zhao, W., Yang, Y., & Chen, L. (2023). *A light weight model for active speaker detection.* **CVPR 2023**, 22932–22941. https://doi.org/10.1109/CVPR52729.2023.02196
- **Aporta:** detecta al hablante activo con **1.0 M de parámetros** y 94.1 % de mAP en AVA-ActiveSpeaker; los pesos son públicos.
- **Tomo:**
  - Solo inferencia en CPU sobre los clips finales, para decidir qué rostro seguir cuando hay 2 o más personas.
  - La detección y el seguimiento de rostros con MediaPipe, más suavizado One-Euro e histéresis de al menos 1 s para no saltar de un rostro a otro.
- **Descarto:** reentrenarlo.
- **Plan B:** si falla en Windows, correlacionar la apertura de boca (landmarks de MediaPipe) con la energía del audio.

### Referencias de apoyo (no cuentan entre las 10)
- **Mr. HiSum** (Sul, Han & Lee, NeurIPS 2023 D&B): fuente original de las curvas Most Replayed y dataset de evaluación general.
- **QVHighlights / Moment-DETR** (Lei, Berg & Bansal, NeurIPS 2021): esquema de saliencia de 1 a 5 y dataset de evaluación con mucha habla.
- **KVSUM** (ICALT 2011) y **Summarize-Pro** (2026): material previo del autor; son las fórmulas de peso de palabras.
- **PySceneDetect** y **KeyBERT** son software, no papers; se citan como herramientas.

### Correspondencia con las 10 técnicas del planteamiento original

| # original | Técnica | Paper que la sustenta | Rol en el modelo |
|---|---|---|---|
| 1 | Resumen con LLM + hook + frases nominales spaCy | P1 Lotus | Contexto |
| 2 | (faltaba) Candidatos por oración + criterios de hook | P2 PodReels | Contexto y segmentación |
| 3 | Most Replayed como etiqueta débil | P3 SPOT + P5 Rhapsody | **Etiqueta principal** |
| 4 | Clips de 20 s + captions + LLM top-K | P4 Minimal Clips | **Etiqueta secundaria** y línea base |
| 5 | TF-IDF | P6 (fórmula KVSUM) | Feature |
| 6 | KeyBERT | P6 | Feature |
| 7 | Sentimiento y energía léxica | P9 | Feature |
| 8 | Audio con librosa | P7 UMT, P8 | Feature |
| 9 | Detección de escenas | P8 SVHighlights | Generación (bordes) |
| 10 | Reencuadre 9:16 + subtítulos | P10 Light-ASD | Generación (render) |

---

## 3. Ingeniería inversa de Opus Clip (solo información pública)

**Qué publica Opus:**
- **Score de 0 a 99 por clip.** Su centro de ayuda nombra cuatro dimensiones: **Hook, Flow, Value y Trend**. Su blog 3.0 llama "Engagement" a Value. https://help.opus.pro/docs/article/virality-score
- **Entrenamiento.** Dicen usar "decenas de miles de videos virales" más las señales de 6 M de usuarios (likes, exportaciones, rendimiento en redes). https://www.opus.pro/blog/opusclip-celebrates-30m-in-funding-and-the-launch-of-clipanything
- **Pipeline de dos fases.** La API expone las etapas `IMPORT → CURATE → REFINE → RENDER`, es decir, primero elige candidatos y después refina bordes y edición.
- **Dos modelos.** *ClipBasic* se basa solo en el transcript y funciona para cabezas parlantes. *ClipAnything* es multimodal y acepta prompts.
- **Opciones de generación:**
  - Duraciones: 0–30, 30–60, 60–90 y 90–180 s.
  - Un enum de 18 géneros que cambia el "modelo de curación".
  - Clips que pueden juntar varios `timeRanges` no contiguos.
- **Reframe.** Detecta al hablante activo con señales de voz y movimiento. Layouts Fill / Fit / Split / Screenshare / Gameplay.
- **Subtítulos.** Animación "pop" con **dos colores de resaltado** (primario y secundario), emojis y marca de muletillas por palabra. Opus **no documenta qué palabras resalta**.

**Qué no publica** y la tesis sí hará auditable:
- La fórmula del score.
- Cómo pondera las dimensiones.
- Si el score está calibrado con datos reales.

Su API ni siquiera devuelve el score. Las reseñas reportan entre **20 y 40 % de clips descartados**, cortes a mitad de idea y peor desempeño en gaming (Opus admite que sus modelos están "ajustados a talking-head").

**Competidores que dejan ver su rúbrica:**
- **Submagic:** hook_strength, story_quality, emotional_impact y shareability.
- **quso.ai:** Trends, Hook & Flow, Engagement y Shareability, con el flujo segmentar → deduplicar → juzgar → ordenar.
- **Klap:** hook en 1–2 s y payoff al final.

**Cómo traslado cada dimensión de Opus al modelo:**

| Dimensión Opus | Implementación abierta | ¿Aprendida? |
|---|---|---|
| **Hook** | Features de los primeros 3 s o 15 palabras: pregunta, cifra, segunda persona, afirmación fuerte, contradicción ("pero", "nadie"), z-score de RMS al inicio y sentimiento inicial | Sí: entran a LightGBM |
| **Flow** | Empieza y termina en límite de oración; sin anáfora colgante al inicio ("eso", "él"); coherencia (coseno medio entre oraciones consecutivas); duración | Sí: entran a LightGBM |
| **Value** | Peso TF-IDF de KVSUM, similitud KeyBERT con el tema del video, densidad de keywords, intensidad emocional, picos de audio | Sí: entran a LightGBM |
| **Trend** | **Se omite** en el modelo entrenado: no hay etiqueta pública ni reproducibilidad. Queda como módulo opcional documentado | No |
| **Score 0–99** | Salida de LambdaRank → percentil sobre la distribución de validación → 0–99. **El desglose** Hook/Flow/Value se obtiene sumando los valores SHAP de cada grupo de features | — |
| **REFINE** | El LLM revisa el top-N: "¿se entiende solo?", título, hook headline y ajuste de bordes a oración y escena | LLM |
| **Deduplicar** | NMS temporal: se descarta un candidato con IoU > 0.5 respecto a otro con mejor score | Heurística |
| **Géneros** | Preset opcional de umbrales o N por género (p. ej. bajar el umbral en gaming, como recomienda Opus) | Heurística |

---

## 4. Modelo de ranking

### 4.1 Unidad y candidatos
- **Candidato:** un tramo continuo de 15 a 90 s que empieza y termina en límite de oración. Los bordes se ajustan al corte de escena más cercano si está a menos de 1.5 s.
- **Cómo se generan:** ventanas deslizantes con paso de una oración y tres duraciones objetivo (≈20, 40 y 60 s). Esto da cientos de candidatos por video.
- **Línea base de segmentación:** ventanas fijas de 20 s (P4).

### 4.2 Etiquetas
- **Principal (P3 + P5): Most Replayed.**
  - Para cada candidato: `y_mr = media de la curva sobre los segmentos del 1 % que cubre`.
  - Se descarta el primer segmento, porque la curva está sesgada al inicio del video.
  - Luego se convierte a **relevancia graduada de 0 a 4** por quintiles *dentro del mismo video*, que es lo que espera LambdaRank.
- **Secundaria (P4): selección top-K por LLM.** Se usa en tres casos:
  - (a) el set en español sin curva;
  - (b) medir el acuerdo LLM ↔ Most Replayed (κ de Cohen);
  - (c) la ablación "¿qué pasa si entreno con etiquetas del LLM?".

  Por costo, solo se etiqueta una muestra (p. ej. 300 videos).

### 4.3 Features (técnicas 5–8 + estructura tipo Opus)

| Grupo | Features | Técnica |
|---|---|---|
| **K: keywords** | Suma y máximo del peso KVSUM; similitud KeyBERT clip ↔ video; nº de keywords del top-20 global; novedad léxica | 5, 6 |
| **S: sentimiento** | Polaridad media y máxima; intensidad \|pos−neg\|; exclamaciones y preguntas por minuto; pronombres de 1.ª y 2.ª persona; números | 7 |
| **A: audio** | RMS (media, p95 y z-score respecto al video); pitch std; proporción de pausas; palabras por segundo; pico de energía en los primeros 3 s | 8 |
| **H/F: estructura** | Features de hook (primeros 3 s); completitud de la oración; anáfora inicial; coherencia; duración | Opus (Hook/Flow), P2 |
| **P: posición** | Posición relativa en el video. **Solo en la ablación**: puede aprender el sesgo de la plataforma en lugar del contenido | — |
| **V: visual** (opcional) | Cortes de escena por minuto, movimiento medio, nº de rostros | 9 |

El grupo V **no se entrena con Rhapsody**, que no incluye video. Se evalúa aparte en QVHighlights y en el set propio.

### 4.4 Modelos
- **Principal: LightGBM `lambdarank`** (grupo = video), con seed fija y early stopping por NDCG@10 en validación. Se eligió porque entrena en minutos en CPU, maneja features heterogéneas, es interpretable con SHAP y optimiza directamente el ranking.
- **Baseline neuronal:** MLP en PyTorch con pérdida pairwise (RankNet) sobre las mismas features y, opcionalmente, embeddings de oración. Responde a la línea "deep learning con ranking por pares" de la ficha y permite comparar árboles frente a red.
- **Líneas base:**
  - (i) aleatoria;
  - (ii) solo TF-IDF;
  - (iii) heurística tipo Opus: suma ponderada fija de Hook, Flow y Value;
  - (iv) LLM top-K zero-shot (P4).

### 4.5 Del puntaje al clip final
1. Se ordenan todos los candidatos y se deduplican con NMS temporal.
2. El **LLM (P1 y P2)** revisa el top-N (N = 15). Genera título, hook, estilo y justificación, y marca "no autocontenido" (penalización). Puede extender los bordes hasta ±1 oración.
3. Se toman los top-K (configurable, por defecto 5 a 10).
4. **Render (P8 y P10):** los bordes se ajustan a escena, se aplica reencuadre 9:16 (layout Fill, Split o Fit según el nº de rostros) y se generan subtítulos ASS palabra por palabra:
   - **color primario:** keywords KVSUM + KeyBERT del clip;
   - **color secundario:** números y palabras emocionales;
   - como máximo 1 palabra resaltada cada 4.

   Se exporta con ffmpeg.
5. Cada clip se entrega con un JSON: score, desglose Hook/Flow/Value, keywords con su frase de contexto, título y justificación del LLM.

### 4.6 LLM configurable
Interfaz única `LLMClient` con proveedores `anthropic`, `openai`, `ollama` (local) y `none`. Con `none` el sistema funciona sin LLM y usa plantillas: esto garantiza reproducibilidad total.
- **Experimentos:** un modelo fijo con versión pinneada y temperatura 0.
- **Caché:** las respuestas se guardan en disco (hash del prompt), así que re-ejecutar el pipeline no vuelve a llamar al LLM.

---

## 5. Datos y evaluación (se detalla en la Fase 3)

| Uso | Dataset | Detalle |
|---|---|---|
| Entrenamiento, validación y test | **Rhapsody** (P5) | Split 70/15/15 **por canal**, para que un mismo podcast no aparezca en train y test. Audio de un subconjunto de 1 000–2 000 episodios (≈10–20 GB, se borra tras extraer features) |
| Fuera de dominio, dominio general | **Mr. HiSum** | Misma señal Most Replayed en videos no conversacionales |
| Fuera de dominio, saliencia humana | **QVHighlights** | Saliencia 1–5 promediada entre consultas |
| Videos muy largos | **SVHighlights** (P8) | Deportes de ≈2 h |
| **Aporte propio: español** | 150–300 videos de YouTube en español con curva (vía `yt-dlp -j`) | Test en español. Solo se publican IDs y datos derivados |

**Métricas:**
- Precision@K, Recall@K y F1 contra los highlights de Most Replayed (definición de Rhapsody).
- MRR, NDCG@K, HIT@1 y Spearman.

**Ablación:** quitar un grupo a la vez (K, S, A, H/F, V), cambiar la fuente de etiquetas (Most Replayed / LLM) y cambiar la segmentación (oraciones frente a ventanas de 20 s).

---

## 6. Limitaciones asumidas desde el diseño

1. **Most Replayed ≠ viralidad en TikTok.** Mide re-reproducción en YouTube, así que el score se reporta como *potencial de retención*. No se puede validar contra vistas reales de TikTok o Reels por falta de un dataset público; queda como trabajo futuro.
2. **"Cualquier video" frente a entrenamiento en podcasts.** El modelo aprende de contenido hablado. En gaming, deportes o videos sin habla se apoya en audio y visual y rinde peor; se mide con Mr. HiSum y SVHighlights. Opus Clip tiene la misma limitación.
3. **Idioma.** Rhapsody es probablemente solo inglés, así que el test en español mide la transferencia entre idiomas. Por eso uso embeddings y sentimiento multilingües.
4. **Hardware.** No hay GPU CUDA: faster-whisper se ejecuta en CPU, y los LLM y la visión solo corren sobre el top-N.
5. **Legal.** Términos de servicio de YouTube y licencias NC (Rhapsody y QVHighlights, CC BY-NC-SA): uso académico no comercial y sin redistribuir audio ni video.
6. **Discrepancia con la ficha.** La ficha habla de deep learning y de un dominio solo conversacional. Aquí el modelo central es LightGBM, con un baseline neuronal comparable, y la entrada es cualquier video. Hay que alinearlo con la asesora.

---

## 7. Iteración 2 — referencias adicionales y cambios (2026-09-22)

Segunda búsqueda de literatura enfocada en qué features y datos mejoran un ranker entrenado con Most Replayed. Todas las referencias se verificaron por DOI, arXiv o ACL Anthology.

| Referencia | Aporte | Qué se adopta | Qué se descarta |
|---|---|---|---|
| Duico, Strafforello & van Gemert (2023). *Can we predict the Most Replayed data of video streaming platforms?* ICCV-W (CVEU). arXiv:2309.06102 | YTMR500: incluso los humanos no superan al azar prediciendo Most Replayed (α≈−0.02); los modelos generalizan poco | Contexto para interpretar resultados modestos; P@K como métrica | Sólo visual |
| Reddy, Lazarova, Yu & Jones (2021). *Modeling language usage and listener engagement in podcasts.* ACL-IJCNLP. doi:10.18653/v1/2021.acl-long.52 | Rasgos lingüísticos asociados al engagement (diversidad léxica, pronombres 1ª/2ª, menos muletillas, menos silencio) | Grupo **L**: entropía léxica, type-token, pronombres 1ª/2ª vs 3ª, muletillas, silencio, longitud de palabra | BERT fine-tuned (costo) |
| Kong et al. (2020). *PANNs.* IEEE/ACM TASLP 28. arXiv:1912.10211 | Etiquetador AudioSet preentrenado (CNN14) | Grupo **E**: probabilidad de risa, aplausos, vítores, música y habla; risa al final y justo después del clip | CNN14 en todo el audio (se muestrea 1 s cada 3 s) |
| Hasan et al. (2019). *UR-FUNNY.* EMNLP-IJCNLP. doi:10.18653/v1/D19-1211 | La risa del público marca momentos enganchadores (punchlines) | Justificación teórica del grupo E | Modelo multimodal |
| Barriere et al. (2025). *StandUp4AI.* arXiv:2505.18903 | Risa como etiqueta en stand-up multilingüe, incluido español | Respaldo para usar la risa en español | Clasificador de humor (costo) |
| Wu et al. (2025). *Repurpose-10K.* AAAI 2025. arXiv:2412.08879 | ~8.4k videos largos con clips elegidos por personas (curación en la plataforma de Opus Clip) | **Segunda etiqueta independiente** (clips humanos) para los videos que además tienen curva | Su modelo |
| Sahu & Pandey (2026). arXiv:2607.01400 (preprint) | Controlar la posición al correlacionar con la curva | Métrica de correlación parcial controlando posición | — |

**Descartados por costo medido en el equipo del autor** (CPU compartida con la transcripción):
- **HuBERT-base**, capa 10, como en Rhapsody: 875 s por 1 min de audio.
- **eGeMAPS** (openSMILE): 42 s por 5 min, sin aportar mucho sobre las features de librosa.
- **Arousal con wav2vec2-large** (Wagner et al., TPAMI 2023): más pesado que HuBERT.

Estos descartes quedan como limitación de hardware. Rhapsody reporta que el embedding de habla es la mejora de audio más grande (HR 0.452 → 0.490 con HuBERT en un LLM fine-tuned).

**Cambios de la iteración 2:** D-021 a D-024 en `DECISIONES.md`.
