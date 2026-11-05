"""MAIN: punto de entrada único para sustentar el código. Todo lo que sale en el PPT se encuentra aquí o está enlazado desde aquí.

Cómo usarlo (desde la carpeta tesis/desarrollo, con el entorno de la tesis):
    python main.py mapa                     qué diapositiva del PPT corresponde a qué parte del código
    python main.py variables                las 73 variables (71 del modelo + 2 de posición) con su fórmula y su peso
    python main.py variable a_pause_ratio   fórmula de UNA variable, su peso, su referencia y la línea de código donde se calcula
    python main.py puntaje                  el ejemplo de la diapositiva 17 paso a paso: percentil -> bandera -> suma ponderada -> 0-99
    python main.py metricas                 acierto@5, precisión, cobertura y F1 temporal con un ejemplo pequeño
    python main.py resultados               de dónde sale cada cifra del PPT (script y archivo de resultados)
    python main.py verificar                comprueba que las cifras del PPT coinciden con los archivos del proyecto
    python main.py clips VIDEO              el pipeline completo: de un video largo a 5 clips 9:16 con puntaje (ver PIPELINE_COMPLETO.py)

Cada bloque importante lleva un comentario "# <- ..." que explica qué hace esa línea, para poder leerlo mientras se muestra.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent                       # <- carpeta tesis/desarrollo, base de todas las rutas
FORMULA = ROOT / "models" / "formula_calor_D045.json"        # <- pesos congelados de las 17 variables de la fórmula
BANDERA_P = 0.75                                             # <- umbral de la bandera: percentil >= 0.75 = 25 % más alto del video
ESCALA = 99                                                  # <- el puntaje final va de 0 a 99

# ==============================================================================================================
# 1. MAPA PPT -> CÓDIGO   (python main.py mapa)
# ==============================================================================================================
MAPA_PPT = [
    # (diapositivas, tema, dónde está en el código)
    ("3",      "Mapa de calor Most Replayed",         "src/ingest/youtube.py:fetch_metadata (descarga la curva); src/ranking/labels.py:corrected_graph (corrige el bin 0)"),
    ("7",      "Marco teórico: Whisper, PANNs",       "src/transcribe/whisper.py:transcribe; src/features/extra.py:audio_events (PANNs)"),
    ("8-11",   "Metodología: ETL y dataset",          "scripts/ampliar_dataset_D050.py, acquire_worker_D050.py (búsqueda, descarga, transcripción, variables); src/data/youtube_dataset.py"),
    ("12",     "Audio frente a transcripción",        "scripts/figura_audio_vs_transcripcion.py (listas AUDIO, TIEMPOS, TEXTO y su peso)"),
    ("13-14",  "Creación del clip, capítulos, cortes", "src/segment/candidates.py:sentence_candidates, nms; src/segment/chapters.py; src/pipeline.py:breathing_margin, snap_to_cuts"),
    ("15, 17", "Cómo se calcula el puntaje",          "main.py sección 3 (percentil_en_video, bandera, suma_ponderada, escala_0_99, puntaje_clip)"),
    ("16",     "Árbol de decisión, LightGBM, campeón/retador", "scripts/figura_arbol_decision.py; scripts/confirmacion_fresca_final_D063.py (R0, parámetros P); scripts/campeon_retador.py"),
    ("18",     "Mejora continua",                     "scripts/minero_papers.py, explorador_ecuaciones.py, auto_mejora.py, auto_mejora_nn.py, campeon_retador.py"),
    ("19",     "Métricas",                            "main.py sección 4 (acierto_5, precision_cobertura_f1); scripts/reverse_engineering_formula.py:f1_temporal, top_k_nms"),
    ("20",     "Datos, entorno y protocolo",          "reports/conjunto_desarrollo_D038.json, conjunto_confirmacion_fresca_D050.json, conjunto_confirmacion_fresca2_D065.json"),
    ("21-22",  "Cuatro formas de puntuar",            "scripts/replicar_fresca_D050.py (azar, V0, V1 en el grupo nuevo 1); scripts/confirmacion_fresca_final_D063.py (R0)"),
    ("23",     "Redes neuronales frente a R0",        "scripts/dl_secuencia_D054.py (clase Net: BiGRU, TCN, Transformer); scripts/replicar_dl_fresca_D054.py"),
    ("24-25",  "Resultados y F1",                     "scripts/confirm_V1_D048.py (V1 en 352), scripts/r0_en_confirmacion_D102.py (R0 en 352)"),
    ("26",     "Matriz de confusión",                 "scripts/tabla_clases_D099.py (cifras) y scripts/matriz_azul_D099.py (figura)"),
    ("27",     "Exploración automática",              "scripts/campeon_retador.py, auto_mejora.py, auto_mejora_nn.py -> reports/campeon_retador, auto_mejora, auto_mejora_nn"),
    ("28",     "Validación con creadores (SUS)",      "scripts/rellenar_validacion_v45.py; cuestionario en ENTREGA_NOTA2_FINAL/6_Consentimientos_informados"),
    ("web",    "Página web y demo",                   "scripts/web_clips.py (servidor), web_assets/, python PIPELINE_COMPLETO.py (mismo flujo en consola)"),
]

# ==============================================================================================================
# 2. CATÁLOGO DE VARIABLES   (python main.py variables | variable NOMBRE)
#    nombre: (grupo, qué mide, fórmula exacta).  Se calcula en src/features/builder.py (K,S,A,H,F,L,E,P)
# ==============================================================================================================
VARIABLES = {
    # K: palabras clave
    "k_kvsum_mean": ("K", "peso medio de los términos de contenido", "promedio(peso_KVSUM[t]) para cada término de contenido t de la ventana"),
    "k_kvsum_max": ("K", "término más pesado", "máx(peso_KVSUM[t])"),
    "k_kvsum_local": ("K", "peso del término dentro de su pasaje", "suma(peso del término en su pasaje de passage_s s) / n_palabras"),
    "k_top_terms_pm": ("K", "términos clave del video por minuto", "n_términos_de_contenido_que_son_top_del_video / minutos"),
    "k_content_ratio": ("K", "proporción de palabras de contenido", "n_términos_de_contenido / n_palabras"),
    "k_novelty": ("K", "novedad respecto de los 300 s previos", "1 - promedio(visto_antes); visto_antes = 1 si el término apareció en los 300 s anteriores"),
    "k_keybert_sim": ("K", "cercanía de la ventana al tema del video", "coseno(media normalizada de embeddings de las oraciones, embedding del documento)"),
    "k_keyphrase_pm": ("K", "frases clave KeyBERT por minuto", "suma(apariciones de cada keyphrase en el texto) / minutos"),
    "k_noun_chunks_ps": ("K", "densidad de sustantivos", "promedio de frases nominales (spaCy) por oración"),
    # S: sentimiento y estilo del texto
    "s_pos_mean": ("S", "positividad media", "promedio de P(positivo) de las oraciones (modelo de sentimiento)"),
    "s_neg_mean": ("S", "negatividad media", "promedio de P(negativo) de las oraciones"),
    "s_polarity_mean": ("S", "polaridad media", "promedio de (P_pos - P_neg)"),
    "s_polarity_std": ("S", "variación de la polaridad", "desviación estándar de (P_pos - P_neg)"),
    "s_intensity_mean": ("S", "intensidad emocional media", "promedio de |P_pos - P_neg|"),
    "s_intensity_max": ("S", "intensidad emocional máxima", "máx |P_pos - P_neg|"),
    "s_questions_pm": ("S", "preguntas por minuto", "(n '?' + n '¿') / minutos"),
    "s_exclaim_pm": ("S", "exclamaciones por minuto", "(n '!' + n '¡') / minutos"),
    "s_second_person": ("S", "habla al público (segunda persona)", "tokens_de_segunda_persona / tokens"),
    "s_first_person": ("S", "habla de sí mismo (primera persona)", "tokens_de_primera_persona / tokens"),
    "s_numbers": ("S", "cifras", "tokens que empiezan con dígito / tokens"),
    "s_intensifiers": ("S", "intensificadores (muy, super...)", "tokens_intensificadores / tokens"),
    "s_hook_words": ("S", "palabras de gancho", "tokens de la lista de gancho / tokens"),
    "s_laughs": ("S", "risas escritas", "n coincidencias de la expresión regular de risa en el texto"),
    # A: audio
    "a_rms_mean": ("A", "volumen medio", "media del RMS en z-score respecto del video"),
    "a_rms_p95": ("A", "picos de volumen", "percentil 95 del RMS z"),
    "a_rms_std": ("A", "dinámica del volumen (susurro vs énfasis)", "desviación estándar del RMS z"),
    "a_pitch_std": ("A", "variación de entonación", "desviación estándar del tono f0 (semitonos) en frames con voz"),
    "a_pitch_range": ("A", "rango de tono", "percentil95(f0) - percentil5(f0)"),
    "a_voiced_ratio": ("A", "voz continua", "fracción de frames con voz"),
    "a_energy_delta": ("A", "subida de energía", "media RMS z de la ventana - media RMS z de los 30 s previos"),
    "a_speech_rate": ("A", "ritmo de habla", "n_palabras / duración en segundos"),
    "a_pause_ratio": ("A", "tiempo en pausas", "suma(huecos entre palabras > 0.3 s) / duración"),
    "a_long_pauses_pm": ("A", "pausas largas por minuto", "n huecos > 1 s / minutos"),
    # H: gancho (primeros segundos)
    "h_rms_onset": ("H", "volumen de arranque", "media del RMS z en los primeros 3 s"),
    "h_question": ("H", "arranca con pregunta", "1 si hay '?' en las primeras palabras o la 1.ª oración termina en '?'"),
    "h_number": ("H", "arranca con cifra", "1 si hay un número en las primeras palabras"),
    "h_second_person": ("H", "arranca hablando al público", "1 si hay segunda persona en las primeras palabras"),
    "h_hook_word": ("H", "arranca con palabra de gancho", "1 si hay palabra de gancho en las primeras palabras"),
    "h_contrast": ("H", "arranca con contraste (pero, sin embargo...)", "1 si hay conector de contraste en las primeras palabras"),
    "h_first_sentence_s": ("H", "duración de la 1.ª oración", "fin - inicio de la primera oración"),
    "h_first_intensity": ("H", "intensidad de la 1.ª oración", "|P_pos - P_neg| de la primera oración"),
    "h_first_keybert": ("H", "tema de la 1.ª oración", "coseno(embedding 1.ª oración, embedding del documento)"),
    # F: fluidez
    "f_starts_dangling": ("F", "empieza colgado (eso, él...)", "1 si la primera palabra es de inicio colgado"),
    "f_ends_complete": ("F", "termina en oración completa", "1 si la última oración está completa"),
    "f_coherence_mean": ("F", "coherencia media", "promedio del coseno entre oraciones consecutivas"),
    "f_coherence_min": ("F", "coherencia mínima", "mínimo de ese coseno"),
    "f_topic_drift": ("F", "cambio de tema", "1 - coseno(media de embeddings 1.ª mitad, media 2.ª mitad)"),
    "f_n_sentences": ("F", "número de oraciones", "s1 - s0"),
    "f_duration": ("F", "duración", "fin - inicio en segundos"),
    "f_filler_rate": ("F", "muletillas", "tokens_muletilla / tokens"),
    "f_word_conf": ("F", "confianza de la transcripción", "promedio de la confianza de Whisper por palabra"),
    # L: lingüística
    "l_entropy": ("L", "variedad léxica", "-suma(p * log2 p) sobre las frecuencias de tokens"),
    "l_type_token": ("L", "riqueza de vocabulario", "tokens_distintos / tokens"),
    "l_pron_12_vs_3": ("L", "diálogo directo frente a terceros", "(pronombres 1.ª+2.ª + 1) / (pronombres 3.ª + 1)"),
    "l_fillers": ("L", "muletillas simples", "muletillas / tokens"),
    "l_silence": ("L", "silencio", "1 - tiempo_hablado / duración"),
    "l_word_len": ("L", "largo de las palabras", "media de letras por palabra"),
    # E: eventos de sonido (PANNs, una probabilidad cada 3 s)
    **{f"e_{c}_{a}": ("E", f"{'máximo' if a == 'max' else 'media'} de P({c}) en la ventana", f"{'máx' if a == 'max' else 'media'} de la probabilidad PANNs de '{c}' en la ventana")
       for c in ("laugh", "applause", "cheering", "music", "speech") for a in ("max", "mean")},
    "e_laugh_frac": ("E", "fracción con risa", "fracción de puntos con P(risa) > 0.2"),
    "e_laugh_tail": ("E", "risa al final del clip", "máx P(risa) en los últimos 6 s"),
    "e_laugh_after": ("E", "risa justo después", "máx P(risa) en los 6 s siguientes"),
    "e_applause_after": ("E", "aplauso justo después", "máx P(aplauso) en los 6 s siguientes"),
    # P: posición (solo ablación; NO entra al modelo)
    "p_rel_pos": ("P", "posición relativa en el video (solo ablación)", "((inicio + fin) / 2) / duración_del_video"),
    "p_rel_pos_sq": ("P", "posición al cuadrado (solo ablación)", "p_rel_pos ** 2"),
}


def cargar_pesos() -> dict[str, float]:
    return json.loads(FORMULA.read_text(encoding="utf-8"))["weights"]      # <- lee las 17 variables y su peso desde el archivo congelado


def linea_de_codigo(nombre: str) -> str:
    """Busca en qué archivo y línea se calcula una variable (para mostrarla en vivo)."""
    for rel in ("src/features/builder.py", "src/features/extra.py"):
        for i, linea in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if re.search(rf"[\"']{re.escape(nombre)}[\"']|\b{re.escape(nombre)}\s*=", linea):   # <- busca f["nombre"] o nombre=
                return f"{rel}:{i}"
    return "src/features/extra.py (se arma con f\"e_{clase}_{max|mean}\")"


def cmd_variables() -> None:
    pesos = cargar_pesos()
    print(f"{len(VARIABLES)} variables en el catálogo (71 del modelo + 2 de posición solo para ablación); {len(pesos)} entran a la fórmula.\n")
    for g in "KSAHFLEP":
        print(f"--- grupo {g} ---")
        for n, (gr, que, formula) in VARIABLES.items():
            if gr == g:
                w = f"peso {pesos[n]:+.4f}" if n in pesos else "no entra a la fórmula"
                print(f"{n:20s} {w:24s} {que}")


def cmd_variable(nombre: str) -> None:
    if nombre not in VARIABLES:
        raise SystemExit(f"variable desconocida: {nombre}")
    g, que, formula = VARIABLES[nombre]
    pesos = cargar_pesos()
    print(f"{nombre}  (grupo {g})\n  qué mide : {que}\n  fórmula  : {formula}")
    print(f"  peso     : {pesos[nombre]:+.4f}" if nombre in pesos else "  peso     : no entra a la fórmula de 17 variables")
    print(f"  se calcula en: {linea_de_codigo(nombre)}")
    fuentes = ROOT / "reports" / "fuentes_71_variables_D099.json"
    if fuentes.exists():
        d = json.loads(fuentes.read_text(encoding="utf-8"))
        if nombre in d["variables"]:
            v = d["variables"][nombre]
            refs = d["refs"]
            citas = lambda ks: "; ".join(f"{refs[k]['autores'][0]} ({refs[k]['anio']})" for k in ks if k in refs) or "-"
            print(f"  definición   : {citas(v.get('definicion', []))}\n  relación     : {citas(v.get('relacion', []))}")


# ==============================================================================================================
# 3. PUNTAJE DE UN CLIP   (python main.py puntaje)   <- diapositivas 16 y 18
#    percentil dentro del video -> bandera 0/1 -> suma ponderada -> escala 0 a 99
# ==============================================================================================================
def percentil_en_video(valores: pd.Series) -> pd.Series:
    """Posición de cada ventana entre las ventanas de SU video: posición / n, de 0 a 1 (la más alta vale 1.0)."""
    return valores.rank(pct=True).fillna(0.5)         # <- rank(pct=True) = posición / n; si falta el dato vale 0.5 (neutro)


def bandera(percentil: pd.Series | float) -> pd.Series | float:
    """1 si la variable está en el 25 % más alto de su video (percentil >= 0.75), 0 si no."""
    return (percentil >= BANDERA_P) * 1.0             # <- compara con 0.75 y devuelve 1.0 o 0.0


def suma_ponderada(banderas: dict[str, float], pesos: dict[str, float]) -> float:
    """raw = suma de peso x bandera. NO es un promedio: no se divide entre nada y un peso negativo resta."""
    return float(sum(pesos[v] * banderas[v] for v in pesos))   # <- cada variable aporta su peso solo si su bandera es 1


def limites(pesos: dict[str, float]) -> tuple[float, float]:
    """Mínimo y máximo posibles del raw: todo lo negativo en 1 (peor clip) y todo lo positivo en 1 (mejor clip)."""
    lo = sum(w for w in pesos.values() if w < 0)      # <- suma de los pesos negativos (-0.4851)
    hi = sum(w for w in pesos.values() if w > 0)      # <- suma de los pesos positivos (+1.2400)
    return lo, hi


def escala_0_99(raw: float, pesos: dict[str, float]) -> int:
    """puntaje = (raw - mín) / (máx - mín) x 99, redondeado y limitado a [0, 99]."""
    lo, hi = limites(pesos)
    return int(np.clip(round((raw - lo) / (hi - lo) * ESCALA), 0, ESCALA))   # <- lleva el raw a la escala fija 0-99


def puntaje_clip(percentiles: dict[str, float], pesos: dict[str, float]) -> tuple[float, int]:
    banderas = {v: float(bandera(percentiles[v])) for v in pesos}   # <- paso 1: percentil -> bandera de cada una de las 17 variables
    raw = suma_ponderada(banderas, pesos)                           # <- paso 2: suma ponderada
    return raw, escala_0_99(raw, pesos)                             # <- paso 3: a la escala 0-99


def cmd_puntaje() -> None:
    """Reproduce el ejemplo real de la diapositiva 17 y comprueba que da raw = +1.0118 y puntaje 86."""
    pesos = cargar_pesos()
    perc = {v: 0.50 for v in pesos}                   # <- las 8 variables que no destacan quedan en el medio (bandera 0)
    perc.update({"a_pause_ratio": 0.8350, "l_silence": 0.8150, "a_long_pauses_pm": 0.9675, "a_rms_std": 0.9625, "k_keybert_sim": 0.7825,
                 "a_pitch_std": 0.8625, "e_music_max": 0.9275, "e_music_mean": 0.9075, "s_questions_pm": 0.7600})   # <- percentiles del ejemplo
    print(f"{'variable':18s} {'percentil':>9s} {'bandera':>8s} {'peso':>8s} {'aporte':>8s}")
    for v, w in pesos.items():
        b = float(bandera(perc[v]))
        print(f"{v:18s} {perc[v]:9.4f} {b:8.0f} {w:+8.4f} {w * b:+8.4f}")
    raw, punt = puntaje_clip(perc, pesos)
    lo, hi = limites(pesos)
    print(f"\nraw = suma de aportes = {raw:+.4f}")
    print(f"mín = {lo:+.4f} | máx = {hi:+.4f} | rango = {hi - lo:.4f}")
    print(f"puntaje = ({raw:.4f} - ({lo:.4f})) / {hi - lo:.4f} x 99 = {(raw - lo) / (hi - lo) * 99:.1f}  ->  {punt}")
    assert abs(raw - 1.0118) < 5e-4 and punt == 86, "el ejemplo del PPT ya no coincide con los pesos guardados"   # <- alarma si algo cambió


# ==============================================================================================================
# 4. MÉTRICAS   (python main.py metricas)   <- diapositiva 19
# ==============================================================================================================
def solape(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))     # <- segundos que comparten dos intervalos


def acierto_5(clips: list[tuple[float, float]], zonas_calientes: list[tuple[float, float]]) -> int:
    """1 si al menos uno de los clips tiene el 50 % o más de su duración dentro de zonas calientes (calor > 0.5)."""
    for c in clips:
        dentro = sum(solape(c, z) for z in zonas_calientes)      # <- segundos del clip que caen en zona caliente
        if dentro >= 0.5 * (c[1] - c[0]):                        # <- ¿es la mitad o más del clip?
            return 1
    return 0


def precision_cobertura_f1(clips, zonas_calientes) -> tuple[float, float, float]:
    t_clips = sum(c[1] - c[0] for c in clips)
    t_caliente = sum(z[1] - z[0] for z in zonas_calientes)
    dentro = sum(solape(c, z) for c in clips for z in zonas_calientes)
    p = dentro / t_clips if t_clips else 0.0                     # <- precisión: del tiempo de mis clips, cuánto era caliente
    r = dentro / t_caliente if t_caliente else 0.0               # <- cobertura: del tiempo caliente del video, cuánto cubrí
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)        # <- F1 = 2PR / (P + R)


def cmd_metricas() -> None:
    zonas = [(60, 120), (300, 360)]                  # <- video de 10 min con 2 min calientes
    clips = [(90, 150), (200, 260), (330, 390)]      # <- 3 clips de 1 min; 60 s caen en zona caliente
    p, r, f1 = precision_cobertura_f1(clips, zonas)
    print(f"acierto@5 del video: {acierto_5(clips, zonas)} (al menos un clip con >= 50 % en zona caliente)")
    print(f"precisión = {p:.2f} | cobertura = {r:.2f} | F1 = {f1:.2f}")
    assert round(f1, 2) == 0.40
    print("acierto@5 del experimento = promedio de ese 0/1 sobre todos los videos (p. ej. 51 de 93 = 54.8 %)")


# ==============================================================================================================
# 5. RESULTADOS: de dónde sale cada cifra del PPT   (python main.py resultados | verificar)
# ==============================================================================================================
RESULTADOS = [
    # (cifra del PPT, valor, script que la produce, archivo con el resultado)
    ("Azar / V0 / V1 en el grupo nuevo 1 (93)", "26.9 % / 47.3 % / 54.8 %", "scripts/replicar_fresca_D050.py", "reports/replicacion_D052/por_video.csv"),
    ("R0 en el grupo nuevo 1 (93)", "62.4 %, F1 0.142", "scripts/confirmacion_fresca_final_D063.py", "reports/confirmacion_fresca_D063/resultado.json"),
    ("V1 en confirmación (352)", "53.4 % frente a 29.1 % del azar", "scripts/confirm_V1_D048.py", "reports/confirmacion_D048/resultado.json"),
    ("R0 en confirmación (352)", "60.2 %, F1 0.136", "scripts/r0_en_confirmacion_D102.py", "reports/r0_en_confirmacion_D102.json"),
    ("Redes de secuencia (444 videos)", "BiGRU 128 54.7 %; TCN/Transformer 53-55 %", "scripts/dl_secuencia_D054.py", "reports/dl_secuencia_D054/resumen.json"),
    ("Redes en el grupo nuevo 1", "BiGRU 128 53.8 %, F1 0.129", "scripts/replicar_dl_fresca_D054.py", "reports/replicacion_DL_D054"),
    ("Matriz de confusión (557 videos)", "468 / 2 317 / 4 039 / 48 876", "scripts/tabla_clases_D099.py", "reports/tabla_clases_D099.json"),
    ("Agentes de mejora", "73 rondas LightGBM; más de 12 000 EQL", "scripts/campeon_retador.py, auto_mejora.py, auto_mejora_nn.py", "reports/campeon_retador, reports/auto_mejora, reports/auto_mejora_nn"),
    ("Pesos de la fórmula (17 variables)", "mín -0.4851, máx +1.2400", "scripts/build_formula_model.py", "models/formula_calor_D045.json"),
    ("SUS 75 y utilidad mediana 4", "5 creadores", "scripts/rellenar_validacion_v45.py", "ENTREGA_NOTA2_FINAL/6_Consentimientos_informados"),
    ("Análisis adicional: R0 sobre ventanas de oraciones", "ver DECISIONES.md D-104", "scripts/r0_oraciones_D104.py", "reports/r0_oraciones_D104/resultado.json"),
]


def cmd_resultados() -> None:
    for cifra, valor, script, archivo in RESULTADOS:
        print(f"* {cifra}: {valor}\n    script : {script}\n    archivo: {archivo}")


def cmd_verificar() -> None:
    """Comprueba que las cifras clave del PPT coinciden con los archivos del proyecto. Imprime OK o DIFERENTE."""
    ok = True

    def chk(nombre: str, obtenido, esperado, tol: float = 5e-4) -> None:
        nonlocal ok
        bien = abs(obtenido - esperado) <= tol
        ok &= bien
        print(f"{'OK       ' if bien else 'DIFERENTE'} {nombre}: archivo={obtenido:.4f} ppt={esperado:.4f}")

    pesos = cargar_pesos()
    lo, hi = limites(pesos)
    chk("mínimo de la fórmula", lo, -0.4851)
    chk("máximo de la fórmula", hi, 1.2400)
    print(f"{'OK       ' if len(pesos) == 17 else 'DIFERENTE'} variables en la fórmula: {len(pesos)} (ppt: 17)")
    n_modelo = sum(1 for g, *_ in VARIABLES.values() if g != "P")
    print(f"{'OK       ' if n_modelo == 71 else 'DIFERENTE'} variables del modelo en el catálogo: {n_modelo} (ppt: 71)")
    tc = ROOT / "reports" / "tabla_clases_D099.json"
    if tc.exists():
        d = json.loads(tc.read_text(encoding="utf-8"))
        chk("precisión de la matriz", d["Caliente"]["precision"], 0.168, 1e-3)
        chk("cobertura de la matriz", d["Caliente"]["recall"], 0.104, 1e-3)
        chk("exactitud de la matriz", d["exactitud"], 0.886, 1e-3)
    r0 = ROOT / "reports" / "confirmacion_fresca_D063" / "resultado.json"
    if r0.exists():
        m = json.loads(r0.read_text(encoding="utf-8"))["metodos"]
        chk("R0 acierto@5 grupo nuevo 1", m["R0"]["hit5"], 0.624, 1e-3)
        chk("R0 F1 grupo nuevo 1", m["R0"]["F1"], 0.142, 1e-3)
    try:
        cmd_puntaje_silencioso()
        print("OK        ejemplo de la diapositiva 17: raw +1.0118 y puntaje 86")
    except AssertionError as e:
        ok = False
        print("DIFERENTE ejemplo de la diapositiva 17:", e)
    print("\nTODO COINCIDE" if ok else "\nHAY DIFERENCIAS: revisar las líneas marcadas")


def cmd_puntaje_silencioso() -> None:
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_puntaje()


# ==============================================================================================================
# 6. PIPELINE COMPLETO   (python main.py clips VIDEO)
# ==============================================================================================================
def cmd_clips(args: list[str]) -> None:
    import runpy
    sys.argv = ["PIPELINE_COMPLETO.py", *args]                 # <- pasa el video y las opciones al pipeline
    runpy.run_path(str(ROOT / "PIPELINE_COMPLETO.py"), run_name="__main__")   # <- 10 etapas: audio -> Whisper -> variables -> puntaje -> clips


def main() -> None:
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help", "ayuda"):
        print(__doc__)
    elif a[0] == "mapa":
        for d, tema, donde in MAPA_PPT:
            print(f"diapositiva {d:7s} {tema}\n    -> {donde}")
    elif a[0] == "variables":
        cmd_variables()
    elif a[0] == "variable" and len(a) > 1:
        cmd_variable(a[1])
    elif a[0] == "puntaje":
        cmd_puntaje()
    elif a[0] == "metricas":
        cmd_metricas()
    elif a[0] == "resultados":
        cmd_resultados()
    elif a[0] == "verificar":
        cmd_verificar()
    elif a[0] == "clips" and len(a) > 1:
        cmd_clips(a[1:])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
