# Instalación desde cero en la PC con GPU

Para una máquina que no tiene absolutamente nada del proyecto. Orden: primero se le lleva el código,
después se instala todo, después se le llevan los datos.

**Lo único que tiene que existir de antemano:** Windows 10/11 con internet y una GPU NVIDIA con su
driver. Si `nvidia-smi` no funciona en una consola, instala el driver desde
<https://www.nvidia.com/Download/index.aspx> antes de seguir.

---

## Paso 1 · Llevar el código (13,6 MB)

Elige **una** de estas tres vías.

### 1.a Con croc (lo más rápido, sin configurar nada)

En la **laptop**:

```bash
croc send C:\tesis_data\transfer\tesis_repo_20260924_1907.zip
```

Imprime una frase de tres o cuatro palabras. En la **PC con GPU**, con PowerShell:

```powershell
winget install schollz.croc
croc <la-frase-que-apareció>
```

Descomprime el zip donde quieras, por ejemplo en `C:\tesis\`. Queda una carpeta `desarrollo`.

### 1.b Con un USB

Copia la carpeta `desarrollo` completa **menos** `.venv`, `__pycache__` y `data\raw`.

### 1.c Con Syncthing (si quieres sincronización permanente)

Ver `docs/TRANSFERENCIA.md`. Requiere instalar Syncthing en ambas máquinas y emparejarlas.

---

## Paso 2 · Instalar todo con un comando

En la **PC con GPU**, abre PowerShell, entra a la carpeta `desarrollo` y ejecuta:

```powershell
cd C:\tesis\desarrollo
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_gpu.ps1
```

El script hace, en orden:

1. Comprueba la GPU con `nvidia-smi` y elige el índice de PyTorch adecuado
   (las GTX 10xx son Pascal y necesitan CUDA 12.6; las RTX 20xx en adelante usan 12.8).
2. Instala con winget: **Python 3.11**, **ffmpeg**, **Deno** (lo exige yt-dlp), **croc**,
   **Syncthing** y **Git**.
3. Crea el entorno virtual en `C:\tesis_data\.venv`.
4. Instala PyTorch con CUDA y verifica que vea la tarjeta.
5. Instala las dependencias del proyecto (sin pisar la versión CUDA de PyTorch) y `panns_inference`.
6. Descarga los modelos de spaCy en español e inglés.
7. Descarga los pesos externos: detector de rostros de MediaPipe, YuNet de OpenCV y PANNs CNN14
   (~313 MB), más la lista de clases de AudioSet.
8. Corre `check_env.py` y las pruebas.

Es reanudable: si algo falla, se corrige y se vuelve a ejecutar; lo ya instalado se omite.

Al final debe imprimir **"Listo para ejecutar"** y las 32 pruebas en verde. Si PyTorch no ve la GPU,
el propio script te dice qué índice probar (`cu126` → `cu121`).

---

## Paso 3 · Llevar los datos (121 MB, o ~1 GB con audio)

En la **laptop**, genera el paquete:

```bash
C:\tesis_data\.venv\Scripts\python scripts\pack_for_gpu.py                 # 121 MB, sin audio
C:\tesis_data\.venv\Scripts\python scripts\pack_for_gpu.py --audio opus    # ~1 GB, con audio
croc send C:\tesis_data\transfer\tesis_gpu_AAAAMMDD_HHMM.zip
```

En la **PC con GPU**:

```powershell
croc <la-frase>
C:\tesis_data\.venv\Scripts\python scripts\unpack_transfer.py tesis_gpu_AAAAMMDD_HHMM.zip
C:\tesis_data\.venv\Scripts\python scripts\rebuild_status.py
```

**Cuándo hace falta el audio:** sin él se puede reentrenar y evaluar con las features ya calculadas,
pero **no** recalcular features acústicas ni construir el grupo U (HuBERT), que es la mejora principal
que justifica usar la GPU. Si vas a hacer eso, usa `--audio opus`; `unpack_transfer.py` lo reconvierte
a WAV de 16 kHz al restaurarlo.

---

## Paso 4 · Comprobar que quedó todo

```powershell
cd C:\tesis\desarrollo
C:\tesis_data\.venv\Scripts\python scripts\check_env.py
C:\tesis_data\.venv\Scripts\python -m pytest
C:\tesis_data\.venv\Scripts\python scripts\build_dashboard.py --serve
```

El panel se abre en el navegador y muestra cuántos videos llegaron, el estado del modelo y los
resultados. Si dice 0 videos, es que faltó el paso 3.

---

## Paso 5 · Poner a trabajar a Claude

1. Instala Claude Code en esa PC y abre la carpeta `desarrollo`.
2. Pégale el prompt de `docs/PROMPT_GPU.md`.

Con eso lee `CLAUDE.md`, la auditoría y las decisiones, y sabe exactamente en qué quedó el trabajo y
qué sigue.

---

## Resumen de lo que debe existir al final

| Ruta | Contenido |
|---|---|
| `C:\tesis\desarrollo\` | Código, configs, docs, manifests, `models\` |
| `C:\tesis_data\.venv\` | Entorno Python 3.11 con PyTorch CUDA |
| `C:\tesis_data\models_ext\` | Rostros (MediaPipe, YuNet) y PANNs CNN14 |
| `C:\tesis_data\data\interim\` | Transcripciones, curvas Most Replayed, features de audio, clips humanos |
| `C:\tesis_data\data\processed\features\` | Tablas de features y etiquetas por video |
| `C:\tesis_data\data\raw\wav\` | Audio (sólo si lo trasladaste; necesario para HuBERT) |
| `%USERPROFILE%\panns_data\` | Lista de clases de AudioSet |
