"""MI_PODCAST_DATOS: video original, audio, transcripción y Excel (clips, 71 variables por clip, eventos de sonido, generaciones) del podcast propio."""
import json, shutil, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import glosario_variables as GL
BASE = Path(r"F:\TESISJF"); OUT = BASE / "MI_PODCAST_DATOS"
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir()
video = next(p for p in (BASE / "MIS_VIDEOS").iterdir() if p.suffix.lower() in {".mp4", ".mkv", ".mov"})
work = next(d for d in (BASE / "tesis_data" / "data" / "interim" / "infer").iterdir() if d.name.startswith("YTDown"))
res = next(d for d in (BASE / "CLIPS_GENERADOS").iterdir() if (d / "clips.json").exists())
J = json.loads((res / "clips.json").read_text(encoding="utf-8"))
shutil.copy(video, OUT / ("1_video_original" + video.suffix.lower()))
shutil.copy(work / "audio.wav", OUT / "2_audio_16k_mono.wav")
tr = json.loads((work / "transcript_medium.json").read_text(encoding="utf-8"))
shutil.copy(work / "transcript_medium.json", OUT / "3_transcripcion_whisper.json")
words = tr["words"] if isinstance(tr, dict) else tr
rows = [(w[0], w[1], w[2], w[3] if len(w) > 3 else None) if isinstance(w, (list, tuple)) else (w.get("word", w.get("text")), w.get("start"), w.get("end"), w.get("probability", w.get("conf"))) for w in words]
dfw = pd.DataFrame(rows, columns=["palabra", "inicio_s", "fin_s", "confianza"])
mm = lambda t: f"{int(t // 60):02d}:{int(t % 60):02d}"
lines, cur, t0 = [], [], 0.0
for p_, a, b, _ in rows:   # un párrafo cada ~30 s
    if not cur: t0 = a
    cur.append(str(p_).strip())
    if b - t0 >= 30: lines.append(f"[{mm(t0)}] " + " ".join(cur)); cur = []
if cur: lines.append(f"[{mm(t0)}] " + " ".join(cur))
(OUT / "3_transcripcion.txt").write_text("\n\n".join(lines), encoding="utf-8")
with pd.ExcelWriter(OUT / "4_transcripcion_palabras.xlsx") as xw:
    dfw.to_excel(xw, sheet_name="palabras", index=False)
    pd.DataFrame({"parrafo_30s": lines}).to_excel(xw, sheet_name="texto_por_30s", index=False)
# clips + 71 variables
ex_rows, v_rows, f_rows = [], [], []
for c in J["clips"]:
    b = c["score_breakdown"]
    ex_rows.append({"rank": c["rank"], "puntaje_final_0_99": c["score_final"], "hook": b["hook"], "flow": b["flow"], "value": b["value"], "inicio": mm(c["start"]), "fin": mm(c["end"]),
                    "duracion_s": round(c["duration"], 1), "titulo": c["context"]["title"], "gancho": c["context"].get("hook"), "texto": c["text"],
                    "palabras_clave": ", ".join(k["term"] for k in c.get("keywords", [])), "archivo": Path(c["render"]["path"]).name})
    en_f = {r["var"] for r in (c.get("explain") or {}).get("vars", [])}
    for dim, rws in (c.get("dim_vars") or {}).items():
        for r in rws:
            g = GL.G.get(r["var"]); loc = GL.LOC.get(r["var"])
            v_rows.append({"clip": c["rank"], "dimension": dim.capitalize(), "variable": r["var"], "grupo": g[0] if g else "", "valor": r["value"], "percentil_0_99": round(r["pct"] * 99), "bandera_0_1": int(r["pct"] >= 0.75),
                           "aporte_shap": r["shap"], "entra_a_la_formula": "sí" if r["var"] in en_f else "no", "que_mide": g[2] if g else "", "formula": g[1] if g else "", "codigo": f"{loc[0]}:{loc[1]}" if loc else ""})
    for r in (c.get("explain") or {}).get("vars", []):
        f_rows.append({"clip": c["rank"], "variable": r["var"], "valor": r["value"], "percentil_0_99": round(r["pct"] * 99), "bandera_0_1": int(r["pct"] >= 0.75), "peso": r["weight"], "aporte_bandera": r["weight"] * int(r["pct"] >= 0.75)})
gens = json.loads((BASE / "_gen" / "generaciones.json").read_text(encoding="utf-8"))
g_rows = [{"generacion": k, "descripcion": v["nombre"], "rank": c["rank"], "inicio": mm(c["start"]), "fin": mm(c["end"]), "puntaje": c["score"], "titulo": c["title"]} for k, v in gens.items() for c in v["clips"]]
with pd.ExcelWriter(OUT / "5_clips_y_variables.xlsx") as xw:
    pd.DataFrame(ex_rows).to_excel(xw, sheet_name="clips", index=False)
    pd.DataFrame(v_rows).to_excel(xw, sheet_name="71_variables_por_clip", index=False)
    pd.DataFrame(f_rows).to_excel(xw, sheet_name="formula_17_por_clip", index=False)
    pd.DataFrame(g_rows).to_excel(xw, sheet_name="generaciones_V0_V1_final", index=False)
ev = pd.read_parquet(work / "audio_events.parquet"); ev.to_excel(OUT / "6_eventos_de_sonido.xlsx", index=False)
shutil.copytree(res, OUT / "7_clips_generados", ignore=shutil.ignore_patterns("local.flag", "*.ass"))
(OUT / "LEEME.txt").write_text("Datos del podcast propio.\n1 video original · 2 audio (wav 16 kHz mono) · 3 transcripción (json de Whisper, txt por párrafos de 30 s) · 4 transcripción por palabra en Excel · "
    "5 Excel con los 5 clips, las 71 variables por clip (valor, percentil, bandera 0/1, aporte, descripción y línea de código), la fórmula de 17 variables y lo que eligió cada generación · "
    "6 eventos de sonido por segundo (PANNs) · 7 los 5 clips renderizados con su reporte.\n", encoding="utf-8")
# indice de la BD en Excel
idx = pd.read_csv(BASE / "BD_TESIS" / "indice_videos.csv"); idx.to_excel(BASE / "BD_TESIS" / "indice_videos.xlsx", index=False)
print("ok", {p.name: round(p.stat().st_size / 1e6, 1) for p in OUT.iterdir() if p.is_file()}, "| indice filas:", len(idx))
