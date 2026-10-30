# 02 — Auditoría del modelo

- **Fecha:** 2026-09-22
- **Estado:** resultados de la primera iteración completa (Fase 3)
- **Tablas completas:** `reports/results.md` (CV), `reports/significance.csv` (Wilcoxon), `reports/regularized/` (análisis de sensibilidad)
- **Regeneración:** `python run_all.py` (semilla 42, versiones en `requirements.txt` y `requirements-lock.txt`, entorno en `reports/environment.json`)

---

## 1. Resumen honesto

1. **El modelo tiene una señal real, pero pequeña.**
   - Con 61 videos de test (validación cruzada por canal), LightGBM LambdaRank supera al azar de forma significativa en **NDCG@10** (0.566 vs 0.495, Wilcoxon p = 0.009).
   - En P@5 la mejora es marginal (0.103 vs 0.057, p = 0.075).
   - En F1 temporal y F1 por bins las mejoras no son significativas.
2. **Supera de forma significativa a las heurísticas de una sola señal:**
   - solo energía RMS (NDCG, F1 temporal y F1 por bins: p < 0.05);
   - solo TF-IDF (F1 temporal: p = 0.02);
   - prior de posición (MRR, F1 temporal y F1 por bins: p < 0.05);
   - heurística tipo Opus con pesos fijos (NDCG: p = 0.02).
3. **Ninguna ablación produce diferencias significativas.** Con 62 videos no se puede afirmar que una técnica concreta sea imprescindible. El audio (técnica 8) es la señal más consistente: domina la importancia de features y "solo audio" rinde igual que el modelo completo.
4. **Se detectó y corrigió una fuga de información (D-018).** La primera versión de `k_novelty` correlacionaba −0.60 con la posición del clip en el video y hacía que los resultados parecieran mejores de lo que eran (P@1 0.173 → 0.049 tras la corrección). Todos los números de este documento son **posteriores** a la corrección.
5. **El baseline neuronal (MLP RankNet) empata con LightGBM** en todas las métricas (ninguna diferencia con p < 0.4). Se mantiene LightGBM por interpretabilidad (desglose SHAP) y costo.

**Conclusión para la tesis:** el enfoque es viable y auditable y supera a las alternativas simples. Pero con 62 videos, la precisión absoluta es baja y la contribución de cada técnica no se puede separar estadísticamente. La prioridad es **escalar el dataset**: Rhapsody, con 13 364 episodios, está listo para usarse (ver §7).

---

## 2. Dataset

| | |
|---|---|
| Nombre | YT-MR (propio), `data/manifests/youtube_mr.csv` |
| Construcción | Búsqueda en YouTube con 12 consultas (6 ES, 6 EN) → duración 15–75 min → sólo videos con curva Most Replayed → máx. 2 por canal |
| Manifest | 71 videos |
| **Válidos** | **62 videos, 50.6 h, 51 canales** (37 ES, 25 EN); duración mediana 52 min (16–74); mediana de vistas 771 k |
| Excluidos (9) | 6 por descarga bloqueada (HTTP 403 o verificación anti-bot de YouTube); 1 porque estaba en portugués; 2 por errores de detección de idioma de Whisper `base` (un video en español detectado como gallego y uno en inglés como indonesio) |
| Transcripción | faster-whisper `base` int8 (D-013) |
| Etiqueta | Curva Most Replayed de 100 bins; primer bin corregido (`g[0] = g[1]`, como Rhapsody) |
| Unidades | 23 649 candidatos alineados a oración (15–90 s; hasta 400 por video), 6 200 bins de 1 %, ventanas fijas de 20 s |
| Relevancia | Graduada de 0 a 4 por quintiles de Most Replayed dentro de cada video (LambdaRank); binaria "relevante" si ≥ 50 % del clip cae en bins highlight (> 0.5, máximo 20 por video) |

**Base rate:** solo ~5 % de los candidatos son "relevantes". Una precisión de 0.10 equivale aproximadamente al doble del azar.

## 3. Splits y protocolo

- **Validación cruzada:** GroupKFold (k = 5) **por canal**, para que un mismo presentador no aparezca en train y test. En cada fold, el 15 % de los canales de entrenamiento se reserva para early stopping y calibración. Se reporta media ± desviación entre folds.
- **Modelo final** (`models/ranker_lgbm.txt`): split fijo 70/15/15 por canal (`reports/split.json`).
  - El test fijo tiene solo 11 videos y resultó favorable (P@1 = 0.27, NDCG@10 = 0.70). **No se usa como resultado principal:** ilustra la varianza entre particiones.
- **Significancia:** Wilcoxon signed-rank pareado por video sobre las predicciones de los 5 folds (n = 60–61 videos).
- **Hiperparámetros:** fijados antes de ver resultados (`configs/default.yaml`). Una configuración más regularizada (hojas = 7, `min_data_in_leaf` = 100) se evaluó solo como análisis de sensibilidad y **no se adoptó**: no mejoró de forma consistente, y elegirla después de ver la CV inflaría los resultados.

## 4. Métricas y resultados principales (CV, 5 folds)

- **Candidatos:** P@K, MRR, NDCG@10 (relevancia graduada), Spearman (score vs Most Replayed) y **F1 temporal vs Most Replayed**. Este último usa los top-5 clips tras NMS y mide qué fracción de su tiempo cae en bins highlight y qué fracción del tiempo highlight cubren.
- **Bins:** protocolo de Rhapsody con top-k bins (hit, P, R, F1, AP). Es una réplica fiel de su `metrics.py`.

| Modelo | P@5 | MRR | NDCG@10 | Spearman | F1 temp.@5 | F1 bins@5 |
|---|---|---|---|---|---|---|
| **LightGBM LambdaRank** | **0.103** | 0.170 | 0.563 | 0.099 | 0.085 | **0.081** |
| MLP RankNet | 0.108 | 0.209 | 0.576 | 0.122 | 0.090 | 0.071 |
| Heurística tipo Opus (fija) | 0.092 | 0.173 | 0.475 | 0.036 | 0.086 | 0.062 |
| Solo KeyBERT | 0.070 | 0.177 | 0.576 | 0.121 | 0.089 | 0.061 |
| Solo TF-IDF KVSUM | 0.063 | 0.161 | 0.478 | 0.021 | 0.045 | 0.058 |
| Solo energía RMS | 0.066 | 0.130 | 0.422 | −0.113 | 0.050 | 0.032 |
| Prior de posición | 0.064 | 0.100 | 0.556 | 0.144 | 0.045 | 0.044 |
| Aleatorio | 0.057 | 0.156 | 0.496 | −0.002 | 0.062 | 0.057 |

Las desviaciones entre folds van de ±0.02 a ±0.13; el detalle está en `reports/results.md`.

**Por idioma:** ES y EN rinden parecido (NDCG@10 0.564 vs 0.565; F1 temporal 0.084 vs 0.086). No se observa que el modelo, con embeddings y sentimiento multilingües, favorezca un idioma.

**Etiqueta graduada vs binaria:** la graduada es mejor en P@5, NDCG@10, F1 temporal y sobre todo en F1 por bins (0.081 vs 0.051), aunque no en MRR (0.170 vs 0.195). Conviene aprovechar la curva completa y no solo el umbral.

**Segmentación (P4 frente a oraciones):** el modelo entrenado sobre ventanas fijas de 20 s alcanza F1 temporal 0.072 en su propio dominio; el modelo por oraciones, 0.085 sobre candidatos por oración. Los conjuntos de candidatos difieren, así que la comparación es indicativa. Además, los clips alineados a oración son publicables (no cortan frases) y las ventanas fijas no.

## 5. Ablación por técnica

Se quita un grupo a la vez (Δ = variante − completo). Ninguna diferencia es significativa (Wilcoxon, todas p > 0.1), salvo "− keywords" en NDCG, que *mejora* NDCG (p = 0.049) pero empeora P@5 y F1 temporal.

| Variante | Técnica | P@5 | MRR | NDCG@10 | F1 temp.@5 | F1 bins@5 |
|---|---|---|---|---|---|---|
| − keywords | 5, 6 (TF-IDF + KeyBERT) | −0.018 | +0.023 | +0.042 | −0.012 | +0.006 |
| − sentimiento | 7 | −0.005 | +0.050 | +0.039 | +0.007 | −0.009 |
| − audio | 8 (librosa) | **−0.020** | +0.023 | −0.014 | **−0.017** | **−0.026** |
| − hook | Opus Hook / P2 | −0.009 | +0.066 | −0.006 | +0.002 | −0.006 |
| − flow | Opus Flow / P2 | −0.015 | +0.012 | +0.018 | −0.008 | −0.007 |
| + posición | (control) | −0.014 | +0.072 | −0.021 | −0.017 | −0.027 |

**Lectura:**
- **Audio (8)** es la técnica cuya eliminación más empeora P@5, F1 temporal y F1 por bins (quitar *flow* también empeora las tres, pero menos). Las 7 features más importantes por ganancia son de audio o de novedad léxica (`k_novelty`, `a_energy_delta`, `a_rms_std`, `a_pause_ratio`, `a_pitch_std`, …). Esto coincide con UMT (P7): el audio aporta de forma consistente.
- **Keywords (5, 6)** aportan a la precisión de los primeros puestos, pero no al orden global. Son esenciales para la **salida** (palabras de mayor peso con contexto y subtítulos), aunque su aporte al ranking es débil.
- **Sentimiento (7)** no aporta con este dataset; es candidato a simplificarse.
- **Añadir la posición empeora el F1**: el modelo no debe aprender *dónde* suele estar lo bueno, sino *qué* es lo bueno.
- Las técnicas 1–4, 9 y 10 no se ablacionan con estas métricas porque actúan en etiquetado o generación: 3 es la etiqueta, 4 la línea base de segmentación y 1, 2, 9 y 10 contexto y render.

## 6. Sesgos y limitaciones

1. **Most Replayed no es viralidad.** Mide re-reproducción dentro de YouTube, así que el score se reporta como *potencial de retención* (D-008). No hay validación contra vistas en TikTok ni Reels.
2. **Sesgo de popularidad.** Solo hay curva en videos con audiencia (mediana de 771 k vistas), de canales grandes y en formatos de podcast y charla. El modelo no vio contenido de creadores pequeños.
3. **Sesgo de dominio.** 62 videos hablados (podcasts, entrevistas, TEDx, stand-up). Para "cualquier video" (gaming, deportes, tutoriales sin cámara) no hay evidencia; el modelo depende de la voz.
4. **Tamaño.** 62 videos y 51 canales dan alta varianza entre folds y baja potencia estadística para las ablaciones.
5. **Ruido en la etiqueta.** La curva se suaviza en bins de ~30 s (1 % de un video de 50 min), mientras que los candidatos duran 15–90 s, así que la etiqueta es gruesa. Tampoco se sabe si la re-reproducción se debe a interés o a confusión.
6. **Sesgo de la transcripción.** Whisper `base` detectó mal el idioma en 2 de 71 videos, y los errores de ASR afectan a las features léxicas (sobre todo en español con acentos regionales).
7. **Sin visión en el ranking** (D-016): no se capturan gestos, gráficos en pantalla ni cambios de escena como señal de interés.
8. **LLM no evaluado** (D-015): sin API key no se midió la selección top-K por LLM (P4) ni la etiqueta secundaria. El título y el hook actuales son plantillas.
9. **Hablante activo con heurística** (D-012) en lugar de Light-ASD; sin evaluación cuantitativa del reencuadre.
10. **Legal.** Datos derivados de YouTube con fines académicos; se publican solo IDs y datos derivados.

## 7. Próximos pasos (por impacto esperado)

1. **Rhapsody** (13 364 episodios): el autor acepta los términos en Hugging Face y ejecuta `hf auth login`; luego `python -m src.data.rhapsody --export`. Multiplica por 200 el dataset y permite comparar con los números publicados en COLM 2025.
2. **API key del LLM** para correr la línea base P4 (LLM top-K) y la etiqueta secundaria.
3. **Evaluación humana** con la rúbrica de PodReels (hook, contexto, duración, producción) frente a clips de Opus Clip sobre los mismos videos, más la tasa de clips descartables (Opus: 20–40 % según reseñas).
4. Simplificar el grupo de sentimiento si se confirma que no aporta con más datos.

## 8. Reproducibilidad

| Elemento | Dónde |
|---|---|
| Semilla | `seed: 42` en `configs/default.yaml` (Python, NumPy, PyTorch y LightGBM con `deterministic=True`) |
| Versiones | `requirements.txt` (directas) y `requirements-lock.txt` (130 paquetes); Python 3.11.9 |
| Datos | `data/manifests/youtube_mr.csv` (IDs) + `youtube_mr_status.csv` (qué videos quedaron válidos) |
| Script | `python run_all.py` → env → manifest → acquire → features → experiments → report (`--demo URL` genera clips) |
| Tests | `python -m pytest` (29 tests) |
| Decisiones | `docs/DECISIONES.md` (D-001 a D-020) |

**Limitación de reproducibilidad:** las curvas Most Replayed cambian con el tiempo y algunos videos pueden desaparecer o bloquear la descarga. Las curvas usadas quedan guardadas en `C:\tesis_data\data\interim\heatmaps\` y deberían archivarse junto con la tesis.
