# HANDOFF: pasar todo el proyecto a la PC con mejor GPU

Fecha: 2026-10-18 · Autor: José Francisco Núñez del Prado Vega (U. de Lima, Ingeniería de Sistemas) · Asesora: Angela Gabriela Maywa
Este documento es lo primero que se lee en la PC nueva. Explica **qué es el proyecto, en qué estado está, cómo se trabaja, cómo se instala,
qué falta y qué trampas ya conocemos.** Todo lo demás está en `docs/DECISIONES.md` (bitácora D-001 a D-073).

---

## 1. Qué es el proyecto (en 30 segundos)

Sistema abierto y auditable tipo Opus Clip: entra un video largo (URL o archivo) y salen **5 clips verticales 9:16** con **score 0–99**, explicación por
variable y subtítulos. Elige **solo con el contenido** (audio + texto). La curva **Most Replayed** de YouTube se usa únicamente para **entrenar y calificar**,
**nunca como entrada** (un video no publicado no la tiene).

- **Método vigente:** fórmula de 17 variables ponderadas (V0), con clips ≤ 45 s (V1). Modelo de aprendizaje de referencia: LightGBM LambdaRank (R0).
- **Resultado confirmado (cohorte fresca 1, 93 videos):** azar 26.9 % → V0 47.3 % → V1 54.8 % → R0 62.4 % de acierto (al menos 1 de 5 clips toca un pico real).
  Cohorte 2 (63 videos): R0 49.2 % frente a 30.0 % del azar. En 557 videos juntos, V1 acierta ≥ 1 de 5 en 55.7 %.
  Techo con solo contenido: 50–69 %. Con la curva real: 85–95 % (no disponible en un video nuevo).
- **No confirmado en datos nuevos:** deep learning de secuencia, juez LLM, señal visual, embeddings de texto, léxico, género, categoría, R4 y ensamble E3.

## 2. Qué se entrega en los paquetes

| Paquete | Contenido | Tamaño aprox. |
|---|---|---|
| `0_LEEME_Y_DOCUMENTOS.zip` | Este HANDOFF, todos los Word y PPT relacionados, demos y entregables | ~50 MB |
| `1_codigo_y_reportes.zip` | `desarrollo/`: código, configs, scripts de todos los experimentos, modelos, reportes, tests, docs | ~60 MB |
| `2_datos_procesados.zip` | `interim` (curvas, transcripciones, cuadros de audio, eventos, HuBERT), `processed` (variables), `models_ext` (PANNs) | ~2.6 GB |
| (no enviado) `raw/wav` | 765 audios, **66 GB** | solo por disco externo o red local |

Repositorio de código (público): **https://github.com/josefrancisco1234/tesis-generador-clips** (carpeta `TESIS_ENTREGA`, versión ordenada para entregar).
La carpeta de trabajo completa, con todos los scripts de experimentos, es `desarrollo/` del paquete 1.

## 3. Cómo se instala en la PC nueva

1. Windows 10/11, internet y driver NVIDIA (`nvidia-smi` debe funcionar).
2. Descomprimir el paquete 1 en `C:\tesis\` (queda `C:\tesis\desarrollo`).
3. Instalar todo con un comando: `powershell -ExecutionPolicy Bypass -File scripts\bootstrap_gpu.ps1` (detalle en `docs/INSTALACION_PC_NUEVA.md`).
   Crea `C:\tesis_data\.venv`, instala PyTorch con CUDA, ffmpeg, yt-dlp, Whisper, LightGBM, etc.
4. Descomprimir el paquete 2 **en `C:\tesis_data\`** (debe quedar `C:\tesis_data\data\interim`, `...\data\processed`, `...\models_ext`).
5. Si usas otra letra de disco, cambiar `paths.data_root` en `configs/default.yaml` (las demás rutas cuelgan de él).
6. Verificar: `C:\tesis_data\.venv\Scripts\python.exe -m pytest -q tests` (deben pasar 52 pruebas) y `python scripts\check_env.py`.

## 4. Cómo trabajamos (reglas y rutina)

**Idioma:** responder siempre en español. El autor escribe rápido e informal; priorizar acción y mostrar el resultado, sin rodeos.

**Reglas metodológicas (no negociables)**
1. **Honestidad:** nada de elegir variantes mirando el test. Lo que se explora en desarrollo se confirma **una sola vez** en videos nuevos, con hipótesis escrita antes.
2. **Toda decisión se registra** en `docs/DECISIONES.md` (fecha, hipótesis, resultado, estado). Numeración correlativa; la última es D-073.
3. **Se reporta lo negativo** igual que lo positivo. No se declara éxito si no se cumple el umbral preregistrado (ejemplo: R4 p = 0.0133 vs 0.0125 → "no se cumple").
4. **Sin fugas:** la posición en el video nunca entra al modelo; los splits se agrupan **por canal**; cohortes frescas se congelan antes de mirar resultados.
5. **Se verifica cada cita** antes de ponerla en un documento. Si no se pudo, se marca.
6. **Nunca usar la curva de YouTube como entrada del sistema.** Es solo regla de calificación. Cualquier demo con curva debe decirlo.

**Rutina de trabajo con Claude Code**
- Cada experimento = un script en `scripts/` + una entrada en `DECISIONES.md` + resultados en `reports/<experimento>/` (y copia en `entregables`).
- Se usó un **loop de investigación** (`/loop` en modo dinámico) con regla de parada por hora: a la hora fijada se corre la prueba final **una sola vez**,
  se registra el resultado y se cierra con un reporte.
- Las entregas para la profesora salen en **`D:\tesis\entregables`** y se copian a `TESIS_ENTREGA/resultados`.
- Para decir "terminó": confirmar con evidencia (log, archivo, render), no solo con que el comando salió bien.

**Herramientas que usamos y cómo**
| Tarea | Herramienta |
|---|---|
| Código y experimentos | Python 3.11 en `C:\tesis_data\.venv` (`C:\tesis_data\.venv\Scripts\python.exe`) |
| Word (artículo) | `python-docx` sobre la plantilla A.3; script `scripts/construir_articulo.py`; render a PDF con Word COM (`ExportAsFixedFormat`) y a PNG con `pymupdf` |
| PPT | `pptxgenjs` (Node) con estilo del PPT anterior (negro/naranja `FF4713`/Verdana); render con PowerPoint COM `Presentation.Export` |
| Demo web local | `python scripts/web_clips.py` → http://localhost:8765 (o `scripts\web_clips.bat`) |
| Demo hospedada | Artifact (HTML con 3 videos precalculados): https://claude.ai/artifact/XcuSXVCLcCVyn8anJoDnBL |
| Pasar archivos entre PCs | `croc send` / `croc <código>` o `python -m wormhole send` / `wormhole receive <código>` |
| Código en la nube | `gh` (GitHub CLI) con la cuenta `josefrancisco1234` |

## 5. Mapa de carpetas (paquete 1)

```
desarrollo/
  CLAUDE.md                  contexto y reglas para Claude Code (leerlo primero)
  configs/                   default.yaml (CPU), gpu.yaml (GPU), ampliacion_D065/D071.yaml
  src/                       pipeline.py, features/ (las 71 variables en builder.py), ranking/retention.py (fórmula), segment/, render/
  models/                    formula_calor_D045.json (17 pesos), ranker_lgbm.txt, explainer_lgbm.txt, dl_secuencia_D054.pt, speech_pca.npz
  scripts/                   un script por experimento (D-044 a D-073), web_clips.py, generar_clips.py, interfaz_clips.py, demos
  reports/                   resultados de cada experimento + conjuntos congelados (cohortes)
  docs/                      DECISIONES.md, HANDOFF_PC_GPU.md, MAPA_FORMULAS_EN_CODIGO.md, FORMULAS_Y_VARIABLES.md, EXPLICACION_COMPLETA.md
  tests/                     52 pruebas
  data/manifests/            youtube_mr.csv (lista de videos) y su estado
```

Datos pesados (fuera del repo, `C:\tesis_data`): `data/raw/wav` (audios), `data/interim/{heatmaps,transcripts/base,audio_frames,audio_events,speech_emb}`,
`data/processed/features/bin` (una tabla por video), `models_ext` (pesos externos), `outputs` (clips renderizados), `logs`.

## 6. Comandos que más se usan

```powershell
cd C:\tesis\desarrollo
$py = "C:\tesis_data\.venv\Scripts\python.exe"
& $py scripts\generar_clips.py "https://www.youtube.com/watch?v=l_-igAkbVII"      # clips de una URL (solo contenido)
& $py scripts\generar_clips.py "<url>" curva                                      # solo demo: usa la curva de YouTube
& $py scripts\web_clips.py                                                       # web local
& $py scripts\matriz_confusion.py                                                # matriz de confusión por ventana (557 videos)
& $py scripts\demo_3_ejemplos.py                                                 # 3 ejemplos explicados
& $py scripts\construir_articulo.py                                              # regenera el Word v9 (ajustar rutas en el script)
& $py -m pytest -q tests
```

Videos de ejemplo: `l_-igAkbVII` (ES, 4/5), `UIC10AA34YU` (EN, 3/5), `3KfZ30O2fEQ` (EN, 3/5).

## 7. Estado de los entregables

- **Artículo (Word):** `Articulo_Investigacion_CIS2026_v9.docx` (versión ganadora). Llenado en la plantilla A.3 hasta **Experimentación** (incluye matriz de confusión y los dos diagramas).
  Faltan Resultados, Discusión, Conclusiones y Trabajos futuros (siguen con el texto guía de la plantilla).
  **Por confirmar:** código de alumno (20221730 en los Word anteriores; 20221730 en el correo), apellido de la asesora (Maywa o Mayhua Quispe), correo de la asesora, y 4 referencias que agregué (Whisper, HuBERT, SHAP, McNemar).
- **PPT de avance:** `Avance_Pipeline_y_Resultados.pptx` (17 diapositivas, base: `Exposicion_Seminario_I_Oficial_V2.pptx`).
- **Demo:** web local y Artifact con 3 videos; interfaz de escritorio `scripts\interfaz_clips.bat`.

## 8. Qué falta (en orden de prioridad para la PC con mejor GPU)

1. **Ampliar el dataset de entrenamiento (D-071):** `scripts/ampliar_dataset_D071.py` + `configs/ampliacion_D071.yaml` (~200 videos nuevos). No corrió; el config se corrigió (un solo nivel de `extends`).
   Cuidado con el bloqueo anti-bot de YouTube (error 429): hay pausas automáticas; si falla, esperar o usar cookies del navegador (pedir permiso al usuario).
2. **Mezcla R0 + submodelo de 17 variables (D-073):** +0.010 de F1 en desarrollo (p = 0.015 sin corregir). **Preregistrar antes** de probarla con los videos nuevos de D-071.
3. **Ciclo de automejora con deep learning** (lo pidió la profesora): campeón (LightGBM) contra retador (BiGRU de secuencia); reentrenar al llegar videos nuevos y
   **promover solo si mejora el F1 con Wilcoxon p < 0.05** en un conjunto congelado por canal; registrar cada ronda. Con ~450 videos el deep learning no superó a la fórmula;
   con más datos y GPU puede cambiar. Es lo más importante para convencer a la profesora.
4. **Completar el artículo:** Resultados, Discusión, Conclusiones, Trabajos futuros con los números de las secciones 1 y 7.
5. **Usar la GPU mejor:** Whisper `medium` o `large` en fp16, HuBERT en lote, transformers de secuencia más grandes (ver `scripts/dl_secuencia_D054.py`).

## 9. Trampas ya conocidas (no repetirlas)

- `Config` devuelve una **copia**: escribir `cfg["ranking"]["max_clip_s"] = 45`, **no** `cfg.ranking[...] = ...`.
- `extends` en los YAML solo resuelve **un nivel** (un config no puede heredar de otro que ya hereda).
- YouTube bloquea tras muchas descargas (429 / "confirma que no eres un bot"). Reintentar más tarde; el pipeline reutiliza el mp4 si ya está en `raw/videos`.
- HuBERT debe correr en **fp32** (fp16 devuelve NaN).
- En PowerShell con `python - <<` o en bash con heredoc, las **barras invertidas y `\n` se rompen**: escribir los scripts con la herramienta de archivos y usar `/` en las rutas.
- El PCA de HuBERT está **congelado** (sha256[:16] = 87a80b42f96a4565): no reajustarlo.
- Las cohortes frescas (`reports/conjunto_confirmacion_fresca*.json`) no se tocan: son la prueba de confirmación.
- La web usa ventanas de oración; la evaluación offline usa 100 tramos por video. Los números exactos difieren un poco; la fórmula es la misma.
- No tocar la curva como entrada: si una demo la usa, aclararlo.

## 10. Prompt de arranque para el Claude de la otra PC

> Eres Claude Code en la PC con mejor GPU de José Francisco Núñez del Prado (tesis de Ingeniería de Sistemas, U. de Lima). Lee primero, en este orden:
> `C:\tesis\desarrollo\CLAUDE.md`, `docs\HANDOFF_PC_GPU.md`, `docs\DECISIONES.md` (al menos D-044 a D-073) y `docs\MAPA_FORMULAS_EN_CODIGO.md`.
> Responde en español, directo y sin rodeos. Respeta las reglas metodológicas: sin elegir variantes mirando el test, una sola confirmación en videos nuevos,
> hipótesis escritas antes, se reporta lo negativo, nunca usar la curva de YouTube como entrada. Registra cada decisión en `DECISIONES.md` (siguiente: D-074).
> Primero instala el entorno (`scripts\bootstrap_gpu.ps1`), verifica `pytest` y la GPU, y dime qué encontraste. Después, en este orden: (1) correr la ampliación D-071,
> (2) preregistrar y probar la mezcla R0 + 17 variables, (3) construir el ciclo campeón/retador con deep learning, (4) completar Resultados y Discusión del artículo v9.
> Antes de borrar, sobrescribir, publicar o enviar algo fuera de la PC, pídeme confirmación.
