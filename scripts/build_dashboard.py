"""Genera docs/panel.html: estado del dataset, del modelo y de los trabajos en curso.

    python scripts/build_dashboard.py            # genera el panel
    python scripts/build_dashboard.py --serve    # además lo sirve en http://localhost:8765

Todo sale de los archivos reales (manifests, reports/, outputs/), así que el panel nunca
muestra números inventados: si un reporte no existe, la tarjeta lo dice.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.common.config import load_config  # noqa: E402
from src.data.featurize import features_path  # noqa: E402
from src.data.youtube_dataset import transcript_path  # noqa: E402
from src.transcribe.whisper import Transcript  # noqa: E402

NOMBRES = {
    "lgbm_autogroups": "Propuesto (selección por fold)", "only_A": "Sólo audio", "lgbm_full": "Todos los grupos",
    "mlp_ranknet": "MLP RankNet", "opus_heuristic": "Heurística tipo Opus", "keybert_only": "Sólo KeyBERT",
    "tfidf_only": "Sólo TF-IDF", "audio_rms_only": "Sólo energía RMS", "position_prior": "Prior de posición",
    "random": "Aleatorio",
}
METRICAS = [("clip_P@5", "P@5"), ("clip_MRR", "MRR"), ("clip_NDCG@10", "NDCG@10"),
            ("clip_tF1@5", "F1 temporal"), ("bin_f1@5", "F1 bins")]


def estado_dataset(cfg) -> dict:
    filas, idiomas = [], {}
    total_h = 0.0
    canales, con_features, con_humano = set(), 0, 0
    for nombre in ("youtube_mr", "youtube_mr_repurpose"):
        f = cfg.path("manifests") / f"{nombre}.csv"
        if not f.exists():
            continue
        m = pd.read_csv(f)
        validos = 0
        for r in m.itertuples():
            tp = transcript_path(cfg, r.video_id, cfg.transcribe["model_dataset"])
            if not tp.exists():
                continue
            tr = Transcript.load(tp)
            if tr.language != r.query_lang or len(tr.words) <= 500:
                continue
            validos += 1
            canales.add(r.channel_id)
            total_h += (r.duration or 0) / 3600
            idiomas[r.query_lang] = idiomas.get(r.query_lang, 0) + 1
            if features_path(cfg, "sentence", r.video_id).exists():
                con_features += 1
            if (cfg.path("interim") / "human_clips" / f"{r.video_id}.json").exists():
                con_humano += 1
        filas.append({"fuente": nombre, "manifest": len(m), "validos": validos})
    return {"filas": filas, "horas": total_h, "canales": len(canales), "idiomas": idiomas,
            "con_features": con_features, "con_humano": con_humano,
            "validos": sum(f["validos"] for f in filas)}


def tabla_modelos(reports: Path) -> str:
    f = reports / "cv_metrics_long.csv"
    if not f.exists():
        return "<p class='vacio'>Aún no hay resultados de validación cruzada.</p>"
    agg = pd.read_csv(f)
    m = agg.pivot(index="model", columns="metric", values="mean")
    s = agg.pivot(index="model", columns="metric", values="std")
    filas = []
    for k in NOMBRES:
        if k not in m.index:
            continue
        celdas = "".join(
            f"<td>{m.loc[k, c]:.3f}<span class='sd'>±{s.loc[k, c]:.3f}</span></td>" if c in m.columns and pd.notna(m.loc[k, c]) else "<td>—</td>"
            for c, _ in METRICAS)
        clase = " class='destacado'" if k == "lgbm_autogroups" else (" class='azar'" if k == "random" else "")
        filas.append(f"<tr{clase}><td>{NOMBRES[k]}</td>{celdas}</tr>")
    cab = "".join(f"<th>{n}</th>" for _, n in METRICAS)
    return f"<table><thead><tr><th>Modelo</th>{cab}</tr></thead><tbody>{''.join(filas)}</tbody></table>"


def tabla_significancia(reports: Path) -> str:
    f = reports / "significance.csv"
    if not f.exists():
        return ""
    d = pd.read_csv(f)
    d = d[(d["comparación"].str.contains("random")) & (d["métrica"].isin(["P@5", "NDCG@10", "tF1@5", "bin_f1@5"]))]
    if d.empty:
        return ""
    filas = "".join(
        f"<tr><td>{r['métrica']}</td><td>{r['media_ref']:.3f}</td><td>{r['media_otro']:.3f}</td>"
        f"<td>{r['diferencia']:+.3f}</td><td class='{'sig' if r['p_wilcoxon'] < 0.05 else 'nosig'}'>"
        f"{r['p_wilcoxon']:.4f}</td></tr>" for _, r in d.iterrows())
    return ("<table><thead><tr><th>Métrica</th><th>Modelo</th><th>Azar</th><th>Diferencia</th><th>p</th></tr>"
            f"</thead><tbody>{filas}</tbody></table>")


def tarjeta_json(path: Path, titulo: str, render) -> str:
    if not path.exists():
        return f"<div class='card'><h3>{titulo}</h3><p class='vacio'>Pendiente.</p></div>"
    return f"<div class='card'><h3>{titulo}</h3>{render(json.loads(path.read_text(encoding='utf-8')))}</div>"


def ultimos_clips(cfg, n=3) -> str:
    out = cfg.path("outputs")
    if not out.exists():
        return "<p class='vacio'>Todavía no se generaron clips.</p>"
    jsons = sorted(out.glob("*/clips.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    if not jsons:
        return "<p class='vacio'>Todavía no se generaron clips.</p>"
    bloques = []
    for j in jsons:
        d = json.loads(j.read_text(encoding="utf-8"))
        filas = "".join(
            f"<tr><td class='sc'>{c.get('score_final', c['score'])}</td><td>{fmt(c['start'])}–{fmt(c['end'])}</td>"
            f"<td>{html.escape(c['context']['title'])}</td>"
            f"<td class='kw'>{html.escape(', '.join(k['term'] for k in c['keywords'][:4]))}</td></tr>"
            for c in d["clips"][:6])
        bloques.append(
            f"<h4>{html.escape(Path(d['input']).name)} <span class='meta'>· {d['duration_s'] / 60:.0f} min · "
            f"{d['language']} · {html.escape(str(d['model']))}</span></h4>"
            f"<table><thead><tr><th>Score</th><th>Tramo</th><th>Título</th><th>Palabras clave</th></tr></thead>"
            f"<tbody>{filas}</tbody></table>")
    return "".join(bloques)


def fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def trabajos(cfg) -> str:
    logs = Path(cfg.logging["file"]).parent.parent
    items = []
    for nombre, patron in [("Descargas Repurpose", "acq_rep_*.log"), ("Descargas principal", "acq_main_*.log"),
                           ("Featurización", "featurize_loop_v3.log"), ("Reentrenamiento", "after_downloads.log")]:
        archivos = sorted(logs.glob(patron))
        if not archivos:
            continue
        ultimo = max(archivos, key=lambda p: p.stat().st_mtime)
        edad = (time.time() - ultimo.stat().st_mtime) / 60
        linea = ""
        try:
            for ln in reversed(ultimo.read_text(encoding="utf-8", errors="replace").splitlines()):
                if "INFO" in ln or "==" in ln:
                    linea = ln.split("| ")[-1][:110]
                    break
        except OSError:
            pass
        if nombre == "Reentrenamiento" and "descargas terminadas" not in ultimo.read_text(encoding="utf-8", errors="replace"):
            estado, linea = "en espera", "se disparará solo cuando terminen las descargas"
        else:
            estado = "activo" if edad < 15 else "detenido"
        items.append(f"<li><b>{nombre}</b> <span class='pill {estado.split()[0]}'>{estado}</span><br>"
                     f"<span class='meta'>hace {edad:.0f} min · {html.escape(linea)}</span></li>")
    return f"<ul class='jobs'>{''.join(items)}</ul>" if items else "<p class='vacio'>Sin trabajos registrados.</p>"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    cfg = load_config()
    reports = cfg.path("reports")
    ds = estado_dataset(cfg)

    conf = tarjeta_json(
        reports / "confirmacion_D022.json", "Hipótesis preregistrada (D-022)",
        lambda d: f"<p class='grande {'ok' if d['veredicto'] == 'CONFIRMADA' else 'no'}'>{d['veredicto']}</p>"
                  f"<p class='meta'>NDCG@10: {d['tests']['NDCG@10']['base']:.3f} → "
                  f"{d['tests']['NDCG@10']['rel_rk']:.3f} · p = {d['tests']['NDCG@10']['p_unilateral']:.3f} · "
                  f"{d['n_new']} videos de confirmación</p>")
    hum = tarjeta_json(
        reports / "clips_humanos.json", "Most Replayed vs curación humana",
        lambda d: (lambda ag: f"<p class='grande no'>ρ = {ag['spearman_mr_humano'].mean():+.3f}</p>"
                              f"<p class='meta'>Correlación media entre ambas etiquetas en {d['n_videos']} videos. "
                              f"F1 temporal entre ellas: {ag['f1_temporal_mr_vs_humano'].mean():.3f}</p>")(
            pd.DataFrame(d["acuerdo"])))

    imp = ""
    fi = reports / "feature_importance.csv"
    if fi.exists():
        top = pd.read_csv(fi).head(8)
        imp = "".join(f"<li><span>{r.feature}</span><i style='width:{100 * r.gain / top.gain.max():.0f}%'></i></li>"
                      for r in top.itertuples())
        imp = f"<ul class='bars'>{imp}</ul>"

    modelo_meta = ""
    mm = ROOT / "models" / "ranker_meta.json"
    if mm.exists():
        d = json.loads(mm.read_text(encoding="utf-8"))
        modelo_meta = (f"<p class='meta'>Modelo desplegado: <b>{d.get('grupos_elegidos', '?')}</b> · "
                       f"{len(d.get('features', []))} features · entrenado con {d.get('n_train_videos', '?')} videos · "
                       f"{d.get('created', '')}</p>")

    idiomas = " · ".join(f"{k.upper()} {v}" for k, v in sorted(ds["idiomas"].items()))
    fuentes = "".join(f"<tr><td>{f['fuente']}</td><td>{f['manifest']}</td><td>{f['validos']}</td></tr>"
                      for f in ds["filas"])

    page = PLANTILLA.format(
        fecha=time.strftime("%d/%m/%Y %H:%M"),
        validos=ds["validos"], horas=f"{ds['horas']:.1f}", canales=ds["canales"], idiomas=idiomas,
        con_features=ds["con_features"], con_humano=ds["con_humano"],
        fuentes=fuentes, tabla=tabla_modelos(reports), sig=tabla_significancia(reports),
        modelo_meta=modelo_meta, importancia=imp, confirmacion=conf, humano=hum,
        clips=ultimos_clips(cfg), trabajos=trabajos(cfg),
    )
    out = ROOT / "docs" / "panel.html"
    out.write_text(page, encoding="utf-8")
    print(f"escrito {out}")

    if args.serve:
        import http.server
        import socketserver

        import webbrowser

        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(ROOT / "docs"), **k)

        with socketserver.TCPServer(("", args.port), H) as s:
            url = f"http://localhost:{args.port}/panel.html"
            print(f"sirviendo en {url}  (Ctrl+C para detener)")
            webbrowser.open(url)
            s.serve_forever()


PLANTILLA = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel de la tesis</title>
<style>
  :root {{ --bg:#fbfbfd; --fg:#1b1b1f; --muted:#5c5f6b; --card:#fff; --line:#e4e4ec; --acc:#3b6ea5;
           --ok:#1f7a45; --no:#a6452c; }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#14151a; --fg:#e9e9ee; --muted:#a2a5b2;
           --card:#1c1e24; --line:#2b2e37; --acc:#7fb2e5; --ok:#5fc389; --no:#e0876b; }} }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); padding:24px 16px 60px;
         font:15px/1.55 -apple-system,Segoe UI,Roboto,sans-serif; }}
  .wrap {{ max-width:1180px; margin:0 auto; }}
  header {{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:8px; margin-bottom:20px; }}
  h1 {{ font-size:1.45rem; margin:0; }}
  h2 {{ font-size:1.05rem; margin:26px 0 10px; }}
  h3 {{ font-size:.95rem; margin:0 0 8px; }}
  h4 {{ font-size:.92rem; margin:14px 0 6px; }}
  .meta {{ color:var(--muted); font-size:.82rem; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:12px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }}
  .kpi {{ font-size:1.9rem; font-weight:700; line-height:1.1; }}
  .kpi small {{ font-size:.8rem; font-weight:400; color:var(--muted); display:block; margin-top:2px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.86rem; }}
  th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-weight:600; }}
  td:not(:first-child) {{ text-align:right; font-variant-numeric:tabular-nums; }}
  tr.destacado td {{ font-weight:700; }}
  tr.azar td {{ color:var(--muted); }}
  .sd {{ color:var(--muted); font-size:.75em; margin-left:3px; }}
  .sig {{ color:var(--ok); font-weight:600; }} .nosig {{ color:var(--muted); }}
  .grande {{ font-size:1.5rem; font-weight:700; margin:2px 0; }}
  .ok {{ color:var(--ok); }} .no {{ color:var(--no); }}
  .vacio {{ color:var(--muted); font-style:italic; }}
  ul.bars {{ list-style:none; padding:0; margin:0; }}
  ul.bars li {{ display:grid; grid-template-columns:150px 1fr; gap:8px; align-items:center; margin-bottom:5px; font-size:.8rem; }}
  ul.bars i {{ display:block; height:9px; background:var(--acc); border-radius:5px; }}
  ul.jobs {{ list-style:none; padding:0; margin:0; }}
  ul.jobs li {{ padding:7px 0; border-bottom:1px solid var(--line); font-size:.86rem; }}
  .pill {{ font-size:.7rem; padding:1px 7px; border-radius:20px; margin-left:6px; }}
  .pill.activo {{ background:#1f7a4522; color:var(--ok); }}
  .pill.detenido {{ background:#8883; color:var(--muted); }}
  .pill.en {{ background:#3b6ea522; color:var(--acc); }}
  .sc {{ font-weight:700; color:var(--acc); }}
  .kw {{ color:var(--muted); }}
  a {{ color:var(--acc); }}
  .links a {{ margin-right:14px; font-size:.85rem; }}
</style></head><body><div class="wrap">
<header>
  <h1>Panel · generación de clips con score</h1>
  <span class="meta">actualizado {fecha} · <code>python scripts/build_dashboard.py</code></span>
</header>

<div class="grid">
  <div class="card"><div class="kpi">{validos}<small>videos válidos</small></div></div>
  <div class="card"><div class="kpi">{horas} h<small>de audio etiquetado</small></div></div>
  <div class="card"><div class="kpi">{canales}<small>canales distintos</small></div></div>
  <div class="card"><div class="kpi">{con_humano}<small>con clips humanos</small></div></div>
</div>

<h2>Dataset</h2>
<div class="card">
  <p class="meta">Idiomas: {idiomas} · con features calculadas: {con_features}</p>
  <table><thead><tr><th>Fuente</th><th>En manifest</th><th>Válidos</th></tr></thead><tbody>{fuentes}</tbody></table>
</div>

<h2>Modelo</h2>
<div class="card">{modelo_meta}{tabla}</div>

<div class="grid" style="margin-top:12px">
  <div class="card"><h3>Significancia frente al azar</h3>{sig}</div>
  {confirmacion}
  {humano}
</div>

<h2>Features más importantes</h2>
<div class="card">{importancia}</div>

<h2>Últimos clips generados</h2>
<div class="card">{clips}</div>

<h2>Trabajos en curso</h2>
<div class="card">{trabajos}</div>

<h2>Documentos</h2>
<div class="card links">
  <a href="diagramas/index.html">Diagramas</a>
  <a href="02_auditoria_modelo.md">Auditoría del modelo</a>
  <a href="01_diseno_metodologico.md">Diseño metodológico</a>
  <a href="DECISIONES.md">Decisiones</a>
  <a href="SETUP_GPU.md">Migración a GPU</a>
  <a href="Documentacion_Tecnica_Tesis.docx">Documento Word</a>
</div>
</div></body></html>"""


if __name__ == "__main__":
    main()
