"""Que habria elegido cada GENERACION del sistema en un mismo video (sin renderizar): V0 (percentiles), V1 (percentiles, clips <= 45 s) y final 0/1.
Guarda F:/TESISJF/_gen/generaciones.json. Protege clips.json/report.md de la salida real (el pipeline los sobreescribe)."""
import json, os, shutil, sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); os.chdir(RAIZ); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config
from src.common.logging_utils import setup_logging
from src.pipeline import run
BASE = Path(r"F:\TESISJF"); OUT = BASE / "_gen"; OUT.mkdir(exist_ok=True)
video = next(p for p in (BASE / "MIS_VIDEOS").iterdir() if p.suffix.lower() in {".mp4", ".mkv", ".mov"})
setup_logging(); cfg = load_config("configs/gpu.yaml")
outputs = cfg.path("outputs")
GENS = [("V0", "Fórmula V0: 17 variables en percentil, clips de 15 a 90 s", None, False), ("V1", "Fórmula V1: percentiles, clips de hasta 45 s", 45, False),
        ("FINAL", "Modelo final: 17 variables en 0/1, clips de hasta 45 s", 45, True)]
res = {}
for k, nombre, maxs, binario in GENS:
    cfg["ranking"]["method"] = "formula"; cfg["ranking"]["max_clip_s"] = maxs; cfg["ranking"]["binary_variables"] = binario
    d = next(x for x in outputs.iterdir() if x.name.startswith(video.stem[:40].replace(" ", "_")))
    bak = {n: (d / n).read_bytes() for n in ("clips.json", "report.md") if (d / n).exists()}
    r = run(str(video), cfg, top_k=5, render=False)
    for n, b in bak.items():
        (d / n).write_bytes(b)
    res[k] = {"nombre": nombre, "clips": [{"rank": c["rank"], "start": c["start"], "end": c["end"], "score": c["score_final"], "title": c["context"]["title"]} for c in r["clips"]]}
    print(k, [(round(c["start"]), round(c["end"]), c["score_final"]) for c in r["clips"]], flush=True)
(OUT / "generaciones.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("listo")
