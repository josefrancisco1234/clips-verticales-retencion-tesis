"""Regenera todo el trabajo experimental de principio a fin (reproducibilidad, Fase 3).

    python run_all.py                 # todas las etapas (reanudable: salta lo que ya existe)
    python run_all.py --from features # desde una etapa
    python run_all.py --demo URL      # además genera clips de un video de demostración

Etapas: env → manifest → acquire → features → experiments → report → (demo)
Semilla global: configs/default.yaml (seed). Versiones: requirements.txt / requirements-lock.txt.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from src.common.config import load_config, set_seeds
from src.common.logging_utils import get_logger, setup_logging

STAGES = ["env", "manifest", "acquire", "features", "experiments", "report", "demo"]
log = get_logger("run_all")


def stage_env(cfg) -> None:
    import ctranslate2
    import lightgbm
    import sklearn
    import torch

    info = {"python": platform.python_version(), "platform": platform.platform(), "torch": torch.__version__,
            "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__, "ctranslate2": ctranslate2.__version__,
            "ffmpeg": shutil.which("ffmpeg"), "seed": cfg.seed}
    if not info["ffmpeg"]:
        raise RuntimeError("ffmpeg no está en el PATH")
    if not platform.python_version().startswith("3.11"):
        log.warning("se esperaba Python 3.11 (actual %s)", platform.python_version())
    out = cfg.path("reports")
    out.mkdir(parents=True, exist_ok=True)
    (out / "environment.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    log.info("entorno: %s", info)


def stage_manifest(cfg) -> None:
    from src.data.youtube_dataset import build_manifest

    path = cfg.path("manifests") / "youtube_mr.csv"
    if path.exists():
        log.info("manifest existente (%d videos): %s — se reutiliza para reproducibilidad",
                 len(pd.read_csv(path)), path)
        return
    build_manifest(cfg, path)


def stage_acquire(cfg) -> None:
    from src.data.youtube_dataset import acquire

    path = cfg.path("manifests") / "youtube_mr.csv"
    df = acquire(cfg, pd.read_csv(path), cfg.transcribe["model_dataset"])
    df.to_csv(path.with_name("youtube_mr_status.csv"), index=False)
    log.info("videos válidos: %d/%d", int(df["ok"].fillna(False).astype(bool).sum()), len(df))


def stage_features(cfg) -> None:
    from src.data.featurize import featurize_video

    st = pd.read_csv(cfg.path("manifests") / "youtube_mr_status.csv")
    ok = st[st["ok"] == True].to_dict("records")  # noqa: E712
    n = sum(featurize_video(cfg, r, cfg.transcribe["model_dataset"]) for r in ok)
    log.info("featurizados %d/%d", n, len(ok))


def stage_experiments(cfg, folds: int) -> None:
    from src.evaluation.experiments import run

    run(cfg, cfg.path("reports"), folds, ablations=True)


def stage_report(cfg) -> None:
    from src.evaluation.report import build

    build(cfg.path("reports"))
    log.info("reporte: %s", cfg.path("reports") / "results.md")


def stage_demo(cfg, url: str | None) -> None:
    if not url:
        log.info("sin --demo: se omite la demostración")
        return
    from src.pipeline import run

    run(url, cfg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--from", dest="start", choices=STAGES, default="env")
    ap.add_argument("--only", choices=STAGES, default=None)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--demo", default=None, help="URL o ruta de un video para la demostración final")
    args = ap.parse_args()
    cfg = load_config(args.config)
    setup_logging(cfg.logging["level"], cfg.logging["file"])
    set_seeds(cfg.seed)
    todo = [args.only] if args.only else STAGES[STAGES.index(args.start):]
    for st in todo:
        t0 = time.time()
        log.info("===== etapa %s =====", st)
        if st == "experiments":
            stage_experiments(cfg, args.folds)
        elif st == "demo":
            stage_demo(cfg, args.demo)
        else:
            globals()[f"stage_{st}"](cfg)
        log.info("etapa %s lista en %.0fs", st, time.time() - t0)


if __name__ == "__main__":
    sys.exit(main())
