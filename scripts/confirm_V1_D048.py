"""Confirmacion preregistrada (D-048): V1 = formula D-045 restringida a clips <= 45 s. Una sola corrida."""
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
dev = set(json.load(open(ROOT/"reports"/"conjunto_desarrollo_D038.json", encoding="utf-8"))["video_ids"])
rep = set(json.load(open(ROOT/"reports"/"conjunto_humano_D040.json", encoding="utf-8"))["replica_independiente"])
rng = np.random.default_rng(42)
rows = []
for p in sorted(fd.glob("*.parquet")):
    v = p.stem
    if v in dev or v in rep or not (hd/f"{v}.json").exists(): continue
    d = pd.read_parquet(p); meta = json.load(open(hd/f"{v}.json", encoding="utf-8"))
    if not meta.get("heatmap") or any(c not in d for c in w) or "y_relevant" not in d: continue
    st, en = d.start.to_numpy(), d.end.to_numpy(); dur = en - st; short = dur <= 45.0
    if short.sum() < 5: continue
    heat_iv = heat_intervals(corrected_graph(meta["heatmap"]))
    rel = d.y_relevant.to_numpy(); mh = float(d.y_mr.mean())
    s0 = d[list(w)].rank(pct=True).fillna(0.5).to_numpy() @ np.array(list(w.values()))
    s1 = np.where(short, s0 - s0.min() + 1.0, 0.0)
    hw = np.nan_to_num(d.y_mr.to_numpy())
    def m(sc):
        k = top_k_nms(st, en, sc)
        return (float(rel[k].max() > 0), f1_temporal([(st[i], en[i]) for i in k], heat_iv), float(d.y_mr.to_numpy()[k].mean()/mh))
    r = {"video_id": v, "channel_id": meta["channel_id"]}
    for name, sc in {"V0": s0, "V1": s1, "calor_directo": hw, "calor_cortos": np.where(short, hw, -1.0)}.items():
        r[f"{name}_hit"], r[f"{name}_F1"], r[f"{name}_lift"] = m(sc)
    dr = [m(rng.random(len(d))) for _ in range(100)]; ds = [m(np.where(short, rng.random(len(d)), -1.0)) for _ in range(100)]
    r["azar_hit"], r["azar_F1"], r["azar_lift"] = np.mean(dr, axis=0)
    r["azar_corto_hit"], r["azar_corto_F1"], r["azar_corto_lift"] = np.mean(ds, axis=0)
    rows.append(r)
pv = pd.DataFrame(rows)
out_dir = ROOT/"reports"/"confirmacion_D048"; out_dir.mkdir(exist_ok=True)
pv.to_csv(out_dir/"por_video.csv", index=False, encoding="utf-8-sig")
a, b = pv.V1_hit.to_numpy() > 0, pv.V0_hit.to_numpy() > 0
oa, ob = int((a & ~b).sum()), int((~a & b).sum())
res = {"n_videos": len(pv), "n_canales": int(pv.channel_id.nunique()),
       "hit5": {k: float(pv[f"{k}_hit"].mean()) for k in ("azar", "azar_corto", "V0", "V1", "calor_directo", "calor_cortos")},
       "F1": {k: float(pv[f"{k}_F1"].mean()) for k in ("azar", "azar_corto", "V0", "V1", "calor_directo", "calor_cortos")},
       "lift": {k: float(pv[f"{k}_lift"].mean()) for k in ("azar", "azar_corto", "V0", "V1", "calor_directo", "calor_cortos")},
       "H_V1_McNemar": {"solo_V1": oa, "solo_V0": ob, "p_unilateral": float(stats.binomtest(oa, oa+ob, 0.5, alternative="greater").pvalue)},
       "V1_vs_azar_corto_hit_wilcoxon_p": float(stats.wilcoxon(pv.V1_hit, pv.azar_corto_hit, alternative="greater").pvalue),
       "V1_vs_V0_F1_wilcoxon_p_bilateral": float(stats.wilcoxon(pv.V1_F1, pv.V0_F1).pvalue),
       "V1_vs_V0_F1_dif": float((pv.V1_F1 - pv.V0_F1).mean())}
json.dump(res, open(out_dir/"resultado.json", "w", encoding="utf-8"), indent=1)
print(json.dumps(res, indent=1))
