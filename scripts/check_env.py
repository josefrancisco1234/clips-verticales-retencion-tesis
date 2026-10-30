"""Verifica que la máquina esté lista para correr el pipeline (CPU o GPU).

    python scripts/check_env.py
Imprime una tabla con lo que falta y devuelve código 1 si hay algo crítico sin cumplir.
"""
from __future__ import annotations

import importlib
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:  # la consola de Windows suele ser cp1252 y no soporta ≥ ni acentos
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OK, BAD, WARN = "[ OK ]", "[FALTA]", "[ AVISO ]"
PKGS = ["faster_whisper", "torch", "lightgbm", "sklearn", "pandas", "numpy", "librosa", "soundfile", "cv2",
        "mediapipe", "scenedetect", "spacy", "sentence_transformers", "transformers", "shap", "yt_dlp"]
OPTIONAL = ["panns_inference", "opensmile", "anthropic", "openai"]


def _prueba_transcripcion(rows: list, config: str | None) -> int:
    """Transcribe ~3 s con el modelo `tiny` en el dispositivo configurado, por el mismo camino del pipeline.

    `import faster_whisper` no basta: en la GTX 1660 SUPER todo parecía listo y la primera inferencia
    fallaba con «cublas64_12.dll not found» (D-036). Devuelve cuántos requisitos críticos fallaron.
    """
    try:
        import numpy as np

        from src.common.config import load_config
        from src.common.devices import cuda_info
        from src.transcribe.whisper import _model

        cfg_path = config or ("configs/gpu.yaml" if cuda_info()[0] and (ROOT / "configs/gpu.yaml").exists()
                              else "configs/default.yaml")
        tc = load_config(cfg_path).transcribe
        t = np.arange(3 * 16000) / 16000
        audio = (0.1 * np.sin(2 * np.pi * 220 * t) + 0.02 * np.random.default_rng(0).standard_normal(t.size)).astype("float32")
        cts = {tc["compute_type"], tc.get("compute_type_inference", tc["compute_type"])}
        for ct in sorted(cts):
            m = _model("tiny", ct, tc["cpu_threads"], tc.get("device", "auto"))
            segs, _ = m.transcribe(audio, beam_size=1, word_timestamps=True)
            list(segs)  # los segmentos se generan perezosamente: hay que consumirlos
            rows.append((OK, "transcripción de prueba", f"{cfg_path}: device={tc.get('device', 'auto')}, {ct}"))
        return 0
    except Exception as exc:
        rows.append((BAD, "transcripción de prueba", f"{type(exc).__name__}: {str(exc)[:160]}"))
        return 1


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None, help="perfil para la prueba de transcripción (por defecto gpu.yaml si hay GPU)")
    args_config = ap.parse_args().config
    rows, critical = [], 0

    py = platform.python_version()
    rows.append((OK if py.startswith("3.11") else WARN, "Python", f"{py} (se recomienda 3.11)"))

    ff = shutil.which("ffmpeg")
    rows.append((OK if ff else BAD, "ffmpeg", ff or "no está en el PATH → winget install Gyan.FFmpeg"))
    critical += 0 if ff else 1

    for mod in PKGS:
        try:
            m = importlib.import_module(mod)
            rows.append((OK, mod, getattr(m, "__version__", "")))
        except Exception as exc:
            rows.append((BAD, mod, f"{type(exc).__name__}: pip install -r requirements.txt"))
            critical += 1
    for mod in OPTIONAL:
        try:
            importlib.import_module(mod)
            rows.append((OK, mod, "opcional"))
        except Exception:
            rows.append((WARN, mod, "opcional, no instalado"))

    try:
        from src.common.devices import cuda_info

        has, name, cc = cuda_info()
        if has:
            from src.common.devices import resolve_compute_type

            rows.append((OK, "GPU NVIDIA", f"{name} (CC {cc[0]}.{cc[1]}) → compute_type "
                                           f"{resolve_compute_type('auto', 'cuda')}"))
        else:
            import torch

            rows.append((WARN, "GPU NVIDIA", f"no detectada; torch {torch.__version__} correrá en CPU"))
    except Exception as exc:
        rows.append((WARN, "GPU NVIDIA", f"no se pudo comprobar: {exc}"))

    for name in ("es_core_news_sm", "en_core_web_sm"):
        try:
            importlib.import_module("spacy").load(name)
            rows.append((OK, f"spaCy {name}", ""))
        except Exception:
            rows.append((BAD, f"spaCy {name}", f"python -m spacy download {name}"))
            critical += 1

    try:
        from src.common.config import load_config

        cfg = load_config()
        root = cfg.path("raw").parents[1]
        rows.append((OK, "config", f"data_root={root}"))
        free = shutil.disk_usage(root.resolve().drive or "C:\\").free / 2**30  # resolve: sigue la junction a D:
        rows.append((OK if free > 40 else WARN, "espacio libre", f"{free:.0f} GB (se recomiendan ≥ 40 GB)"))
        for f in ("blaze_face_short_range.tflite", "face_detection_yunet_2023mar.onnx"):
            p = cfg.path("models_ext") / f
            rows.append((OK if p.exists() else WARN, f"modelo {f}", "" if p.exists() else f"falta en {p.parent}"))
        p = cfg.path("models_ext") / "panns" / "Cnn14_mAP=0.431.pth"
        rows.append((OK if p.exists() else WARN, "modelo PANNs CNN14", "" if p.exists() else "descargar de Zenodo"))
        rows.append((OK if (ROOT / "models" / "ranker_lgbm.txt").exists() else WARN, "modelo entrenado",
                     "" if (ROOT / "models" / "ranker_lgbm.txt").exists() else "se genera con run_all.py"))
    except Exception as exc:
        rows.append((BAD, "config", str(exc)))
        critical += 1

    critical += _prueba_transcripcion(rows, args_config)

    w = max(len(r[1]) for r in rows)
    for status, name, detail in rows:
        print(f"{status:9} {name:<{w}}  {detail}")
    print()
    print("Listo para ejecutar." if critical == 0 else f"Faltan {critical} requisitos críticos.")
    return 0 if critical == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
