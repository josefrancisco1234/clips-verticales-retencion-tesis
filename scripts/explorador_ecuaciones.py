"""D-086: explorador automático de ecuaciones (red de ecuaciones EQL) con selección interna y bucle campeón/retador.

    python scripts/explorador_ecuaciones.py [--simular]

Preregistro en docs/DECISIONES.md (D-086). La selección de configuración usa SOLO validación cruzada interna por canal sobre el
entrenamiento; el holdout congelado (md5(canal) % 5 == 0, igual que D-080) se evalúa una vez por ronda.
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

SIMULAR = "--simular" in sys.argv
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
cfg = load_config("configs/gpu.yaml")
bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
VARS68 = "--vars68" in sys.argv  # D-092: la red recibe las 68 variables y descubre cuales importan
OUT = ROOT / "reports" / ("explorador_ecuaciones_68" if VARS68 else "explorador_ecuaciones")
OUT.mkdir(parents=True, exist_ok=True)
feats = json.loads((ROOT / "reports" / "dl_secuencia_D054" / "resumen.json").read_text(encoding="utf-8"))["features"]
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
F17 = [k for k in W if k in feats]
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"])  # noqa: E731
reservados = J("conjunto_confirmacion_fresca_D050.json") | J("conjunto_confirmacion_fresca2_D065.json")
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
CH = np.array(CH)
hold = np.array([int(hashlib.md5(str(c).encode()).hexdigest(), 16) % 5 == 0 for c in CH])
tr, te = np.where(~hold)[0], np.where(hold)[0]
print(f"desarrollo={len(V)} | entrenamiento={len(tr)} | holdout={len(te)}", flush=True)

RK = np.stack([d[feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
X17 = np.stack([d[F17].rank(pct=True).fillna(0.5).to_numpy(np.float32) for d in T])
G = np.stack([d["y_grade"].to_numpy(int) for d in T])
Y = np.stack([d["y_mr"].to_numpy(np.float32) for d in T])
Yz = (Y - Y.mean(1, keepdims=True)) / (Y.std(1, keepdims=True) + 1e-6)
REL = np.stack([d["y_relevant"].to_numpy() for d in T])
ST = np.stack([d["start"].to_numpy() for d in T])
EN = np.stack([d["end"].to_numpy() for d in T])
HEAT = [heat_intervals(corrected_graph(json.loads((hd / f"{v}.json").read_text(encoding="utf-8"))["heatmap"])) for v in V]
wv = np.array([W[k] for k in F17], np.float32)
FN = feats if VARS68 else F17
XIN = RK if VARS68 else X17


class EQL(nn.Module):
    """Capas de unidades identidad / tanh / producto / cuadrado seguidas de una salida lineal."""

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
        pa, pb = p[..., :c], p[..., c:]
        return torch.cat([i, torch.tanh(t), pa * pb, s ** 2], dim=-1)

    def forward(self, x):
        h = x
        for l in self.lin:
            h = self.units(l(h))
        return self.out(h).squeeze(-1)

    def l1(self):
        return sum(l.weight.abs().sum() for l in self.lin) + self.out.weight.abs().sum()


def fit(Xtr, Ytr, hp, seed=0, epochs=60):
    torch.manual_seed(seed)
    net = EQL(Xtr.shape[2], hp["n_id"], hp["n_tanh"], hp["n_prod"], hp["n_sq"], hp["depth"]).to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=hp["lr"], weight_decay=0.0)
    X, Yt = torch.tensor(Xtr, device=DEV), torch.tensor(Ytr, device=DEV)
    n = X.shape[0]
    g = torch.Generator().manual_seed(seed)
    for ep in range(epochs):
        net.train()
        perm = torch.randperm(n, generator=g)
        lam = hp["l1"] * min(1.0, ep / (0.3 * epochs))  # calentamiento de la penalizacion
        for i in range(0, n, 16):
            idx = perm[i:i + 16].tolist()
            p = net(X[idx])
            loss = -(Fn.softmax(2.0 * Yt[idx], dim=1) * Fn.log_softmax(p, dim=1)).sum(1).mean() + lam * net.l1()
            opt.zero_grad()
            loss.backward()
            opt.step()
    return net.eval()


def predict(net, Xte):
    with torch.no_grad():
        return net(torch.tensor(Xte, device=DEV)).cpu().numpy()


def score(S, idx):
    o = []
    for k, i in enumerate(idx):
        sel = top_k_nms(ST[i], EN[i], S[k])
        o.append((float(REL[i][sel].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in sel], HEAT[i])))
    return np.array(o)


def formula_text(net, thr=0.08):
    """Ecuación de una red de profundidad 1 podada: salida = suma v_j * unidad_j(combinacion lineal de variables)."""
    if len(net.lin) != 1:
        return "(red profunda: ecuación no expandida; ver pesos)"
    a, b, c, d = net.sizes
    Wm, bm = net.lin[0].weight.detach().cpu().numpy(), net.lin[0].bias.detach().cpu().numpy()
    v = net.out.weight.detach().cpu().numpy()[0]
    lin = lambda j: " + ".join(f"{Wm[j, k]:+.2f}*{FN[k]}" for k in range(len(FN)) if abs(Wm[j, k]) > thr) or "0"  # noqa: E731
    terms = []
    for j in range(a):
        if abs(v[j]) > thr:
            terms.append(f"{v[j]:+.2f}*({lin(j)})")
    for j in range(b):
        if abs(v[a + j]) > thr:
            terms.append(f"{v[a + j]:+.2f}*tanh({lin(a + j)})")
    for j in range(c):
        if abs(v[a + b + j]) > thr:
            terms.append(f"{v[a + b + j]:+.2f}*({lin(a + b + j)})*({lin(a + b + c + j)})")
    for j in range(d):
        if abs(v[a + b + c + j]) > thr:
            terms.append(f"{v[a + b + c + j]:+.2f}*({lin(a + b + 2 * c + j)})^2")
    return " ".join(terms) or "0"


rng = np.random.default_rng(int(time.time()) % 10_000 if "--semilla-tiempo" in sys.argv else 7)
state_p = OUT / "estado.json"
state = json.loads(state_p.read_text(encoding="utf-8")) if state_p.exists() else {"ronda": 0, "campeon": "LGBM_R0"}
space = [dict(n_id=int(rng.choice([4, 8, 16])), n_tanh=int(rng.choice([0, 4, 8])), n_prod=int(rng.choice([0, 2, 4, 8])),
              n_sq=int(rng.choice([0, 2, 4])), depth=int(rng.choice([1, 1, 2])), l1=float(rng.choice([1e-4, 3e-4, 1e-3, 3e-3])),
              lr=float(rng.choice([3e-3, 1e-2]))) for _ in range(12)]
t0 = time.time()
cv_scores = []
for hp in space:
    f = []
    for a, b in GroupKFold(3).split(tr, groups=CH[tr]):
        net = fit(XIN[tr[a]], Yz[tr[a]], hp)
        f.append(score(predict(net, XIN[tr[b]]), tr[b])[:, 1].mean())
    cv_scores.append(float(np.mean(f)))
    print(f"  {hp} -> F1 CV interno {cv_scores[-1]:.4f}", flush=True)
best = space[int(np.argmax(cv_scores))]
nets = [fit(XIN[tr], Yz[tr], best, seed=s) for s in range(3)]
pred_eql = np.mean([predict(n, XIN[te]) for n in nets], axis=0)
m = lgb.train(dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
                   min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, num_threads=8,
                   verbose=-1, seed=42, deterministic=True, force_row_wise=True),
              lgb.Dataset(RK[tr].reshape(-1, RK.shape[2]), G[tr].reshape(-1), group=[100] * len(tr)), 300)
pred_lgb = m.predict(RK[te].reshape(-1, RK.shape[2])).reshape(len(te), 100)
pred_v0 = (X17[te] * wv).sum(2)
a_eql, a_lgb, a_v0 = score(pred_eql, te), score(pred_lgb, te), score(pred_v0, te)
az = np.mean([score(np.random.default_rng(s).random((len(te), 100)), te) for s in range(20)], axis=0).mean(0)
d = a_eql[:, 1] - a_lgb[:, 1]
p = float(stats.wilcoxon(a_eql[:, 1], a_lgb[:, 1], alternative="greater").pvalue) if np.any(d != 0) else 1.0
promueve = bool(d.mean() > 0 and p < 0.05)
ec = formula_text(nets[0])
ronda = {"ronda": state["ronda"] + 1, "fecha": time.strftime("%Y-%m-%d %H:%M"), "n_entrenamiento": int(len(tr)), "n_holdout": int(len(te)),
         "mejor_config": best, "F1_cv_interno": max(cv_scores), "EQL_hit5": float(a_eql[:, 0].mean()), "EQL_F1": float(a_eql[:, 1].mean()),
         "LGBM_R0_hit5": float(a_lgb[:, 0].mean()), "LGBM_R0_F1": float(a_lgb[:, 1].mean()),
         "V0_hit5": float(a_v0[:, 0].mean()), "V0_F1": float(a_v0[:, 1].mean()), "azar_hit5": float(az[0]), "azar_F1": float(az[1]),
         "dif_F1_EQL_vs_campeon": float(d.mean()), "p_unilateral": p, "promueve": promueve, "ecuacion_aprendida": ec,
         "segundos": round(time.time() - t0)}
print(json.dumps(ronda, indent=1, ensure_ascii=False))
if not SIMULAR:
    with open(OUT / "rondas.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ronda, ensure_ascii=False) + "\n")
    state_p.write_text(json.dumps({"ronda": ronda["ronda"], "campeon": "EQL" if promueve else state["campeon"]}), encoding="utf-8")
    (OUT / f"ecuacion_ronda{ronda['ronda']}.txt").write_text(ec, encoding="utf-8")
