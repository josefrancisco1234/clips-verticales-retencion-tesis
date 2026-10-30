"""Modelo profundo de secuencia (D-054): linea de tiempo del video (100 bins) -> curva de calor.

Validacion GroupKFold(10) por canal. Recortes aleatorios de 40 bins (sin posicion absoluta).
Salidas en reports/dl_secuencia_D054/.
"""
from __future__ import annotations

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
from scripts.reverse_engineering_formula import PREFIXES, f1_temporal, heat_intervals, top_k_nms  # noqa: E402
from src.common.config import load_config  # noqa: E402
from src.ranking.labels import corrected_graph  # noqa: E402

OUT = ROOT / "reports" / "dl_secuencia_D054"
DEV = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEED, CROP, EPOCHS, BS, LR = 42, 40, 40, 16, 2e-3
CONFIGS = [  # (nombre, arquitectura, hidden, perdida, dropout, contraste_local)
    ("MLP64_listnet", "mlp", 64, "listnet", 0.1, False),
    ("GRU64_mse", "gru", 64, "mse", 0.1, False),
    ("GRU64_listnet", "gru", 64, "listnet", 0.1, False),
    ("GRU128_mse_d3", "gru", 128, "mse", 0.3, False),
    ("TCN64_mse", "tcn", 64, "mse", 0.1, False),
    ("TCN64_listnet", "tcn", 64, "listnet", 0.1, False),
    ("TCN128_listnet_d3", "tcn", 128, "listnet", 0.3, False),
    ("TRF64_mse", "trf", 64, "mse", 0.1, False),
    ("TRF64_listnet", "trf", 64, "listnet", 0.1, False),
    ("TRF128_listnet_d3", "trf", 128, "listnet", 0.3, False),
    ("GRU64_mse_cx", "gru", 64, "mse", 0.1, True),
    ("TCN64_listnet_cx", "tcn", 64, "listnet", 0.1, True),
]


class Net(nn.Module):
    def __init__(self, f_in, arch, h, drop):
        super().__init__()
        self.arch = arch
        self.inp = nn.Sequential(nn.Linear(f_in, h), nn.GELU(), nn.Dropout(drop))
        if arch == "mlp":
            self.body = nn.Sequential(nn.Linear(h, h), nn.GELU(), nn.Dropout(drop))
            out = h
        elif arch == "gru":
            self.body = nn.GRU(h, h, batch_first=True, bidirectional=True)
            out = 2 * h
        elif arch == "tcn":
            self.convs = nn.ModuleList([nn.Conv1d(h, h, 3, padding=d, dilation=d) for d in (1, 2, 4)])
            self.drop = nn.Dropout(drop)
            out = h
        else:  # trf: convolucion local (orden relativo) + atencion sin posicion absoluta
            self.conv = nn.Conv1d(h, h, 5, padding=2)
            layer = nn.TransformerEncoderLayer(h, 4, 2 * h, drop, batch_first=True, activation="gelu")
            self.body = nn.TransformerEncoder(layer, 2)
            out = h
        self.head = nn.Linear(out, 1)

    def forward(self, x):
        z = self.inp(x)
        if self.arch == "mlp":
            z = self.body(z)
        elif self.arch == "gru":
            z, _ = self.body(z)
        elif self.arch == "tcn":
            t = z.transpose(1, 2)
            for c in self.convs:
                t = t + self.drop(Fn.gelu(c(t)))
            z = t.transpose(1, 2)
        else:
            z = z + Fn.gelu(self.conv(z.transpose(1, 2))).transpose(1, 2)
            z = self.body(z)
        return self.head(z).squeeze(-1)


def loss_fn(pred, y, kind):
    if kind == "mse":
        return Fn.mse_loss(pred, y)
    return -(Fn.softmax(2.0 * y, dim=1) * Fn.log_softmax(pred, dim=1)).sum(dim=1).mean()


def add_cx(x):
    """Concatena el contraste local (valor menos media de +-3 bins) a cada feature."""
    k = torch.ones(1, 1, 7, device=x.device) / 6.0
    k[0, 0, 3] = 0
    f = x.shape[2]
    t = x.permute(0, 2, 1).reshape(-1, 1, x.shape[1])
    m = Fn.conv1d(Fn.pad(t, (3, 3), mode="replicate"), k).reshape(x.shape[0], f, -1).permute(0, 2, 1)
    return torch.cat([x, x - m], dim=2)


def fit_predict(Xtr, ytr, Xte, cfg, seed):
    _, arch, h, loss, drop, _cx = cfg
    torch.manual_seed(seed)
    g = torch.Generator(device="cpu").manual_seed(seed)
    net = Net(Xtr.shape[2], arch, h, drop).to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=1e-2)
    n = Xtr.shape[0]
    steps = EPOCHS * int(np.ceil(n / BS))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, LR, total_steps=steps)
    net.train()
    for _ in range(EPOCHS):
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, BS):
            idx = perm[i:i + BS].tolist()
            st = torch.randint(0, Xtr.shape[1] - CROP + 1, (len(idx),), generator=g).tolist()
            xb = torch.stack([Xtr[j, s:s + CROP] for j, s in zip(idx, st)])
            yb = torch.stack([ytr[j, s:s + CROP] for j, s in zip(idx, st)])
            yb = (yb - yb.mean(1, keepdim=True)) / (yb.std(1, keepdim=True) + 1e-6)
            opt.zero_grad()
            loss_fn(net(xb), yb, loss).backward()
            opt.step()
            sched.step()
    net.eval()
    T = Xte.shape[1]
    acc = torch.zeros(Xte.shape[0], T, device=DEV)
    cnt = torch.zeros(Xte.shape[0], T, device=DEV)
    with torch.no_grad():
        for s in range(0, T - CROP + 1, 5):
            p = net(Xte[:, s:s + CROP])
            p = (p - p.mean(1, keepdim=True)) / (p.std(1, keepdim=True) + 1e-6)
            acc[:, s:s + CROP] += p
            cnt[:, s:s + CROP] += 1
    return (acc / cnt.clamp(min=1)).cpu().numpy()


def main():
    t0 = time.time()
    cfg = load_config("configs/gpu.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
    snap = set(json.loads((ROOT / "reports" / "conjunto_manifest_previo_D050.json").read_text(encoding="utf-8"))["video_ids"])
    rep = set(json.loads((ROOT / "reports" / "conjunto_humano_D040.json").read_text(encoding="utf-8"))["replica_independiente"])
    frozen = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
    vids, T, feats_all = [], {}, None
    for p in sorted(bd.glob("*.parquet")):
        v = p.stem
        if v in rep or v not in snap or not (hd / f"{v}.json").exists():
            continue
        d = pd.read_parquet(p)
        if len(d) != 100:
            continue
        fs = [c for c in d.columns if c.startswith(PREFIXES)]
        feats_all = fs if feats_all is None else [c for c in feats_all if c in fs]
        T[v] = d
        vids.append(v)
    const = {f: np.mean([T[v][f].nunique() <= 1 for v in vids]) for f in feats_all}
    feats = [f for f in feats_all if const[f] < 0.2]
    print(f"{len(vids)} videos | {len(feats)} features | dispositivo {DEV}", flush=True)
    meta = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
    chan = np.array([meta[v]["channel_id"] for v in vids])
    X = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
    Y = np.stack([T[v]["y_mr"].to_numpy(np.float32) for v in vids])
    REL = np.stack([T[v]["y_relevant"].to_numpy(int) for v in vids])
    GRADE = np.stack([T[v]["y_grade"].to_numpy(int) for v in vids])
    ST = np.stack([T[v]["start"].to_numpy() for v in vids])
    EN = np.stack([T[v]["end"].to_numpy() for v in vids])
    HEAT = [heat_intervals(corrected_graph(meta[v]["heatmap"])) for v in vids]
    Xt = torch.tensor(X, device=DEV)
    Xt_cx = add_cx(Xt)
    Yt = torch.tensor(Y, device=DEV)
    wv = np.array([frozen[c] for c in frozen])
    cols = [feats.index(c) for c in frozen]
    folds = list(GroupKFold(10).split(np.arange(len(vids)), groups=chan))

    oof = {c[0]: np.zeros_like(Y) for c in CONFIGS}
    oof["LGBM_bin"] = np.zeros_like(Y)
    P = dict(objective="lambdarank", metric="ndcg", lambdarank_truncation_level=20, learning_rate=0.05, num_leaves=15,
             min_data_in_leaf=50, feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0,
             num_threads=8, verbose=-1, seed=SEED, deterministic=True, force_row_wise=True)
    for tr, te in folds:
        m = lgb.train(P, lgb.Dataset(X[tr].reshape(-1, X.shape[2]), GRADE[tr].reshape(-1), group=[100] * len(tr)), 300)
        oof["LGBM_bin"][te] = m.predict(X[te].reshape(-1, X.shape[2])).reshape(len(te), 100)
    V0 = X[:, :, cols] @ wv
    print(f"LGBM por bin listo ({time.time() - t0:.0f}s)", flush=True)
    for ci, c in enumerate(CONFIGS):
        t1 = time.time()
        src = Xt_cx if c[5] else Xt
        for tr, te in folds:
            oof[c[0]][te] = fit_predict(src[tr], Yt[tr], src[te], c, SEED)
        print(f"[{ci + 1}/{len(CONFIGS)}] {c[0]} listo ({time.time() - t1:.0f}s)", flush=True)

    def metrics(S):
        out = []
        for i in range(len(vids)):
            k = top_k_nms(ST[i], EN[i], S[i])
            out.append((float(REL[i][k].max() > 0), f1_temporal([(ST[i][j], EN[i][j]) for j in k], HEAT[i]),
                        float(Y[i][k].mean() / Y[i].mean())))
        return np.array(out)

    rng = np.random.default_rng(SEED)
    M = {"azar": np.mean([metrics(rng.random(Y.shape)) for _ in range(20)], axis=0), "V0_bin": metrics(V0),
         "LGBM_bin": metrics(oof["LGBM_bin"]), "calor_directo": metrics(Y)}
    for c in CONFIGS:
        M[c[0]] = metrics(oof[c[0]])
    ref = M["V0_bin"]
    rows = []
    print(f"\n{'metodo':22s} {'hit@5':>7s} {'F1':>7s} {'lift':>6s}  p(F1 vs V0)  p(F1 vs LGBM)", flush=True)
    for n, a in M.items():
        pv = pl = float("nan")
        if n not in ("azar", "V0_bin", "calor_directo"):
            try:
                pv = float(stats.wilcoxon(a[:, 1], ref[:, 1]).pvalue)
            except ValueError:
                pass
            if n != "LGBM_bin":
                try:
                    pl = float(stats.wilcoxon(a[:, 1], M["LGBM_bin"][:, 1]).pvalue)
                except ValueError:
                    pass
        rows.append(dict(metodo=n, hit5=float(a[:, 0].mean()), F1=float(a[:, 1].mean()), lift=float(a[:, 2].mean()),
                         p_vs_V0=pv, p_vs_LGBM=pl))
        print(f"{n:22s} {a[:, 0].mean():7.1%} {a[:, 1].mean():7.3f} {a[:, 2].mean():6.2f}  {pv:10.4f}  {pl:10.4f}", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "configuraciones.csv", index=False)
    np.savez_compressed(OUT / "oof.npz", vids=np.array(vids), Y=Y, V0=V0, **oof)
    names = {c[0] for c in CONFIGS}
    best = max((r for r in rows if r["metodo"] in names), key=lambda r: r["F1"])
    print(f"\nMEJOR CONFIGURACION (F1): {best['metodo']} F1={best['F1']:.3f} hit={best['hit5']:.1%}", flush=True)
    json.dump({"mejor": best["metodo"], "n_videos": len(vids), "features": feats, "filas": rows},
              open(OUT / "resumen.json", "w", encoding="utf-8"), indent=1)

    # fusion "el modelo propone, la curva valida"
    S = oof[best["metodo"]]
    zs = lambda a: (a - a.mean(1, keepdims=True)) / (a.std(1, keepdims=True) + 1e-9)  # noqa: E731
    thr = np.quantile(Y, 0.8, axis=1, keepdims=True)
    fus = {"A_calor": Y, "B_modelo": S,
           "C_valida_20pct_ordena_modelo": np.where(Y >= thr, S - S.min() + 1.0, 0.0),
           "D_z(calor)+0.5z(modelo)": zs(Y) + 0.5 * zs(S)}
    hp = cfg.path("interim") / "human_clips"
    print("\n=== FUSION (mismos oof) ===", flush=True)
    fr = []
    for n, sc in fus.items():
        a = metrics(sc)
        hum = []
        for i, v in enumerate(vids):
            f = hp / f"{v}.json"
            if f.exists() and "y_human_overlap" in T[v] and T[v]["y_human_overlap"].notna().any():
                segs = [(x, y) for x, y in json.loads(f.read_text(encoding="utf-8"))["segments"]]
                k = top_k_nms(ST[i], EN[i], sc[i])
                hum.append(f1_temporal([(ST[i][j], EN[i][j]) for j in k], segs))
        fr.append(dict(variante=n, hit5=float(a[:, 0].mean()), F1_calor=float(a[:, 1].mean()), lift=float(a[:, 2].mean()),
                       F1_vs_humano=float(np.nanmean(hum)) if hum else float("nan"), n_humano=len(hum)))
        print(f"{n:30s} hit={a[:, 0].mean():.1%} F1={a[:, 1].mean():.3f} lift={a[:, 2].mean():.2f} "
              f"F1_humano={fr[-1]['F1_vs_humano']:.3f} (n={len(hum)})", flush=True)
    pd.DataFrame(fr).to_csv(OUT / "fusion.csv", index=False)

    # modelo final con todo el desarrollo ampliado (se evalua una vez en la cohorte fresca)
    cfg_b = next(c for c in CONFIGS if c[0] == best["metodo"])
    src = Xt_cx if cfg_b[5] else Xt
    final = []
    for s in range(3):
        torch.manual_seed(SEED + s)
        _, arch, h, loss, drop, _ = cfg_b
        net = Net(src.shape[2], arch, h, drop).to(DEV)
        opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=1e-2)
        n = src.shape[0]
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, LR, total_steps=EPOCHS * int(np.ceil(n / BS)))
        g = torch.Generator(device="cpu").manual_seed(SEED + s)
        net.train()
        for _ in range(EPOCHS):
            perm = torch.randperm(n, generator=g)
            for i in range(0, n, BS):
                idx = perm[i:i + BS].tolist()
                st = torch.randint(0, src.shape[1] - CROP + 1, (len(idx),), generator=g).tolist()
                xb = torch.stack([src[j, a:a + CROP] for j, a in zip(idx, st)])
                yb = torch.stack([Yt[j, a:a + CROP] for j, a in zip(idx, st)])
                yb = (yb - yb.mean(1, keepdim=True)) / (yb.std(1, keepdim=True) + 1e-6)
                opt.zero_grad()
                loss_fn(net(xb), yb, loss).backward()
                opt.step()
                sched.step()
        final.append({k: v.cpu() for k, v in net.state_dict().items()})
    torch.save({"config": cfg_b, "features": feats, "state_dicts": final}, ROOT / "models" / "dl_secuencia_D054.pt")
    print(f"\nmodelo final guardado: models/dl_secuencia_D054.pt | total {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
