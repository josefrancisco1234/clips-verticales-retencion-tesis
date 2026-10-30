"""Producto final de la tesis: pones tu video (podcast, entrevista, charla) en la carpeta MIS_VIDEOS y el sistema genera 5 clips verticales 9:16
con puntaje 0-99, desglose Hook/Flow/Value, palabras de mayor peso, subtitulos y un reporte, en CLIPS_GENERADOS/<nombre del video>/.

El sistema elige SOLO con el contenido (audio + texto); no usa la curva de YouTube. Metodo: formula de 17 variables V1 (clips de hasta 45 s),
el mismo que se valido en las cohortes frescas (ver docs/DECISIONES.md).

Uso:  python scripts/clips_desde_carpeta.py [--forzar] [--top-k 5] [--carpeta RUTA]
"""
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
EXT_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv"}
EXT_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
BASE = Path(os.environ.get("TESIS_BASE", RAIZ.parent.parent))  # F:\TESISJF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", action="store_true", help="volver a procesar videos que ya tienen clips")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--entrada", default=str(BASE / "MIS_VIDEOS"))
    ap.add_argument("--salida", default=str(BASE / "CLIPS_GENERADOS"))
    a = ap.parse_args()
    entrada, salida = Path(a.entrada), Path(a.salida)
    entrada.mkdir(parents=True, exist_ok=True)
    salida.mkdir(parents=True, exist_ok=True)
    os.chdir(RAIZ)
    archivos = sorted(p for p in entrada.iterdir() if p.is_file() and p.suffix.lower() in EXT_VIDEO | EXT_AUDIO)
    if not archivos:
        print(f"\nNo hay videos en: {entrada}\nCopia ahi tu podcast (mp4, mkv, mov, mp3...) y vuelve a ejecutar.")
        os.startfile(str(entrada))  # type: ignore[attr-defined]
        return
    from src.common.config import load_config
    from src.common.logging_utils import setup_logging
    from src.pipeline import run

    setup_logging()
    cfg = load_config("configs/gpu.yaml")
    cfg["ranking"]["max_clip_s"] = 45
    cfg["ranking"]["method"] = "formula"   # solo contenido (audio + texto), nunca la curva de YouTube
    outputs = cfg.path("outputs")
    outputs.mkdir(parents=True, exist_ok=True)
    hechos = []
    for i, v in enumerate(archivos, 1):
        destino = salida / v.stem
        if (destino / "clips.json").exists() and not a.forzar:
            print(f"[{i}/{len(archivos)}] {v.name}: ya tiene clips en {destino} (usa --forzar para rehacerlos)")
            continue
        print(f"\n[{i}/{len(archivos)}] {v.name}: transcribiendo, puntuando y renderizando (varios minutos)...")
        t0 = time.time()
        try:
            res = run(str(v), cfg, top_k=a.top_k, render=v.suffix.lower() in EXT_VIDEO)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR con {v.name}: {e}")
            continue
        antes = t0 - 2
        cand = [d for d in outputs.iterdir() if d.is_dir() and (d / "clips.json").exists() and (d / "clips.json").stat().st_mtime >= antes]
        if not cand:
            print("  no se encontró la carpeta de salida")
            continue
        origen = max(cand, key=lambda d: (d / "clips.json").stat().st_mtime)
        if destino.exists():
            shutil.rmtree(destino)
        shutil.copytree(origen, destino)
        hechos.append(destino)
        print(f"  listo en {time.time() - t0:.0f} s -> {destino}")
        for c in res["clips"]:
            print(f"   #{c['rank']} score {c['score_final']:>2}  {int(c['start'] // 60):02d}:{int(c['start'] % 60):02d}-{int(c['end'] // 60):02d}:{int(c['end'] % 60):02d}  {c['context']['title']}")
    print("\nTerminado.", f"{len(hechos)} video(s) procesado(s). Resultados en: {salida}")
    try:
        os.startfile(str(hechos[-1] if hechos else salida))  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
