"""Capítulos del video (D-100): el video se divide por los capítulos que muestra YouTube sobre la barra de reproducción.

Para cada capítulo se elige su mejor clip con el mismo puntaje del sistema; el top 5 general se sigue eligiendo sobre todo el video.
Si el video no trae capítulos (o es un archivo local) se usan bloques de duración fija, marcados como automáticos.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.common.logging_utils import get_logger
from src.segment.candidates import Window, nms

log = get_logger(__name__)


@dataclass
class Chapter:
    index: int
    title: str
    start: float
    end: float
    auto: bool = False

    def as_dict(self) -> dict:
        return {"index": self.index, "title": self.title, "start": round(self.start, 2), "end": round(self.end, 2), "auto": self.auto}


def from_youtube(raw: list[dict] | None, duration: float) -> list[Chapter]:
    """Normaliza la lista `chapters` de yt-dlp (start_time, end_time, title): ordena, recorta a la duración y descarta los vacíos."""
    out: list[Chapter] = []
    for c in sorted(raw or [], key=lambda c: float(c.get("start_time") or 0)):
        s = max(0.0, float(c.get("start_time") or 0))
        e = min(float(duration), float(c.get("end_time") or duration))
        if e - s >= 1.0:
            out.append(Chapter(len(out), str(c.get("title") or f"Capítulo {len(out) + 1}").strip(), s, e))
    return out


def auto_blocks(duration: float, block_s: float, min_last_s: float = 120.0) -> list[Chapter]:
    """Bloques de duración fija para videos sin capítulos; un último bloque muy corto se une al anterior."""
    n = max(1, int(duration // block_s))
    edges = [i * block_s for i in range(n)] + [float(duration)]
    if n > 1 and edges[-1] - edges[-2] < min_last_s:
        edges.pop(-2)
    return [Chapter(i, f"Bloque {i + 1}", edges[i], edges[i + 1], auto=True) for i in range(len(edges) - 1)]


def _cached_chapters(video_id: str, interim: Path) -> list[dict] | None:
    f = interim / "heatmaps" / f"{video_id}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8")).get("chapters")
        except (OSError, ValueError):
            return None
    return None


def get_chapters(src: str, duration: float, cfg) -> list[Chapter]:
    """Capítulos de YouTube (caché del dataset o yt-dlp) o, si no hay, bloques automáticos."""
    cc = cfg.ranking.get("chapters") or {}
    raw = None
    if src.startswith(("http://", "https://")):
        from src.ingest import youtube
        from src.ranking.retention import video_id_from_url

        vid = video_id_from_url(src)
        if vid:
            raw = _cached_chapters(vid, cfg.path("interim"))
            if raw is None:
                meta = youtube.fetch_metadata(vid)
                raw = (meta or {}).get("chapters")
    chapters = from_youtube(raw, duration)
    if chapters:
        log.info("%d capítulos de YouTube", len(chapters))
        return chapters
    if cc.get("fallback_block_s"):
        chapters = auto_blocks(duration, float(cc["fallback_block_s"]))
        log.info("sin capítulos: %d bloques automáticos de %.0f s", len(chapters), float(cc["fallback_block_s"]))
    return chapters


def chapter_of(start: float, end: float, chapters: list[Chapter]) -> int:
    """Índice del capítulo con el que más se solapa la ventana (si empata, el primero)."""
    best, best_ov = 0, -1.0
    for ch in chapters:
        ov = min(end, ch.end) - max(start, ch.start)
        if ov > best_ov:
            best, best_ov = ch.index, ov
    return best


def pick_per_chapter(wins: list[Window], scores: np.ndarray, eligible: np.ndarray, chapters: list[Chapter],
                     k: int, overlap: float, min_chapter_s: float = 0.0, min_inside: float = 0.7) -> dict[int, list[int]]:
    """Mejores `k` ventanas de cada capítulo (sin traslape mayor a `overlap` dentro del capítulo).

    Cada ventana pertenece al capítulo con el que más se solapa y debe caer al menos `min_inside` (70 %) dentro de él. Solo cuentan las ventanas elegibles (autocontenidas o de hasta 45 s,
    según el método); un capítulo sin ventanas elegibles, o más corto que `min_chapter_s`, no recibe clip.
    """
    por_cap: dict[int, list[int]] = {}
    for i, w in enumerate(wins):
        if not eligible[i]:
            continue
        ch = chapters[chapter_of(w.start, w.end, chapters)]
        if (min(w.end, ch.end) - max(w.start, ch.start)) >= min_inside * (w.end - w.start):
            por_cap.setdefault(ch.index, []).append(i)
    out: dict[int, list[int]] = {}
    for ch in chapters:
        idx = por_cap.get(ch.index, [])
        if not idx or ch.end - ch.start < min_chapter_s:
            continue
        sub = nms([wins[i] for i in idx], np.asarray([scores[i] for i in idx]), overlap, k, mode="iomin")
        out[ch.index] = [idx[j] for j in sub]
    return out
