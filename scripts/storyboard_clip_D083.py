"""D-083: descarga storyboards sb1 y guarda embeddings CLIP (ViT-B/32) por frame. Reanudable (salta lo que ya existe).

    python scripts/storyboard_clip_D083.py [--cohortes]
Primero los videos de desarrollo; con --cohortes tambien las cohortes frescas 1 y 2 (solo extraccion, no evaluacion).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import CLIPModel, CLIPProcessor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.storyboard_fetch_D053 import fetch_frames  # noqa: E402
from src.common.config import load_config  # noqa: E402

cfg = load_config("configs/gpu.yaml")
OUT = cfg.path("interim") / "storyboard_clip"
OUT.mkdir(parents=True, exist_ok=True)
bd = cfg.path("processed") / "features" / "bin"
J = lambda f: json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"]  # noqa: E731
c1, c2 = J("conjunto_confirmacion_fresca_D050.json"), J("conjunto_confirmacion_fresca2_D065.json")
rep = set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])
have = {p.stem for p in bd.glob("*.parquet")}
dev = sorted(have - set(c1) - set(c2) - rep)
ids = dev + (sorted(set(c1 + c2) & have) if "--cohortes" in sys.argv else [])
print(f"a procesar: {len(ids)} videos ({len(dev)} desarrollo)", flush=True)

dev_t = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(dev_t).half().eval()
proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
TEXTS = ["a close-up of a person's face", "a wide shot of a studio with people talking",
         "a slide or title card with text on screen", "an audience or a crowd of people"]
with torch.no_grad():
    t = proc(text=TEXTS, return_tensors="pt", padding=True).to(dev_t)
    tf = model.get_text_features(**t)
    tf = (tf / tf.norm(dim=-1, keepdim=True)).float().cpu().numpy()
np.save(OUT / "_text_feats.npy", tf)

ok = bad = 0
for v in ids:
    p = OUT / f"{v}.npz"
    if p.exists():
        continue
    try:
        frames, fps = fetch_frames(v)
        embs = []
        for i in range(0, len(frames), 64):
            batch = [f[:, :, ::-1] for f in frames[i:i + 64]]  # BGR -> RGB
            x = proc(images=batch, return_tensors="pt").to(dev_t)
            with torch.no_grad():
                e = model.get_image_features(pixel_values=x["pixel_values"].half())
            embs.append((e / e.norm(dim=-1, keepdim=True)).float().cpu().numpy())
        np.savez_compressed(p, emb=np.concatenate(embs).astype(np.float16), fps=fps, n=len(frames))
        ok += 1
    except Exception as ex:  # noqa: BLE001
        bad += 1
        print("fallo", v, str(ex)[:110], flush=True)
    time.sleep(2.5)
    if (ok + bad) % 20 == 0:
        print(f"{ok} ok / {bad} fallos", flush=True)
print(f"terminado: {ok} ok / {bad} fallos", flush=True)
