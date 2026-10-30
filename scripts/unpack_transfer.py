"""Restaura en esta máquina un paquete creado con `pack_for_gpu.py`.

    python scripts/unpack_transfer.py <carpeta o zip del paquete>

Copia transcripciones, curvas, features y modelos a `C:\\tesis_data` y, si el paquete trae audio
comprimido, lo reconvierte a WAV de 16 kHz mono (formato que esperan librosa, PANNs y HuBERT).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.common.config import load_config  # noqa: E402


def restaurar_audio(src: Path, dst: Path, sr: int) -> int:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("  ffmpeg no está en el PATH: se omite el audio")
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    archivos = [f for f in src.iterdir() if f.suffix in (".opus", ".flac", ".wav")]
    for i, f in enumerate(archivos, 1):
        o = dst / f"{f.stem}.wav"
        if o.exists():
            continue
        if f.suffix == ".wav":
            shutil.copy2(f, o)
        else:
            subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(f), "-ac", "1", "-ar", str(sr),
                            "-c:a", "pcm_s16le", str(o)], check=False)
        if i % 25 == 0:
            print(f"  audio {i}/{len(archivos)}")
    return len(archivos)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paquete", help="carpeta o .zip generado por pack_for_gpu.py")
    ap.add_argument("--no-repo", action="store_true", help="no restaurar models/ ni reports/ del repo")
    args = ap.parse_args()

    cfg = load_config()
    root = cfg.path("raw").parents[1]
    src = Path(args.paquete)
    tmp = None
    if src.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp())
        print(f"descomprimiendo en {tmp} …")
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp)
        src = tmp

    manif = src / "MANIFIESTO.json"
    if manif.exists():
        print("paquete:", json.loads(manif.read_text(encoding="utf-8"))["creado"])

    for parte in ("data", "cache", "models_ext"):
        s = src / parte
        if s.exists():
            print(f"  restaurando {parte} → {root / parte}")
            shutil.copytree(s, root / parte, dirs_exist_ok=True)

    if not args.no_repo and (src / "repo").exists():
        for parte in ("models", "reports", "data/manifests"):
            s = src / "repo" / parte
            if s.exists():
                print(f"  restaurando repo/{parte}")
                shutil.copytree(s, ROOT / parte, dirs_exist_ok=True)

    if (src / "audio").exists():
        print("  restaurando audio a WAV 16 kHz …")
        n = restaurar_audio(src / "audio", cfg.path("raw") / "wav", cfg.ingest["audio_sr"])
        print(f"  {n} archivos de audio")

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nlisto. Comprueba con:  python scripts/check_env.py")


if __name__ == "__main__":
    main()
