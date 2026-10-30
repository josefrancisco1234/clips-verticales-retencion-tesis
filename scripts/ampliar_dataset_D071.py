"""D-071: amplia el dataset de ENTRENAMIENTO con consultas nuevas (no es confirmacion). Espera a que termine D-065."""
import json, subprocess, sys, time
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config
from src.common.logging_utils import setup_logging, get_logger
from src.data.youtube_dataset import acquire, build_manifest

cfg = load_config("configs/ampliacion_D071.yaml")
setup_logging("INFO", cfg.logging["file"])
log = get_logger("ampliar_D071")
man = cfg.path("manifests") / "youtube_mr.csv"
snap = ROOT / "reports" / "conjunto_manifest_previo_D071.json"
out = ROOT / "reports" / "conjunto_entrenamiento_extra_D071.json"
if not snap.exists():
    snap.write_text(json.dumps({"creado": time.strftime("%Y-%m-%d %H:%M"),
                                "video_ids": pd.read_csv(man)["video_id"].tolist()}), encoding="utf-8")
before = set(json.loads(snap.read_text(encoding="utf-8"))["video_ids"])
df = build_manifest(cfg, man)
new = df[~df["video_id"].isin(before)]
out.write_text(json.dumps({"creado": time.strftime("%Y-%m-%d %H:%M"), "uso": "solo entrenamiento",
                           "video_ids": new["video_id"].tolist()}), encoding="utf-8")
log.info("videos nuevos D-071: %d", len(new))
st = acquire(cfg, new.reset_index(drop=True), cfg.transcribe["model_dataset"])
sp = man.with_name("youtube_mr_status.csv")
old = pd.read_csv(sp)
pd.concat([old[~old["video_id"].isin(st["video_id"])], st]).to_csv(sp, index=False)
log.info("validos: %d/%d", int(st["ok"].fillna(False).astype(bool).sum()), len(st))
subprocess.run([sys.executable, "-m", "src.data.featurize_loop", "data/manifests/youtube_mr.csv", "--una-vez"], cwd=ROOT, check=False)
subprocess.run([sys.executable, "scripts/rebuild_status.py"], cwd=ROOT, check=False)
log.info("ampliacion D-071 terminada")
