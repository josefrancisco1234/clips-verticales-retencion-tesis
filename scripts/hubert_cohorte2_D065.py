"""Calcula el grupo U (HuBERT) SOLO para la cohorte fresca, con el PCA CONGELADO (D-061 B).

No reajusta el PCA ni modifica ningun video de desarrollo. Idempotente: salta los videos que ya tienen u_*.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config  # noqa: E402
from src.data.youtube_dataset import wav_path  # noqa: E402
from src.features.speech_embed import augment_table, chunk_embeddings, project  # noqa: E402

cfg = load_config("configs/gpu.yaml")
sc = cfg.features["speech_embed"]
pca = cfg.path("models") / "speech_pca.npz"
h = hashlib.sha256(pca.read_bytes()).hexdigest()[:16]
print(f"PCA congelado: {pca.name} sha256[:16]={h}", flush=True)
fresh = json.loads((ROOT / "reports" / "conjunto_confirmacion_fresca2_D065.json").read_text(encoding="utf-8"))["video_ids"]
cache = cfg.path("interim") / "speech_emb"
done = skipped = 0
for v in fresh:
    p = cfg.path("processed") / "features" / "bin" / f"{v}.parquet"
    w = wav_path(cfg, v)
    if not p.exists() or not w.exists():
        continue
    d = pd.read_parquet(p)
    if any(c.startswith("u_") for c in d.columns):
        skipped += 1
        continue
    t0 = time.time()
    t, e = chunk_embeddings(w, cache / f"{v}.npz", cfg.ingest["audio_sr"], sc["chunk_s"], sc["layer"],
                            cfg.features.get("device", "auto"), sc["model"], sc.get("batch_size", 1))
    augment_table(d, t, project(e, pca)).to_parquet(p, index=False)
    done += 1
    print(f"{v}: {len(e)} trozos en {time.time() - t0:.0f}s", flush=True)
assert hashlib.sha256(pca.read_bytes()).hexdigest()[:16] == h, "el PCA cambio durante la corrida"
print(f"listo: nuevos={done} ya_tenian={skipped}", flush=True)
