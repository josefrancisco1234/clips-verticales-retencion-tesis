"""D-102 (descriptivo): R0 (LightGBM LambdaRank por tramo) en los 352 videos de confirmación, con las predicciones fuera de pliegue guardadas en
reports/dl_secuencia_D054/oof.npz (validación cruzada de 10 pliegues agrupada por canal sobre los 444 videos de desarrollo ampliado, que incluyen los 352).
Mismas definiciones de acierto@5, F1 temporal y calor que dl_secuencia_D054.py (100 tramos por video)."""
import json
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
z = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in z["vids"]]
conf = set(pd.read_csv(ROOT / "reports" / "confirmacion_D048" / "por_video.csv").video_id)
idx = [i for i, v in enumerate(vids) if v in conf]
T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in (vids[i] for i in idx)}
HEAT = {v: heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in T}


def metricas(S):
    out = []
    for i in idx:
        v = vids[i]
        d = T[v]
        st, en, rel, y = d.start.to_numpy(), d.end.to_numpy(), d.y_relevant.to_numpy(int), d.y_mr.to_numpy(float)
        k = top_k_nms(st, en, S[i])
        out.append((float(rel[k].max() > 0), f1_temporal([(st[j], en[j]) for j in k], HEAT[v]), float(y[k].mean() / np.nanmean(y))))
    return np.array(out, dtype=float)


rng = np.random.default_rng(42)
M = {"R0": metricas(z["LGBM_bin"]), "V0_por_tramo": metricas(z["V0"]),
     "azar": np.mean([metricas(rng.random(z["V0"].shape)) for _ in range(30)], axis=0)}
res = {"n_videos": len(idx), "metodo": "predicciones fuera de pliegue, 10 pliegues agrupados por canal"}
for k, a in M.items():
    res[k] = {"acierto5_pct": round(100 * float(np.nanmean(a[:, 0])), 1), "videos_con_acierto": round(float(np.nansum(a[:, 0])), 1),
              "F1_temporal": round(float(np.nanmean(a[:, 1])), 3), "calor_vs_video": round(float(np.nanmean(a[:, 2])), 2)}
(ROOT / "reports" / "r0_en_confirmacion_D102.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(res, indent=1, ensure_ascii=False))
