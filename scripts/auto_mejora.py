"""Agente de mejora automática (D-095). Corre solo, sin intervención: en cada ronda
  1) (cada N rondas) refresca el minero de papers y lee qué señales faltan;
  2) GENERA variables nuevas: expresiones aleatorias (razones, productos, diferencias, máx/mín, suavizados, derivadas temporales)
     sobre las 68 variables base, más las m_* minadas;
  3) las criba con validación cruzada por canal SOLO en el conjunto de desarrollo;
  4) el mejor candidato se enfrenta al campeón en el conjunto reservado (md5(canal)%5==0) con Wilcoxon unilateral y
     Bonferroni sobre el presupuesto total de pruebas; si gana, se PROMUEVE y el campeón incorpora la variable;
  5) registra todo (estado.json, rondas.jsonl) y repite hasta que se detenga el proceso.
La curva Most Replayed solo califica (etiquetas); nunca entra como variable. Cohortes frescas no se tocan aquí.
Uso: python scripts/auto_mejora.py [--rondas N] [--cands K]   (sin --rondas: infinito)"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

ARG = lambda k, d: (int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d)  # noqa: E731
RONDAS, NC = ARG("--rondas", 10**9), ARG("--cands", 10)
BUDGET = 25  # pruebas máximas sobre el reservado -> alfa de Bonferroni = 0.05/25
OUT = ROOT / "reports" / "auto_mejora"
OUT.mkdir(parents=True, exist_ok=True)
EST = OUT / "estado.json"

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"]) if (ROOT / "reports" / f).exists() else set()  # noqa: E731
reservados = J("conjunto_confirmacion_fresca_D050.json") | J("conjunto_confirmacion_fresca2_D065.json") | J("conjunto_confirmacion_fresca3_D091.json")
reservados |= set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])
reservados |= J("conjunto_libres_D078.json") | J("conjunto_entrenamiento_extra_D071.json")
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
CH = np.array(CH)
n = len(V)
G = np.stack([d["y_grade"].to_numpy(int) for d in T])
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in V]
RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])  # n x 100 x 68
hold = np.array([int(hashlib.md5(str(c).encode()).hexdigest(), 16) % 5 == 0 for c in CH])
dev_i, ho_i = np.nonzero(~hold)[0], np.nonzero(hold)[0]
print(f"videos {n} | desarrollo {len(dev_i)} | reservado {len(ho_i)}", flush=True)

P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
         min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
         num_threads=4, verbose=-1, seed=42, deterministic=True, force_row_wise=True)


def fit_pred(X, tr, te, rounds=200):
    m = lgb.train(P, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), rounds)
    return m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)


def metrica(S, idx):
    r = []
    for k, i in enumerate(idx):
        sel = top_k_nms(ST[i], EN[i], S[k])
        r.append((float(REL[i][sel].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in sel], HEAT[i])))
    return np.array(r)


def cv_dev(X):
    o = np.zeros((len(dev_i), 100))
    pos = {v: k for k, v in enumerate(dev_i)}
    for tr, te in GroupKFold(5).split(dev_i, groups=CH[dev_i]):
        o[te] = fit_pred(X, dev_i[tr], dev_i[te])
    return metrica(o, dev_i)


# ---------------- generador de variables (matemática nueva: expresiones sobre las variables base)
OPS = ["prod", "dif", "ratio", "max", "min", "suav", "deriv", "dist_mediana", "z_loc"]


def shift(x, k):
    o = np.roll(x, k, axis=1)
    if k > 0:
        o[:, :k] = 0.5
    else:
        o[:, k:] = 0.5
    return o


def evalua(expr):
    op, i, j = expr["op"], expr["i"], expr.get("j", 0)
    a, b = RK[:, :, i], RK[:, :, j]
    if op == "prod":
        x = a * b
    elif op == "dif":
        x = a - b
    elif op == "ratio":
        x = a / (b + 0.05)
    elif op == "max":
        x = np.maximum(a, b)
    elif op == "min":
        x = np.minimum(a, b)
    elif op == "suav":
        x = (shift(a, 1) + a + shift(a, -1) + shift(a, 2) + shift(a, -2)) / 5
    elif op == "deriv":
        x = a - shift(a, 1)
    elif op == "dist_mediana":
        x = np.abs(a - 0.5)
    else:  # z_loc: contraste local contra el entorno
        x = a - (shift(a, 3) + shift(a, -3)) / 2
    r = np.apply_along_axis(lambda z: pd.Series(z).rank(pct=True).to_numpy(), 1, x)
    return r.astype(np.float32)


def texto(e):
    f = feats
    op = e["op"]
    if op in ("prod", "dif", "ratio", "max", "min"):
        return f"{op}({f[e['i']]}, {f[e['j']]})"
    return f"{op}({f[e['i']]})"


def refrescar_minero():
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "minero_papers.py")], timeout=900, capture_output=True)
        return json.loads((ROOT / "reports" / "minero_papers" / "resumen.json").read_text(encoding="utf-8")).get("n_papers")
    except Exception as e:  # noqa: BLE001
        return f"fallo {str(e)[:60]}"


est = json.loads(EST.read_text(encoding="utf-8")) if EST.exists() else {"ronda": 0, "campeon_vars": [], "pruebas_reservado": 0, "historial": []}
rng = np.random.default_rng(int(time.time()) % 2**31)


def matriz_campeon():
    cols = [evalua(e) for e in est["campeon_vars"]]
    return np.concatenate([RK] + [c[:, :, None] for c in cols], axis=2) if cols else RK


while est["ronda"] < RONDAS:
    est["ronda"] += 1
    t0 = time.time()
    extra = ""
    if est["ronda"] % 10 == 1:
        extra = f"minero refrescado: {refrescar_minero()} papers"
    Xc = matriz_campeon()
    base = cv_dev(Xc)
    cands = []
    for _ in range(NC):
        op = str(rng.choice(OPS))
        e = {"op": op, "i": int(rng.integers(len(feats))), "j": int(rng.integers(len(feats)))}
        if op in ("prod", "dif", "ratio", "max", "min") and e["i"] == e["j"]:
            continue
        x = evalua(e)
        m = cv_dev(np.concatenate([Xc, x[:, :, None]], axis=2))
        cands.append((float(m[:, 1].mean() - base[:, 1].mean()), e, m))
    cands.sort(key=lambda c: -c[0])
    mejor = cands[0]
    reg = {"ronda": est["ronda"], "dev_F1_campeon": float(base[:, 1].mean()), "mejor_candidato": texto(mejor[1]), "dev_dif_F1": mejor[0],
           "n_candidatos": len(cands), "extra": extra, "promovido": False}
    if mejor[0] > 0.002 and est["pruebas_reservado"] < BUDGET:  # solo si vale la pena gastar una prueba del presupuesto
        est["pruebas_reservado"] += 1
        alfa = 0.05 / BUDGET
        xn = evalua(mejor[1])
        Xn = np.concatenate([Xc, xn[:, :, None]], axis=2)
        a = metrica(fit_pred(Xc, dev_i, ho_i, 300), ho_i)
        b = metrica(fit_pred(Xn, dev_i, ho_i, 300), ho_i)
        try:
            p = float(stats.wilcoxon(b[:, 1], a[:, 1], alternative="greater").pvalue)
        except ValueError:
            p = 1.0
        reg.update({"reservado_F1_campeon": float(a[:, 1].mean()), "reservado_F1_retador": float(b[:, 1].mean()), "p_wilcoxon": p, "alfa_bonferroni": alfa,
                    "hit5_campeon": float(a[:, 0].mean()), "hit5_retador": float(b[:, 0].mean())})
        if p < alfa:
            est["campeon_vars"].append(mejor[1])
            reg["promovido"] = True
    elif mejor[0] > 0.002:  # presupuesto del reservado agotado: queda en cola para la confirmación en cohorte fresca (D-091)
        est.setdefault("cola_confirmacion", []).append({"expr": mejor[1], "texto": texto(mejor[1]), "dev_dif_F1": mejor[0], "ronda": est["ronda"]})
        reg["en_cola"] = True
    est["historial"].append(reg)
    EST.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / "rondas.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(f"ronda {est['ronda']} ({time.time() - t0:.0f}s) mejor {reg['mejor_candidato']} dev {mejor[0]:+.4f}"
          + (f" | reservado p={reg['p_wilcoxon']:.4f} promovido={reg['promovido']}" if "p_wilcoxon" in reg else " | sin prueba") + f" | vars aprendidas {len(est['campeon_vars'])}", flush=True)
