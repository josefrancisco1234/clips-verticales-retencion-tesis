"""Reconstruye los CSV de estado a partir de lo que hay en disco (sin pedir nada a YouTube).

Necesario porque los workers en paralelo sólo escriben el estado desde el proceso principal.
Un video es válido si tiene transcripción, el idioma detectado coincide con el de la consulta
y supera las 500 palabras.

    python scripts/rebuild_status.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.common.config import load_config  # noqa: E402
from src.data.youtube_dataset import transcript_path  # noqa: E402
from src.transcribe.whisper import Transcript  # noqa: E402


def rebuild(cfg, manifest: Path) -> pd.DataFrame:
    df = pd.read_csv(manifest)
    ok, langs = [], []
    for r in df.itertuples():
        p = transcript_path(cfg, r.video_id, cfg.transcribe["model_dataset"])
        if not p.exists():
            ok.append(False), langs.append(None)
            continue
        tr = Transcript.load(p)
        langs.append(tr.language)
        ok.append(tr.language == r.query_lang and len(tr.words) > 500)
    out = df.assign(ok=ok, detected_lang=langs)
    dst = manifest.with_name(manifest.stem + "_status.csv")
    out.to_csv(dst, index=False)
    print(f"{manifest.name}: {int(out['ok'].sum())}/{len(out)} válidos → {dst.name}")
    return out


if __name__ == "__main__":
    cfg = load_config()
    base = cfg.path("manifests")
    total = [rebuild(cfg, base / f) for f in ("youtube_mr.csv", "youtube_mr_repurpose.csv") if (base / f).exists()]
    allv = pd.concat(total)
    v = allv[allv["ok"]]
    print(f"\nTOTAL válidos: {len(v)} videos, {v['duration'].sum() / 3600:.1f} h, "
          f"{v['channel_id'].nunique()} canales, idiomas {v['query_lang'].value_counts().to_dict()}")
