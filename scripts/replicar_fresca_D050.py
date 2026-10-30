"""Replicacion preregistrada (D-052) de V0/V1 congeladas en la cohorte fresca de D-050."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from src.common.config import load_config
from src.ranking.labels import corrected_graph
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms

cfg = load_config("configs/gpu.yaml")
fd, hd = cfg.path("processed")/"features"/"sentence", cfg.path("interim")/"heatmaps"
w = json.load(open(ROOT/"models"/"formula_calor_D045.json", encoding="utf-8"))["weights"]
ids = json.load(open(ROOT/"reports"/"conjunto_confirmacion_fresca_D050.json", encoding="utf-8"))["video_ids"]
man = pd.read_csv(cfg.path("manifests")/"youtube_mr.csv").set_index("video_id")
rng = np.random.default_rng(42); rows = []
for v in ids:
    p = fd/f"{v}.parquet"
    if not p.exists() or not (hd/f"{v}.json").exists(): continue
    d = pd.read_parquet(p); meta = json.load(open(hd/f"{v}.json", encoding="utf-8"))
    if not meta.get("heatmap") or any(c not in d for c in w) or "y_relevant" not in d: continue
    st, en = d.start.to_numpy(), d.end.to_numpy(); short = (en - st) <= 45.0
    if short.sum() < 5: continue
    heat = heat_intervals(corrected_graph(meta["heatmap"])); rel = d.y_relevant.to_numpy(); mh = float(d.y_mr.mean())
    s0 = d[list(w)].rank(pct=True).fillna(0.5).to_numpy() @ np.array(list(w.values()))
    hw = np.nan_to_num(d.y_mr.to_numpy())
    def m(sc, mask=None):
        s = np.where(mask, sc - sc[mask].min() + 1.0, 0.0) if mask is not None else sc
        k = top_k_nms(st, en, s)
        return (float(rel[k].max() > 0), f1_temporal([(st[i], en[i]) for i in k], heat), float(d.y_mr.to_numpy()[k].mean()/mh))
    r = {"video_id": v, "lang": man.loc[v, "query_lang"] if v in man.index else "?", "channel_id": meta["channel_id"]}
    for name, (sc, mask) in {"V0": (s0, None), "V1": (s0, short), "calor": (hw, None)}.items():
        r[f"{name}_hit"], r[f"{name}_F1"], r[f"{name}_lift"] = m(sc, mask)
    r["azar_hit"], r["azar_F1"], r["azar_lift"] = np.mean([m(rng.random(len(d))) for _ in range(100)], axis=0)
    r["azar_corto_hit"], r["azar_corto_F1"], r["azar_corto_lift"] = np.mean([m(rng.random(len(d)), short) for _ in range(100)], axis=0)
    rows.append(r)
pv = pd.DataFrame(rows)
out = ROOT/"reports"/"replicacion_D052"; out.mkdir(exist_ok=True)
pv.to_csv(out/"por_video.csv", index=False, encoding="utf-8-sig")
res = {"n_videos": len(pv), "n_canales": int(pv.channel_id.nunique()), "descriptiva": len(pv) < 40,
       "hit5": {k: float(pv[f"{k}_hit"].mean()) for k in ("azar", "azar_corto", "V0", "V1", "calor")},
       "F1": {k: float(pv[f"{k}_F1"].mean()) for k in ("azar", "azar_corto", "V0", "V1", "calor")},
       "lift": {k: float(pv[f"{k}_lift"].mean()) for k in ("azar", "azar_corto", "V0", "V1", "calor")}}
if len(pv) >= 5:
    res["H_R1_V1_hit_vs_azar_corto_p"] = float(stats.wilcoxon(pv.V1_hit, pv.azar_corto_hit, alternative="greater").pvalue)
    res["V0_F1_vs_azar_p"] = float(stats.wilcoxon(pv.V0_F1, pv.azar_F1, alternative="greater").pvalue)
    a, b = pv.V1_hit.to_numpy() > 0, pv.V0_hit.to_numpy() > 0
    oa, ob = int((a & ~b).sum()), int((~a & b).sum())
    res["V1_vs_V0_McNemar"] = {"solo_V1": oa, "solo_V0": ob, "p": float(stats.binomtest(oa, oa+ob, 0.5).pvalue) if oa+ob else None}
    res["por_idioma"] = {l: {"n": int(len(g)), "V0_hit": float(g.V0_hit.mean()), "V1_hit": float(g.V1_hit.mean()),
                              "azar_hit": float(g.azar_hit.mean()), "V0_F1": float(g.V0_F1.mean())} for l, g in pv.groupby("lang")}
json.dump(res, open(out/"resultado.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
