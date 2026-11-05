"""TODO LO QUE DIGO EN EL PPT, EN CÓDIGO Y CON CADA LÍNEA EXPLICADA (para leerlo mientras expongo).

ÍNDICE POR DIAPOSITIVA (el código corre en el orden en que cada paso necesita al anterior):
    Diap. 11 y 13  ETL y candidatos de 15 a 90 s ...... sección 1
    Diap. 12       variables ......................... sección 2
    Diap. 13       margen de respiración ............. sección 5
    Diap. 14       V1 (<= 45 s), NMS, top 5, capítulos  sección 4
    Diap. 15 y 17  percentil, bandera, suma, 0-99 .... sección 3
    Diap. 16       LightGBM / árbol (R0) ............. sección 8
    Diap. 18       campeón / retador ................. sección 9
    Diap. 19       métricas (acierto@5, F1, matriz) .. sección 6
    Diap. 21-22    azar, V0, V1, R0 .................. sección 7
    Diap. 23       redes neuronales vs R0 ............ sección 10

Es AUTÓNOMO: corre sin datos, sin GPU y sin internet, con un video de
ejemplo inventado, usando solo numpy y pandas (LightGBM es opcional). Los pesos de la fórmula SÍ son los reales.
El código de producción que hace lo mismo con videos de verdad está en PIPELINE_COMPLETO.py y main.py.

    python EXPLICACION_LINEA_POR_LINEA.py
"""
import json                                                   # lee el archivo con los 17 pesos congelados de la fórmula
import sys                                                    # para poder imprimir tildes en la consola de Windows
from pathlib import Path                                      # rutas de archivos sin pelear con las barras

import numpy as np                                            # cuentas con arreglos (sumas, productos, aleatorios)
import pandas as pd                                           # tablas: una fila por clip candidato

sys.stdout.reconfigure(encoding="utf-8", errors="replace")    # la consola de Windows no sabe tildes: se lo pedimos en UTF-8
rng = np.random.default_rng(42)                               # generador aleatorio con semilla: el ejemplo sale igual siempre


def titulo(txt):                                              # imprime un encabezado para separar cada diapositiva
    print(f"\n{'=' * 90}\n{txt}\n{'=' * 90}")                 # línea de "=" arriba y abajo del texto


# =====================================================================================================
# DIAPOSITIVAS 11 y 13 · ETL Y CANDIDATOS: del video largo a una lista de candidatos
# =====================================================================================================
titulo("DIAP. 11 y 13 · El video entra, se transcribe y se cortan candidatos de 15 a 90 s")
DURACION = 1800.0                                             # el video de ejemplo dura 30 minutos (1800 s)
# En el sistema real: yt-dlp baja el audio, ffmpeg lo pasa a WAV de 16 kHz y Whisper entrega cada palabra con su tiempo.
# Aquí inventamos directamente las ORACIONES (inicio, fin) porque el candidato siempre empieza y termina en una oración.
dur_oraciones = rng.uniform(3, 9, size=400)                   # cada oración dura entre 3 y 9 segundos
fin_oracion = np.cumsum(dur_oraciones)                        # el fin de cada oración es la suma acumulada de duraciones
fin_oracion = fin_oracion[fin_oracion <= DURACION]            # nos quedamos solo con las que caben en los 30 minutos
ini_oracion = np.r_[0.0, fin_oracion[:-1]]                    # el inicio de cada oración es el fin de la anterior
print(f"oraciones del video: {len(fin_oracion)}")             # cuántas oraciones tiene el video de ejemplo

filas = []                                                    # aquí guardamos un candidato por fila
for i in range(len(ini_oracion)):                             # para cada oración posible como INICIO del clip...
    for j in range(i, min(i + 20, len(fin_oracion))):         # ...probamos terminarlo en esa u hasta 19 oraciones más tarde
        dur = fin_oracion[j] - ini_oracion[i]                 # duración del candidato = fin de la última - inicio de la primera
        if 15.0 <= dur <= 90.0:                               # REGLA DE LA DIAP. 13: solo ventanas de 15 a 90 segundos
            filas.append((ini_oracion[i], fin_oracion[j], j - i + 1))   # guardamos inicio, fin y cuántas oraciones tiene
cand = pd.DataFrame(filas, columns=["start", "end", "f_n_sentences"])   # tabla de candidatos (f_n_sentences es una variable real)
cand["dur"] = cand.end - cand.start                           # duración de cada candidato en segundos
print(f"candidatos 15-90 s: {len(cand)} (en el sistema real son ~400 por video)")   # tamaño del universo del ejemplo

# =====================================================================================================
# DIAPOSITIVA 12 · LAS 71 VARIABLES (aquí inventamos los valores; en el sistema real salen del audio y del texto)
# =====================================================================================================
titulo("DIAP. 12 · Variables por ventana (audio, eventos de sonido, texto, gancho, fluidez)")
RUTA_PESOS = Path(__file__).parent / "models" / "formula_calor_D045.json"   # archivo con los 17 pesos congelados (V0)
if RUTA_PESOS.exists():                                       # si estamos dentro del repo...
    PESOS = json.load(open(RUTA_PESOS, encoding="utf-8"))["weights"]   # ...leemos los pesos REALES
else:                                                         # si alguien copió solo este archivo...
    PESOS = {"a_pause_ratio": .1797, "l_silence": .1634, "a_long_pauses_pm": .1478, "a_rms_std": .1218,
             "a_pitch_range": .1115, "a_voiced_ratio": -.1071, "k_keybert_sim": .1022, "e_speech_mean": -.1009,
             "k_noun_chunks_ps": -.0979, "a_speech_rate": -.0976, "a_pitch_std": .0887, "e_music_max": .0831,
             "a_rms_mean": -.0816, "e_music_mean": .0669, "f_n_sentences": .0604, "s_questions_pm": .0582,
             "s_second_person": .0562}                        # copia de los mismos 17 pesos (por si no está el json)
print(f"variables de la fórmula: {len(PESOS)} | pesos positivos: {sum(w > 0 for w in PESOS.values())} | "
      f"negativos: {sum(w < 0 for w in PESOS.values())}")     # 17 variables; el signo dice si ayuda o resta
for v in PESOS:                                               # recorremos cada variable de la fórmula
    if v not in cand:                                         # si aún no existe en la tabla de candidatos...
        cand[v] = rng.normal(size=len(cand))                  # ...le ponemos un valor inventado (en real: librosa, PANNs, KeyBERT)
cand["a_pause_ratio"] += rng.normal(size=len(cand)) * 0.3     # (solo para el ejemplo) ruido extra en una variable
print("ejemplo de 3 candidatos y 4 variables:")              # mostramos un pedazo de la tabla
print(cand[["start", "end", "a_pause_ratio", "a_rms_std", "s_questions_pm"]].head(3).round(2).to_string(index=False))

# =====================================================================================================
# DIAPOSITIVAS 15 y 17 · PERCENTIL → BANDERA → SUMA PONDERADA → PUNTAJE 0-99
# =====================================================================================================
titulo("DIAP. 15 y 17 · Percentil dentro del video, bandera 0/1, suma ponderada y escala 0-99")
BANDERA_P = 0.75                                              # umbral: la bandera vale 1 si el percentil es 0.75 o más
ESCALA = 99                                                   # el puntaje final va de 0 a 99

# PASO 1 · PERCENTIL: cada valor se compara SOLO con los demás candidatos de ESTE video.
pct = cand[list(PESOS)].rank(pct=True).fillna(0.5)            # rank(pct=True) = posición ÷ n (1.0 = el más alto del video); NaN -> 0.5 neutro
print(f"percentil de a_pause_ratio en el candidato 0: {pct.loc[0, 'a_pause_ratio']:.2f}  "
      "(0.80 significa: está por encima del 80 % de los candidatos de este video)")

# PASO 2 · BANDERA: solo "enciende" la variable que destaca (25 % más alto); el resto vale 0 y no mete ruido.
banderas = (pct >= BANDERA_P).astype(float)                   # True/False -> 1.0/0.0
print(f"banderas en 1 por candidato: promedio {banderas.sum(axis=1).mean():.1f} de {len(PESOS)} "
      "(con umbral 0.75 se espera ~4 de 17)")                 # 25 % de 17 = ~4

# PASO 3 · SUMA PONDERADA: raw = Σ peso × bandera. NO es promedio ni "un porcentaje".
w = np.array(list(PESOS.values()))                            # vector con los 17 pesos, en el mismo orden que las columnas
desempate = 1e-4 * (pct.to_numpy() @ w)                       # el percentil continuo solo rompe empates (pesa 0.0001)
raw = banderas.to_numpy() @ w + desempate                     # producto punto: suma de peso×bandera + desempate mínimo
cand["raw"] = raw                                             # guardamos el puntaje "crudo" de cada candidato

# PASO 4 · ESCALA FIJA 0-99: el mismo clip da el mismo puntaje en cualquier video.
lo = float(w[w < 0].sum())                                    # mínimo posible: solo los pesos negativos encendidos (-0.4851)
hi = float(w[w > 0].sum())                                    # máximo posible: solo los pesos positivos encendidos (+1.2400)
cand["score"] = np.clip(np.round((raw - lo) / (hi - lo) * ESCALA), 0, ESCALA).astype(int)   # (raw-mín)/(máx-mín)×99
print(f"mínimo posible {lo:+.4f} | máximo posible {hi:+.4f} | puntaje del mejor candidato: {cand.score.max()}")

# =====================================================================================================
# DIAPOSITIVA 14 (y 21-22) · V1 = V0 + CLIPS DE HASTA 45 s  →  NMS  →  TOP 5  →  MEJOR POR CAPÍTULO
# =====================================================================================================
titulo("DIAP. 14 (y 21-22) · V1: clips <= 45 s, orden por puntaje, NMS sin traslape y top 5")
MAX_CLIP_S = 45.0                                             # V1: los clips largos pierden contra los cortos, así que se excluyen
SOLAPE_MAX = 0.30                                             # dos clips elegidos no pueden compartir más del 30 % del más corto
TOP_K = 5                                                     # entregamos 5 clips


def solape_iomin(a, b):                                       # cuánto se traslapan dos clips respecto al MÁS CORTO
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))       # segundos en común = fin menor - inicio mayor (si es negativo, 0)
    return inter / min(a[1] - a[0], b[1] - b[0])              # intersección dividida entre la duración del más corto


def nms(df, col, k, max_dur=None):                            # NMS: elige de mayor a menor puntaje y salta los que se traslapan
    orden = df.sort_values(col, ascending=False)              # ordena todos los candidatos del mejor al peor
    if max_dur:                                               # si hay tope de duración (V1)...
        orden = orden[orden.dur <= max_dur]                   # ...descarta los más largos de 45 s
    elegidos = []                                             # aquí se acumulan los clips ya elegidos
    for idx, r in orden.iterrows():                           # recorremos de mejor a peor
        if all(solape_iomin((r.start, r.end), (df.loc[e].start, df.loc[e].end)) <= SOLAPE_MAX for e in elegidos):   # ¿no choca con ninguno?
            elegidos.append(idx)                              # no choca: lo elegimos
        if len(elegidos) == k:                                # al llegar a 5 paramos
            break                                             # salimos del bucle
    return elegidos                                           # índices de los clips elegidos


top_v1 = nms(cand, "raw", TOP_K, MAX_CLIP_S)                  # V1 = fórmula + clips <= 45 s + NMS + top 5
top_v0 = nms(cand, "raw", TOP_K, None)                        # V0 = la fórmula sola (sin tope de 45 s)
print("TOP 5 de V1 (inicio-fin en s | duración | puntaje):")  # mostramos los 5 elegidos
for n, i in enumerate(top_v1, 1):                             # numeramos 1 a 5
    r = cand.loc[i]                                           # fila del candidato elegido
    print(f"  #{n}: {r.start:7.1f}-{r.end:7.1f} | {r.dur:4.1f} s | puntaje {r.score}")   # una línea por clip

# Mejor clip de CADA CAPÍTULO (capítulos de YouTube o bloques de 10 min): garantiza cobertura de todo el video.
bloques = (cand.start // 600).astype(int)                     # a qué bloque de 10 minutos (600 s) pertenece cada candidato
extra = []                                                    # clips extra por capítulo
for b, g in cand[cand.dur <= MAX_CLIP_S].groupby(bloques):    # para cada bloque, solo con candidatos cortos...
    mejor = g.sort_values("raw", ascending=False).index[0]    # ...el de mayor puntaje del bloque
    if mejor not in top_v1:                                   # si aún no está en el top 5...
        extra.append(mejor)                                   # ...se agrega como "mejor del capítulo"
print(f"clips extra por capítulo: {len(extra)} (se suman al top 5)")

# =====================================================================================================
# DIAPOSITIVA 13 · MARGEN DE RESPIRACIÓN (corte natural, no a media palabra)
# =====================================================================================================
titulo("DIAP. 13 · Margen de respiración del corte")
PRE_S, POST_S = 0.15, 0.35                                    # medio segundo en total: 0.15 s antes y 0.35 s después
ini, fin = cand.loc[top_v1[0], ["start", "end"]]              # tomamos el mejor clip como ejemplo
print(f"corte crudo: {ini:.2f}-{fin:.2f} s  ->  con margen: {ini - PRE_S:.2f}-{fin + POST_S:.2f} s "
      "(en real se recorta si invadiría la palabra vecina)")   # el margen evita que el clip arranque o termine seco

# =====================================================================================================
# DIAPOSITIVA 19 · MÉTRICAS (y resultados 25-26): ACIERTO@5, F1 TEMPORAL Y MATRIZ
# =====================================================================================================
titulo("DIAP. 19 (y 25-26) · Cómo se califica: acierto@5, F1 temporal y matriz de confusión")
# La curva "Most Replayed" de YouTube es solo la REGLA DE CALIFICACIÓN: nunca entra al sistema.
calor = np.zeros(int(DURACION // 35) + 1)                     # la curva se parte en tramos de ~35 s (un valor por tramo)
calor[:] = rng.uniform(0.0, 0.5, size=len(calor))             # tramos "fríos": calor bajo
for c in rng.choice(len(calor), size=4, replace=False):       # elegimos 4 tramos al azar para que sean "picos reales"
    calor[c] = rng.uniform(0.6, 1.0)                          # tramos calientes: calor > 0.5
zonas = [(i * 35.0, (i + 1) * 35.0) for i, h in enumerate(calor) if h > 0.5]   # intervalos (inicio, fin) de las zonas calientes
print(f"zonas calientes (calor > 0.5) en el video de ejemplo: {len(zonas)}")   # cuántos picos reales tiene este video


def seg_comunes(clip, zona):                                  # segundos que un clip comparte con una zona caliente
    return max(0.0, min(clip[1], zona[1]) - max(clip[0], zona[0]))   # fin menor - inicio mayor, nunca negativo


def acierto_5(clips):                                         # ACIERTO@5: ¿al menos 1 de los 5 clips cae en zona caliente?
    for c in clips:                                           # revisamos cada clip entregado
        if sum(seg_comunes(c, z) for z in zonas) >= 0.5 * (c[1] - c[0]):   # >= 50 % de su duración dentro de zonas calientes
            return 1                                          # con uno que acierte basta (para ese video vale 1)
    return 0                                                  # ninguno acertó: vale 0


def f1_temporal(clips):                                       # F1 TEMPORAL: mide cuánto tiempo del clip y de la zona coinciden
    t_clips = sum(c[1] - c[0] for c in clips)                 # tiempo total entregado
    en_zona = sum(seg_comunes(c, z) for c in clips for z in zonas)   # tiempo entregado que sí cayó en zona caliente
    t_zonas = sum(z[1] - z[0] for z in zonas)                 # tiempo total de zonas calientes del video
    P = en_zona / t_clips                                     # PRECISIÓN: de lo que entregué, cuánto era caliente
    R = en_zona / t_zonas                                     # COBERTURA (recall): de lo caliente, cuánto cubrí
    return 0.0 if P + R == 0 else 2 * P * R / (P + R)         # F1 = media armónica de las dos


clips_v1 = [(cand.loc[i].start, cand.loc[i].end) for i in top_v1]   # los 5 clips de V1 como pares (inicio, fin)
print(f"V1 en este video -> acierto@5 = {acierto_5(clips_v1)} | F1 temporal = {f1_temporal(clips_v1):.3f}")
print("Diferencia: el ACIERTO solo pregunta 'tocaste algún pico?' (sí/no). El F1 pregunta 'cuánto tiempo acertaste y cuánto pico cubriste?'.")
print("Por eso R0 gana en acierto (62.4 %) pero el F1 sale parecido entre sistemas (0.14): 5 clips de ~35 s cubren poco de un video de 1 h.")

# Matriz de confusión a nivel de tramo de ~35 s: ¿el clip cayó en tramo caliente y el tramo era caliente de verdad?
tramo_en_clip = np.zeros(len(calor), dtype=bool)              # True si algún clip entregado toca ese tramo
for c in clips_v1:                                            # para cada clip...
    tramo_en_clip[int(c[0] // 35): int(c[1] // 35) + 1] = True   # ...marcamos los tramos que cubre
real = calor > 0.5                                            # ¿el tramo es realmente caliente?
TP = int((tramo_en_clip & real).sum())                        # clip en tramo caliente (acierto)
FP = int((tramo_en_clip & ~real).sum())                       # clip en tramo frío (falsa alarma)
FN = int((~tramo_en_clip & real).sum())                       # tramo caliente que no cubrimos
TN = int((~tramo_en_clip & ~real).sum())                      # tramo frío que no elegimos (correcto)
print(f"matriz: TP={TP} FP={FP} FN={FN} TN={TN} -> casi todos son TN porque 'lo caliente' es raro (~1-2 % del video)")

# =====================================================================================================
# DIAPOSITIVAS 21-22 · LAS CUATRO FORMAS DE PUNTUAR: AZAR, V0, V1, R0
# =====================================================================================================
titulo("DIAP. 21-22 · Azar vs V0 vs V1 (y R0 como referencia)")
cortos = cand[cand.dur <= MAX_CLIP_S].index.to_numpy()        # candidatos de 45 s o menos
res = {"Azar": [], "V0": [], "V1": []}                        # aciertos por método
for _ in range(200):                                          # repetimos el experimento con 200 calendarios de zonas calientes distintos
    calor_s = rng.uniform(0, 0.5, size=len(calor))            # nueva curva de calor sintética
    for c in rng.choice(len(calor_s), size=4, replace=False): # 4 picos nuevos
        calor_s[c] = 0.8                                      # picos calientes
    zonas = [(i * 35.0, (i + 1) * 35.0) for i, h in enumerate(calor_s) if h > 0.5]   # zonas de esta repetición
    azar = rng.choice(cortos, size=TOP_K, replace=False)      # AZAR: 5 clips elegidos al azar (la línea base)
    res["Azar"].append(acierto_5([(cand.loc[i].start, cand.loc[i].end) for i in azar]))   # lo calificamos
    res["V0"].append(acierto_5([(cand.loc[i].start, cand.loc[i].end) for i in top_v0]))   # V0: fórmula de 17 variables
    res["V1"].append(acierto_5(clips_v1))                     # V1: V0 + clips <= 45 s + banderas 0/1
print("Mecánica ejecutada (Azar, V0 y V1 calificados con acierto@5 sobre curvas inventadas).")   # con valores inventados los % NO significan nada, por eso no se imprimen
print("Resultados REALES (93 videos nuevos): Azar 26.9 % | V0 47.3 % | V1 54.8 % | R0 62.4 %  (ver main.py resultados)")

# =====================================================================================================
# DIAPOSITIVA 16 · ÁRBOL DE DECISIÓN Y LIGHTGBM (LambdaRank) = R0
# =====================================================================================================
titulo("DIAP. 16 · R0: LightGBM con LambdaRank (un árbol que aprende a ORDENAR, no a clasificar)")
# Idea: en la fórmula yo elijo los pesos; en R0 el modelo aprende solo qué variables y combinaciones importan.
# Un árbol hace preguntas "si variable X >= umbral -> izquierda, si no -> derecha" hasta llegar a una HOJA con un número.
# LightGBM suma cientos de árboles chicos; cada uno corrige el error del anterior. LambdaRank lo entrena para que el
# ORDEN de los 5 primeros sea correcto (no el valor exacto), y un video = un grupo: solo compara clips del mismo video.
try:                                                          # LightGBM es opcional: si no está instalado, saltamos esta parte
    import lightgbm as lgb                                    # librería de árboles con boosting
    X = pct.to_numpy()                                        # entrada: los percentiles dentro del video
    y = (rng.random(len(X)) < 0.05).astype(int)               # etiqueta inventada: 5 % de candidatos "calientes" (en real: curva de calor 0-4)
    modelo = lgb.train(dict(objective="lambdarank", metric="ndcg", learning_rate=0.05, num_leaves=15,   # 15 hojas máx. por árbol
                            min_data_in_leaf=50, verbose=-1, seed=42),                                   # mín. 50 filas por hoja; semilla fija
                       lgb.Dataset(X, y, group=[len(X)]), num_boost_round=50)                            # 1 video = 1 grupo; 50 árboles
    print(f"entrenado con {len(X)} candidatos de 1 video de juguete; pre-entrenado NO: se entrena desde cero con nuestros 444 videos")
except ImportError:                                               # si no hay LightGBM...
    print("(LightGBM no instalado: esta parte se omite; el entrenamiento real está en scripts/ y models/)")
print("Resultado real de R0: 62.4 % de acierto en 93 videos nuevos, pero medido en tramos de ~35 s; no es lo mismo que en ventanas de producto.")

# =====================================================================================================
# DIAPOSITIVAS 16 y 18 · CAMPEÓN / RETADOR (agente automático de mejora continua)
# =====================================================================================================
titulo("DIAP. 16 y 18 · Campeón y retador: una variante nueva solo reemplaza al campeón si lo supera")
campeon = 0.588                                               # puntaje del campeón actual (LightGBM, NDCG/acierto en validación cruzada)
for ronda in range(1, 6):                                     # el agente probó 73 rondas; aquí simulamos 5
    retador = campeon + rng.normal(0, 0.01)                   # el retador es una variante con otro conjunto de variables o parámetros
    if retador > campeon + 0.01:                              # SOLO se promueve si supera al campeón por un margen mínimo (evita falsos avances)
        campeon = retador                                     # nuevo campeón
        print(f"  ronda {ronda}: retador {retador:.3f} > campeón -> PROMOVIDO (nuevo clip campeón)")
    else:                                                     # si no lo supera...
        print(f"  ronda {ronda}: retador {retador:.3f} <= campeón -> descartado")
print("Real: el agente corrió 73 rondas y más de 12 000 evaluaciones; la promoción se decide con datos de validación, y lo promovido se confirma luego en videos nuevos.")

# =====================================================================================================
# DIAPOSITIVA 23 · REDES NEURONALES VS R0 (todas entrenadas DESDE CERO, no pre-entrenadas)
# =====================================================================================================
titulo("DIAP. 23 · Redes neuronales vs árbol (validación cruzada, 444 videos, acierto@5)")
tabla = pd.DataFrame({                                        # resultados reales del experimento inicial
    "modelo": ["Azar", "V0 (17 variables)", "LightGBM (R0)", "BiGRU 128", "BiGRU 64 + contraste", "TCN", "Transformer"],
    "acierto@5": ["32.8 %", "53.4 %", "58.8 %", "54.7 %", "55.2 %", "53-55 %", "53-55 %"],   # lo que sale en la diapositiva
    "F1": [0.055, 0.121, 0.130, 0.121, 0.117, 0.113, 0.114]})  # F1 temporal de cada uno
print(tabla.to_string(index=False))                           # imprimimos la tabla tal cual el PPT
print("Conclusión: con ~444 videos las redes no superan al árbol (pocos datos, etiqueta ruidosa). Se piensa retomarlas con más datos y visión.")

titulo("FIN · Para ver las fórmulas de las 71 variables:  python main.py variables   |   python main.py variable a_pause_ratio")
