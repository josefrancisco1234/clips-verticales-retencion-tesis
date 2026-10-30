"""Ciclo campeón/retador (pedido de la profesora): reentrena y promueve solo con evidencia.

    python scripts/campeon_retador.py            # una ronda
    python scripts/campeon_retador.py --simular  # no escribe estado ni rondas (prueba en seco)

Reglas (fijadas antes de correr):
- Conjunto de desarrollo = videos con 100 bins + 68 variables que NO están en las cohortes frescas (D-050, D-065), en la
  réplica Repurpose ni en el conjunto reservado de D-075/D-078 (hasta que D-075 corra y los libere).
- Holdout CONGELADO por canal: un canal va al holdout si md5(channel_id) % 5 == 0. Mismo canal, misma decisión en todas las rondas.
- Campeón inicial: LightGBM R0 (lambdarank sobre rangos). Retador: BiGRU 128 (MSE, dropout 0.3, 3 semillas) sobre los mismos rangos.
- Se promueve al retador solo si su F1 temporal@5 es mayor y Wilcoxon pareado unilateral p < 0.05 en el holdout. Si no, el campeón sigue.
- Cada ronda se agrega a reports/campeon_retador/rondas.jsonl (también las negativas). La curva solo califica, nunca entra al modelo.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import scripts.dl_secuencia_D054 as dl  # noqa: E402
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

SIMULAR = "--simular" in sys.argv
cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
OUT = ROOT / "reports" / "campeon_retador"
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])  # noqa: E731
reservados = J("conjunto_confirmacion_fresca_D050.json") | J("conjunto_confirmacion_fresca2_D065.json")
if not (ROOT / "reports" / "confirmacion_D075" / "resultado.json").exists():  # D-075 aún no corrió: siguen reservados
    for f in ("conjunto_libres_D078.json", "conjunto_entrenamiento_extra_D071.json"):
        if (ROOT / "reports" / f).exists():
            reservados |= J(f)
reservados |= set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])

V, T, CH = [], [], []
for p in sorted(bd.glob("*.parquet")):
    v = p.stem
    if v in reservados or not (hd / f"{v}.json").exists():
        continue
    d = pd.read_parquet(p)
    if len(d) == 100 and all(f in d for f in feats):
        V.append(v)
        T.append(d)
        CH.append(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["channel_id"])
in_hold = np.array([int(hashlib.md5(str(c).encode()).hexdigest(), 16) % 5 == 0 for c in CH])
tr, te = np.where(~in_hold)[0], np.where(in_hold)[0]
print(f"desarrollo={len(V)} | entrenamiento={len(tr)} | holdout congelado={len(te)} ({len(set(np.array(CH)[te]))} canales)", flush=True)

RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
G = np.stack([d["y_grade"].to_numpy(int) for d in T])
Y = np.stack([d["y_mr"].to_numpy(np.float32) for d in T])
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in V]
P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=8, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def champion_lgbm():
    m = lgb.train(P, lgb.Dataset(RK[tr].reshape(-1, RK.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
    return m.predict(RK[te].reshape(-1, RK.shape[2])).reshape(len(te), 100)


def challenger_gru():
    c = ("GRU128_mse_d3", "gru", 128, "mse", 0.3, False)
    return np.mean([dl.fit_predict(torch.tensor(RK[tr], device=dl.DEV), torch.tensor(Y[tr], device=dl.DEV),
                                   torch.tensor(RK[te], device=dl.DEV), c, 42 + s) for s in range(3)], axis=0)


def ev(S):
    o = []
    for k, i in enumerate(te):
        sel = top_k_nms(ST[i], EN[i], S[k])
        o.append((float(REL[i][sel].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in sel], HEAT[i])))
    return np.array(o)


state_p = OUT / "estado.json"
state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {"campeon": "LGBM_R0", "ronda": 0}
models = {"LGBM_R0": champion_lgbm, "BiGRU128": challenger_gru}
champ = state["campeon"]
chall = "BiGRU128" if champ == "LGBM_R0" else "LGBM_R0"
t0 = time.time()
rc, rr = ev(models[champ]()), ev(models[chall]())
d = rr[:, 1] - rc[:, 1]
p = float(stats.wilcoxon(rr[:, 1], rc[:, 1], alternative="greater").pvalue) if np.any(d != 0) else 1.0
promueve = bool(d.mean() > 0 and p < 0.05)
ronda = {"ronda": state["ronda"] + 1, "fecha": time.strftime("%Y-%m-%d %H:%M"), "n_entrenamiento": int(len(tr)), "n_holdout": int(len(te)),
         "campeon": champ, "retador": chall,
         "campeon_hit5": float(rc[:, 0].mean()), "campeon_F1": float(rc[:, 1].mean()),
         "retador_hit5": float(rr[:, 0].mean()), "retador_F1": float(rr[:, 1].mean()),
         "dif_F1": float(d.mean()), "p_unilateral": p, "promueve": promueve,
         "campeon_nuevo": chall if promueve else champ, "segundos": round(time.time() - t0)}
print(json.dumps(ronda, indent=1, ensure_ascii=False))
if not SIMULAR:
    with open(OUT / "rondas.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ronda, ensure_ascii=False) + "\n")
    state_p.write_text(json.dumps({"campeon": ronda["campeon_nuevo"], "ronda": ronda["ronda"]}), encoding="utf-8")
