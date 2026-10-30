"""D-068 (exploratorio): posicion y contenido de los picos extremos + palabras sobre-representadas en los picos."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config  # noqa: E402
from src.data.youtube_dataset import transcript_path  # noqa: E402
from src.transcribe.whisper import Transcript  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
Y = base["Y"]
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}

# (i) donde cae el maximo global segun la picudez de la curva
pic = np.array([(y.max() - np.median(y)) / (y.std() + 1e-9) for y in Y])
imax = Y.argmax(axis=1)
q = pd.qcut(pic, 4, labels=["Q1 plano", "Q2", "Q3", "Q4 picudo"])
print("(i) posicion del maximo global (bin 0-99) por cuartil de picudez:")
df = pd.DataFrame({"q": q, "bin_max": imax})
df["en_primeros_5"] = df.bin_max < 5
df["en_ultimos_5"] = df.bin_max >= 95
print(df.groupby("q", observed=True).agg(mediana=("bin_max", "median"), pct_primeros5=("en_primeros_5", "mean"),
                                       pct_ultimos5=("en_ultimos_5", "mean")).round(3).to_string())
print(f"    todos: maximo en los primeros 5 bins en {np.mean(imax < 5):.1%} (azar 5 %), en los ultimos 5 en {np.mean(imax >= 95):.1%}")

# (ii) palabras sobre-representadas en el bin del pico frente al resto (log-odds con prior informativo)
tok = re.compile(r"[a-záéíóúñü']{3,}")
peak, rest = {"en": Counter(), "es": Counter()}, {"en": Counter(), "es": Counter()}
npk = Counter()
for i, v in enumerate(vids):
    lang = "es" if (M[v].get("language") or "en").startswith("es") else "en"
    tr = Transcript.load(transcript_path(cfg, v, "base"))
    starts = np.array([w.start for w in tr.words])
    st, en = pd.read_parquet(bd / f"{v}.parquet", columns=["start", "end"]).to_numpy().T
    top = set(np.argsort(-Y[i])[:3].tolist())
    for b in range(100):
        i0, i1 = np.searchsorted(starts, st[b], "left"), np.searchsorted(starts, en[b], "left")
        words = set(tok.findall(" ".join(w.text for w in tr.words[i0:i1]).lower()))
        (peak if b in top else rest)[lang].update(words)
        if b in top:
            npk[lang] += 1
for lang in ("en", "es"):
    P, R = peak[lang], rest[lang]
    np_, nr = npk[lang], 100 * sum(1 for v in vids if ((M[v].get("language") or "en").startswith("es")) == (lang == "es")) - npk[lang]
    rows = []
    for w, c in P.items():
        if c < 15:
            continue
        r = R.get(w, 0)
        a, b = c / np_, (r + 1) / (nr + 1)
        z = (a - b) / np.sqrt(a * (1 - a) / np_ + b * (1 - b) / nr + 1e-12)
        rows.append((w, c, a, b, z))
    rows.sort(key=lambda t: -t[4])
    print(f"\n(ii) [{lang}] palabras sobre-representadas en los bins de pico (docs pico={np_}); top 15 por z:")
    for w, c, a, b, z in rows[:15]:
        print(f"      {w:14s} en {a:5.1%} de los picos vs {b:5.1%} del resto (z={z:+.1f})")
    print("     sub-representadas (top 8):")
    for w, c, a, b, z in rows[::-1][:8]:
        print(f"      {w:14s} en {a:5.1%} de los picos vs {b:5.1%} del resto (z={z:+.1f})")
