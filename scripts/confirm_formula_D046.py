"""Confirmacion preregistrada (D-046) de la formula de contenido de D-045.

Pesos CONGELADOS desde reports/reverse_engineering_dev121/resumen.json (clave
formula_calor). Se evalua UNA sola vez en los videos que no estan en desarrollo.
No ajusta nada: solo lee los pesos y mide.
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

from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402
from src.ranking.model import RankerBundle  # noqa: E402
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402

OUT = ROOT / "reports" / "confirmacion_D046"
SEED = 42


def main():
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    w = json.load(open(ROOT / "reports" / "reverse_engineering_dev121" / "resumen.json", encoding="utf-8"))["formula_calor"]
    dev = set(json.load(open(ROOT / "reports" / "conjunto_desarrollo_D038.json", encoding="utf-8"))["video_ids"])
    hum = json.load(open(ROOT / "reports" / "conjunto_humano_D040.json", encoding="utf-8"))
    replica = set(hum["replica_independiente"])
    feat_dir = cfg.path("processed") / "features" / "sentence"
    heat_dir = cfg.path("interim") / "heatmaps"
    ids = sorted(p.stem for p in feat_dir.glob("*.parquet") if (heat_dir / f"{p.stem}.json").exists())
    conf = [v for v in ids if v not in dev and v not in replica]
    print(f"confirmacion: {len(conf)} videos (excluidos {len(replica & set(ids))} de la replica humana)")
    print("pesos congelados:", len(w), "features")

    bundle = RankerBundle.load(ROOT / "models")
    rng = np.random.default_rng(SEED)
    rows = []
    for v in conf:
        d = pd.read_parquet(feat_dir / f"{v}.parquet")
        meta = json.load(open(heat_dir / f"{v}.json", encoding="utf-8"))
        if not meta.get("heatmap") or any(c not in d for c in w):
            continue
        bins = corrected_graph(meta["heatmap"])
        heat_iv = heat_intervals(bins)
        rk = d[list(w)].rank(pct=True).fillna(0.5)
        s_form = rk.to_numpy() @ np.array([w[c] for c in w])
        ok_q = ((d["f_starts_dangling"] == 0) & (d["f_ends_complete"] == 1)).to_numpy()
        s_form_q = np.where(ok_q, s_form - s_form.min() + 1.0, 0.0)
        s_model = bundle.score(d)["raw"].to_numpy()
        heat_w = np.nan_to_num(d["y_mr"].to_numpy(), nan=0.0)
        st, en = d["start"].to_numpy(), d["end"].to_numpy()
        mean_heat = float(d["y_mr"].mean())
        row = {"video_id": v, "channel_id": meta["channel_id"], "lang": meta.get("language"),
               "dur_min": meta["duration"] / 60, "n_cand": len(d)}
        for name, sc in {"formula": s_form, "formula_mas_calidad": s_form_q, "modelo_prod": s_model,
                         "calor_directo": heat_w, "calor_mas_calidad": np.where(ok_q, heat_w, -1.0)}.items():
            keep = top_k_nms(st, en, sc)
            cl = [(st[i], en[i]) for i in keep]
            row[f"{name}_tF1"] = f1_temporal(cl, heat_iv)
            row[f"{name}_lift"] = float(d["y_mr"].to_numpy()[keep].mean() / mean_heat)
            row[f"{name}_colgado"] = float(d["f_starts_dangling"].to_numpy()[keep].mean())
        draws = []
        for _ in range(200):
            keep = top_k_nms(st, en, rng.random(len(d)))
            draws.append((f1_temporal([(st[i], en[i]) for i in keep], heat_iv),
                          float(d["y_mr"].to_numpy()[keep].mean() / mean_heat)))
        row["azar_tF1"], row["azar_lift"] = np.mean(draws, axis=0)
        rows.append(row)
    pv = pd.DataFrame(rows)
    pv.to_csv(OUT / "por_video.csv", index=False, encoding="utf-8-sig")

    def test(a, b, col, alt="two-sided", by_channel=False):
        x, y = pv[f"{a}_{col}"].to_numpy(float), pv[f"{b}_{col}"].to_numpy(float)
        if by_channel:
            g = pv.groupby("channel_id")[[f"{a}_{col}", f"{b}_{col}"]].mean()
            x, y = g.iloc[:, 0].to_numpy(), g.iloc[:, 1].to_numpy()
        ok = ~(np.isnan(x) | np.isnan(y))
        p = float(stats.wilcoxon(x[ok], y[ok], alternative=alt).pvalue)
        return {"n": int(ok.sum()), "media_a": float(x[ok].mean()), "media_b": float(y[ok].mean()),
                "dif": float((x[ok] - y[ok]).mean()), "a_mejor_en": int((x[ok] > y[ok]).sum()), "p": p, "alt": alt}

    res = {"n_videos": len(pv), "n_canales": int(pv.channel_id.nunique()),
           "H_F1_primaria_formula_vs_azar_tF1": test("formula", "azar", "tF1", "greater"),
           "H_F1_por_canal": test("formula", "azar", "tF1", "greater", by_channel=True),
           "formula_vs_modelo_tF1": test("formula", "modelo_prod", "tF1"),
           "formula_vs_azar_lift": test("formula", "azar", "lift"),
           "modelo_vs_azar_tF1": test("modelo_prod", "azar", "tF1"),
           "formula_calidad_vs_azar_tF1": test("formula_mas_calidad", "azar", "tF1"),
           "formula_calidad_inicio_colgado_media": float(pv.formula_mas_calidad_colgado.mean()),
           "formula_inicio_colgado_media": float(pv.formula_colgado.mean()),
           "calor_directo_tF1": float(pv.calor_directo_tF1.mean()), "calor_directo_lift": float(pv.calor_directo_lift.mean()),
           "calor_mas_calidad_tF1": float(pv.calor_mas_calidad_tF1.mean()),
           "calor_mas_calidad_lift": float(pv.calor_mas_calidad_lift.mean()),
           "por_idioma": {}}
    for lg, g in pv.groupby(pv["lang"].fillna("?")):
        if len(g) >= 10:
            res["por_idioma"][lg] = {"n": int(len(g)), "formula_tF1": float(g.formula_tF1.mean()),
                                     "azar_tF1": float(g.azar_tF1.mean()), "modelo_tF1": float(g.modelo_prod_tF1.mean())}
    json.dump(res, open(OUT / "resultado.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    print(json.dumps(res, indent=1, ensure_ascii=False))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    names = [("azar", "azar"), ("modelo_prod", "modelo actual"), ("formula", "formula contenido"),
             ("formula_mas_calidad", "formula + calidad"), ("calor_mas_calidad", "calor + calidad"),
             ("calor_directo", "calor directo")]
    for a, suf, t in zip(ax, ("tF1", "lift"), ("F1 temporal@5 vs picos", "calor del clip / calor del video")):
        a.boxplot([pv[f"{k}_{suf}"].dropna() for k, _ in names], tick_labels=[n for _, n in names], showmeans=True)
        a.set_title(f"{t} | CONFIRMACION n={len(pv)} videos nuevos")
        a.tick_params(axis="x", rotation=25, labelsize=8)
        if suf == "lift":
            a.axhline(1, color="gray", ls="--", lw=0.8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_confirmacion.png", dpi=110)


if __name__ == "__main__":
    main()
