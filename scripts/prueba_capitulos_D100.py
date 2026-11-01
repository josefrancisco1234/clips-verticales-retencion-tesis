"""D-100: prueba de la selección por capítulos con datos ya calculados (sin volver a transcribir). Uso: python scripts/prueba_capitulos_D100.py [VIDEO_ID]."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph, window_mr  # noqa: E402
from src.ranking.retention import formula_raw, load_formula  # noqa: E402
from src.segment.candidates import Window, nms  # noqa: E402
from src.segment.chapters import chapter_of, from_youtube, pick_per_chapter  # noqa: E402

vid = sys.argv[1] if len(sys.argv) > 1 else "-6rWqJhDv7M"
cfg = load_config("configs/gpu.yaml")
W = load_formula(ROOT / "models")["weights"]
meta = json.loads((cfg.path("interim") / "heatmaps" / f"{vid}.json").read_text(encoding="utf-8"))
df = pd.read_parquet(cfg.path("processed") / "features" / "sentence" / f"{vid}.parquet")
chs = from_youtube(meta.get("chapters"), meta["duration"])
raw = formula_raw(df, W, True)
ok = ((df.end - df.start) <= 45).to_numpy()
raw = np.where(ok, raw, raw.min() - 10)
wins = [Window(r.start, r.end, int(r.s0), int(r.s1)) for r in df.itertuples()]
top = nms(wins, raw, 0.3, 5, mode="iomin")
pick = pick_per_chapter(wins, raw, ok, chs, 1, 0.3, 60)
st, en, vals = corrected_graph(meta["heatmap"])


def calor(i):
    return window_mr(wins[i], st, en, vals)


print(f"{meta['title']} | {len(chs)} capítulos | {len(df)} candidatos")
print("\nTOP 5 GENERAL")
for n, i in enumerate(top, 1):
    c = chs[chapter_of(wins[i].start, wins[i].end, chs)]
    print(f" {n}. {wins[i].start:7.0f}-{wins[i].end:7.0f} s | capítulo: {c.title:28s} | calor {calor(i):.2f}")
print("\nMEJOR CLIP POR CAPÍTULO")
for ch in chs:
    i = pick.get(ch.index, [None])[0]
    marca = "★ también en el top 5" if i in top else ""
    print(f" {ch.index + 1}. {ch.title:28s} [{ch.start:5.0f}-{ch.end:5.0f}] -> " + (f"{wins[i].start:7.0f}-{wins[i].end:7.0f} s | calor {calor(i):.2f} {marca}" if i is not None else "sin clip elegible"))
caps_top = {chapter_of(wins[i].start, wins[i].end, chs) for i in top}
print(f"\ncapítulos cubiertos por el top 5: {len(caps_top)} de {len(chs)}; con el mejor por capítulo: {len(pick)} de {len(chs)}")
