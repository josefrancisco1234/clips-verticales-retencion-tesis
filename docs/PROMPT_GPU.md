# Prompt para arrancar en la PC con GPU

Copiar y pegar tal cual en Claude Code, con la carpeta `desarrollo/` abierta.
Si el proyecto todavía no está en esa máquina, primero hay que traerlo (ver `TRANSFERENCIA.md`).

---

Estoy continuando mi tesis de Ingeniería de Sistemas (Universidad de Lima) en esta PC, que tiene GPU
NVIDIA. El proyecto venía trabajándose en mi laptop, que sólo tiene CPU, y todo el contexto está en el
repositorio: lee primero `CLAUDE.md`, luego `docs/02_auditoria_modelo.md` y `docs/DECISIONES.md`
(D-001 a D-032). Responde siempre en español.

El sistema convierte un video largo en clips verticales 9:16 con un score 0–99, y está entrenado con
la curva "Most Replayed" de YouTube. El modelo actual usa sólo features de audio y supera al azar de
forma significativa, pero hay dos limitaciones grandes que esta PC puede atacar y la laptop no.

**Qué quiero que hagas, en este orden:**

1. **Verificar el entorno.** Sigue `docs/SETUP_GPU.md`: Python 3.11, ffmpeg, driver NVIDIA y un
   entorno en `C:\tesis_data\.venv` con la variante de PyTorch con CUDA que corresponda a esta tarjeta
   (ojo: las compilaciones nuevas de PyTorch dejaron fuera las GPU Pascal, como la GTX 10xx; ahí hay
   que usar el índice cu126). Luego corre `python scripts/check_env.py` y `python -m pytest`, y no
   sigas hasta que el verificador diga "Listo para ejecutar" y muestre la GPU detectada.

2. **Restaurar los datos** si no llegaron por Syncthing: hay un paquete generado con
   `scripts/pack_for_gpu.py`; se restaura con `python scripts/unpack_transfer.py <paquete>`.
   Comprueba cuántos videos quedaron válidos con `python scripts/rebuild_status.py`.

3. **Construir el grupo U (embeddings HuBERT).** Es la mejora de audio más grande según Rhapsody
   (COLM 2025) y la descarté en la laptop porque costaba 875 s por minuto de audio. El código ya está
   en `src/features/speech_embed.py` y se ejecuta con
   `python scripts/build_speech_embeddings.py --config configs/gpu.yaml`.
   **Necesita los WAV en `C:\tesis_data\data\raw\wav`**; si no llegaron, dime antes de empezar.

4. **Reentrenar y reevaluar** con `python run_all.py --config configs/gpu.yaml --from experiments`.
   Reporta si el grupo U entra o no en la selección automática de features, y contrasta con Wilcoxon
   (`python -m src.evaluation.significance`).

5. **Entrenar con la etiqueta humana:** `python -m src.evaluation.human_train`. Esto responde al
   hallazgo D-028, que es el más importante de la tesis: la curva Most Replayed y los clips que eligen
   editores humanos casi no correlacionan (Spearman −0.04). Quiero saber si un modelo entrenado
   directamente con clips humanos sí los recupera.

6. **Ampliar el dataset.** Con GPU la transcripción deja de ser el cuello de botella: `configs/gpu.yaml`
   ya sube la meta a 250 videos por idioma y usa Whisper `small`. Las descargas se hacen desde esta
   casa y espaciadas, porque YouTube bloquea si se piden muchas seguidas.

**Reglas que no se negocian** (están en `CLAUDE.md`, pero las repito):

- Nada de elegir variantes mirando el test. Si algo se prueba sobre un conjunto, la mejora se confirma
  en datos nuevos, y las hipótesis se preregistran en `DECISIONES.md` antes de mirarlos.
- Toda decisión se registra en `docs/DECISIONES.md` con fecha y justificación, numerada correlativa.
- Reportar también lo negativo: resultados no significativos, hipótesis refutadas y fugas detectadas.
- Ninguna feature puede codificar la posición del clip dentro del video (ya pasó una vez: D-018).
- Los splits se agrupan por canal, nunca por video.
- Ninguna referencia entra a la tesis sin DOI o enlace verificado.
- Si cambias el modelo de Whisper, hay que borrar `data/processed/features/`, volver a featurizar y
  anotarlo, porque cambian las transcripciones y con ellas todas las features.

Cuando termines cada paso, muéstrame los números y actualiza `docs/02_auditoria_modelo.md`, el panel
(`python scripts/build_dashboard.py`) y el documento Word si los resultados cambian.

Empieza por el paso 1 y dime qué encontraste antes de seguir.
