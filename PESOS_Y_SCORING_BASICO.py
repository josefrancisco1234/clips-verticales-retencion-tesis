"""PESO POR VARIABLE Y PUNTAJE, SUPER BÁSICO (para explicarlo en 2 minutos).

Idea en una frase:
    cada clip tiene variables (pausas, volumen, preguntas...). Cada variable tiene un PESO que dice cuánto ayuda (+) o
    estorba (-). Si el clip destaca en una variable, se enciende una bandera y se suma su peso. El total se lleva a 0-99.

Usa solo 5 de las 17 variables y 6 clips de un video de juguete, pero los pesos son los reales de la fórmula.

    python PESOS_Y_SCORING_BASICO.py
"""
import sys                                                       # para imprimir tildes en la consola de Windows

import numpy as np                                               # cuentas con arreglos
import pandas as pd                                              # tablas para mostrar cada paso

sys.stdout.reconfigure(encoding="utf-8", errors="replace")       # consola en UTF-8

# ---------------------------------------------------------------------------------------------------------------------
# PASO 0 · LOS PESOS (la "receta"). Salen de models/formula_calor_D045.json: se calcularon UNA vez con 121 videos
#          viendo qué variables se parecen a los tramos que la gente re-ve, y desde entonces están congelados.
# ---------------------------------------------------------------------------------------------------------------------
PESOS = {
    "a_pause_ratio": +0.1797,   # tiempo en pausas / duración: peso POSITIVO, los clips con pausas dramáticas suelen engancharse
    "a_rms_std": +0.1218,       # cuánto varía el volumen: positivo, gritar/susurrar da énfasis
    "s_questions_pm": +0.0582,  # preguntas por minuto: positivo, una pregunta engancha
    "a_voiced_ratio": -0.1071,  # fracción de tiempo con voz: NEGATIVO, hablar sin parar sin respirar resta
    "a_speech_rate": -0.0976,   # palabras por segundo: NEGATIVO, ir muy rápido resta
}
print("PESOS (+ suma, - resta):", PESOS)                         # los mostramos tal cual

# ---------------------------------------------------------------------------------------------------------------------
# PASO 1 · LOS DATOS: 6 clips candidatos de UN video, con el valor medido de cada variable.
# ---------------------------------------------------------------------------------------------------------------------
valores = pd.DataFrame({                                         # una fila por clip, una columna por variable
    "a_pause_ratio":  [0.05, 0.30, 0.12, 0.22, 0.08, 0.15],      # clip B tiene muchas pausas, clip A casi ninguna
    "a_rms_std":      [0.9, 1.8, 1.1, 1.6, 0.7, 1.3],            # variación de volumen de cada clip
    "s_questions_pm": [0.0, 3.0, 1.0, 0.5, 2.0, 0.0],            # preguntas por minuto
    "a_voiced_ratio": [0.95, 0.70, 0.90, 0.75, 0.92, 0.85],      # fracción con voz
    "a_speech_rate":  [3.4, 2.2, 3.0, 2.5, 3.2, 2.8],            # palabras por segundo
}, index=list("ABCDEF"))                                         # los clips se llaman A a F
print("\nPASO 1 · valores medidos de cada clip:\n", valores)

# ---------------------------------------------------------------------------------------------------------------------
# PASO 2 · PERCENTIL: ¿en qué lugar queda cada clip COMPARADO CON LOS OTROS DE SU VIDEO? (0 a 1)
#          1.0 = el mayor valor del video en esa variable; ~0.17 = el menor (con 6 clips, 1/6).
#          Se compara solo dentro del video: un video callado y uno gritón quedan en la misma escala.
# ---------------------------------------------------------------------------------------------------------------------
percentil = valores.rank(pct=True)                               # rank(pct=True) = posición ÷ cantidad de clips
print("\nPASO 2 · percentil dentro del video:\n", percentil.round(2))

# ---------------------------------------------------------------------------------------------------------------------
# PASO 3 · BANDERA: 1 si el clip está en el 25 % más alto de esa variable (percentil >= 0.75), 0 si no.
#          Así solo cuentan las variables en las que el clip DESTACA; el resto no mete ruido.
# ---------------------------------------------------------------------------------------------------------------------
bandera = (percentil >= 0.75).astype(int)                        # True/False pasado a 1/0
print("\nPASO 3 · bandera (1 = destaca):\n", bandera)

# ---------------------------------------------------------------------------------------------------------------------
# PASO 4 · PESO x BANDERA: cada bandera encendida aporta su peso (con su signo).
# ---------------------------------------------------------------------------------------------------------------------
aporte = bandera * pd.Series(PESOS)                              # multiplica cada columna por el peso de su variable
print("\nPASO 4 · aporte = peso x bandera:\n", aporte.round(4))

# ---------------------------------------------------------------------------------------------------------------------
# PASO 5 · SUMA PONDERADA: el puntaje crudo ("raw") de cada clip es la SUMA de sus aportes. No es un promedio.
# ---------------------------------------------------------------------------------------------------------------------
raw = aporte.sum(axis=1)                                         # suma de la fila: peso1xbandera1 + peso2xbandera2 + ...
print("\nPASO 5 · raw (suma de aportes):\n", raw.round(4))

# ---------------------------------------------------------------------------------------------------------------------
# PASO 6 · ESCALA 0-99: se compara con lo PEOR y lo MEJOR que se podría sacar con estos pesos.
#          Peor posible = solo las banderas negativas encendidas; mejor posible = solo las positivas encendidas.
#          En el sistema real son 17 variables: mínimo -0.4851 y máximo +1.2400; aquí son 5.
# ---------------------------------------------------------------------------------------------------------------------
pesos = np.array(list(PESOS.values()))                           # los 5 pesos en un arreglo
minimo = pesos[pesos < 0].sum()                                  # suma de los pesos negativos (el peor caso)
maximo = pesos[pesos > 0].sum()                                  # suma de los pesos positivos (el mejor caso)
puntaje = ((raw - minimo) / (maximo - minimo) * 99).round().clip(0, 99).astype(int)   # (raw - mín) / (máx - mín) x 99
print(f"\nPASO 6 · mínimo posible {minimo:+.4f}, máximo posible {maximo:+.4f}")
print("puntaje final 0-99:\n", puntaje)

# ---------------------------------------------------------------------------------------------------------------------
# PASO 7 · ORDENAR: el mejor puntaje va primero; esos son los clips que se entregan (en el real, además, <= 45 s y sin
#          traslape entre clips).
# ---------------------------------------------------------------------------------------------------------------------
print("\nPASO 7 · ranking (mejor primero):")                      # encabezado del resultado
for clip, pts in puntaje.sort_values(ascending=False).items():   # recorremos de mayor a menor puntaje
    encendidas = [v for v in PESOS if bandera.loc[clip, v] == 1]  # variables en las que ese clip destacó
    print(f"  clip {clip}: puntaje {pts:>2} | banderas en 1: {', '.join(encendidas) or 'ninguna'}")   # y por qué

# ---------------------------------------------------------------------------------------------------------------------
# PARA ENTENDER EL PESO: ¿qué pasa si cambio uno?  Subimos a_pause_ratio al doble y vemos cómo cambia el orden.
# ---------------------------------------------------------------------------------------------------------------------
pesos2 = dict(PESOS, a_pause_ratio=PESOS["a_pause_ratio"] * 2)   # copia de los pesos con uno duplicado
raw2 = (bandera * pd.Series(pesos2)).sum(axis=1)                 # mismo cálculo con el peso nuevo
print("\nSi a_pause_ratio pesara el doble, el orden sería:", list(raw2.sort_values(ascending=False).index))
print("Conclusión: el PESO decide cuánto pesa una variable; la BANDERA decide si el clip la 'merece'.")
