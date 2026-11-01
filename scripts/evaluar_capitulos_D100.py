"""D-100 (descriptivo, no preregistrado): en los videos con capítulos, qué tanto cubre el top 5 general y cuántos mejores clips por capítulo tocan un pico real.
Fórmula V1 en banderas 0/1, ventanas por oración. Salida: reports/capitulos_D100.json"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402
from src.ranking.retention import formula_raw, load_formula  # noqa: E402
from src.segment.candidates import Window, nms  # noqa: E402
from src.segment.chapters import chapter_of, from_youtube, pick_per_chapter  # noqa: E402

cfg = load_config("configs/gpu.yaml")
W = load_formula(ROOT / "models")["weights"]
rng = np.random.default_rng(42)
R = dict(videos=0, caps=0, cubiertos_top5=0, clips_cap=0, toca_cap=0, toca_azar=0, hit_top5=0, hit_union=0)
for f in sorted((cfg.path("interim") / "heatmaps").glob("*.json")):
    vid = f.stem
    pq = cfg.path("processed") / "features" / "sentence" / f"{vid}.parquet"
    if not pq.exists():
        continue
    meta = json.loads(f.read_text(encoding="utf-8"))
    chs = from_youtube(meta.get("chapters"), meta.get("duration") or 0)
    if len(chs) < 3 or not meta.get("heatmap"):
        continue
    df = pd.read_parquet(pq)
    if not all(c in df for c in W):
        continue
    raw = formula_raw(df, W, True)
    ok = ((df.end - df.start) <= 45).to_numpy()
    raw = np.where(ok, raw, raw.min() - 10)
    wins = [Window(r.start, r.end, int(r.s0), int(r.s1)) for r in df.itertuples()]
    top = nms(wins, raw, 0.3, 5, mode="iomin")
    pick = pick_per_chapter(wins, raw, ok, chs, 1, 0.3, 60)
    st, en, vals = corrected_graph(meta["heatmap"])
    idx = np.nonzero(vals > 0.5)[0]
    idx = idx[np.argsort(vals[idx])[::-1]][:20]
    if len(idx) == 0:
        idx = np.argsort(vals)[::-1][:5]
    hot = [(st[i], en[i]) for i in idx]
    toca = lambda i: any(min(wins[i].end, b) - max(wins[i].start, a) > 0 for a, b in hot)
    R["videos"] += 1
    R["caps"] += len(chs)
    R["cubiertos_top5"] += len({chapter_of(wins[i].start, wins[i].end, chs) for i in top})
    R["hit_top5"] += int(any(toca(i) for i in top))
    R["hit_union"] += int(any(toca(i) for i in set(top) | {j for v in pick.values() for j in v}))
    for ci, v in pick.items():
        R["clips_cap"] += 1
        R["toca_cap"] += int(toca(v[0]))
        cand = [i for i in range(len(wins)) if ok[i] and chapter_of(wins[i].start, wins[i].end, chs) == ci]
        R["toca_azar"] += int(toca(int(rng.choice(cand))))
R["pct_capitulos_cubiertos_top5"] = round(100 * R["cubiertos_top5"] / R["caps"], 1)
R["pct_mejor_por_capitulo_toca_pico"] = round(100 * R["toca_cap"] / R["clips_cap"], 1)
R["pct_azar_en_capitulo_toca_pico"] = round(100 * R["toca_azar"] / R["clips_cap"], 1)
R["pct_videos_top5_toca_pico"] = round(100 * R["hit_top5"] / R["videos"], 1)
R["pct_videos_union_toca_pico"] = round(100 * R["hit_union"] / R["videos"], 1)
(ROOT / "reports" / "capitulos_D100.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(R, indent=1, ensure_ascii=False))
