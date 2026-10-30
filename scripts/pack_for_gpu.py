"""Empaqueta todo lo necesario para continuar el trabajo en la PC con GPU.

Empaqueta lo que vive fuera del repo (`C:\\tesis_data`): transcripciones, curvas, features,
etiquetas humanas, modelos y reportes. El traslado se hace con Syncthing o croc, ambos open source
(ver `docs/TRANSFERENCIA.md`).

    python scripts/pack_for_gpu.py                      # paquete básico (~120 MB) en C:/tesis_data/transfer
    python scripts/pack_for_gpu.py --audio opus         # + audio comprimido (necesario para HuBERT)
    python scripts/pack_for_gpu.py --with-cache --with-models-ext
    python scripts/pack_for_gpu.py --dest E:\\           # a un USB

En la PC con GPU: descomprimir y ejecutar `python scripts/unpack_transfer.py <carpeta>`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.common.config import load_config  # noqa: E402

# (ruta relativa a data_root, descripción, ¿por defecto?)
PARTES = [
    ("data/interim/transcripts", "transcripciones con marca de tiempo", True),
    ("data/interim/heatmaps", "curvas Most Replayed (etiquetas)", True),
    ("data/interim/audio_events", "probabilidades de risa/aplausos (grupo E)", True),
    ("data/interim/human_clips", "clips elegidos por editores (Repurpose-10K)", True),
    ("data/interim/audio_frames", "features de audio por frame", True),
    ("data/processed/features", "tablas de features y etiquetas por video", True),
    ("cache", "embeddings y sentimiento ya calculados", False),
    ("models_ext", "pesos externos: rostros y PANNs", False),
]


def carpeta_destino(dest: Path | None, cfg) -> Path:
    """Por defecto `C:\tesis_data\transfer`; el traslado se hace con Syncthing o croc (D-032)."""
    return Path(dest) if dest else cfg.path("raw").parents[1] / "transfer"


def comprimir_audio(cfg, out_dir: Path, fmt: str) -> int:
    """Convierte los wav a opus (≈32 kbps) o flac (sin pérdida). Devuelve cuántos archivos."""
    src = cfg.path("raw") / "wav"
    if not src.exists():
        return 0
    dst = out_dir / "audio"
    dst.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    wavs = sorted(src.glob("*.wav"))
    for i, w in enumerate(wavs, 1):
        ext = "opus" if fmt == "opus" else "flac"
        o = dst / f"{w.stem}.{ext}"
        if o.exists():
            continue
        cmd = ([ffmpeg, "-y", "-v", "error", "-i", str(w), "-c:a", "libopus", "-b:a", "32k", str(o)]
               if fmt == "opus" else
               [ffmpeg, "-y", "-v", "error", "-i", str(w), "-c:a", "flac", "-compression_level", "8", str(o)])
        subprocess.run(cmd, check=False)
        if i % 20 == 0:
            print(f"  audio {i}/{len(wavs)}")
    return len(wavs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=None, help="carpeta destino (por defecto C:/tesis_data/transfer)")
    ap.add_argument("--audio", choices=["none", "opus", "flac", "raw"], default="none",
                    help="incluir audio: opus (~1 GB), flac (~6 GB), raw (12 GB) o ninguno")
    ap.add_argument("--with-cache", action="store_true", help="incluir embeddings y sentimiento cacheados")
    ap.add_argument("--with-models-ext", action="store_true", help="incluir pesos de rostros y PANNs (313 MB)")
    ap.add_argument("--no-zip", action="store_true", help="dejar la carpeta sin comprimir")
    args = ap.parse_args()

    cfg = load_config()
    root = cfg.path("raw").parents[1]                      # C:\tesis_data
    stamp = time.strftime("%Y%m%d_%H%M")
    dest = carpeta_destino(args.dest, cfg)
    out = dest / f"tesis_gpu_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    print(f"destino: {out}")

    incluidas = []
    for rel, desc, por_defecto in PARTES:
        activar = por_defecto or (rel == "cache" and args.with_cache) or (rel == "models_ext" and args.with_models_ext)
        src = root / rel
        if not activar or not src.exists():
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"  copiando {rel} …")
        shutil.copytree(src, dst, dirs_exist_ok=True)
        incluidas.append({"ruta": rel, "descripcion": desc})

    # modelos entrenados y reportes viven en el repo, pero se incluyen para no depender de la sincronización
    for rel in ("models", "reports", "data/manifests"):
        src = ROOT / rel
        if src.exists():
            shutil.copytree(src, out / "repo" / rel, dirs_exist_ok=True)
            incluidas.append({"ruta": f"repo/{rel}", "descripcion": "copia de seguridad del repositorio"})

    n_audio = 0
    if args.audio != "none":
        print(f"  comprimiendo audio a {args.audio} (esto tarda)…")
        if args.audio == "raw":
            shutil.copytree(cfg.path("raw") / "wav", out / "audio", dirs_exist_ok=True)
            n_audio = len(list((out / "audio").glob("*.wav")))
        else:
            n_audio = comprimir_audio(cfg, out, args.audio)
        incluidas.append({"ruta": "audio", "descripcion": f"audio en {args.audio} ({n_audio} archivos)"})

    manifiesto = {
        "creado": time.strftime("%Y-%m-%d %H:%M"),
        "origen": str(root),
        "contenido": incluidas,
        "audio": args.audio,
        "instrucciones": "python scripts/unpack_transfer.py <esta carpeta>  (en la PC con GPU)",
    }
    (out / "MANIFIESTO.json").write_text(json.dumps(manifiesto, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "LEEME.md").write_text(LEEME.format(stamp=stamp, audio=args.audio), encoding="utf-8")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 2**20
    print(f"\ncarpeta lista: {total:,.0f} MB")

    if not args.no_zip and args.audio in ("none", "opus"):
        zpath = dest / f"tesis_gpu_{stamp}.zip"
        print(f"comprimiendo en {zpath} …")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in out.rglob("*"):
                if f.is_file():
                    z.write(f, f.relative_to(out))
        shutil.rmtree(out, ignore_errors=True)
        print(f"listo: {zpath}  ({zpath.stat().st_size / 2**20:,.0f} MB)")
    else:
        print("se deja sin comprimir (por el tamaño del audio); cópiala tal cual")


LEEME = """# Paquete para la PC con GPU ({stamp})

Contiene todo lo que vive fuera del repositorio. El código, los documentos y los diagramas viajan
por Syncthing o git (ver `docs/TRANSFERENCIA.md`); esto son los datos.

## Qué hacer en la PC con GPU

1. Seguir `docs/SETUP_GPU.md` pasos 1 a 5 (Python 3.11, ffmpeg, driver, entorno, PyTorch CUDA).
2. Descomprimir este paquete en cualquier carpeta.
3. Restaurar los datos:

   ```
   C:\\tesis_data\\.venv\\Scripts\\python scripts\\unpack_transfer.py <carpeta descomprimida>
   ```

4. Comprobar el entorno:

   ```
   C:\\tesis_data\\.venv\\Scripts\\python scripts\\check_env.py
   C:\\tesis_data\\.venv\\Scripts\\python -m pytest
   ```

5. Continuar el trabajo:

   ```
   C:\\tesis_data\\.venv\\Scripts\\python run_all.py --config configs\\gpu.yaml --from experiments
   ```

## Sobre el audio

Audio incluido en este paquete: **{audio}**.

- Si dice `none`, la PC con GPU puede reentrenar y evaluar con las features ya calculadas, pero **no**
  puede recalcular features de audio ni construir los embeddings HuBERT (grupo U), porque eso necesita
  las ondas originales.
- Si dice `opus`, `unpack_transfer.py` los reconvierte a WAV de 16 kHz al restaurar.
"""


if __name__ == "__main__":
    main()
