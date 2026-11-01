"""Pipeline de inferencia: video largo (archivo o URL) → clips 9:16 con score 0–99.

Uso:
    python -m src.pipeline RUTA_O_URL [--top-k 8] [--no-render] [--config configs/default.yaml]
"""
from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import Config, load_config, set_seeds
from src.common.io import write_json
from src.common.logging_utils import get_logger, setup_logging
from src.context.llm import LLMClient
from src.context.refine import refine
from src.evaluation.baselines import opus_heuristic
from src.features.audio import load_or_compute
from src.features.builder import build_context, windows_frame
from src.ingest import media, youtube
from src.keywords.extractor import highlight_terms, window_keywords
from src.ranking.model import RankerBundle
from src.segment.candidates import Window, nms, sentence_candidates
from src.segment.scenes import detect_cuts
from src.segment.sentences import split_sentences
from src.transcribe.whisper import transcribe

log = get_logger(__name__)


def _key(path: Path) -> str:
    h = hashlib.sha1(f"{path.name}:{path.stat().st_size}".encode()).hexdigest()[:8]
    return f"{path.stem[:40]}_{h}".replace(" ", "_")


def resolve_input(src: str, cfg: Config) -> Path:
    if src.startswith(("http://", "https://")):
        from src.ranking.retention import video_id_from_url
        vid = video_id_from_url(src)
        cached = cfg.path("raw") / "videos" / f"{vid}.mp4" if vid else None
        if cached is not None and cached.exists() and cached.stat().st_size > 1_000_000:
            log.info("video ya descargado, se reutiliza: %s", cached)   # evita volver a pedirlo a YouTube (429/anti-bot)
            return cached
        return youtube.download_video(src, cfg.path("raw") / "videos", cfg.ingest["youtube_video_format"])
    p = Path(src)
    if not p.exists():
        raise FileNotFoundError(src)
    return p


def snap_to_cuts(start: float, end: float, cuts: list[float], word_gaps: list[tuple[float, float]], tol: float) -> tuple[float, float]:
    """Ajusta bordes a un corte de escena sólo si el corte cae en una pausa entre palabras (no corta habla)."""
    def ok(c: float) -> bool:
        return any(a - 0.05 <= c <= b + 0.05 for a, b in word_gaps)

    def nearest(t: float) -> float:
        cand = [c for c in cuts if abs(c - t) <= tol and ok(c)]
        return min(cand, key=lambda c: abs(c - t)) if cand else t

    s, e = nearest(start), nearest(end)
    return (s, e) if e - s >= 10 else (start, end)


def breathing_margin(start: float, end: float, words, duration: float, pre: float = 0.15, post: float = 0.35,
                     guard: float = 0.03) -> tuple[float, float]:
    """Margen de respiración (D-101): el clip empieza un poco antes de su primera palabra y termina un poco después de la última,
    pero nunca invade la palabra vecina; así nadie queda cortado a media palabra ni a media frase."""
    prev_end = max((w.end for w in words if w.end <= start + 0.02), default=0.0)
    next_start = min((w.start for w in words if w.start >= end - 0.02), default=duration)
    s = max(prev_end + guard, start - pre) if prev_end + guard < start else start
    e = min(next_start - guard, end + post) if next_start - guard > end else end
    return max(0.0, min(s, start)), min(duration, max(e, end))


def rank_concepts(ctx, s0: int, s1: int, k: int = 8) -> list[str]:
    """Conceptos tipo Lotus: frases nominales del clip ordenadas por el peso KVSUM de sus términos."""
    from src.keywords.text import content_token

    chunks = dict.fromkeys(c for i in range(s0, s1) for c in (ctx.kw.noun_chunks[i] if ctx.kw.noun_chunks else []))
    scored = []
    for c in chunks:
        toks = [t for t in (content_token(x, ctx.lang) for x in c.split()) if t]
        if toks:
            scored.append((sum(ctx.kw.term_weight.get(t, 0.0) for t in toks) + 0.1 * len(toks), c))
    return [c for _, c in sorted(scored, reverse=True)[:k]]


def run(src: str, cfg: Config, top_k: int | None = None, render: bool = True) -> dict:
    t0 = time.time()
    set_seeds(cfg.seed)
    video = resolve_input(src, cfg)
    key = _key(video)
    out_dir = cfg.path("outputs") / key
    work = cfg.path("interim") / "infer" / key
    out_dir.mkdir(parents=True, exist_ok=True)
    info = media.probe(video)
    log.info("video: %s (%.1f min, video=%s)", video.name, info["duration"] / 60, info["has_video"])

    # 1-2. audio + transcripción
    wav = media.extract_audio(video, work / "audio.wav", cfg.ingest["audio_sr"])
    tc = cfg.transcribe
    tr = transcribe(wav, work / f"transcript_{tc['model_inference']}.json", tc["model_inference"],
                    tc.get("compute_type_inference", tc["compute_type"]),  # D-037: ruta de inferencia propia
                    tc["cpu_threads"], tc["beam_size"], tc["vad_filter"], tc["language"], tc.get("device", "auto"))

    # 3. candidatos
    sc = cfg.segment
    sents = split_sentences(tr, sc["sentence_max_words"], sc["sentence_pause_split_s"])
    cands = sentence_candidates(sents, sc["min_clip_s"], sc["max_clip_s"], sc["target_durations"], 1)
    if not cands:
        raise RuntimeError("no se generaron candidatos (¿video sin habla o demasiado corto?)")
    log.info("%d oraciones → %d candidatos", len(sents), len(cands))

    # 4. features
    audio = load_or_compute(wav, work / "audio_frames.npz", cfg.ingest["audio_sr"], cfg.features["audio_hop"])
    ctx = build_context(tr, sents, cfg, audio, work, "infer")
    df = windows_frame(ctx, cands, cfg.features["hook_window_s"], cfg.features["hook_words"],
                       {"video_id": key}).reset_index(drop=True)

    # 5. ranking
    shap_df = None
    method = str(cfg.ranking.get("method", "lgbm"))
    if method in ("auto", "heat", "formula"):   # la fórmula final usa variables de eventos de audio (E) y lingüísticas (L)
        from src.ranking.retention import load_formula as _lf0

        if any(c.startswith(("e_", "l_")) for c in _lf0(cfg.path("models"))["weights"]) and "e_speech_mean" not in df.columns:
            from src.features.extra import audio_events, augment_table

            ev = audio_events(wav, work / "audio_events.parquet", str(cfg.path("models_ext") / "panns" / "Cnn14_mAP=0.431.pth"))
            df = augment_table(df, tr, ev)
    model_dir = cfg.path("models")
    if (model_dir / "ranker_lgbm.txt").exists():
        bundle = RankerBundle.load(model_dir)
        needed = list(bundle.features) + list(bundle.explainer_features or [])  # el explicador usa todos los grupos
        if any(f.startswith(("e_", "l_")) for f in needed) and "e_speech_mean" not in df.columns:  # grupos de la iteración 2
            from src.features.extra import audio_events, augment_table

            ev = audio_events(wav, work / "audio_events.parquet",
                              str(cfg.path("models_ext") / "panns" / "Cnn14_mAP=0.431.pth"))
            df = augment_table(df, tr, ev)
        if any("__rk" in f or "__cx" in f for f in needed):
            from src.features.relative import add_relative

            df = add_relative(df, kinds=tuple(sorted({f.split("__")[1] for f in needed if "__" in f})))
        scored = bundle.score(df)
        df = pd.concat([df, scored], axis=1)
        try:   # aporte SHAP de cada variable al desglose Hook/Flow/Value (modelo explicador)
            _exp, _fs = (bundle.explainer, bundle.explainer_features) if bundle.explainer is not None else (bundle.booster, bundle.features)
            shap_df = pd.DataFrame(_exp.predict(df[_fs], pred_contrib=True)[:, :-1], columns=_fs, index=df.index)
        except Exception as exc:  # noqa: BLE001
            log.warning("sin SHAP por variable: %s", exc)
            shap_df = None
        model_name = f"lgbm ({bundle.meta.get('created', '?')})"
    else:
        log.warning("no hay modelo entrenado en %s → uso heurística tipo Opus (sin aprendizaje)", model_dir)
        raw = opus_heuristic(df)
        pct = pd.Series(raw).rank(pct=True).to_numpy()
        df["raw"], df["score"] = raw, np.round(pct * 99).astype(int)
        for d in ("hook", "flow", "value"):
            df[f"score_{d}"] = -1
        model_name = "opus_heuristic"

    # 5b. selección guiada por retención (D-045/D-047); por defecto "lgbm" = sin cambios
    if method in ("auto", "heat", "formula"):
        from src.ranking.retention import apply as apply_retention

        df, model_name = apply_retention(df, cfg, src, method, model_name, cfg.ranking.get("max_clip_s"))

    explain_w = None
    try:
        from src.ranking.retention import FORMULA_FILE, explain, load_formula as _lf

        explain_w = _lf(cfg.path("models"))["weights"]
    except Exception as exc:  # noqa: BLE001
        log.warning("sin formula para explicar: %s", exc)

    # 6. NMS + contexto (LLM sólo sobre top-N). D-100: además del top 5 general, el mejor clip de cada capítulo
    wins = [Window(r.start, r.end, int(r.s0), int(r.s1)) for r in df.itertuples()]
    keep = nms(wins, df["raw"].to_numpy(), cfg.ranking["output_overlap"], cfg.ranking["top_n_llm"], mode="iomin")
    ch_cfg = cfg.ranking.get("chapters") or {}
    chapters, chap_pick = [], {}
    if ch_cfg.get("enabled", False):
        from src.segment.chapters import chapter_of, get_chapters, pick_per_chapter

        chapters = get_chapters(src, tr.duration, cfg)
        if chapters:
            ok = df["ok_clip"].to_numpy() if "ok_clip" in df else np.ones(len(df), bool)
            chap_pick = pick_per_chapter(wins, df["raw"].to_numpy(), ok, chapters, int(ch_cfg.get("per_chapter_k", 1)),
                                         cfg.ranking["output_overlap"], float(ch_cfg.get("min_chapter_s", 0)))
    sel = list(dict.fromkeys(list(keep) + [i for v in chap_pick.values() for i in v]))
    clips = []
    for i in sel:
        r = df.iloc[i]
        w = wins[i]
        cap = chapters[chapter_of(w.start, w.end, chapters)] if chapters else None
        clips.append({
            "start": float(w.start), "end": float(w.end), "s0": w.s0, "s1": w.s1,
            "text": " ".join(s.text for s in sents[w.s0:w.s1]),
            "score": int(r["score"]), "score_breakdown": {d: int(r[f"score_{d}"]) for d in ("hook", "flow", "value")},
            "keywords": window_keywords(ctx.kw, tr, sents, w.start, w.end, 6),
            "concepts": rank_concepts(ctx, w.s0, w.s1),
            "features": {k: (None if pd.isna(v) else float(v)) for k, v in r.items()
                         if isinstance(k, str) and k[:2] in ("h_", "f_", "s_", "k_", "a_")},
            "explain": (explain(df, i, explain_w, bool(cfg.ranking.get("binary_variables", False))) if explain_w else None),
            "dim_vars": _dim_vars(df, shap_df, i),
            "chapter": ({"index": cap.index, "title": cap.title, "auto": cap.auto} if cap else None),
            "_top": i in keep, "_cap": any(i in v for v in chap_pick.values()),
        })
    llm = LLMClient.from_config(cfg)
    clips = refine(clips, llm, tr.language)
    penalty = cfg.context["non_self_contained_penalty"]
    for c in clips:
        cx = c["context"]
        trim = int(cx.get("trim_start_sentences") or 0)
        if 0 < trim < c["s1"] - c["s0"] and sents[c["s1"] - 1].end - sents[c["s0"] + trim].start >= sc["min_clip_s"]:
            c["s0"] += trim
            c["start"] = sents[c["s0"]].start
            c["text"] = " ".join(s.text for s in sents[c["s0"]:c["s1"]])
        c["score_final"] = max(0, c["score"] - (penalty if cx.get("self_contained") is False else 0))
    top = sorted([c for c in clips if c["_top"]], key=lambda c: -c["score_final"])[: top_k or cfg.ranking["top_k_output"]]
    cap_clips = [c for c in clips if c["_cap"]]
    ids_top = {id(c) for c in top}
    for c in clips:
        c["rank"] = None
    todos = top + [c for c in cap_clips if id(c) not in ids_top]

    # 7. cortes naturales + render
    rc = dict(cfg.render)
    detector = None
    gaps = [(a.end, b.start) for a, b in zip(tr.words, tr.words[1:]) if b.start - a.end > 0.12]
    for n, c in enumerate(todos, 1):
        es_top = id(c) in ids_top
        if es_top:
            c["rank"] = top.index(c) + 1
        if info["has_video"]:
            tol = rc["scene_snap_s"]
            cuts = detect_cuts(video, c["start"] - tol, c["end"] + tol)
            c["start"], c["end"] = snap_to_cuts(c["start"], c["end"], cuts, gaps, tol)
        # margen de respiración: 0.15 s antes/después, sin invadir otra palabra
        c["start"], c["end"] = breathing_margin(c["start"], c["end"], tr.words, tr.duration)
        c["duration"] = round(c["end"] - c["start"], 2)
        if (es_top or ch_cfg.get("render", True)) and render and info["has_video"]:
            from src.render.export import export_clip
            from src.render.reframe import FaceDetector

            detector = detector or FaceDetector(rc["face_detector"], cfg.path("models_ext"))
            hl = highlight_terms(ctx.kw, tr, c["start"], c["end"], rc["captions"]["max_highlight_ratio"])
            c["highlighted_terms"] = sorted(hl)
            nombre = (f"clip_{c['rank']:02d}_score{c['score_final']}.mp4" if es_top
                      else f"cap{c['chapter']['index'] + 1:02d}_score{c['score_final']}.mp4")
            c["render"] = export_clip(video, c["start"], c["end"], tr.words, hl, tr.language, out_dir / nombre, rc, detector,
                                      c["context"].get("hook"))
        c.pop("features", None)
    clips = top   # el top 5 general conserva su formato; los de capítulo van aparte
    por_capitulo = []
    for ch in chapters:
        mine = sorted([c for c in cap_clips if c["chapter"] and c["chapter"]["index"] == ch.index], key=lambda c: -c["score_final"])
        por_capitulo.append({**ch.as_dict(), "clips": mine})
    for c in clips + cap_clips:
        for k in ("_top", "_cap"):
            c.pop(k, None)

    result = {"input": str(video), "duration_s": tr.duration, "language": tr.language, "model": model_name,
              "llm": f"{llm.provider}:{llm.model}" if llm.enabled else "none (plantillas)",
              "video_keywords": [{"term": t, "weight": round(ctx.kw.term_weight[t], 3)} for t in ctx.kw.top_terms[:15]],
              "video_keyphrases": [p for p, _ in ctx.kw.keyphrases[:10]],
              "n_candidates": len(cands), "clips": clips, "chapters": por_capitulo, "elapsed_s": round(time.time() - t0, 1)}
    write_json(out_dir / "clips.json", result)
    (out_dir / "report.md").write_text(_report(result), encoding="utf-8")
    log.info("listo: %d clips en %s (%.0fs)", len(clips), out_dir, time.time() - t0)
    return result


def _dim_vars(df: pd.DataFrame, shap_df, i: int) -> dict | None:
    """Variables que alimentan Hook / Flow / Value de la ventana i: valor y aporte SHAP de cada una."""
    if shap_df is None:
        return None
    from src.features.builder import DIMENSIONS

    out = {}
    for dim, prefixes in DIMENSIONS.items():
        rows = []
        for f in shap_df.columns:
            if f.startswith(prefixes):
                v = df[f].iloc[i] if f in df else float("nan")
                pc = float(df[f].rank(pct=True).fillna(0.5).iloc[i]) if f in df else 0.5
                rows.append({"var": f, "value": None if pd.isna(v) else float(v), "pct": round(pc, 3),
                             "shap": round(float(shap_df[f].iloc[i]), 4)})
        rows.sort(key=lambda r: -abs(r["shap"]))
        out[dim] = rows
    return out


def _fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def _report(res: dict) -> str:
    lines = [f"# Clips generados — {Path(res['input']).name}", "",
             f"- Duración: {res['duration_s'] / 60:.1f} min · idioma: {res['language']} · modelo: {res['model']} · LLM: {res['llm']}",
             f"- Keywords del video (KVSUM): {', '.join(k['term'] for k in res['video_keywords'])}",
             f"- Keyphrases (KeyBERT): {', '.join(res['video_keyphrases'])}", "",
             "| # | Score | Capítulo | Hook | Flow | Value | Inicio | Fin | Título | Palabras de mayor peso |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for c in res["clips"]:
        b = c["score_breakdown"]
        cap = (c.get("chapter") or {}).get("title", "—")
        lines.append(f"| {c['rank']} | **{c['score_final']}** | {cap} | {b['hook']} | {b['flow']} | {b['value']} | {_fmt(c['start'])} | "
                     f"{_fmt(c['end'])} | {c['context']['title']} | {', '.join(k['term'] for k in c['keywords'][:4])} |")
    lines.append("")
    if res.get("chapters"):
        lines += ["## Mejor clip de cada capítulo", "", "| Capítulo | Tramo | Score | Inicio | Fin | Título |", "|---|---|---|---|---|---|"]
        for ch in res["chapters"]:
            auto = " (bloque automático)" if ch["auto"] else ""
            if ch["clips"]:
                for c in ch["clips"]:
                    lines.append(f"| {ch['title']}{auto} | {_fmt(ch['start'])}–{_fmt(ch['end'])} | **{c['score_final']}** | {_fmt(c['start'])} | {_fmt(c['end'])} | {c['context']['title']} |")
            else:
                lines.append(f"| {ch['title']}{auto} | {_fmt(ch['start'])}–{_fmt(ch['end'])} | — | — | — | sin clip elegible |")
        lines.append("")
    for c in res["clips"]:
        lines += [f"## {c['rank']}. {c['context']['title']} (score {c['score_final']})", "",
                  f"*Hook:* {c['context']['hook']}  ", f"*Estilo:* {c['context']['style']} · *Autocontenido:* {c['context']['self_contained']}  ",
                  f"*Por qué:* {c['context']['reason']}", "", "**Palabras de mayor peso y su contexto:**", ""]
        lines += [f"- **{k['term']}** ({k['weight']}): “{k['context'][:160]}”" for k in c["keywords"]]
        ex = c.get("explain")
        if ex:   # banderas 0/1: 1 = la variable esta en el 25 % mas alto de su video (el puntaje usa el percentil completo)
            altas = [r["var"] for r in ex["vars"] if r["pct"] >= 0.75]
            bajas = [r["var"] for r in ex["vars"] if r["pct"] < 0.75]
            lines += ["", f"**Variables de la fórmula como 0/1** (1 = en el 25 % más alto de su video): **{len(altas)} de {len(ex['vars'])} en 1**",
                      f"- En 1: {', '.join(altas) or 'ninguna'}", f"- En 0: {', '.join(bajas) or 'ninguna'}"]
        lines += ["", f"> {c['text'][:700]}", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Genera clips verticales con score desde un video largo.")
    ap.add_argument("source", help="ruta local o URL de YouTube")
    ap.add_argument("--config", default=None)
    ap.add_argument("--top-k", type=int, default=None)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    setup_logging(cfg.logging["level"], cfg.logging["file"])
    res = run(args.source, cfg, args.top_k, not args.no_render)
    for c in res["clips"]:
        print(f"#{c['rank']} score={c['score_final']:>2} {_fmt(c['start'])}–{_fmt(c['end'])} {c['context']['title']}")


if __name__ == "__main__":
    main()
