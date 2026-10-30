# Proyecto: generación automática de clips cortos con score (tesis ULima)

Sistema abierto y auditable tipo **Opus Clip**: entra un video largo (archivo o URL), salen clips
verticales 9:16 con un **score 0–99** y su desglose Hook/Flow/Value, las palabras de mayor peso con
su contexto y subtítulos con keywords resaltadas.

Tesis de Ingeniería de Sistemas, Universidad de Lima. Autor: José Francisco Núñez del Prado Vega.
**Responder siempre en español.**

## Estado (2026-10-18)

- **Leer primero `docs/HANDOFF_PC_GPU.md`** (estado, como se trabaja, instalacion, pendientes, trampas) y `docs/DECISIONES.md` (D-001 a D-073).
- Dataset YT-MR ampliado: ~770 videos con curva y audio (ES/EN), 765 transcripciones, 678 con las 71 variables. Cohortes frescas congeladas en `reports/`.
- Metodo vigente: **formula de 17 variables (V0)** y **V1** (clips <= 45 s); referencia de aprendizaje **R0** (LightGBM LambdaRank con percentiles).
  Acierto (>= 1 de 5 clips toca un pico real) en cohorte fresca 1 (93 videos): azar 26.9 %, V0 47.3 %, V1 54.8 %, R0 62.4 %. Cohorte 2 (63): R0 49.2 % vs 30.0 %.
- No confirmado en videos nuevos: deep learning de secuencia, juez LLM, visual, texto semantico, lexico, genero, categoria, R4, ensamble E3.
- La curva Most Replayed es **solo regla de calificacion**, nunca entrada del sistema.
- Entregables: articulo v9 (Word, plantilla A.3 llena hasta Experimentacion), PPT de avance (17 diapositivas), web local (`scripts/web_clips.py`), demo hospedada.
- Pendiente: ampliar dataset (D-071), preregistrar R0 + 17 variables (D-073), ciclo campeon/retador con deep learning, completar Resultados y Discusion del articulo.

## Reglas de trabajo (no negociables)

1. **Honestidad metodológica.** Nada de elegir variantes mirando el test. Si algo se prueba sobre un
   conjunto, la mejora se confirma en datos nuevos. Las hipótesis se preregistran en `DECISIONES.md`
   antes de mirar los datos de confirmación (ver D-021/D-022).
2. **Toda decisión se registra** en `docs/DECISIONES.md` con fecha, justificación y alternativas
   descartadas. Numeración correlativa D-0NN.
3. **Verificar cada cita.** Ninguna referencia entra a la tesis sin DOI o enlace comprobado. Si no se
   pudo verificar, se marca ⚠️.
4. **Reportar también lo negativo.** Resultados no significativos, hipótesis refutadas y fugas
   detectadas (como D-018) se documentan igual que los positivos.
5. **Fugas de información:** ninguna feature puede codificar la posición del clip en el video
   (ver D-018). Los splits se agrupan **por canal**, nunca por video.

## Entorno

- Python **3.11** en `C:\tesis_data\.venv` (fuera de OneDrive). `ffmpeg` en el PATH.
- Datos pesados en `C:\tesis_data` (`data/raw`, `data/interim`, `data/processed`, `outputs`, `models_ext`).
- En el repo sólo van código, configs, manifests (IDs), modelos entrenados (livianos), reportes y docs.
- Comprobar todo: `python scripts/check_env.py`.
- GPU: perfil listo en `configs/gpu.yaml` (hereda de `default.yaml` con la clave `extends`): activa
  `cuda`, Whisper `small`/`medium` y el grupo **U** de embeddings HuBERT. Guía: `docs/SETUP_GPU.md`.

```bash
C:\tesis_data\.venv\Scripts\python -m pytest                 # 31 tests
C:\tesis_data\.venv\Scripts\python run_all.py                # env→manifest→acquire→features→experiments→report
C:\tesis_data\.venv\Scripts\python -m src.pipeline "URL"     # generar clips de un video
```

## Arquitectura (resumen; detalle en docs/01 y docs/diagramas)

```
ingest → transcribe → segment → features → ranking → context(LLM) → render
```

- `src/ingest/` yt-dlp (metadatos, curva, audio, video) y ffmpeg.
- `src/transcribe/` faster-whisper con timestamps por palabra y caché JSON.
- `src/segment/` oraciones, candidatos de 15–90 s, ventanas fijas de 20 s (línea base), escenas.
- `src/keywords/` TF-IDF por pasaje (fórmula KVSUM), KeyBERT multilingüe, frases nominales spaCy.
- `src/features/` grupos **K** keywords, **S** sentimiento, **A** audio (librosa), **H** hook, **F** flow,
  **E** eventos de audio (PANNs), **L** lingüísticas (Reddy et al.), **P** posición (sólo ablación).
  `relative.py` añade percentiles dentro del video (`__rk`) y contraste local (`__cx`).
- `src/ranking/` etiquetas Most Replayed → relevancia 0–4 por quintiles dentro del video; LightGBM
  LambdaRank; MLP RankNet (baseline); calibración a 0–99 contra los top-10 clips de validación.
- `src/context/` cliente LLM configurable (anthropic|openai|ollama|none) con caché; sin API key usa
  plantillas deterministas.
- `src/render/` reencuadre 9:16 con seguimiento de rostro, subtítulos ASS con keywords resaltadas, ffmpeg.
- `src/evaluation/` métricas (incluye réplica del protocolo de Rhapsody), líneas base, CV agrupada,
  ablación, significancia (Wilcoxon), confirmación preregistrada, evaluación contra clips humanos.

## Convenciones de código

- Módulos y funciones documentados **en español**, citando la técnica o el paper que los sustenta
  (p. ej. "(téc. 8, P7 UMT)"). Los nombres de variables y funciones, en inglés cuando ya es estándar.
- Prefijo de columna = grupo de feature. Cambiarlo rompe ablaciones y el desglose del score.
- Las rutas salen siempre de `cfg.path(...)`; nada de rutas absolutas en el código.
- Cada cambio de comportamiento necesita test en `tests/` (pytest, datos sintéticos, sin red).
- Logging con `get_logger(__name__)`; nada de `print` fuera de scripts de CLI.
- La consola de Windows es cp1252: los scripts que imprimen acentos hacen
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.

## Trampas conocidas

- **YouTube bloquea** tras muchas descargas seguidas ("confirma que no eres un bot"). Hay que espaciar
  las peticiones y descargar desde una IP doméstica, nunca desde la nube.
- Los workers en paralelo usan un **lock por video**; si un proceso muere, quedan `.lock` huérfanos:
  `find … -name "*.lock" -delete`. El estado real se reconstruye con `scripts/rebuild_status.py`.
- `mediapipe` 1.x ya no expone `mp.solutions`: se usa la API `tasks` con el `.tflite` en `models_ext`.
- PANNs busca `class_labels_indices.csv` en `%USERPROFILE%\panns_data\`.
- Con 100 videos y etiqueta ruidosa, **más features empeoran**: por eso la selección de grupos por fold.

## Pendientes (por impacto)

1. Entrenar con **clips humanos** de Repurpose-10K (~8.4k videos): es la etiqueta alineada con el producto.
2. **Rhapsody** (13 364 podcasts, COLM 2025): requiere que el autor acepte los términos y haga `hf auth login`.
3. **GPU**: `run_all.py --config configs/gpu.yaml` y `scripts/build_speech_embeddings.py` habilitan
   Whisper `small`/`medium` y el grupo U (HuBERT), descartado en CPU por costar 875 s por minuto de audio.
4. Evaluación humana con la rúbrica de PodReels frente a clips de Opus Clip.
5. API key de LLM para la línea base de selección top-K y los títulos generados.
