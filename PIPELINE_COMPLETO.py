"""PIPELINE COMPLETO EN UN SOLO ARCHIVO: de un video largo (audio y sonido) a 5 clips con puntaje 0-99.

Sirve para sustentar el código: cada ETAPA está numerada y se lee de arriba abajo, igual que la Figura 1 del artículo.
Usa los mismos módulos que el sistema real (src/pipeline.py y la página web), pero deja a la vista cada paso:

    ETAPA 1  Entrada y audio            ffmpeg saca el audio WAV de 16 kHz
    ETAPA 2  Transcripción              Whisper: cada palabra con inicio, fin y confianza
    ETAPA 3  Oraciones y candidatos     ventanas de 15 a 90 s que empiezan y terminan en límite de oración
    ETAPA 4  Variables                  71 variables por ventana (audio, eventos de sonido, texto, gancho, fluidez)
    ETAPA 5  Percentil dentro del video cada variable pasa a su posición relativa (0 a 1) dentro de ESTE video
    ETAPA 6  Banderas 0/1               la variable vale 1 si está en el 25 % más alto de su video (percentil >= 0.75)
    ETAPA 7  Puntaje                    suma de (peso x bandera) de las 17 variables de la fórmula -> escala 0 a 99
    ETAPA 8  Orden y selección          clips <= 45 s, orden por puntaje, NMS (sin traslape > 30 %), top 5
    ETAPA 9  Capítulos                  además, el mejor clip de cada capítulo de YouTube (o bloques de 10 min)
    ETAPA 10 Cortes y recorte 9:16      margen de respiración, seguimiento del hablante, subtítulos

La curva "Most Replayed" de YouTube NO entra en ningún paso: solo se usa fuera de aquí para calificar el sistema.

Uso (desde la carpeta tesis/desarrollo, con el entorno de la tesis):
    python PIPELINE_COMPLETO.py RUTA_O_URL [--sin-render] [--top 5]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.common.config import load_config, set_seeds
from src.features.audio import load_or_compute                 # volumen, tono y voz por cuadro (librosa)
from src.features.builder import build_context, windows_frame  # las 71 variables por ventana
from src.ingest import media
from src.ranking.retention import BANDERA_P, load_formula     # umbral 0.75 y pesos congelados de la fórmula
from src.segment.candidates import Window, nms, sentence_candidates
from src.segment.sentences import split_sentences
from src.transcribe.whisper import transcribe

# --------------------------------------------------------------------------------------------------
# Parámetros del modelo final (V1 + banderas 0/1). Todos salen del artículo, sección 4.
# --------------------------------------------------------------------------------------------------
MAX_CLIP_S = 45.0      # V1: solo clips cortos de hasta 45 s
TOP_K = 5              # clips que se entregan
SOLAPE_MAX = 0.30      # dos clips no pueden compartir más del 30 % del más corto (NMS)
PRE_S, POST_S, GUARDA_S = 0.15, 0.35, 0.03   # margen de respiración del clip (D-101)


def titulo(n: int, texto: str) -> None:
    print(f"\n{'=' * 100}\nETAPA {n}: {texto}\n{'=' * 100}")


def mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fuente", help="archivo de video/audio o URL de YouTube")
    ap.add_argument("--sin-render", action="store_true", help="no exportar los mp4 9:16 (solo imprime la selección)")
    ap.add_argument("--top", type=int, default=TOP_K)
    args = ap.parse_args()
    t0 = time.time()

    cfg = load_config(None)
    set_seeds(cfg.seed)

    # ==============================================================================================
    titulo(1, "ENTRADA Y AUDIO (ffmpeg)")
    # ==============================================================================================
    from src.pipeline import resolve_input            # descarga con yt-dlp si es URL; si es archivo lo usa tal cual
    video = resolve_input(args.fuente, cfg)   # <- usa el archivo tal cual o descarga la URL con yt-dlp
    clave = hashlib.sha1(f"{video.name}:{video.stat().st_size}".encode()).hexdigest()[:8]
    nombre = f"{video.stem[:40]}_{clave}".replace(" ", "_")
    salida, trabajo = cfg.path("outputs") / nombre, cfg.path("interim") / "infer" / nombre
    salida.mkdir(parents=True, exist_ok=True)
    info = media.probe(video)
    wav = media.extract_audio(video, trabajo / "audio.wav", cfg.ingest["audio_sr"])   # WAV mono de 16 kHz   # <- ffmpeg: saca el audio en WAV mono de 16 kHz
    print(f"video: {video.name} | {info['duration'] / 60:.1f} min | con imagen: {info['has_video']} | audio: {wav.name}")

    # ==============================================================================================
    titulo(2, "TRANSCRIPCIÓN CON TIEMPOS POR PALABRA (Whisper)")
    # ==============================================================================================
    tc = cfg.transcribe
    tr = transcribe(wav, trabajo / f"transcript_{tc['model_inference']}.json", tc["model_inference"],   # <- Whisper: devuelve cada palabra con inicio, fin y confianza
                    tc.get("compute_type_inference", tc["compute_type"]), tc["cpu_threads"], tc["beam_size"],
                    tc["vad_filter"], tc["language"], tc.get("device", "auto"))
    print(f"idioma: {tr.language} | palabras: {len(tr.words)} | primera: {tr.words[0].text!r} "
          f"({tr.words[0].start:.2f}-{tr.words[0].end:.2f} s, confianza {tr.words[0].prob:.2f})")

    # ==============================================================================================
    titulo(3, "ORACIONES Y VENTANAS CANDIDATAS (15 a 90 s, bordes en límite de oración)")
    # ==============================================================================================
    sc = cfg.segment
    oraciones = split_sentences(tr, sc["sentence_max_words"], sc["sentence_pause_split_s"])   # <- junta las palabras en oraciones (corta por puntuación o pausa larga)
    candidatos = sentence_candidates(oraciones, sc["min_clip_s"], sc["max_clip_s"], sc["target_durations"], 1)   # <- arma ventanas de 15 a 90 s que empiezan y terminan en una oración (objetivos de 20, 40 y 60 s)
    if not candidatos:
        raise SystemExit("sin candidatos: el video no tiene habla suficiente")
    print(f"{len(oraciones)} oraciones -> {len(candidatos)} ventanas candidatas")

    # ==============================================================================================
    titulo(4, "71 VARIABLES POR VENTANA (audio + eventos de sonido + texto)")
    # ==============================================================================================
    #   a_*  audio (volumen RMS, tono f0, pausas, ritmo)   e_*  eventos de sonido (habla/música, PANNs)
    #   k_*  palabras clave (KeyBERT, sustantivos)        s_*  sentimiento, preguntas, segunda persona
    #   h_*  gancho (primeros segundos)                    f_*  fluidez (nº de oraciones, inicio colgado)   l_*  silencio
    audio = load_or_compute(wav, trabajo / "audio_frames.npz", cfg.ingest["audio_sr"], cfg.features["audio_hop"])
    ctx = build_context(tr, oraciones, cfg, audio, trabajo, "infer")   # <- prepara lo que necesitan las variables: palabras clave, sentimiento, audio y embeddings
    df = windows_frame(ctx, candidatos, cfg.features["hook_window_s"], cfg.features["hook_words"],   # <- calcula las variables de cada ventana candidata (una fila por ventana)
                       {"video_id": nombre}).reset_index(drop=True)
    formula = load_formula(cfg.path("models"))
    pesos = formula["weights"]                                   # las 17 variables de la fórmula y su peso   # <- las 17 variables de la fórmula y su peso congelado
    if any(c.startswith(("e_", "l_")) for c in pesos) and "e_speech_mean" not in df.columns:
        from src.features.extra import audio_events, augment_table   # eventos de sonido (PANNs) y variables lingüísticas
        ev = audio_events(wav, trabajo / "audio_events.parquet", str(cfg.path("models_ext") / "panns" / "Cnn14_mAP=0.431.pth"))
        df = augment_table(df, tr, ev)
    n_vars = len([c for c in df.columns if c[:2] in ("a_", "e_", "k_", "s_", "h_", "f_", "l_")])
    print(f"tabla de ventanas: {df.shape[0]} filas x {n_vars} variables de contenido; la fórmula usa {len(pesos)}")

    # ==============================================================================================
    titulo(5, "PERCENTIL DENTRO DEL VIDEO (cada variable se compara solo con las ventanas de ESTE video)")
    # ==============================================================================================
    # rank(pct=True): percentil = posición ÷ n. 1.0 = la ventana con el valor más alto de esa variable en el video; la más baja vale 1/n (casi 0);
# los empates reciben el promedio de sus posiciones.
    # Si una variable falta, vale 0.5 (neutra) y no suma ni resta.
    pct = pd.DataFrame({v: (df[v].rank(pct=True).fillna(0.5) if v in df else 0.5) for v in pesos})   # <- percentil de cada variable DENTRO de este video (0 a 1)

    # ==============================================================================================
    titulo(6, "BANDERAS 0/1 (1 = la variable está en el 25 % más alto de su video)")
    # ==============================================================================================
    # Se escanean las variables de cada ventana y solo cuentan las que superan el umbral: así el ruido de las que no
    # destacan no suma al puntaje y cada clip se explica con unas pocas variables que sí sobresalen.
    bandera = (pct >= BANDERA_P).astype(float)   # <- bandera 1 si el percentil es 0.75 o más (25 % más alto del video), 0 si no
    print(f"umbral: percentil >= {BANDERA_P} | banderas en 1 por ventana: media {bandera.sum(axis=1).mean():.1f} de {len(pesos)}")

    # ==============================================================================================
    titulo(7, "PUNTAJE: suma ponderada de las banderas, llevada a la escala 0-99")
    # ==============================================================================================
    w = np.array(list(pesos.values()), dtype=float)
    desempate = 1e-4 * (pct.to_numpy() @ w)                      # el percentil continuo solo rompe empates   # <- el percentil continuo solo rompe empates entre clips con el mismo raw
    bruto = bandera.to_numpy() @ w + desempate                   # raw = suma de peso x bandera   # <- SUMA PONDERADA: raw = suma de peso x bandera (no es un promedio)
    lo, hi = float(w[w < 0].sum()), float(w[w > 0].sum())        # mínimo y máximo posibles de la fórmula   # <- mínimo posible (solo pesos negativos en 1) y máximo posible (solo positivos en 1)
    puntaje = np.clip(np.round((bruto - lo) / (hi - lo) * 99), 0, 99).astype(int)   # <- escala fija 0-99: (raw - mín) / (máx - mín) x 99
    print(f"escala fija: mínimo {lo:+.4f}, máximo {hi:+.4f} (rango {hi - lo:.4f}) -> puntaje = (raw - mín) / (máx - mín) x 99")
    df["raw"], df["score"] = bruto, puntaje

    # ==============================================================================================
    titulo(8, f"ORDEN Y SELECCIÓN (clips <= {MAX_CLIP_S:g} s, NMS con solape <= {SOLAPE_MAX:.0%}, top {args.top})")
    # ==============================================================================================
    elegible = ((df["end"] - df["start"]).to_numpy() <= MAX_CLIP_S)          # V1: solo clips cortos   # <- V1: solo clips de 45 s o menos
    df["raw_sel"] = np.where(elegible, df["raw"], float(df["raw"].min()) - 10.0)   # los largos quedan al final
    ventanas = [Window(r.start, r.end, int(r.s0), int(r.s1)) for r in df.itertuples()]
    # NMS: se recorre de mayor a menor puntaje y se descartan las ventanas que se traslapan > 30 % con una ya elegida.
    elegidas = nms(ventanas, df["raw_sel"].to_numpy(), SOLAPE_MAX, cfg.ranking["top_n_llm"], mode="iomin")   # <- NMS: de mayor a menor puntaje, descarta los que se traslapan más de 30 % con uno ya elegido
    elegidas = sorted(elegidas, key=lambda i: -df["raw_sel"].iloc[i])[: args.top]

    # ==============================================================================================
    titulo(9, "MEJOR CLIP DE CADA CAPÍTULO (capítulos de YouTube o bloques automáticos de 10 min)")
    # ==============================================================================================
    por_capitulo = {}
    ch_cfg = cfg.ranking.get("chapters") or {}
    if ch_cfg.get("enabled", False):
        from src.segment.chapters import chapter_of, get_chapters, pick_per_chapter
        capitulos = get_chapters(args.fuente, tr.duration, cfg)
        if capitulos:
            por_capitulo = pick_per_chapter(ventanas, df["raw_sel"].to_numpy(), elegible, capitulos,
                                            int(ch_cfg.get("per_chapter_k", 1)), SOLAPE_MAX, float(ch_cfg.get("min_chapter_s", 0)))
            print(f"{len(capitulos)} capítulos -> {sum(len(v) for v in por_capitulo.values())} clips de capítulo")
    if not por_capitulo:
        print("sin capítulos: solo se entrega el top general")

    # ==============================================================================================
    titulo(10, "CORTES NATURALES, RECORTE 9:16, SUBTÍTULOS Y EXPLICACIÓN")
    # ==============================================================================================
    from src.keywords.extractor import highlight_terms, window_keywords
    from src.pipeline import breathing_margin, snap_to_cuts

    huecos = [(a.end, b.start) for a, b in zip(tr.words, tr.words[1:]) if b.start - a.end > 0.12]   # pausas entre palabras
    rc = dict(cfg.render)
    detector = None
    extra = [i for v in por_capitulo.values() for i in v if i not in elegidas]
    resultado = []
    for n, i in enumerate(elegidas + extra, 1):
        v = ventanas[i]
        ini, fin = v.start, v.end
        if info["has_video"]:                                   # el corte de escena solo se usa si cae en una pausa
            from src.segment.scenes import detect_cuts
            tol = rc["scene_snap_s"]
            ini, fin = snap_to_cuts(ini, fin, detect_cuts(video, ini - tol, fin + tol), huecos, tol)
        ini, fin = breathing_margin(ini, fin, tr.words, tr.duration, PRE_S, POST_S, GUARDA_S)   # nunca corta a media palabra   # <- margen de respiración: 0.15 s antes y 0.35 s después, sin invadir la palabra vecina
        top = i in elegidas
        fila = df.iloc[i]
        activas = [k for k in pesos if bandera.iloc[i][k] == 1]
        resultado.append((i, top))
        etiqueta = f"#{elegidas.index(i) + 1}" if top else "cap"
        print(f"{etiqueta:>4} | puntaje {int(fila['score']):>2} | {mmss(ini)}-{mmss(fin)} ({fin - ini:4.1f} s) | "
              f"{len(activas)} de {len(pesos)} banderas en 1")
        print(f"       en 1: {', '.join(activas) or 'ninguna'}")
        print(f"       texto: {' '.join(s.text for s in oraciones[v.s0:v.s1])[:140]}...")
        if not args.sin_render and info["has_video"]:
            from src.render.export import export_clip
            from src.render.reframe import FaceDetector
            detector = detector or FaceDetector(rc["face_detector"], cfg.path("models_ext"))
            palabras = highlight_terms(ctx.kw, tr, ini, fin, rc["captions"]["max_highlight_ratio"])
            archivo = salida / (f"clip_{elegidas.index(i) + 1:02d}_score{int(fila['score'])}.mp4" if top else f"cap_score{int(fila['score'])}_{n:02d}.mp4")
            export_clip(video, ini, fin, tr.words, palabras, tr.language, archivo, rc, detector, None)   # 9:16 + subtítulos   # <- recorta a 9:16 con seguimiento del hablante y subtítulos, y guarda el mp4
            print(f"       exportado: {archivo}")

    print(f"\nlisto en {time.time() - t0:.0f} s | carpeta de salida: {salida}")


if __name__ == "__main__":
    main()
