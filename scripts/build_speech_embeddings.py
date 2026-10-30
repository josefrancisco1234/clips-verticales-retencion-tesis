"""Construye el grupo U (embeddings HuBERT) para todos los videos featurizados. Requiere GPU.

    python scripts/build_speech_embeddings.py --config configs/gpu.yaml

Pasos: embeddings por trozo (cacheados) → PCA ajustado SÓLO con videos de entrenamiento →
proyección y escritura de las columnas u_* en los parquet de features.
El PCA es no supervisado, pero se ajusta sólo con train para no usar información del test.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.common.config import load_config  # noqa: E402
from src.common.logging_utils import get_logger, setup_logging  # noqa: E402
from src.data.featurize import KINDS, features_path  # noqa: E402
from src.data.youtube_dataset import wav_path  # noqa: E402
from src.features.speech_embed import augment_table, chunk_embeddings, fit_pca, project  # noqa: E402

log = get_logger("speech_embed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/gpu.yaml")
    ap.add_argument("--split", default="reports/split.json", help="para ajustar el PCA sólo con train")
    args = ap.parse_args()
    cfg = load_config(args.config)
    setup_logging(cfg.logging["level"], cfg.logging["file"])
    sc = cfg.features.get("speech_embed", {})
    if not sc.get("enabled"):
        raise SystemExit("features.speech_embed.enabled = false; usa --config configs/gpu.yaml")

    from src.common.devices import cuda_info

    has, name, cc = cuda_info()
    log.info("GPU: %s", f"{name} (CC {cc[0]}.{cc[1]})" if has else "NO DETECTADA (será muy lento)")

    vids = sorted(p.stem for p in (cfg.path("processed") / "features" / "sentence").glob("*.parquet"))
    cache_dir = cfg.path("interim") / "speech_emb"
    embs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for i, vid in enumerate(vids, 1):
        wav = wav_path(cfg, vid)
        if not wav.exists():
            continue
        t0 = time.time()
        embs[vid] = chunk_embeddings(wav, cache_dir / f"{vid}.npz", cfg.ingest["audio_sr"], sc["chunk_s"],
                                     sc["layer"], cfg.features.get("device", "auto"), sc["model"],
                                     sc.get("batch_size", 1))
        log.info("[%d/%d] %s: %d trozos en %.0fs", i, len(vids), vid, len(embs[vid][1]), time.time() - t0)

    import json

    train = set(json.loads(Path(args.split).read_text(encoding="utf-8"))["train"]) if Path(args.split).exists() else set(embs)
    pca_path = cfg.path("models") / "speech_pca.npz"
    fit_pca([e for v, (_, e) in embs.items() if v in train], sc["n_components"], cfg.seed, pca_path)

    for vid, (t, e) in embs.items():
        proj = project(e, pca_path)
        for kind in KINDS:
            p = features_path(cfg, kind, vid)
            if p.exists():
                augment_table(pd.read_parquet(p), t, proj).to_parquet(p, index=False)
    log.info("grupo U escrito para %d videos", len(embs))


if __name__ == "__main__":
    main()
