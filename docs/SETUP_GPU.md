# Migrar a la PC con GPU NVIDIA

El código ya está preparado: `device: auto` en `configs/default.yaml` usa la GPU si la encuentra y CPU si no.
No hay que cambiar nada más.

## Qué se copia y qué no

| Carpeta | ¿Copiar? | Cómo |
|---|---|---|
| `desarrollo/` (código, configs, manifests, docs, `models/`) | Sí | Syncthing o git; ver `docs/TRANSFERENCIA.md` |
| `C:\tesis_data\models_ext\` (~313 MB: rostros + PANNs) | Sí, o volver a descargar | Syncthing, o los comandos de abajo |
| `C:\tesis_data\data\interim\` y `data\processed\` (transcripciones, curvas, features) | **Recomendado** | Syncthing, croc o `scripts/pack_for_gpu.py`. Evita volver a descargar y transcribir |
| `C:\tesis_data\data\raw\wav\` (~6 GB de audio) | No hace falta | Se vuelve a descargar, o se copia si la conexión es lenta |
| `C:\tesis_data\.venv` | **No** | Se crea de nuevo; los binarios dependen de la máquina |

Sin `interim`, `run_all.py` vuelve a descargar y transcribir todo, lo que con GPU es rápido.

## Pasos en la PC con GPU

### 1. Requisitos del sistema
```bash
winget install Python.Python.3.11 --scope user
winget install Gyan.FFmpeg
```
Comprueba el driver NVIDIA (debe listar la GPU y una versión de CUDA):
```bash
nvidia-smi
```

### 2. Entorno
```bash
py -3.11 -m venv C:\tesis_data\.venv
C:\tesis_data\.venv\Scripts\python -m pip install -U pip
```

### 3. PyTorch con CUDA (elige según la GPU)

**GTX 10xx (Pascal, como la GTX 1080):** las compilaciones más nuevas de PyTorch dejaron de incluir Pascal,
así que hay que instalar una variante con CUDA 12.6:
```bash
C:\tesis_data\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cu126
```

**RTX 20xx o posterior:**
```bash
C:\tesis_data\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
```

Verifica que la GPU se vea desde Python:
```bash
C:\tesis_data\.venv\Scripts\python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Si imprime `False`, prueba con el índice de CUDA inmediatamente anterior (cu126 → cu121).

### 4. Resto de dependencias
```bash
C:\tesis_data\.venv\Scripts\python -m pip install -r requirements.txt
C:\tesis_data\.venv\Scripts\python -m spacy download es_core_news_sm
C:\tesis_data\.venv\Scripts\python -m spacy download en_core_web_sm
C:\tesis_data\.venv\Scripts\python -m pip install panns_inference
```
`requirements.txt` fija `torch==2.14.0+cpu`; si pip intenta reemplazar la versión CUDA que instalaste,
reinstala la del paso 3 al final.

### 5. Pesos externos (si no copiaste `models_ext`)
```bash
mkdir C:\tesis_data\models_ext\panns
curl -L -o C:\tesis_data\models_ext\blaze_face_short_range.tflite https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite
curl -L -o C:\tesis_data\models_ext\face_detection_yunet_2023mar.onnx https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
curl -L -o "C:\tesis_data\models_ext\panns\Cnn14_mAP=0.431.pth" "https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth?download=1"
```
PANNs además busca su lista de clases en `%USERPROFILE%\panns_data\class_labels_indices.csv`:
```bash
mkdir %USERPROFILE%\panns_data
curl -L -o %USERPROFILE%\panns_data\class_labels_indices.csv https://raw.githubusercontent.com/qiuqiangkong/audioset_tagging_cnn/master/metadata/class_labels_indices.csv
```

### 6. Comprobar todo
```bash
cd <ruta a desarrollo>
C:\tesis_data\.venv\Scripts\python scripts\check_env.py
C:\tesis_data\.venv\Scripts\python -m pytest
```
`check_env.py` debe decir **Listo para ejecutar** y mostrar la GPU detectada con su `compute_type`.

### 7. Aprovechar la GPU
Existe un perfil listo, `configs/gpu.yaml`, que hereda de `default.yaml` (clave `extends`) y cambia sólo
lo necesario: dispositivo `cuda`, transcripción con `small`/`medium` y el **grupo U de embeddings de
habla (HuBERT)**, que en CPU era inviable.

```bash
C:\tesis_data\.venv\Scripts\python run_all.py --config configs\gpu.yaml
C:\tesis_data\.venv\Scripts\python scripts\build_speech_embeddings.py --config configs\gpu.yaml
C:\tesis_data\.venv\Scripts\python run_all.py --config configs\gpu.yaml --from experiments
```

La segunda línea calcula los embeddings HuBERT y escribe las columnas `u_*`; la tercera reentrena
incluyendo ese grupo entre los candidatos de la selección automática de features.

**Importante:** cambiar el modelo de Whisper cambia las transcripciones y, con ellas, todas las features.
Si se rehace el dataset con `small` o `medium`, hay que borrar `data/processed/features/`, volver a
featurizar y anotarlo en `DECISIONES.md`.

### 8. Tareas que sólo tienen sentido con GPU

| Tarea | Comando | Beneficio |
|---|---|---|
| Transcribir con modelo mayor | `run_all.py --config configs\gpu.yaml` | Menos errores de reconocimiento, sobre todo en español |
| Embeddings de habla (grupo U) | `scripts\build_speech_embeddings.py` | La mayor mejora de audio según Rhapsody (COLM 2025) |
| Ampliar el dataset | El perfil sube la meta a 250 videos por idioma | Ataca la principal limitación actual: el tamaño |
| Entrenar con clips humanos | `python -m src.evaluation.human_train` | Responde al hallazgo D-028; requiere ≥ 25 videos de Repurpose |

## Avisos
- **Descarga de YouTube:** hazla desde una conexión doméstica. Los servidores en la nube suelen recibir el
  bloqueo "confirma que no eres un bot"; en una PC de casa no pasa.
- **`compute_type`:** se elige solo. En GTX 10xx usa `int8_float32`, porque esa generación no acelera `float16`.
- **Reproducibilidad:** cambiar de modelo de Whisper cambia las transcripciones y, por lo tanto, las features.
  Si se rehace el dataset con `small` o `medium`, hay que volver a entrenar y anotarlo en `DECISIONES.md`.
- **VRAM:** con 8 GB alcanza para Whisper `medium`, PANNs y HuBERT, pero uno a la vez.
