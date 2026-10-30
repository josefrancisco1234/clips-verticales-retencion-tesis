# 02 — Auditoría del modelo

- **Fecha:** 2026-09-22 (iteración 2). La auditoría de la iteración 1 quedó en `docs/02_auditoria_modelo_iter1.md` y sus reportes en `reports_iter1/`.
- **Tablas completas:** `reports/results.md` (CV), `reports/significance.csv` (Wilcoxon), `reports/confirmacion_D022.json`, `reports/clips_humanos.json`
- **Regeneración:** `python run_all.py` (semilla 42; versiones en `requirements-lock.txt`; entorno en `reports/environment.json`)

---

## 1. Resumen

1. **El modelo funciona, con efecto pequeño pero significativo.** El procedimiento que elige sus grupos de features dentro de cada fold (`lgbm_autogroups`) supera al azar en las cuatro métricas principales, con 99–101 videos de test en validación cruzada:

   | Métrica | Modelo | Azar | p (Wilcoxon) |
   |---|---|---|---|
   | P@5 | **0.137** | 0.055 | 0.0012 |
   | NDCG@10 | **0.599** | 0.487 | <0.0001 |
   | F1 temporal@5 | **0.109** | 0.056 | 0.0002 |
   | F1 bins@5 | **0.090** | 0.050 | 0.0105 |

   También supera a la **heurística tipo Opus Clip** con pesos fijos (NDCG 0.599 vs 0.495, p = 0.0001) y al modelo con **todos los grupos** (P@5 p = 0.008; F1 temporal p = 0.001).

2. **La señal está casi toda en el audio.** El procedimiento eligió "sólo audio" en 3 de 5 folds (los otros: audio+lingüísticas y keywords+audio). Las features más importantes son proporción de pausas, RMS p95, pausas largas por minuto, variación de energía y variación de pitch. Es decir, **cómo se dice** pesa más que **qué se dice**.

3. **Hallazgo negativo central: Most Replayed y curación humana miden cosas distintas.** En los 11 videos que tienen ambas etiquetas, la correlación entre la curva y los clips elegidos por editores es **−0.04** (prácticamente nula) y el F1 temporal entre ambas es 0.067. Ningún modelo entrenado con Most Replayed recupera los clips humanos mejor que el azar.

4. **La hipótesis preregistrada no se confirmó.** Las features relativas al video (`rel_rk`, D-022) mejoraron en las cinco métricas sobre los 39 videos nuevos (NDCG +0.040, F1 bins +0.033, F1 temporal +0.023), pero sin significancia (p = 0.14). Se reporta como tendencia, no como mejora demostrada.

5. **Risa y aplausos (PANNs) no aportaron.** Quitar el grupo E no empeora ningún resultado y "sólo eventos de audio" queda cerca del azar. El respaldo de la literatura (UR-FUNNY, StandUp4AI) no se traslada a este dataset, probablemente porque sólo una parte es humor y porque se muestrea 1 s de cada 3.

**Conclusión para la tesis:** el sistema es viable, auditable y mejor que las alternativas simples, pero su etiqueta actual (Most Replayed) **no es la que usaría un editor**. El siguiente paso de mayor impacto es entrenar con clips humanos (Repurpose-10K, ~8.4k videos) y comparar ambas señales.

---

## 2. Dataset

| | Iteración 1 | **Iteración 2** |
|---|---|---|
| Videos válidos | 62 | **102** |
| Horas | 50.6 | **83.8** |
| Canales | 51 | **85** |
| Idiomas | 37 ES / 25 EN | **62 ES / 40 EN** |
| Candidatos | 23 649 | **39 505** |
| Con clips humanos | 0 | **11** (Repurpose-10K) |

- **Construcción:** 26 consultas en español y 24 en inglés por género y país, más 80 videos muestreados de Repurpose-10K; máximo 2 videos por canal; sólo videos con curva Most Replayed.
- **Bajas:** de 232 videos con curva en los manifests, 130 no se pudieron usar. La causa dominante fue el **bloqueo anti-bot de YouTube** tras muchas descargas en un día (64 de los 80 de Repurpose), más algunos errores de detección de idioma de Whisper `base`.
- **Etiquetas:** curva Most Replayed de 100 bins con el primer bin corregido (como Rhapsody) → relevancia graduada 0–4 por quintiles dentro del video. En los 11 videos de Repurpose, además `y_human_overlap` y `y_human`.

## 3. Protocolo

- **Validación cruzada GroupKFold (k = 5) por canal.** En cada fold, el 15 % de los canales de entrenamiento se reserva para early stopping, calibración y **selección del subconjunto de grupos** (D-027).
- **Significancia:** Wilcoxon signed-rank pareado por video sobre predicciones fuera de fold (n = 99–101).
- **Desarrollo y confirmación (D-021):** las variantes de la iteración 2 se exploraron sólo en los 62 videos de v1; la hipótesis se fijó por escrito (D-022) y se probó en los 39 videos nuevos.
- **Modelo desplegado:** subconjunto elegido por mayoría entre folds (**A: sólo audio, 10 features**), entrenado con el split fijo 70/15/15 y calibrado contra los top-10 clips de cada video de validación. El desglose Hook/Flow/Value lo aporta un modelo explicador entrenado con todos los grupos.

## 4. Resultados (CV, 5 folds, media ± desviación)

| Modelo | P@5 | MRR | NDCG@10 | Spearman | F1 temp.@5 | F1 bins@5 |
|---|---|---|---|---|---|---|
| **lgbm_autogroups (propuesto)** | **0.137 ± 0.079** | **0.254 ± 0.137** | **0.599 ± 0.049** | 0.128 ± 0.041 | **0.109 ± 0.048** | 0.090 ± 0.028 |
| Sólo audio (referencia) | 0.146 ± 0.071 | 0.271 ± 0.126 | 0.582 ± 0.047 | 0.129 ± 0.037 | 0.105 ± 0.051 | 0.091 ± 0.027 |
| LightGBM con los 7 grupos | 0.082 ± 0.035 | 0.154 ± 0.043 | 0.564 ± 0.048 | 0.103 ± 0.046 | 0.064 ± 0.021 | 0.074 ± 0.007 |
| MLP RankNet (baseline neuronal) | 0.088 ± 0.033 | 0.209 ± 0.066 | 0.585 ± 0.085 | 0.135 ± 0.028 | 0.086 ± 0.026 | 0.065 ± 0.031 |
| Heurística tipo Opus (pesos fijos) | 0.089 ± 0.027 | 0.176 ± 0.071 | 0.495 ± 0.053 | 0.055 ± 0.016 | 0.086 ± 0.016 | 0.063 ± 0.019 |
| Sólo KeyBERT | 0.057 ± 0.025 | 0.155 ± 0.058 | 0.548 ± 0.048 | 0.097 ± 0.040 | 0.085 ± 0.011 | 0.061 ± 0.013 |
| Sólo TF-IDF (KVSUM) | 0.064 ± 0.033 | 0.161 ± 0.045 | 0.498 ± 0.032 | 0.035 ± 0.027 | 0.048 ± 0.025 | 0.067 ± 0.026 |
| Sólo energía RMS | 0.070 ± 0.017 | 0.126 ± 0.045 | 0.456 ± 0.033 | −0.074 ± 0.036 | 0.046 ± 0.015 | 0.040 ± 0.013 |
| Prior de posición | 0.071 ± 0.024 | 0.112 ± 0.030 | 0.522 ± 0.033 | 0.111 ± 0.033 | 0.055 ± 0.011 | 0.054 ± 0.012 |
| Aleatorio | 0.055 ± 0.016 | 0.126 ± 0.024 | 0.487 ± 0.020 | −0.002 ± 0.011 | 0.056 ± 0.014 | 0.050 ± 0.019 |

**Por idioma** (modelo con todos los grupos): español NDCG 0.557 y F1 temporal 0.063; inglés 0.569 y 0.065. No hay diferencia apreciable.

**Etiqueta graduada vs binaria:** la graduada sigue siendo mejor (F1 bins 0.074 vs 0.061; F1 temporal 0.064 vs 0.056).

## 5. Ablación (sobre el modelo con los 7 grupos)

| Variante | P@5 | MRR | NDCG@10 | F1 temp.@5 | F1 bins@5 | Lectura |
|---|---|---|---|---|---|---|
| Todos los grupos | 0.082 | 0.154 | 0.564 | 0.064 | 0.074 | referencia |
| − keywords (téc. 5-6) | 0.093 | 0.193 | **0.607** | 0.085 | 0.074 | **mejora** NDCG (p = 0.02) |
| − sentimiento (téc. 7) | 0.108 | 0.238 | 0.586 | 0.095 | 0.084 | mejora F1 temporal (p = 0.07) |
| − hook | 0.099 | 0.196 | 0.595 | 0.093 | 0.076 | mejora F1 temporal (p = 0.04) |
| − flow | 0.093 | 0.192 | 0.576 | 0.079 | 0.078 | sin efecto claro |
| − audio (téc. 8) | 0.091 | 0.192 | 0.555 | 0.087 | 0.073 | baja NDCG |
| − eventos E (risa) | 0.083 | 0.175 | 0.592 | 0.075 | 0.078 | sin aporte |
| − lingüísticas L | 0.102 | 0.177 | 0.569 | 0.073 | **0.099** | sin aporte |
| Sólo audio | **0.146** | **0.271** | 0.582 | **0.105** | 0.091 | mejor variante |
| Sólo eventos E | 0.078 | 0.182 | 0.540 | 0.071 | 0.055 | cerca del azar |

**Interpretación:** con ~100 videos y una etiqueta ruidosa, cada grupo de texto agrega parámetros sin señal suficiente y el modelo sobreajusta. Por eso el procedimiento de selección (D-027) es parte del método y no un truco posterior.

## 6. Evaluación contra clips humanos (Repurpose-10K, 11 videos)

**¿Coinciden las dos etiquetas?** No.

| Medida | Media | Mediana | Rango |
|---|---|---|---|
| Spearman (Most Replayed vs solapamiento con clips humanos) | −0.039 | 0.008 | −0.364 a 0.382 |
| F1 temporal (bins highlight vs clips humanos) | 0.067 | 0.020 | 0 a 0.210 |

**¿El ranker recupera los clips humanos?** Tampoco (predicciones fuera de fold, top-5 por video):

| Modelo | P@5 | MRR | F1 temporal vs humano | p vs azar |
|---|---|---|---|---|
| Sólo KeyBERT | 0.291 | 0.545 | 0.194 | 0.18 |
| Aleatorio | 0.291 | 0.518 | 0.152 | — |
| Heurística tipo Opus | 0.309 | 0.471 | 0.124 | 0.93 |
| LightGBM (7 grupos) | 0.273 | 0.521 | 0.118 | 0.77 |
| lgbm_autogroups | 0.273 | 0.362 | 0.107 | 0.95 |

Es coherente con el punto 3: si la etiqueta de entrenamiento no correlaciona con la curación humana, el modelo que la optimiza no puede recuperarla. La señal **semántica** (KeyBERT) es la que más se acerca a lo que eligen los editores, aunque sin significancia con 11 videos.

## 7. Limitaciones

1. **La etiqueta no es la tarea.** Most Replayed mide re-reproducción; un editor busca otra cosa. Ya no es una sospecha: está medido (§6).
2. **Tamaño.** 102 videos y 85 canales; las desviaciones entre folds siguen siendo grandes (±0.05 a ±0.14).
3. **Sólo 11 videos con clips humanos**, por el bloqueo anti-bot de YouTube. Con esa n, §6 es indicativo.
4. **Sin visión en el ranking** y sin embeddings de habla (HuBERT descartado por costo en CPU: 875 s por minuto de audio).
5. **LLM no evaluado:** sin API key, el título y el hook salen de plantillas y no se pudo medir la línea base de P4.
6. **Sesgo de popularidad:** sólo hay curva en videos con audiencia, así que el modelo no vio creadores pequeños.
7. **Whisper `base`** en el dataset: errores de ASR y 3 idiomas mal detectados de 232.
8. **Reproducibilidad temporal:** las curvas cambian con el tiempo; las usadas quedan guardadas en `C:\tesis_data\data\interim\heatmaps\`.

## 8. Próximos pasos, por impacto

1. **Entrenar con clips humanos** (Repurpose-10K, ~8.4k videos con timestamps): es la etiqueta alineada con el producto. Requiere descargar el audio desde una IP doméstica y con pausas largas.
2. **Rhapsody** (13 364 podcasts): multiplica por 130 el dataset de Most Replayed y permite comparar con los números publicados en COLM 2025. Necesita que el autor acepte los términos en Hugging Face.
3. **GPU** (`docs/SETUP_GPU.md`): habilita Whisper `small`/`medium` y HuBERT, que Rhapsody reporta como la mayor mejora de audio.
4. **Evaluación humana** con la rúbrica de PodReels, comparando contra clips de Opus Clip sobre los mismos videos.
5. **API key de LLM** para la línea base de selección top-K y los títulos generados.

---

## 9. Iteración 3 (GPU, 2026-09-24) — grupo U (HuBERT): resultado exploratorio

Todo lo anterior (§1–§8) corresponde a la iteración 2 (102 videos) y se conserva en `reports_iter2_base/`. Esta sección usa **121 videos** (101 canales, 97,5 h) y es **exploratoria**: la hipótesis se preregistró en D-038 y su confirmación está pendiente de los videos nuevos de la laptop.

- **Costo del grupo U:** 0,34 s por minuto de audio en una GTX 1660 SUPER (fp32; 97,5 h en 33,6 min), frente a 875 s por minuto en CPU. En fp16 HuBERT devolvía NaN (D-035).
- **¿Entra en la selección automática?** Sí, en 3 de 5 folds (D-039).
- **¿Mejora al modelo?** No de forma demostrable: NDCG@10 0,622 con U frente a 0,626 sin U (p = 0,94); P@5, MRR, F1 temporal y F1 por bins no difieren significativamente (p 0,24–0,87). Ambos procedimientos superan al azar (NDCG@10 p < 0,0001).
- **Lectura:** con ~120 videos, 32 dimensiones de embeddings de habla no aportan señal detectable sobre lo que ya captura el audio de bajo nivel; no se puede descartar que un dataset mayor cambie esto. Es un resultado negativo que se reporta como tal.
- **Limitaciones específicas:** PCA con fuga no supervisada (D-038); selección de grupos inestable entre folds; ~24 videos por fold de prueba.
- **Modelo desplegado:** sin U (D-027, regenerado con el dataset de 121 videos).
- **Otros hallazgos técnicos de la migración:** HuBERT en fp16 devolvía NaN (D-035); `faster-whisper` no cargaba `cublas64_12.dll` en GPU y `check_env.py` no lo detectaba (D-036, D-037); fp16 no corrompe Whisper pero es 2× más lento que fp32 en una GTX 16xx (D-036).

## 10. Entrenamiento con etiqueta humana (2026-09-25, D-040/D-041)

Preregistrado antes de correr, ejecutado una sola vez sobre **29 videos** de Repurpose-10K (26 canales, todos en inglés), CV por canal k = 5.

| Modelo | P@5 | MRR | P@1 | F1 temporal@5 |
|---|---|---|---|---|
| entrenado con clips humanos | 0,345 | 0,483 | 0,310 | 0,117 |
| entrenado con Most Replayed | 0,331 | 0,440 | 0,276 | 0,124 |
| aleatorio | 0,345 | 0,519 | 0,276 | 0,136 |

**Resultado negativo:** H-H1 (humano > Most Replayed en F1 temporal) no se confirma (p = 0,61); el modelo humano tampoco supera al azar (p = 0,82). **Interpretación cautelosa:** es un resultado de falta de poder (29 videos, ~23 de entrenamiento por fold, hasta ~130 features), no una prueba de que las etiquetas sean equivalentes. El hallazgo de D-028 (Most Replayed no predice la curación humana) se mantiene, pero la alternativa propuesta (entrenar con clips humanos) **no queda respaldada por esta muestra**. Siguiente paso: réplica con los videos nuevos y escalar hacia las ~8,4 k de Repurpose-10K.
