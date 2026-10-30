"""D-066: ingenieria inversa exploratoria de los picos de retencion (sin decision de modelo asociada).

(a) alineacion de picos con capitulos de YouTube, (b) promedio disparado por picos (que hay antes/despues),
(c) analisis de error: cuando acierta y cuando falla el modelo, (d) metadatos del video como contexto.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import PREFIXES, f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "ingenieria_inversa_D066"
OUT.mkdir(parents=True, exist_ok=True)
base = np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)
vids = [str(v) for v in base["vids"]]
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
T = {v: pd.read_parquet(bd / f"{v}.parquet") for v in vids}
M = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
Y = base["Y"]
rng = np.random.default_rng(0)

# ---------------------------------------------------------------- (a) capitulos
n_ch = sum(1 for v in vids if M[v].get("chapters"))
print(f"(a) videos con capitulos de YouTube: {n_ch}/{len(vids)} ({n_ch / len(vids):.0%})")
rows = []
for i, v in enumerate(vids):
    ch = M[v].get("chapters")
    if not ch or len(ch) < 3:
        continue
    starts = np.array([c["start_time"] for c in ch if c["start_time"] > 1.0])
    bs, be = T[v]["start"].to_numpy(), T[v]["end"].to_numpy()
    has = np.array([((starts >= s) & (starts < e)).any() for s, e in zip(bs, be)])
    if has.sum() == 0 or has.all():
        continue
    r = pd.Series(Y[i]).rank(pct=True).to_numpy()
    top5 = np.argsort(-Y[i])[:5]
    exp = 1 - np.prod([(len(has) - has.sum() - k) / (len(has) - k) for k in range(5)])
    rows.append(dict(video=v, n_cap=len(starts), rank_heat_en_bin_con_capitulo=r[has].mean(),
                     rank_heat_resto=r[~has].mean(), top5_contiene_capitulo=float(has[top5].any()),
                     esperado_azar=float(exp)))
if rows:
    ca = pd.DataFrame(rows)
    d = ca.rank_heat_en_bin_con_capitulo - ca.rank_heat_resto
    print(f"    videos analizables={len(ca)} | rango de calor del bin con inicio de capitulo = "
          f"{ca.rank_heat_en_bin_con_capitulo.mean():.3f} vs resto {ca.rank_heat_resto.mean():.3f} "
          f"(Wilcoxon p = {stats.wilcoxon(d).pvalue:.4g})")
    print(f"    el top-5 de calor contiene un inicio de capitulo en {ca.top5_contiene_capitulo.mean():.1%} "
          f"de los videos (esperado por azar {ca.esperado_azar.mean():.1%})")
    ca.to_csv(OUT / "capitulos.csv", index=False)

# ---------------------------------------------------------------- (b) promedio disparado por picos
K = 6
prof, n_pk = {f: [] for f in feats}, 0
for i, v in enumerate(vids):
    y = Y[i]
    rk = T[v][feats].rank(pct=True).fillna(0.5).to_numpy()
    for j in np.argsort(-y)[:3]:
        if K <= j < 100 - K and y[j] >= y[j - 1] and y[j] >= y[j + 1]:
            n_pk += 1
            for fi, f in enumerate(feats):
                prof[f].append(rk[j - K:j + K + 1, fi] - 0.5)
print(f"\n(b) picos analizados (maximos locales entre los 3 mayores, sin bordes): {n_pk}")
tab = []
for f in feats:
    a = np.array(prof[f])
    mu = a.mean(axis=0)
    se = a.std(axis=0, ddof=1) / np.sqrt(len(a))
    z = mu / (se + 1e-12)
    j = int(np.argmax(np.abs(z)))
    tab.append(dict(feature=f, offset_max=j - K, efecto=float(mu[j]), z=float(z[j]), z_en_pico=float(z[K]),
                    perfil=mu.round(3).tolist()))
tb = pd.DataFrame(tab).sort_values("z", key=np.abs, ascending=False)
tb.drop(columns="perfil").to_csv(OUT / "promedio_disparado.csv", index=False)
print("    top 12 por |z| (offset en bins de ~35 s; 0 = bin del pico; efecto = rango percentil medio - 0.5):")
for _, r in tb.head(12).iterrows():
    print(f"      {r.feature:22s} offset {int(r.offset_max):+d}  efecto {r.efecto:+.3f}  z={r.z:+.1f}")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

top = tb.head(18)
mat = np.array([r.perfil for _, r in top.iterrows()])
fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(mat, aspect="auto", cmap="RdBu_r", vmin=-0.15, vmax=0.15)
ax.set_yticks(range(len(top)))
ax.set_yticklabels(top.feature, fontsize=8)
ax.set_xticks(range(0, 2 * K + 1, 2))
ax.set_xticklabels([str(o) for o in range(-K, K + 1, 2)])
ax.axvline(K, color="k", lw=0.8, ls="--")
ax.set_xlabel("bins respecto al pico (0 = pico)")
ax.set_title(f"Que rodea a un pico de retencion ({n_pk} picos): rango percentil - 0.5")
fig.colorbar(im)
fig.tight_layout()
fig.savefig(OUT / "fig_promedio_disparado.png", dpi=110)

# ---------------------------------------------------------------- (c) analisis de error
from scripts.reverse_engineering_formula import f1_temporal as _f1  # noqa: E402,F811

S = base["LGBM_bin"]
rec = []
for i, v in enumerate(vids):
    st, en = T[v].start.to_numpy(), T[v].end.to_numpy()
    k = top_k_nms(st, en, S[i])
    hit = float(T[v].y_relevant.to_numpy()[k].max() > 0)
    f1 = _f1([(st[j], en[j]) for j in k], heat_intervals(corrected_graph(M[v]["heatmap"])))
    y = Y[i]
    rec.append(dict(video=v, hit=hit, F1=f1, dur_min=M[v]["duration"] / 60,
                    log_views=np.log10(max(M[v].get("view_count") or 1, 1)),
                    lang=M[v].get("language") or "?", n_bins_hl=int((y > 0.5).sum()),
                    picudez=float((y.max() - np.median(y)) / (y.std() + 1e-9)),
                    curtosis=float(stats.kurtosis(y)), heat_medio=float(y.mean()),
                    tiene_capitulos=int(bool(M[v].get("chapters")))))
er = pd.DataFrame(rec)
print("\n(c) correlacion de Spearman con el acierto (hit@5) y el F1 por video:")
for col in ("dur_min", "log_views", "n_bins_hl", "picudez", "curtosis", "heat_medio", "tiene_capitulos"):
    print(f"      {col:16s} con hit: {stats.spearmanr(er[col], er.hit)[0]:+.3f} | con F1: {stats.spearmanr(er[col], er.F1)[0]:+.3f}")
er["cuartil_picudez"] = pd.qcut(er.picudez, 4, labels=["Q1 plano", "Q2", "Q3", "Q4 picudo"])
print("    por cuartil de 'picudez' de la curva:")
print(er.groupby("cuartil_picudez", observed=True)[["hit", "F1"]].mean().round(3).to_string())
er["cuartil_dur"] = pd.qcut(er.dur_min, 4, labels=["Q1 corto", "Q2", "Q3", "Q4 largo"])
print("    por cuartil de duracion:")
print(er.groupby("cuartil_dur", observed=True)[["hit", "F1", "dur_min"]].mean().round(3).to_string())
er.to_csv(OUT / "error_por_video.csv", index=False)

# ---------------------------------------------------------------- (d) metadatos como contexto
import lightgbm as lgb  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

chan = np.array([M[v]["channel_id"] for v in vids])
RK = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
G = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
meta = np.array([[np.log(M[v]["duration"]), np.log10(max(M[v].get("view_count") or 1, 1)),
                  float((M[v].get("language") or "en").startswith("es")),
                  float(bool(M[v].get("chapters")))] for v in vids], dtype=np.float32)
X2 = np.concatenate([RK, np.repeat(meta[:, None, :], 100, axis=1)], axis=2)
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=4, verbose=-1, seed=42, deterministic=True, force_row_wise=True)
o = np.zeros_like(Y)
for tr, te in GroupKFold(10).split(np.arange(len(vids)), groups=chan):
    m = lgb.train(P, lgb.Dataset(X2[tr].reshape(-1, X2.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
    o[te] = m.predict(X2[te].reshape(-1, X2.shape[2])).reshape(len(te), 100)
f_base, f_meta = [], []
for i, v in enumerate(vids):
    st, en = T[v].start.to_numpy(), T[v].end.to_numpy()
    hv = heat_intervals(corrected_graph(M[v]["heatmap"]))
    for S_, acc in ((S, f_base), (o, f_meta)):
        k = top_k_nms(st, en, S_[i])
        acc.append(_f1([(st[j], en[j]) for j in k], hv))
fb, fm = np.array(f_base), np.array(f_meta)
print(f"\n(d) metadatos (duracion, vistas, idioma, capitulos) como contexto: F1 {fb.mean():.3f} -> {fm.mean():.3f} "
      f"(dif {fm.mean() - fb.mean():+.4f}, Wilcoxon p = {stats.wilcoxon(fm, fb).pvalue:.3f})")
json.dump({"n_picos": n_pk, "capitulos_disponibles": n_ch, "F1_base": float(fb.mean()), "F1_con_metadatos": float(fm.mean())},
          open(OUT / "resumen.json", "w", encoding="utf-8"), indent=1)
