"""D-099: la formula de 17 variables restringida a las variables con respaldo en papers (FUENTES/RESPALDO_VARIABLES_EN_PAPERS.md).
Descriptivo, UNA corrida, los subconjuntos se definieron por la revision bibliografica (no mirando resultados) y se mantienen los pesos originales.
Sin tocar el modelo final. Salida: reports/subconjuntos_respaldo_D099.json."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms
from src.common.config import load_config
from src.ranking.labels import corrected_graph
from src.ranking.retention import formula_raw
cfg = load_config("configs/gpu.yaml"); bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
DIRECTO = ["a_rms_std", "a_pitch_range", "a_pitch_std", "s_second_person"]
METODO = ["k_keybert_sim"]
INDIRECTO = ["a_pause_ratio", "l_silence", "a_long_pauses_pm", "e_music_max", "e_music_mean", "s_questions_pm", "k_noun_chunks_ps"]
SUBS = {"17 variables (modelo actual)": list(W), "12 con respaldo (directo + metodo + indirecto)": DIRECTO + METODO + INDIRECTO,
        "5 (directo + metodo)": DIRECTO + METODO, "4 (solo directo)": DIRECTO,
        "5 sin respaldo (control)": [k for k in W if k not in DIRECTO + METODO + INDIRECTO and k != "a_speech_rate"],
        "1 posible contradiccion (a_speech_rate)": ["a_speech_rate"]}
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])
grupos = {"cohorte fresca 1": J("conjunto_confirmacion_fresca_D050.json"), "cohorte fresca 2": J("conjunto_confirmacion_fresca2_D065.json")}
grupos["desarrollo"] = {p.stem for p in bd.glob("*.parquet")} - set().union(*grupos.values())
out = {}
for g, ids in grupos.items():
    R = {(s, m): [] for s in SUBS for m in ("0/1", "continuo")}
    R[("azar", "")] = []
    rng = np.random.default_rng(0)
    n = 0
    for v in sorted(ids):
        p = bd / f"{v}.parquet"
        if not p.exists() or not (hd / f"{v}.json").exists(): continue
        d = pd.read_parquet(p)
        if len(d) != 100 or not all(k in d for k in W): continue
        n += 1
        heat = heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"]))
        st, en, rel = d["start"].to_numpy(), d["end"].to_numpy(), d["y_relevant"].to_numpy()
        def ev(S):
            k = top_k_nms(st, en, S)
            return (float(rel[k].max() > 0), f1_temporal([(st[j], en[j]) for j in k], heat))
        for s, cols in SUBS.items():
            w = {c: W[c] for c in cols}
            R[(s, "0/1")].append(ev(formula_raw(d, w, True)))
            R[(s, "continuo")].append(ev(formula_raw(d, w, False)))
        R[("azar", "")].append(ev(rng.random(100)))
    A = {k: np.array(x) for k, x in R.items()}
    base = A[("17 variables (modelo actual)", "0/1")]
    out[g] = {"n": n}
    print(f"\n=== {g} (n={n}) | azar {A[('azar','')][:,0].mean():.1%} / {A[('azar','')][:,1].mean():.3f}")
    for (s, m), a in A.items():
        if s == "azar": continue
        dF = a[:, 1] - base[:, 1] if m == "0/1" else None
        p = float(stats.wilcoxon(a[:, 1], base[:, 1]).pvalue) if (m == "0/1" and np.any(dF != 0)) else None
        out[g][f"{s} | {m}"] = {"hit5": float(a[:, 0].mean()), "F1": float(a[:, 1].mean()), "dif_F1_vs_17_01": float(dF.mean()) if dF is not None else None, "p": p}
        print(f"  {s:50s} {m:9s} hit@5 {a[:,0].mean():5.1%}  F1 {a[:,1].mean():.3f}" + (f"  dF1 vs 17(0/1) {dF.mean():+.4f} p={p:.3f}" if p is not None else ""))
Path(ROOT / "reports" / "subconjuntos_respaldo_D099.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
