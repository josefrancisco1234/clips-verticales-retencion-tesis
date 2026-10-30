# Clips con score desde videos largos (tesis ULima)

Sistema abierto y auditable tipo Opus Clip: recibe **cualquier video largo** (archivo o URL de YouTube) y devuelve
clips verticales 9:16 con un **score de 0 a 99**, desglose **Hook / Flow / Value**, las **palabras de mayor peso con
su contexto** y subtítulos con keywords resaltadas.

- Diseño y justificación de las 10 técnicas: [docs/01_diseno_metodologico.md](docs/01_diseno_metodologico.md)
- Auditoría del modelo (dataset, métricas, ablación, sesgos): [docs/02_auditoria_modelo.md](docs/02_auditoria_modelo.md)
- Registro de decisiones: [docs/DECISIONES.md](docs/DECISIONES.md)

## Instalación (Windows, Python 3.11, sólo CPU)

```bash
py -3.11 -m venv C:\tesis_data\.venv
C:\tesis_data\.venv\Scripts\python -m pip install -r requirements.txt
C:\tesis_data\.venv\Scripts\python -m spacy download es_core_news_sm
C:\tesis_data\.venv\Scripts\python -m spacy download en_core_web_sm
```

Requiere `ffmpeg` en el PATH. Los pesos del detector de rostros van en `C:\tesis_data\models_ext\`
(`blaze_face_short_range.tflite` de MediaPipe y `face_detection_yunet_2023mar.onnx` de OpenCV Zoo).

## Uso

```bash
# generar clips de un video (archivo local o URL)
C:\tesis_data\.venv\Scripts\python -m src.pipeline "https://www.youtube.com/watch?v=XXXX" --top-k 8

# regenerar todo el trabajo experimental (dataset → features → CV → modelo → reporte)
C:\tesis_data\.venv\Scripts\python run_all.py

# tests
C:\tesis_data\.venv\Scripts\python -m pytest
```

Salida en `C:\tesis_data\outputs\<video>\`: `clip_XX_scoreYY.mp4`, `clips.json` (score, desglose, keywords con
contexto, título, hook, justificación) y `report.md`.

**LLM (opcional):** en `configs/default.yaml → context.provider` elige `anthropic`, `openai`, `ollama` o `none`.
Si falta la API key (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) el sistema usa plantillas deterministas.

## Estructura

```
src/
  ingest/       ffmpeg, yt-dlp (audio, video, curva Most Replayed)
  transcribe/   faster-whisper con timestamps por palabra
  segment/      oraciones, candidatos 15–90 s, ventanas fijas, cortes de escena
  keywords/     TF-IDF por pasaje (KVSUM), KeyBERT, frases nominales spaCy
  features/     keywords, sentimiento/léxico, audio (librosa), hook, flow
  ranking/      etiquetas Most Replayed, LightGBM LambdaRank, MLP RankNet, calibración 0–99
  context/      cliente LLM con caché + plantillas (título, hook, autocontenido)
  render/       reencuadre 9:16 con seguimiento de rostro, subtítulos ASS, exportación
  evaluation/   métricas, líneas base, validación cruzada, ablación, reporte
  data/         construcción del dataset propio y featurización
  pipeline.py   inferencia de punta a punta
configs/  data/manifests/  models/  reports/  notebooks/  tests/  docs/
```
