"""Figuras de Python para Resultados (pedido de la profesora, 26-oct-2026): salidas de matplotlib, no de Word.

1) Curvas de pérdida de entrenamiento y validación del BiGRU 128 (10 pliegues por canal, 40 épocas).
2) Descriptivos del conjunto de datos: duración de los videos y videos por canal.
Salidas: reports/curvas_bigru_D099.png, reports/descriptivos_dataset_D099.png y reports/curvas_bigru_D099.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as Fn
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.dl_secuencia_D054 import BS, CROP, DEV, EPOCHS, LR, SEED, Net, loss_fn  # noqa: E402
from scripts.reverse_engineering_formula import PREFIXES  # noqa: E402
from src.common.config import load_config  # noqa: E402

CFG = ("GRU128_mse_d3", "gru", 128, "mse", 0.3, False)


def val_loss(net, X, Y, kind):
    net.eval()
    tot, n = 0.0, 0
    with torch.no_grad():
        for s in range(0, X.shape[1] - CROP + 1, 20):
            yb = Y[:, s:s + CROP]
            yb = (yb - yb.mean(1, keepdim=True)) / (yb.std(1, keepdim=True) + 1e-6)
            tot += float(loss_fn(net(X[:, s:s + CROP]), yb, kind)) * X.shape[0]
            n += X.shape[0]
    return tot / n


def corr_media(net, X, Y):
    """Correlación de Pearson media entre la salida y el calor real estandarizado, en ventanas de CROP (segunda métrica de la figura)."""
    net.eval()
    cs = []
    with torch.no_grad():
        for s in range(0, X.shape[1] - CROP + 1, 20):
            yb = Y[:, s:s + CROP]
            yb = (yb - yb.mean(1, keepdim=True)) / (yb.std(1, keepdim=True) + 1e-6)
            o = net(X[:, s:s + CROP])
            o = (o - o.mean(1, keepdim=True)) / (o.std(1, keepdim=True) + 1e-6)
            cs.append((o * yb).mean(1))
    return float(torch.cat(cs).mean())


def curvas(Xt, Yt, folds):
    _, arch, h, kind, drop, _ = CFG
    tr_all, va_all, trc_all, vac_all = [], [], [], []
    for k, (tr, te) in enumerate(folds):
        torch.manual_seed(SEED)
        g = torch.Generator(device="cpu").manual_seed(SEED)
        net = Net(Xt.shape[2], arch, h, drop).to(DEV)
        opt = torch.optim.AdamW(net.parameters(), lr=LR, weight_decay=1e-2)
        n = len(tr)
        sched = torch.optim.lr_scheduler.OneCycleLR(opt, LR, total_steps=EPOCHS * int(np.ceil(n / BS)))
        Xtr, Ytr, Xte, Yte = Xt[tr], Yt[tr], Xt[te], Yt[te]
        t_loss, v_loss, t_cor, v_cor = [], [], [], []
        for ep in range(EPOCHS):
            net.train()
            perm = torch.randperm(n, generator=g)
            acc, nb = 0.0, 0
            for i in range(0, n, BS):
                idx = perm[i:i + BS].tolist()
                st = torch.randint(0, Xtr.shape[1] - CROP + 1, (len(idx),), generator=g).tolist()
                xb = torch.stack([Xtr[j, s:s + CROP] for j, s in zip(idx, st)])
                yb = torch.stack([Ytr[j, s:s + CROP] for j, s in zip(idx, st)])
                yb = (yb - yb.mean(1, keepdim=True)) / (yb.std(1, keepdim=True) + 1e-6)
                opt.zero_grad()
                l = loss_fn(net(xb), yb, kind)
                l.backward()
                opt.step()
                sched.step()
                acc += float(l) * len(idx)
                nb += len(idx)
            t_loss.append(acc / nb)
            v_loss.append(val_loss(net, Xte, Yte, kind))
            t_cor.append(corr_media(net, Xtr, Ytr))
            v_cor.append(corr_media(net, Xte, Yte))
        tr_all.append(t_loss)
        va_all.append(v_loss)
        trc_all.append(t_cor)
        vac_all.append(v_cor)
        print(f"pliegue {k + 1}/{len(folds)}: entrenamiento {t_loss[-1]:.3f} | validación {v_loss[-1]:.3f}", flush=True)
    return np.array(tr_all), np.array(va_all), np.array(trc_all), np.array(vac_all)


def main():
    cfg = load_config("configs/gpu.yaml")
    bd, hd = cfg.path("processed") / "features" / "bin", cfg.path("interim") / "heatmaps"
    snap = set(json.loads((ROOT / "reports" / "conjunto_manifest_previo_D050.json").read_text(encoding="utf-8"))["video_ids"])
    rep = set(json.loads((ROOT / "reports" / "conjunto_humano_D040.json").read_text(encoding="utf-8"))["replica_independiente"])
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
    meta = {v: json.loads((hd / f"{v}.json").read_text(encoding="utf-8")) for v in vids}
    chan = np.array([meta[v]["channel_id"] for v in vids])
    X = np.stack([T[v][feats].rank(pct=True).fillna(0.5).to_numpy(np.float32) for v in vids])
    Y = np.stack([T[v]["y_mr"].to_numpy(np.float32) for v in vids])
    Xt, Yt = torch.tensor(X, device=DEV), torch.tensor(Y, device=DEV)
    folds = list(GroupKFold(10).split(np.arange(len(vids)), groups=chan))
    print(f"{len(vids)} videos | {len(feats)} variables | {DEV}", flush=True)
    tr, va, trc, vac = curvas(Xt, Yt, folds)

    # --- figura 1: pérdida y correlación por época (entrenamiento y validación), en el formato de un notebook de Python
    ep = np.arange(1, EPOCHS + 1)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.9), dpi=200)
    fig.suptitle("BiGRU 128: historial de entrenamiento (media de 10 pliegues por canal)", fontsize=10)
    for M, c, lab in ((tr, "#1f77b4", "Entrenamiento"), (va, "#ff7f0e", "Validación (canales no vistos)")):
        axs[0].plot(ep, M.mean(0), color=c, lw=1.4, label=lab)
    axs[0].set_title("Pérdida de entrenamiento y validación")
    axs[0].set_xlabel("Época"); axs[0].set_ylabel("Pérdida (error cuadrático medio)")
    for M, c, lab in ((trc, "#1f77b4", "Entrenamiento"), (vac, "#ff7f0e", "Validación (canales no vistos)")):
        axs[1].plot(ep, M.mean(0), color=c, lw=1.4, label=lab)
    axs[1].set_title("Correlación de entrenamiento y validación")
    axs[1].set_xlabel("Época"); axs[1].set_ylabel("Correlación de Pearson media")
    for a in axs:
        a.legend(); a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(ROOT / "reports" / "curvas_bigru_D099.png")
    plt.close(fig)
    json.dump({"modelo": CFG[0], "videos": len(vids), "pliegues": len(folds), "epocas": EPOCHS,
               "entrenamiento_final": float(tr[:, -1].mean()), "validacion_final": float(va[:, -1].mean()),
               "validacion_minima": float(va.mean(0).min()), "epoca_minima": int(va.mean(0).argmin() + 1), "correlacion_validacion_final": float(vac[:, -1].mean()), "correlacion_entrenamiento_final": float(trc[:, -1].mean())},
              open(ROOT / "reports" / "curvas_bigru_D099.json", "w", encoding="utf-8"), indent=1)

    # --- figura 2: descriptivos del conjunto
    dur = np.array([float(meta[v].get("duration") or meta[v].get("duration_s") or np.nan) for v in vids]) / 60
    dur = dur[~np.isnan(dur)]
    cnt = pd.Series(chan).value_counts()
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.4), dpi=200)
    axs[0].hist(np.clip(dur, 0, 180), bins=30, color="#1f4e79")
    axs[0].set_xlabel("Duración del video (min)")
    axs[0].set_ylabel("Videos")
    axs[1].hist(cnt.values, bins=np.arange(0.5, cnt.max() + 1.5, 1), color="#e8710a")
    axs[1].set_xlabel("Videos por canal")
    axs[1].set_ylabel("Canales")
    for a in axs:
        a.grid(alpha=0.25)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(ROOT / "reports" / "descriptivos_dataset_D099.png")
    print(json.dumps({"n_dur": int(len(dur)), "mediana_min": float(np.median(dur)), "canales": int(len(cnt)), "max_por_canal": int(cnt.max())}))


if __name__ == "__main__":
    main()
