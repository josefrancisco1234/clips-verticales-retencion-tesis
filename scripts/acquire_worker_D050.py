"""Worker de adquisicion para la cohorte fresca D-050 (sentido inverso; usa locks por video)."""
import json, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.common.config import load_config
from src.common.logging_utils import setup_logging
from src.data.youtube_dataset import acquire
cfg = load_config("configs/ampliacion_D050.yaml")
setup_logging("INFO", cfg.logging["file"])
ids = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca_D050.json").read_text(encoding="utf-8"))["video_ids"]
m = pd.read_csv(cfg.path("manifests") / "youtube_mr.csv")
acquire(cfg, m[m.video_id.isin(ids)].reset_index(drop=True), cfg.transcribe["model_dataset"], reverse=True)
