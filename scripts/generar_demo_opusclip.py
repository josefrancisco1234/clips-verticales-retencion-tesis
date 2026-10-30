"""Genera la pagina demo estilo Opus Clip (HTML autocontenido + mp4) para UN video de ejemplo (el del PPT)."""
import json, shutil, sys
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VID = "-Gzz2LZGowU"
OUT = Path(r"D:\tesis\entregables\demo_opusclip")
RUN = Path(r"D:\tesis_data\outputs\-Gzz2LZGowU_49d5b65d")
meta = json.loads(Path(rf"D:\tesis_data\data\interim\heatmaps\{VID}.json").read_text(encoding="utf-8"))
cl = json.loads((RUN / "clips.json").read_text(encoding="utf-8"))["clips"]
hm = meta["heatmap"]
st = np.array([b["start_time"] for b in hm]); en = np.array([b["end_time"] for b in hm]); v = np.array([b["value"] for b in hm]); v[0] = v[1]
clips = []
for c in cl:
    m = (en > c["start"]) & (st < c["end"])
    hot = bool(((v > 0.5) & m).any())
    f = next(RUN.glob(f"clip_{c['rank']:02d}_score{c['score']}.mp4"))
    shutil.copy(f, OUT / f.name)
    clips.append(dict(rank=c["rank"], start=c["start"], end=c["end"], score=c["score"], hook=c["score_breakdown"]["hook"],
                      flow=c["score_breakdown"]["flow"], value=c["score_breakdown"]["value"], title=c["context"]["title"],
                      hookText=c["context"]["hook"], text=c["text"], heat=float(v[m].mean()), hot=hot, file=f.name,
                      terms=c.get("highlighted_terms", [])[:6]))
data = dict(title=meta["title"], channel=meta["channel"], dur=meta["duration"], vid=VID,
            heat=[dict(t=float((a + b) / 2), v=float(x)) for a, b, x in zip(st, en, v)], clips=clips)
tpl = Path(__file__).with_name("demo_opusclip_template.html").read_text(encoding="utf-8")
(OUT / "index.html").write_text(tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
print("ok", OUT / "index.html")
