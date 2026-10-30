"""Convierte los wav de la tesis (data/raw/wav, 16 kHz mono, ~84 GB) a mp3 de voz (mono, 16 kHz, 32 kbps) en BD_TESIS/09_audio_mp3.
Reanudable: salta los mp3 ya hechos. Uso: python scripts/convertir_audio_mp3_bd.py [--workers 3]"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SRC = Path(r"F:\TESISJF\tesis_data\data\raw\wav")
DST = Path(r"F:\TESISJF\BD_TESIS\09_audio_mp3")
DST.mkdir(parents=True, exist_ok=True)
W = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 3
wavs = sorted(SRC.glob("*.wav"))
t0 = time.time()
hechos = 0


def conv(w: Path) -> str:
    out = DST / f"{w.stem}.mp3"
    if out.exists() and out.stat().st_size > 10_000:
        return "ya"
    tmp = out.with_suffix(".part.mp3")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(w), "-ac", "1", "-ar", "16000", "-codec:a", "libmp3lame", "-b:a", "32k", str(tmp)], capture_output=True)
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        return "error: " + r.stderr.decode(errors="replace")[:80]
    tmp.replace(out)
    return "ok"


with ThreadPoolExecutor(W) as ex:
    for i, (w, r) in enumerate(zip(wavs, ex.map(conv, wavs)), 1):
        if r.startswith("error"):
            print(f"[{i}/{len(wavs)}] {w.name}: {r}", flush=True)
        if i % 25 == 0 or i == len(wavs):
            gb = sum(f.stat().st_size for f in DST.glob("*.mp3")) / 1e9
            print(f"[{i}/{len(wavs)}] {gb:.1f} GB | {time.time() - t0:.0f} s", flush=True)
print("listo", flush=True)
