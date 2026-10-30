"""D-084 (descriptivo): desempeño de R0 en podcast vs no-podcast (regla por metadatos fijada en DECISIONES.md)."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
S = base["LGBM_bin"]
man = pd.concat([pd.read_csv(ROOT / "data" / "manifests" / f) for f in ("youtube_mr.csv", "youtube_mr_v1.csv")]).drop_duplicates("video_id").set_index("video_id")
RX = re.compile(r"podcast|pódcast|entrevista|interview|conversaci|episod|episode", re.I)
rows = []
for i, v in enumerate(vids):
    d = pd.read_parquet(bd / f"{v}.parquet")
    m = json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))
    st, en, rel = d["start"].to_numpy(), d["end"].to_numpy(), d["y_relevant"].to_numpy()
    heat = heat_intervals(corrected_graph(m["heatmap"]))
    sel = top_k_nms(st, en, S[i])
    rng = np.random.default_rng(i)
    az = np.mean([rel[top_k_nms(st, en, rng.random(len(st)))].max() > 0 for _ in range(20)])
    txt = f"{man['query'].get(v, '')} {man['title'].get(v, '')}"
    rows.append(dict(v=v, ch=m["channel_id"], podcast=bool(RX.search(txt)), hit=float(rel[sel].max() > 0), azar=float(az),
                     f1=f1_temporal([(st[j], en[j]) for j in sel], heat)))
df = pd.DataFrame(rows)
rng = np.random.default_rng(0)


def boot(x, ch):
    g = pd.Series(x.values, index=ch.values).groupby(level=0).mean()
    b = [g.sample(len(g), replace=True, random_state=int(s)).mean() for s in rng.integers(0, 1e6, 500)]
    return float(g.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


out = {}
for name, sub in (("podcast", df[df.podcast]), ("no_podcast", df[~df.podcast])):
    h, f, a = boot(sub.hit, sub.ch), boot(sub.f1, sub.ch), boot(sub.hit - sub.azar, sub.ch)
    out[name] = {"n": len(sub), "hit5": h, "F1": f, "exceso_hit_sobre_azar": a, "azar_hit": float(sub.azar.mean())}
    print(f"{name:11s} n={len(sub):3d} | hit@5 {h[0]:.1%} [{h[1]:.1%}, {h[2]:.1%}] (azar {sub.azar.mean():.1%}) | exceso {a[0]:+.1%} | F1 {f[0]:.3f} [{f[1]:.3f}, {f[2]:.3f}]")
json.dump(out, open(ROOT / "reports" / "alcance_podcast_D084.json", "w", encoding="utf-8"), indent=1)
