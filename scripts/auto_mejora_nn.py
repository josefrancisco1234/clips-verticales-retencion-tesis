"""Agente de mejora automática con REDES NEURONALES (D-096). Corre solo, 24/7, en GPU.

El modelo que se mejora es una red EQL (Equation Learner, Sahoo et al. 2018) que entrega una ecuación legible. En cada ronda el agente
  1) MUTA la arquitectura del campeón (anchos de cada tipo de unidad, profundidad, penalización L1, tasa de aprendizaje), y
  2) INVENTA variables de entrada nuevas (variables base de las 68 o expresiones matemáticas sobre ellas: producto, razón, diferencia,
     máx, mín, suavizado, derivada temporal, distancia a la mediana, contraste local),
  3) entrena cada candidato en la GPU con validación cruzada por canal SOLO en desarrollo,
  4) enfrenta al mejor contra el campeón en el reservado (md5(canal)%5==0) con Wilcoxon unilateral y Bonferroni sobre el total de pruebas
     acumuladas, y si gana lo PROMUEVE (nueva arquitectura o nueva variable de entrada),
  5) registra todo y repite. Las mejores candidatas se confirman una sola vez en la cohorte fresca 3.
La curva Most Replayed solo califica; nunca entra como variable.   Uso: python scripts/auto_mejora_nn.py [--rondas N]"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as Fn
from scipy import stats
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.reverse_engineering_formula import f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

RONDAS = int(sys.argv[sys.argv.index("--rondas") + 1]) if "--rondas" in sys.argv else 10**9
PRUEBAS_PREVIAS = 25  # el reservado ya se usó 25 veces con el agente de LightGBM (D-095)
BUDGET = 25
ALFA = 0.05 / (PRUEBAS_PREVIAS + BUDGET)
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
OUT = ROOT / "reports" / "auto_mejora_nn"
OUT.mkdir(parents=True, exist_ok=True)
EST = OUT / "estado.json"

cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
F17 = [feats.index(k) for k in W if k in feats]
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
RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])  # n x 100 x 68
Y = np.stack([d["y_mr"].to_numpy(np.float32) for d in T])
Yz = (Y - Y.mean(1, keepdims=True)) / (Y.std(1, keepdims=True) + 1e-6)
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in V]
hold = np.array([int(hashlib.md5(str(c).encode()).hexdigest(), 16) % 5 == 0 for c in CH])
tr, te = np.nonzero(~hold)[0], np.nonzero(hold)[0]
print(f"videos {len(V)} | desarrollo {len(tr)} | reservado {len(te)} | dispositivo {DEV}", flush=True)


class EQL(nn.Module):
    """Capas de unidades identidad / tanh / producto / cuadrado seguidas de una salida lineal (ecuación legible)."""

    def __init__(self, f_in, n_id, n_tanh, n_prod, n_sq, depth):
        super().__init__()
        self.sizes = (n_id, n_tanh, n_prod, n_sq)
        width = n_id + n_tanh + 2 * n_prod + n_sq
        self.lin = nn.ModuleList()
        d_in = f_in
        for _ in range(depth):
            self.lin.append(nn.Linear(d_in, width))
            d_in = n_id + n_tanh + n_prod + n_sq
        self.out = nn.Linear(d_in, 1)

    def units(self, z):
        a, b, c, d = self.sizes
        i, t, p, s = torch.split(z, [a, b, 2 * c, d], dim=-1)
        return torch.cat([i, torch.tanh(t), p[..., :c] * p[..., c:], s ** 2], dim=-1)

    def forward(self, x):
        h = x
        for l in self.lin:
            h = self.units(l(h))
        return self.out(h).squeeze(-1)

    def l1(self):
        return sum(l.weight.abs().sum() for l in self.lin) + self.out.weight.abs().sum()


def fit(X, Yt_, hp, seed=0, epochs=50):
    torch.manual_seed(seed)
    net = EQL(X.shape[2], hp["n_id"], hp["n_tanh"], hp["n_prod"], hp["n_sq"], hp["depth"]).to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=hp["lr"], weight_decay=0.0)
    Xt, Yt = torch.tensor(X, device=DEV), torch.tensor(Yt_, device=DEV)
    n = Xt.shape[0]
    g = torch.Generator().manual_seed(seed)
    for ep in range(epochs):
        perm = torch.randperm(n, generator=g)
        lam = hp["l1"] * min(1.0, ep / (0.3 * epochs))
        for i in range(0, n, 16):
            idx = perm[i:i + 16].to(DEV)
            loss = -(Fn.softmax(2.0 * Yt[idx], dim=1) * Fn.log_softmax(net(Xt[idx]), dim=1)).sum(1).mean() + lam * net.l1()
            opt.zero_grad()
            loss.backward()
            opt.step()
    return net.eval()


def predict(net, X):
    with torch.no_grad():
        return net(torch.tensor(X, device=DEV)).cpu().numpy()


def score(S, idx):
    o = []
    for k, i in enumerate(idx):
        sel = top_k_nms(ST[i], EN[i], S[k])
        o.append((float(REL[i][sel].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in sel], HEAT[i])))
    return np.array(o)


def cv_dev(X, hp):
    o = np.zeros((len(tr), 100), np.float32)
    for a, b in GroupKFold(3).split(tr, groups=CH[tr]):
        o[b] = predict(fit(X[tr[a]], Yz[tr[a]], hp), X[tr[b]])
    return score(o, tr)


def shift(x, k):
    o = np.roll(x, k, axis=1)
    if k > 0:
        o[:, :k] = 0.5
    else:
        o[:, k:] = 0.5
    return o


OPS = ["base", "prod", "dif", "ratio", "max", "min", "suav", "deriv", "dist_mediana", "z_loc"]


def evalua(e):
    op, i, j = e["op"], e["i"], e.get("j", 0)
    a, b = RK[:, :, i], RK[:, :, j]
    x = {"base": a, "prod": a * b, "dif": a - b, "ratio": a / (b + 0.05), "max": np.maximum(a, b), "min": np.minimum(a, b),
         "suav": (shift(a, 1) + a + shift(a, -1) + shift(a, 2) + shift(a, -2)) / 5, "deriv": a - shift(a, 1), "dist_mediana": np.abs(a - 0.5),
         "z_loc": a - (shift(a, 3) + shift(a, -3)) / 2}[op]
    return np.apply_along_axis(lambda z: pd.Series(z).rank(pct=True).to_numpy(), 1, x).astype(np.float32)


def texto(e):
    return f"{e['op']}({feats[e['i']]}" + (f", {feats[e['j']]})" if e["op"] in ("prod", "dif", "ratio", "max", "min") else ")")


GRID = dict(n_id=[4, 8, 16], n_tanh=[0, 4, 8], n_prod=[0, 2, 4, 8], n_sq=[0, 2, 4], depth=[1, 2], l1=[1e-4, 3e-4, 1e-3, 3e-3], lr=[3e-3, 1e-2])
HP0 = dict(n_id=8, n_tanh=4, n_prod=4, n_sq=2, depth=1, l1=1e-3, lr=1e-2)
est = json.loads(EST.read_text(encoding="utf-8")) if EST.exists() else {"ronda": 0, "hp": HP0, "extra": [], "pruebas": 0, "cola": [], "historial": []}
rng = np.random.default_rng(int(time.time()) % 2**31)


def podar_cola(cola, k=20):
    """Deja solo las k mejores candidatas distintas (por texto): la cola es la lista corta para confirmar en la cohorte fresca 3, no un registro de todo."""
    mejor = {}
    for c in cola:
        if c["mejor"] not in mejor or c["dev_dif_F1"] > mejor[c["mejor"]]["dev_dif_F1"]:
            mejor[c["mejor"]] = c
    return sorted(mejor.values(), key=lambda c: -c["dev_dif_F1"])[:k]


est["cola"] = podar_cola(est.get("cola", []))


def entradas(extra):
    cols = [RK[:, :, F17]] + [evalua(e)[:, :, None] for e in extra]
    return np.concatenate(cols, axis=2)


def ecuacion(net, nombres, thr=0.08):
    if len(net.lin) != 1:
        return "(red profunda: ecuación no expandida)"
    a, b, c, d = net.sizes
    Wm, v = net.lin[0].weight.detach().cpu().numpy(), net.out.weight.detach().cpu().numpy()[0]
    lin = lambda j: " + ".join(f"{Wm[j, k]:+.2f}*{nombres[k]}" for k in range(len(nombres)) if abs(Wm[j, k]) > thr) or "0"  # noqa: E731
    t = [f"{v[j]:+.2f}*({lin(j)})" for j in range(a) if abs(v[j]) > thr]
    t += [f"{v[a + j]:+.2f}*tanh({lin(a + j)})" for j in range(b) if abs(v[a + j]) > thr]
    t += [f"{v[a + b + j]:+.2f}*({lin(a + b + j)})*({lin(a + b + c + j)})" for j in range(c) if abs(v[a + b + j]) > thr]
    t += [f"{v[a + b + c + j]:+.2f}*({lin(a + b + 2 * c + j)})^2" for j in range(d) if abs(v[a + b + c + j]) > thr]
    return " ".join(t) or "0"


while est["ronda"] < RONDAS:
    est["ronda"] += 1
    t0 = time.time()
    X = entradas(est["extra"])
    base = cv_dev(X, est["hp"])
    base_f1 = float(base[:, 1].mean())
    cands = []  # (dif_dev, tipo, descripcion, hp, extra)
    for _ in range(5):  # mutaciones de arquitectura
        hp = dict(est["hp"])
        k = str(rng.choice(list(GRID)))
        hp[k] = type(GRID[k][0])(rng.choice(GRID[k]))
        if hp == est["hp"]:
            continue
        m = cv_dev(X, hp)
        cands.append((float(m[:, 1].mean() - base_f1), "arquitectura", f"{k}={hp[k]}", hp, est["extra"]))
    for _ in range(5):  # variables nuevas
        op = str(rng.choice(OPS))
        e = {"op": op, "i": int(rng.integers(len(feats))), "j": int(rng.integers(len(feats)))}
        if op in ("prod", "dif", "ratio", "max", "min") and e["i"] == e["j"]:
            continue
        ex = est["extra"] + [e]
        m = cv_dev(entradas(ex), est["hp"])
        cands.append((float(m[:, 1].mean() - base_f1), "variable", texto(e), est["hp"], ex))
    cands.sort(key=lambda c: -c[0])
    dif, tipo, desc, hp_n, ex_n = cands[0]
    reg = {"ronda": est["ronda"], "dev_F1_campeon": base_f1, "mejor": f"{tipo}: {desc}", "dev_dif_F1": dif, "n_candidatos": len(cands), "promovido": False,
           "variables_extra": len(est["extra"])}
    if dif > 0.002 and est["pruebas"] < BUDGET:
        est["pruebas"] += 1
        Xn = entradas(ex_n)
        pa = np.mean([predict(fit(X[tr], Yz[tr], est["hp"], s, 50), X[te]) for s in range(3)], axis=0)
        pb = np.mean([predict(fit(Xn[tr], Yz[tr], hp_n, s, 50), Xn[te]) for s in range(3)], axis=0)
        a, b = score(pa, te), score(pb, te)
        try:
            p = float(stats.wilcoxon(b[:, 1], a[:, 1], alternative="greater").pvalue)
        except ValueError:
            p = 1.0
        reg.update({"reservado_F1_campeon": float(a[:, 1].mean()), "reservado_F1_retador": float(b[:, 1].mean()), "p_wilcoxon": p, "alfa": ALFA,
                    "hit5_campeon": float(a[:, 0].mean()), "hit5_retador": float(b[:, 0].mean())})
        if p < ALFA:
            est["hp"], est["extra"] = hp_n, ex_n
            reg["promovido"] = True
            net = fit(Xn[tr], Yz[tr], hp_n, 0, 50)
            nombres = [feats[k] for k in F17] + [texto(e) for e in ex_n]
            (OUT / f"ecuacion_ronda{est['ronda']}.txt").write_text(ecuacion(net, nombres), encoding="utf-8")
    elif dif > 0.002:
        est["cola"] = podar_cola(est["cola"] + [{"ronda": est["ronda"], "mejor": reg["mejor"], "dev_dif_F1": dif}])
        reg["en_cola"] = True
    est["historial"].append(reg)
    EST.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / "rondas.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    print(f"ronda {est['ronda']} ({time.time() - t0:.0f}s) campeón dev F1 {base_f1:.4f} | mejor {reg['mejor']} dev {dif:+.4f}"
          + (f" | reservado p={reg['p_wilcoxon']:.4f} promovido={reg['promovido']}" if "p_wilcoxon" in reg else " | sin prueba"), flush=True)
