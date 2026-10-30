"""Arma Articulo_Investigacion_CIS2026_v13.docx desde la v12 aplicando las correcciones de la profesora (sin tocar v11 ni v12).

Cambios: marco teórico ampliado y con arquitecturas, sección 4.9 (aprendizaje profundo que explora ecuaciones) con pseudocódigo,
hiperparámetros reales de los modelos de secuencia (sustituyen los [COMPLETAR]), entorno y bitácora actualizados, resultados de los modelos
de secuencia, discusión/conclusiones/trabajos futuros al día y la referencia de las redes de ecuaciones.
"""
import copy
import sys
from pathlib import Path

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v12.docx")
DST = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v13.docx")
d = docx.Document(str(SRC))


def paras():
    return d.paragraphs


def find(start, after=0):
    for i, p in enumerate(paras()):
        if i >= after and p.text.strip().startswith(start):
            return i
    raise KeyError(start)


def set_text(p, text):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)


def clone_after(anchor_p, tpl_p, text):
    el = copy.deepcopy(tpl_p._p)
    anchor_p._p.addnext(el)
    p = docx.text.paragraph.Paragraph(el, anchor_p._parent)
    set_text(p, text)
    return p


def clone_before(anchor_p, tpl_p, text):
    el = copy.deepcopy(tpl_p._p)
    anchor_p._p.addprevious(el)
    p = docx.text.paragraph.Paragraph(el, anchor_p._parent)
    set_text(p, text)
    return p


# plantillas de formato
HEAD = paras()[find("3.6 ")]
BODY = paras()[find("3.6 ") + 1]
ALG_T = paras()[find("Algoritmo 3.")]
ALG_L = paras()[find("Algoritmo 3.") + 2]

# ---------------------------------------------------------------- Introducción: contribución (v)
p = paras()[find("Para cerrar esta brecha")]
t = p.text.replace(
    "; y (iv) un resultado negativo documentado, pues modelos más complejos no mejoraron de forma confirmada a la fórmula sencilla.",
    "; (iv) un resultado negativo documentado, pues modelos más complejos no mejoraron de forma confirmada a la fórmula sencilla; y (v) un explorador "
    "automático de ecuaciones basado en aprendizaje profundo que propone fórmulas legibles y las somete al mismo protocolo de validación.")
assert t != p.text
set_text(p, t)

# ---------------------------------------------------------------- Marco teórico
p = paras()[find("La transcripción con marcas de tiempo")]
clone_after(p, BODY, (
    "Whisper convierte el audio en trozos de 30 segundos representados como espectrogramas log-Mel, los procesa con un codificador transformer y genera el texto con un "
    "decodificador autorregresivo que, mediante símbolos especiales, indica el idioma, la tarea y las marcas de tiempo (Radford et al., 2023). Esta propiedad permite "
    "transcribir de una sola vez videos en español y en inglés sin entrenar un modelo por idioma y es la razón por la que el pipeline parte de su salida."))

p = paras()[find("En lugar de predecir un valor absoluto")]
clone_after(p, BODY, (
    "LightGBM construye un conjunto de árboles de decisión de forma secuencial, de modo que cada árbol corrige los errores del anterior. A diferencia de otras "
    "implementaciones, agrupa los valores de cada variable en histogramas para buscar los cortes y hace crecer el árbol por hojas, expandiendo siempre la hoja con mayor "
    "ganancia, lo que reduce el costo de memoria y de cómputo (Ke et al., 2017). En el aprendizaje de ranking cada grupo de consulta aporta pares de elementos con "
    "relevancias distintas; LambdaRank multiplica el gradiente de cada par por el cambio que produciría en el NDCG intercambiar sus posiciones, de modo que el modelo "
    "concentra su esfuerzo en ordenar bien la parte alta de la lista (Burges, 2010). El NDCG@k suma la relevancia de los primeros k elementos descontada por el "
    "logaritmo de su posición y la divide por el valor máximo posible, por lo que vale 1 cuando el orden es perfecto."))

p = paras()[find("Para modelar el contexto temporal")]
clone_after(p, BODY, (
    "En una GRU, la compuerta de actualización decide cuánto del estado anterior se conserva y la compuerta de reinicio cuánto se olvida al calcular el nuevo estado "
    "candidato (Cho et al., 2014); en la versión bidireccional se ejecutan dos redes, una hacia adelante y otra hacia atrás, y se concatenan sus estados para cada "
    "tramo (Schuster & Paliwal, 1997). Una red convolucional temporal apila convoluciones sobre el eje del tiempo, y al dilatarlas amplía cuántos tramos vecinos "
    "influyen en cada salida sin aumentar el número de parámetros por capa (Lea et al., 2017). En el transformer de detección de momentos destacados, la atención "
    "relaciona cada tramo con todos los demás y se combina con una capa convolucional que aporta información de orden local (Liu et al., 2022). Estos tres "
    "modelos reciben la secuencia de variables de un video y emiten un puntaje por tramo, por lo que son el contrapeso de aprendizaje profundo del ranker de árboles."))

p = paras()[find("La explicabilidad del puntaje")]
clone_after(p, BODY, (
    "Las métricas siguen el protocolo de evaluación de los conjuntos con curva de re-reproducción (Sul et al., 2023; Park et al., 2025): la curva se corrige igualando el "
    "primer tramo al segundo y se consideran momentos destacados los tramos con valor mayor a 0.5, hasta un máximo de 20 por video. El acierto@5 vale 1 cuando al menos "
    "uno de los cinco clips elegidos se solapa con un momento destacado. El F1 temporal compara el tiempo cubierto por los clips con el tiempo de los momentos "
    "destacados mediante la precisión y la cobertura. El cociente de calor mide cuánto más alta es la re-reproducción media de los clips que la del video completo."))

# 3.7 Redes de ecuaciones (nueva subsección antes de "4. METODOLOGÍA")
i4 = find("4. METODOLOGÍA")
h = clone_before(paras()[i4], HEAD, "3.7 Redes de ecuaciones y exploración automática de fórmulas")
clone_before(paras()[i4], BODY, (
    "Una red de ecuaciones (Equation Learner) sustituye las activaciones habituales por unidades con significado algebraico, como la identidad, el seno o el producto "
    "de dos combinaciones lineales, y añade una penalización L1 que lleva a cero los pesos poco útiles; después del entrenamiento, la red podada se lee como una "
    "expresión cerrada y no como una caja negra (Sahoo et al., 2018). Esto la hace adecuada para un sistema que debe ser auditable, porque combina la capacidad de "
    "aprender relaciones no lineales con una fórmula que el editor puede inspeccionar. En este trabajo la red se adapta con unidades identidad, tangente "
    "hiperbólica, producto y cuadrado, y se entrena con una pérdida de ranking por listas sobre el calor de cada video."))

# ---------------------------------------------------------------- 4.6 [COMPLETAR] -> hiperparámetros reales
p = paras()[find("[COMPLETAR por el autor: dimensión oculta")]
set_text(p, (
    "Configuración de los modelos de secuencia: cada modelo proyecta las variables a una dimensión oculta de 64 o 128 unidades con una capa lineal, activación GELU y "
    "dropout de 0.1 o 0.3. La BiGRU usa una capa bidireccional; la TCN, tres convoluciones de núcleo 3 con dilataciones 1, 2 y 4 y conexiones residuales; y el Transformer, "
    "una convolución de núcleo 5 seguida de dos capas de atención con cuatro cabezas y dimensión de la red intermedia igual al doble de la oculta, sin codificación posicional "
    "absoluta para que el modelo no aprenda la posición en el video. La salida es una capa lineal por tramo. Se entrenaron 40 épocas con lotes de 16 videos, optimizador AdamW "
    "(tasa de aprendizaje de 0.002 con programación de ciclo único y decaimiento de pesos de 0.01) y recortes aleatorios de 40 tramos; en la inferencia se promedian las "
    "ventanas deslizantes. La pérdida fue el error cuadrático medio sobre el calor estandarizado por video o la entropía cruzada de ranking por listas (ListNet), según la configuración."))

# ---------------------------------------------------------------- 4.9 Exploración automática de ecuaciones
i5 = find("5. EXPERIMENTACIÓN")
anchor = paras()[i5]
clone_before(anchor, HEAD, "4.9 Exploración automática de ecuaciones con aprendizaje profundo")
clone_before(anchor, BODY, (
    "Para que el criterio de puntuación no dependa solo de una fórmula elegida a mano, se añadió una etapa de aprendizaje profundo que explora por sí misma nuevas "
    "formas de la ecuación. El explorador entrena redes de ecuaciones sobre los percentiles de las 17 variables de la fórmula V0 (Sahoo et al., 2018). En cada ronda "
    "sortea 12 configuraciones (ancho de cada tipo de unidad, profundidad de una o dos capas, intensidad de la penalización L1 y tasa de aprendizaje), las evalúa con "
    "validación cruzada interna de tres particiones agrupadas por canal dentro del conjunto de entrenamiento y entrena la mejor con tres semillas. El resultado se compara "
    "una sola vez con el campeón vigente en un conjunto de videos reservado por canal; el retador se promueve solo si mejora el F1 con una prueba de Wilcoxon de p menor "
    "que 0.05, y cada ronda queda registrada con su ecuación (Algoritmo 4)."))
clone_before(anchor, ALG_T, "Algoritmo 4. Exploración automática de ecuaciones (campeón/retador)")
for line in [
    "Entrada: percentiles X de 17 variables por ventana, calor y por video, canal c(v), campeón C",
    "Salida: ecuación aprendida, decisión de promoción",
    "1. separar un holdout congelado por canal; el resto es entrenamiento",
    "2. sortear 12 configuraciones θ (unidades, profundidad, λ de L1, tasa de aprendizaje)",
    "3. para cada θ: F1 de validación cruzada interna (3 particiones por canal) del entrenamiento",
    "4. θ* ← configuración con mayor F1 interno; entrenar EQL(θ*) con 3 semillas",
    "5. podar pesos pequeños y escribir la ecuación resultante",
    "6. evaluar EQL y el campeón C en el holdout (acierto@5 y F1 por video)",
    "7. si F1(EQL) > F1(C) y Wilcoxon unilateral p < 0.05: C ← EQL; registrar la ronda",
]:
    clone_before(anchor, ALG_L, line)

# ---------------------------------------------------------------- 5.1 / 5.3 / 5.6
p = paras()[find("Todos los experimentos se ejecutaron")]
set_text(p, p.text.replace("Todos los experimentos se ejecutaron", "Los experimentos hasta las cohortes frescas se ejecutaron", 1) + (
    " Las pruebas posteriores a las cohortes frescas (ampliación del conjunto, variables de frontera, ciclo campeón/retador y exploración de ecuaciones) se ejecutaron en una "
    "segunda computadora con procesador Intel Core i5-7400 (3.00 GHz), 16 GB de RAM y una GPU NVIDIA GeForce RTX 3060 de 12 GB, también bajo Windows 10 y Python 3.11, "
    "con PyTorch 2.11 y CUDA 12.8 para las redes."))
p = paras()[find("El modelo de aprendizaje de referencia (R0) es LightGBM")]
set_text(p, p.text + (
    " Las redes de ecuaciones usan 17 entradas, entre 4 y 16 unidades de cada tipo (identidad, tangente hiperbólica, producto y cuadrado), una o dos capas y penalización L1 "
    "de 0.0001 a 0.003 con calentamiento durante el primer 30 % de las épocas; se entrenan 60 épocas con AdamW, lotes de 16 videos y tasas de aprendizaje de 0.003 o 0.01."))
p = paras()[find("El código, la fórmula con sus pesos")]
assert "73 entradas" in p.text
set_text(p, p.text.replace("73 entradas", "87 entradas"))

# ---------------------------------------------------------------- 6.3 [COMPLETAR] -> números reales
p = paras()[find("Además de la fórmula y de LightGBM, se evaluaron")]
i0 = p.text.index("[COMPLETAR")
set_text(p, p.text[:i0] + (
    "En el desarrollo (444 videos, 10 particiones por canal), la BiGRU de 128 unidades alcanzó 54.7 % de acierto@5 y F1 de 0.121, frente a 58.8 % y 0.130 de LightGBM por "
    "tramo; la TCN y el Transformer quedaron entre 53 y 55 % y F1 de 0.113 a 0.114, y ninguna de las 12 configuraciones superó a la fórmula V0 (p mayor que 0.2). En la cohorte "
    "fresca 1, la BiGRU acertó en 53.8 % de los videos con F1 de 0.129, frente a 62.4 % y 0.142 de LightGBM (p = 0.15 en F1)."))

# ---------------------------------------------------------------- 7 Discusión, 8 Conclusiones, 9 Trabajos futuros
p = paras()[find("Las limitaciones del estudio son las siguientes")]
clone_before(p, BODY, (
    "Las pruebas posteriores refuerzan esa lectura. Con 83 videos nuevos de 82 canales, la mezcla del ranker con un submodelo de 17 variables no mejoró (p = 0.37), y la "
    "curva de aprendizaje indica que cada duplicación de los datos suma cerca de un punto de acierto, de modo que 10 000 videos llegarían solo a cerca de 57 %. Por tanto, "
    "alcanzar valores mucho mayores con audio y texto exigiría una señal nueva y no solo más datos. La red de ecuaciones igualó en F1 a LightGBM con una ecuación de 17 "
    "variables y términos cuadráticos, es decir, una relación no monótona que la fórmula lineal no expresa; como su ventaja no fue significativa, se mantiene como hallazgo "
    "interpretable y no como reemplazo, y queda pendiente su confirmación en una cohorte fresca."))
p = paras()[find("Este trabajo propuso un pipeline abierto")]
set_text(p, p.text + (
    " Un explorador de ecuaciones basado en aprendizaje profundo alcanzó el mismo F1 que LightGBM con una fórmula legible de 17 variables, sin superarlo de forma significativa, "
    "y las pruebas posteriores con 83 videos nuevos no mostraron mejoras confirmadas."))
p = paras()[find("Primero, se ampliará el conjunto")]
set_text(p, (
    "Primero, se continuará ampliando el conjunto de podcasts y se incorporará el conjunto Rhapsody, con unos 13 000 episodios, para evaluar si los modelos de secuencia y "
    "las redes de ecuaciones superan al ranker de árboles con mayor tamaño de muestra (Park et al., 2025). Segundo, se confirmará en una cohorte fresca la ecuación aprendida "
    "por el explorador y se repetirán sus rondas con otras configuraciones. Tercero, se entrenará el ranker directamente con los clips de curación humana de Repurpose-10K, que "
    "requiere más videos con etiqueta humana, para contrastar ambas etiquetas (Wu et al., 2025). Cuarto, dado que en un podcast la imagen cambia poco, el análisis visual se "
    "reservará para otros géneros y se evaluará bajo el mismo protocolo (Liu et al., 2022; Kwak et al., 2025). Quinto, se diseñará un prototipo del sistema como servicio para "
    "creadores y empresas de contenido y se contrastará la selección con el mapa de calor de retención en cohortes nuevas con hipótesis previa."))

# ---------------------------------------------------------------- Referencias
p = paras()[find("Radford, A., Kim, J. W.")]
set_text(p, p.text.rstrip() + " https://proceedings.mlr.press/v202/radford23a.html")
p_s = paras()[find("Schuster, M., & Paliwal")]
clone_before(p_s, p, "Sahoo, S., Lampert, C., & Martius, G. (2018). Learning equations for extrapolation and control. Proceedings of Machine Learning Research, 80, 4442–4450. "
                     "https://proceedings.mlr.press/v80/sahoo18a.html")

d.save(str(DST))
d2 = docx.Document(str(DST))
txt = "\n".join(p.text for p in d2.paragraphs)
print("guardado:", DST, "| párrafos:", len(d2.paragraphs))
print("quedan [COMPLETAR]:", txt.count("[COMPLETAR"))
for k in ("3.7 ", "4.9 ", "Algoritmo 4.", "Sahoo, S."):
    print(k, "->", k in txt)
