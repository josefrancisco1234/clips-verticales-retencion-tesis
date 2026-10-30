"""Descarga storyboards sb1 de YouTube y calcula features visuales gruesas por frame (D-053)."""
import json, sys, time, urllib.request
from pathlib import Path
import cv2, numpy as np, yt_dlp
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config
cfg = load_config("configs/gpu.yaml")
OUT = cfg.path("interim") / "storyboard"; OUT.mkdir(parents=True, exist_ok=True)

def fetch_frames(vid):
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    f = next(x for x in info["formats"] if x.get("format_id") == "sb1")
    rows, cols, fps, dur = f["rows"], f["columns"], float(f["fps"]), float(info["duration"])
    tiles = []
    for fr in f["fragments"]:
        data = urllib.request.urlopen(urllib.request.Request(fr["url"], headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
        sheet = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        w, h = int(f["width"]), int(f["height"])        # tamano declarado; la ultima hoja puede venir recortada
        for r in range(rows):
            for c in range(cols):
                tile = sheet[r*h:(r+1)*h, c*w:(c+1)*w]
                if tile.shape[0] == h and tile.shape[1] == w:
                    tiles.append(tile)
    n = min(len(tiles), int(dur * fps) + 1)
    return np.stack(tiles[:n]), fps

def frame_feats(frames):
    g = np.array([cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).astype(np.float32) for x in frames])
    diff = np.r_[0.0, np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))]
    hist = np.array([cv2.calcHist([x], [0], None, [32], [0, 256]).ravel() / x.size for x in g.astype(np.uint8)])
    hdiff = np.r_[0.0, 0.5 * np.abs(np.diff(hist, axis=0)).sum(axis=1)]
    edge = np.array([np.abs(cv2.Sobel(x, cv2.CV_32F, 1, 1)).mean() for x in g])
    bright = g.mean(axis=(1, 2)); contrast = g.std(axis=(1, 2))
    return dict(diff=diff, hdiff=hdiff, edge=edge, bright=bright, contrast=contrast)

if __name__ == "__main__":
    ids = json.load(open(ROOT/"reports"/"conjunto_desarrollo_D038.json", encoding="utf-8"))["video_ids"]
    ok = bad = 0
    for v in sorted(ids):
        p = OUT / f"{v}.npz"
        if p.exists(): continue
        try:
            fr, fps = fetch_frames(v)
            np.savez_compressed(p, fps=fps, n=len(fr), **frame_feats(fr))
            ok += 1
        except Exception as e:
            bad += 1; print("fallo", v, str(e)[:100])
        time.sleep(2.5)
        if (ok + bad) % 10 == 0: print(f"{ok} ok / {bad} fallos", flush=True)
    print("terminado:", ok, "ok /", bad, "fallos", flush=True)
