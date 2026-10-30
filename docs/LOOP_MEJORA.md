# Loop de mejora continua (arranque 2026-10-19)

Orden del autor: mejorar el modelo (dataset, variables nuevas, deep learning, LLM) iterando por prueba y error, sin parar hasta que él lo diga.

## Objetivo vigente (2026-10-19): acierto estable de 80 % (hit@5), reporte cada 30 min
- **Definición:** acierto = al menos 1 de 5 clips toca un pico real, medido SOLO en videos nuevos (confirmación), sin curva como entrada.
- **Línea base honesta:** con solo contenido el techo medido va de 47 a 65 % (azar 27–32 %; D-051, D-064, D-072). El 80 % solo se alcanzó usando la curva (fusión 82–85 %, D-055/D-064), que NO es un sistema válido para un video nuevo.
- **Regla:** no se declara 80 % si viene de la curva, de elegir variantes mirando el test o de una sola cohorte pequeña. Si tras agotar las vías el techo real queda por debajo, se reporta cuánto y por qué.
- **Vías:** más datos (D-071 y siguientes), variables nuevas, retador de deep learning, LLM sobre la transcripción (pendiente de crédito en la API).

## Protocolo (respeta las reglas no negociables)
1. **Explorar** solo en desarrollo (444 videos + los que se vayan consumiendo), validación cruzada agrupada por canal, presupuesto de contrastes declarado y Bonferroni. Cada ronda = un script en `scripts/` + entrada D-0NN en `docs/DECISIONES.md` + `reports/<exp>/`.
2. **Confirmar una sola vez** en videos nuevos que nunca participaron en una decisión. Hipótesis y reglas escritas ANTES de mirar (preregistro). Las cohortes D-050 y D-065 ya se usaron para R4/E3: no sirven de nuevo para esas familias.
3. **Reportar lo negativo.** Nada se adopta sin pasar la confirmación. Nunca la curva de YouTube como entrada.
4. **Campeón/retador:** reentrenar al llegar datos nuevos; promover solo si F1 mejora con Wilcoxon p < 0.05 en un conjunto congelado por canal; registrar cada ronda.
5. **LLM:** usa clave del autor vía variable de entorno `ANTHROPIC_API_KEY` (la pone él; no se escribe en archivos ni en el chat). Solo con el contenido (transcripción), con caché, y evaluado como cualquier otra variable.

## Cola (en orden)
- [x] D-074 migración y arranque de D-071.
- [x] D-075 preregistro de la mezcla R0 + 17 variables (script `scripts/confirmacion_D075.py` listo; corre UNA vez cuando D-071 termine de featurizar).
- [ ] Esperar fin de D-071 (`reports/conjunto_entrenamiento_extra_D071.json` + features en `tesis_data/data/processed/features/bin`).
- [ ] Correr `confirmacion_D075.py` una vez; registrar resultado (D-076).
- [ ] Reentrenar con desarrollo + D-071; ciclo campeón (LightGBM) vs retador (BiGRU) con GPU (`scripts/dl_secuencia_D054.py`).
- [ ] Nuevas familias de variables (preregistrar presupuesto): prosodia más rica, embeddings de audio en lote, LLM sobre transcripción.
- [ ] Nueva cohorte fresca (nuevas consultas) para confirmar lo que gane en desarrollo.
- [ ] Completar Resultados/Discusión del artículo v9 con números finales (incluidos los negativos).
