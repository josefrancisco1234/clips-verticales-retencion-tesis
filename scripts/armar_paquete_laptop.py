"""Paquete portátil para mostrar en cualquier laptop con Windows (sin Python, sin GPU, sin internet).

Construye un único .exe que sirve una pantalla de inicio con (1) la demo de los 3 videos de ejemplo y (2) el resultado REAL de un podcast propio
(5 clips verticales con puntaje, desglose y texto). Luego lo empaqueta con el Word, el PPT, la ficha y la carpeta de fuentes."""
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import glosario_variables as GL  # noqa: E402
BASE = Path(r"F:\TESISJF")
TMP = BASE / "_paquete"
SITE = TMP / "site"
PY = BASE / "tesis_data" / ".venv" / "Scripts" / "python.exe"
if TMP.exists():
    shutil.rmtree(TMP, ignore_errors=True)
(SITE / "mi_podcast").mkdir(parents=True)
shutil.copytree(BASE / "tesis" / "documentos" / "entregables" / "demo_publicada", SITE / "demo3")
_ix = SITE / "demo3" / "index.html"   # la demo original no declara codificacion: se fuerza UTF-8
_h = _ix.read_text(encoding="utf-8")
if "charset" not in _h[:600].lower():
    _h = _h.replace("<head>", '<head><meta charset="utf-8">', 1) if "<head>" in _h else '<meta charset="utf-8">' + _h
    _ix.write_text(_h, encoding="utf-8")

# ---------------- resultado real del podcast propio
import random
src = next(d for d in (BASE / "CLIPS_GENERADOS").iterdir() if (d / "clips.json").exists())
J = json.loads((src / "clips.json").read_text(encoding="utf-8"))
video = next(p for p in (BASE / "MIS_VIDEOS").iterdir() if p.suffix.lower() in {".mp4", ".mkv", ".mov"})
DUR = J["duration_s"]
# 5 tramos AL AZAR del mismo video (misma duracion que los elegidos, sin solape con ellos ni entre si; semilla fija = reproducible)
rng = random.Random(2026)
usados = [(c["start"], c["end"]) for c in J["clips"]]
azar = []
for c in J["clips"]:
    for _ in range(500):
        t0 = rng.uniform(60, DUR - 120)
        t1 = t0 + c["duration"]
        if all(t1 < a or t0 > b for a, b in usados):
            usados.append((t0, t1)); azar.append((t0, t1)); break
for k, (t0, t1) in enumerate(azar, 1):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.2f}", "-i", str(video), "-t", f"{t1 - t0:.2f}", "-vf", "crop=ih*9/16:ih,scale=540:960",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", str(SITE / "mi_podcast" / f"azar_{k:02d}.mp4")], check=True)
mm = lambda t: f"{int(t // 60):02d}:{int(t % 60):02d}"
GEN = json.loads((BASE / "_gen" / "generaciones.json").read_text(encoding="utf-8"))
final_sel = [(c["start"], c["end"]) for c in J["clips"]]
def solapa(a, b): return min(a[1], b[1]) - max(a[0], b[0]) > 0
def fila_gen(titulo, sub, sel, cls, prefijo, puntajes=None, cortar=True):
    if cortar:
        for k, (t0, t1) in enumerate(sel, 1):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.2f}", "-i", str(video), "-t", f"{t1 - t0:.2f}", "-vf", "crop=ih*9/16:ih,scale=540:960",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", str(SITE / "mi_podcast" / f"{prefijo}_{k}.mp4")], check=True)
    marcas = "".join(f'<i class="m {cls}" style="left:{a / DUR * 100:.2f}%;width:{max((b - a) / DUR * 100, 0.5):.2f}%"></i>' for a, b in sel)
    comunes = sum(any(solapa(x, y) for y in final_sel) for x in sel)
    det = "".join(f'<figure><video src="{prefijo}_{k}.mp4" controls preload="metadata"></video><figcaption>{mm(a)}–{mm(b)} · {b - a:.0f} s' + (f" · puntaje {puntajes[k - 1]}" if puntajes else "") + "</figcaption></figure>" for k, (a, b) in enumerate(sel, 1))
    return f'<div class="gen"><div class="gh"><b>{titulo}</b><span>{sub} · coincide con el modelo final en {comunes} de 5 tramos</span></div><div class="tl all" style="margin:6px 0">{marcas}</div><details><summary>Ver sus 5 clips (recorte vertical sin subtítulos)</summary><div class="fig">{det}</div></details></div>'
gen_html = fila_gen("Generación 0 · Azar (el punto de partida)", "5 tramos sorteados, sin ningún criterio", azar, "a", "azar", cortar=False)
for k_, cls_, pref_ in (("V0", "g1", "gv0"), ("V1", "g2", "gv1"), ("FINAL", "g3", "gfin")):
    g_ = GEN[k_]
    gen_html += fila_gen(f"Generación {['V0','V1','FINAL'].index(k_) + 1} · {g_['nombre']}", "elige con audio y texto", [(c["start"], c["end"]) for c in g_["clips"]], cls_, pref_, [c["score"] for c in g_["clips"]])
tarjetas = []
for c in J["clips"]:
    f = Path(c["render"]["path"]).name
    nuevo = f"clip_{c['rank']:02d}.mp4"
    shutil.copy(src / f, SITE / "mi_podcast" / nuevo)
    b = c["score_breakdown"]
    barras = "".join(f'<div class="b"><span>{n}</span><div><i style="width:{v}%"></i></div><em>{v}</em></div>' for n, v in (("Hook", b["hook"]), ("Flow", b["flow"]), ("Value", b["value"])))
    kws = "".join(f"<li><b>{html.escape(k['term'])}</b> <small>{html.escape(k['context'][:140])}…</small></li>" for k in c.get("keywords", [])[:4])
    ex = c.get("explain")
    ban = ""
    if ex:
        filas = "".join(f'<tr><td>{html.escape(r["var"])}</td><td>{round(r["pct"] * 99)}</td><td><span class="fl {"f1" if r["pct"] >= 0.75 else "f0"}">{1 if r["pct"] >= 0.75 else 0}</span></td><td>{r["weight"]:+.2f}</td></tr>' for r in sorted(ex["vars"], key=lambda r: -r["pct"]))
        n1 = sum(r["pct"] >= 0.75 for r in ex["vars"])
        ban = f'<details><summary>Variables de la fórmula como 0/1 ({n1} de {len(ex["vars"])} en 1): las que puntúan</summary><p class="x">1 = la variable está en el 25 % más alto de este video. El puntaje usa el percentil completo (0–99); la bandera solo ayuda a leerlo.</p><table class="vt"><tr><th>variable</th><th>0–99</th><th>0/1</th><th>peso</th></tr>{filas}</table></details>'
    dv = c.get("dim_vars") or {}
    ban71 = ""
    if dv:
        en_formula = {r["var"] for r in (ex or {}).get("vars", [])}
        orden = {v_: i_ for i_, v_ in enumerate(GL.ORDER)}
        NOM = {"hook": "Hook · gancho", "flow": "Flow · fluidez", "value": "Value · contenido, audio, emoción"}
        def info_var(v_):
            g_ = GL.G.get(v_)
            loc = GL.LOC.get(v_)
            return (f'<br><small>{html.escape(g_[2])}' + (f' · <code>{html.escape(str(loc[0]).split("/")[-1])}:{loc[1]}</code>' if loc else "") + "</small>") if g_ else ""
        bloques = ""
        for dim in ("hook", "flow", "value"):
            rows = sorted(dv.get(dim, []), key=lambda r_: orden.get(r_["var"], 9999))
            tot = sum(r_["shap"] for r_ in rows); ab = sum(abs(r_["shap"]) for r_ in rows) or 1
            filas_ = "".join(f'<tr><td><b>{html.escape(r_["var"])}</b>{info_var(r_["var"])}</td><td>{"—" if r_["value"] is None else f"{r_[chr(118)+chr(97)+chr(108)+chr(117)+chr(101)]:.3g}"}</td><td>{round(r_["pct"] * 99)}</td><td><span class="fl {"f1" if r_["pct"] >= 0.75 else "f0"}">{1 if r_["pct"] >= 0.75 else 0}</span></td><td class="{"pos" if r_["shap"] >= 0 else "neg"}">{r_["shap"]:+.3f}</td><td>{round(abs(r_["shap"]) / ab * 100)} %</td><td>{"✔" if r_["var"] in en_formula else ""}</td></tr>' for r_ in rows)
            bloques += f'<div class="dimb"><b>{NOM[dim]}</b> · puntaje de la dimensión <b>{b[dim]}</b>/99 · suma de aportes {tot:+.2f}<div class="scr"><table class="vt dv"><tr><th>variable (en el orden del código)</th><th>valor</th><th>0–99</th><th>0/1</th><th>aporte</th><th>peso</th><th>puntúa</th></tr>{filas_}</table></div></div>'
        n_tot = sum(len(v_) for v_ in dv.values())
        ban71 = f'<details open><summary><b>Desglose por variable: las {n_tot} variables de este clip</b></summary><p class="x"><b>0–99</b> = qué tan alta es la variable en este clip frente a las demás ventanas del mismo video; <b>0/1</b> = 1 si está en el 25 % más alto. <b>aporte</b> = cuánto sumó (verde) o restó (rojo) a la dimensión. <b>puntúa ✔</b> = la variable entra a la fórmula del puntaje final (17 de {n_tot}); las demás explican el clip y alimentan al modelo aprendido. El puntaje global sale de la fórmula de 17 variables.</p>{bloques}</details>'
    tarjetas.append(f"""<article><video src="{nuevo}" controls preload="metadata"></video><div class="info">
<div class="top"><span class="score">{c['score_final']}</span><div><h3>#{c['rank']} · {html.escape(c['context']['title'])}</h3><p class="t">{mm(c['start'])} – {mm(c['end'])} · {c['duration']:.0f} s</p></div></div>
{barras}<p class="hook"><b>Gancho:</b> {html.escape(str(c['context'].get('hook') or ''))}</p>
<details><summary>Por qué se eligió y palabras de mayor peso</summary><p>{html.escape(str(c['context'].get('reason') or ''))}</p><ul>{kws}</ul></details>
{ban}{ban71}<details><summary>Texto del clip</summary><p class="x">{html.escape(c['text'][:900])}</p></details></div></article>""")
tarj_azar = "".join(f'<article class="az"><video src="azar_{k:02d}.mp4" controls preload="metadata"></video><div class="info"><h3>Azar {k}</h3><p class="t">{mm(t0)} – {mm(t1)} · {t1 - t0:.0f} s</p><p class="x">Tramo sorteado: sin puntaje, sin gancho elegido y sin subtítulos.</p></div></article>' for k, (t0, t1) in enumerate(azar, 1))
marc_sis = "".join(f'<i class="m s" style="left:{c["start"] / DUR * 100:.2f}%;width:{max((c["end"] - c["start"]) / DUR * 100, 0.5):.2f}%" title="#{c["rank"]}"></i>' for c in J["clips"])
marc_az = "".join(f'<i class="m a" style="left:{t0 / DUR * 100:.2f}%;width:{max((t1 - t0) / DUR * 100, 0.5):.2f}%"></i>' for t0, t1 in azar)
pasos = [("Leer el video", f"{DUR / 60:.0f} minutos de audio y video"), ("Transcribir con Whisper", f"idioma detectado: {J['language']}; palabras con marcas de tiempo"),
         ("Segmentar", f"{J['n_candidates']} candidatos de 15 a 90 s alineados a oración"), ("Calcular variables", "audio, texto, gancho, fluidez, eventos de sonido (71 variables por candidato)"),
         ("Puntuar y elegir", "17 variables en 0/1 (top 25 % de su video) × su peso; 5 clips sin solape mayor a 30 % (NMS)"), ("Renderizar 9:16", "reencuadre vertical y subtítulos con palabras clave resaltadas")]
pasos_html = "".join(f'<li id="p{k}"><b>{t}</b><span>{d}</span></li>' for k, (t, d) in enumerate(pasos))
barras_tesis = "".join(f'<div class="bt"><span>{n}</span><div><i style="width:{v}%;background:{c}"></i></div><em>{v} %</em></div>' for n, v, c in
                       (("Azar", 26.9, "#8e93a6"), ("Fórmula V0 (17 variables)", 47.3, "#5b8def"), ("Fórmula V1 (clips ≤ 45 s)", 54.8, "#8b73ff"), ("LightGBM R0 (aprendido)", 62.4, "#5fe08e")))
hitos = [("22 sep 2026", "Se define el problema y el modelo", "Elegir clips de podcasts con audio y texto; LightGBM LambdaRank como ranker y una red RankNet como línea base."),
         ("fin sep 2026", "Se construye el pipeline", "Whisper, variables de audio (PANNs), texto y embeddings; HuBERT se descarta por costo en CPU."),
         ("12 oct 2026", "La fórmula simple gana", "Una batería de 9 modelos y 12 redes de secuencia no supera a la fórmula de 17 variables en videos nuevos."),
         ("oct 2026", "Se amplía y se confirma", "765 audios; cohortes frescas congeladas antes de mirarlas; la hipótesis se escribe antes de probar."),
         ("oct 2026", "Redes neuronales propias", "Red de ecuaciones (EQL) que entrega una fórmula legible y empata con LightGBM."),
         ("22 oct 2026", "Agente neuronal 24/7", "Una red que muta su arquitectura e inventa variables, y solo se promueve con evidencia."),
         ("hoy", "Producto final", "Pones un podcast en una carpeta y salen 5 clips verticales con puntaje.")]
hitos_html = "".join(f'<li><em>{a}</em><div><b>{b}</b><p>{c}</p></div></li>' for a, b, c in hitos)
(SITE / "mi_podcast" / "index.html").write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mi podcast: 5 clips</title>
<style>:root{{--bg:#0f1015;--s:#171923;--l:#272b3a;--f:#e9eaf0;--m:#8e93a6;--a:#8b73ff;--g:#5fe08e}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--f);font:15px/1.5 Segoe UI,system-ui,sans-serif}}
header{{padding:22px 28px;border-bottom:1px solid var(--l)}}h1{{margin:0;font-size:22px}}header p{{margin:4px 0 0;color:var(--m)}}a{{color:var(--a)}}.wrap{{max-width:1200px;margin:0 auto;padding:22px}}h2{{font-size:18px;margin:28px 0 10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:18px}}article{{background:var(--s);border:1px solid var(--l);border-radius:14px;padding:14px;display:flex;gap:14px}}article.az{{opacity:.92}}
video{{width:190px;aspect-ratio:9/16;background:#000;border-radius:10px;flex:none}}.info{{flex:1;min-width:0}}.top{{display:flex;gap:12px;align-items:center}}.score{{background:var(--a);color:#0f1015;font-weight:700;font-size:26px;border-radius:12px;padding:6px 12px}}
h3{{margin:0;font-size:16px}}.t{{margin:2px 0 0;color:var(--m);font-size:13px}}.b{{display:grid;grid-template-columns:48px 1fr 26px;gap:6px;align-items:center;font-size:12px;color:var(--m);margin-top:5px}}.b div{{height:6px;background:var(--l);border-radius:3px}}.b i{{display:block;height:100%;background:var(--g);border-radius:3px}}
.hook{{font-size:13px}}details{{margin-top:6px;font-size:13px}}summary{{cursor:pointer;color:var(--a)}}small{{color:var(--m)}}.x{{color:var(--m);font-size:13px}}.nota{{background:var(--s);border:1px solid var(--l);border-radius:12px;padding:12px 16px;margin-bottom:10px;color:var(--m);font-size:13px}}
button{{background:var(--a);color:#0f1015;border:0;border-radius:10px;padding:9px 16px;font-weight:700;cursor:pointer;font-size:14px}}ol.pasos{{list-style:none;padding:0;margin:12px 0;display:grid;gap:6px}}ol.pasos li{{display:grid;grid-template-columns:230px 1fr;gap:10px;padding:8px 12px;border:1px solid var(--l);border-radius:10px;opacity:.35;transition:.3s}}
ol.pasos li.on{{opacity:1;border-color:var(--a)}}ol.pasos li.ok{{opacity:1;border-color:var(--g)}}ol.pasos li span{{color:var(--m);font-size:13px}}.tl{{position:relative;height:34px;background:var(--s);border:1px solid var(--l);border-radius:8px;margin:6px 0 2px;overflow:hidden}}
.tl .m{{position:absolute;top:4px;bottom:4px;border-radius:4px;opacity:0;transition:opacity .6s}}.tl .m.s{{background:var(--g)}}.tl .m.a{{background:#8e93a6}}.tl.show .m{{opacity:1}}.tl .scan{{position:absolute;top:0;bottom:0;width:2px;background:var(--a);left:0}}
.lbl{{font-size:12px;color:var(--m)}}.gen{{background:var(--s);border:1px solid var(--l);border-radius:12px;padding:12px 14px;margin:10px 0}}.gh b{{display:block}}.gh span{{color:var(--m);font-size:13px}}.tl.all .m{{opacity:1}}.tl .m.g1{{background:#5b8def}}.tl .m.g2{{background:#8b73ff}}.tl .m.g3{{background:var(--g)}}.fig{{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}}figure{{margin:0;width:150px}}figure video{{width:150px}}figcaption{{font-size:11px;color:var(--m)}}.bt{{display:grid;grid-template-columns:210px 1fr 54px;gap:10px;align-items:center;margin:6px 0;font-size:14px}}.bt div{{height:14px;background:var(--l);border-radius:7px}}.bt i{{display:block;height:100%;border-radius:7px}}
ul.tm{{list-style:none;padding:0;margin:8px 0}}ul.tm li{{display:grid;grid-template-columns:110px 1fr;gap:12px;padding:8px 0;border-top:1px solid var(--l)}}ul.tm em{{color:var(--a);font-style:normal;font-weight:600}}ul.tm p{{margin:2px 0 0;color:var(--m);font-size:13px}}
.dimb{{margin-top:10px}}.scr{{max-height:340px;overflow:auto;border:1px solid var(--l);border-radius:8px;margin-top:4px}}.dv small{{color:var(--m);font-weight:400}}.dv code{{background:var(--l);border-radius:4px;padding:0 4px}}.pos{{color:var(--g)}}.neg{{color:#ff6b6b}}.vt{{border-collapse:collapse;font-size:12px;margin-top:4px}}.vt td,.vt th{{padding:2px 8px;border-bottom:1px solid var(--l);text-align:left}}.fl{{display:inline-block;min-width:22px;text-align:center;border-radius:6px;font-weight:700}}.f1{{background:#1f6b3a;color:#fff}}.f0{{background:#2a2e3b;color:var(--m)}}
@media(max-width:620px){{.grid{{grid-template-columns:1fr}}article{{flex-direction:column}}video{{width:100%;max-width:260px}}ol.pasos li{{grid-template-columns:1fr}}.bt{{grid-template-columns:1fr 54px}}.bt span{{grid-column:1/3}}}}</style></head><body>
<header><h1>Resultado real: 5 clips verticales de un podcast propio</h1><p>{DUR / 60:.0f} min de video · idioma {html.escape(J['language'])} · método: {html.escape(J['model'])} · <a href="../inicio.html">← inicio</a></p></header>
<div class="wrap"><div class="nota">El sistema eligió estos 5 tramos <b>solo con audio y texto</b>; no usó la curva de repetición de YouTube. El puntaje 0–99 es el potencial de retención relativo a este video: ordena los clips, no es una probabilidad.</div>
<h2>1 · Cómo lo procesó <button id="sim">▶ Empezar proceso</button></h2>
<div class="nota" style="margin-top:8px">Pulsa «Empezar proceso» y mira cómo el sistema llega a los 5 clips. La animación es una simulación ilustrativa de las etapas; el procesamiento real tardó {J.get('elapsed_s', 0) / 60:.0f} minutos y los clips que aparecen al final son el resultado real, ya cargado.</div>
<ol class="pasos">{pasos_html}</ol>
<div class="lbl">Línea de tiempo del video (0 a {DUR / 60:.0f} min) · verde = elegidos por el sistema</div><div class="tl" id="tl1"><div class="scan" id="scan"></div>{marc_sis}</div>
<div class="lbl">Gris = 5 tramos al azar de la misma duración</div><div class="tl" id="tl2">{marc_az}</div>
<div id="res" style="display:none"><h2>2 · Los 5 clips elegidos por el sistema</h2><div class="grid">{''.join(tarjetas)}</div>
<h2>3 · Y si fuera al azar: 5 tramos sorteados del mismo video</h2>
<div class="nota">Para ver la diferencia, estos 5 tramos se sortearon con una semilla fija y se recortaron en vertical sin subtítulos. Sirven para comparar a simple vista; en este video no hay curva real contra la cual medir cuál retiene más.</div><div class="grid">{tarj_azar}</div>
<h2>4 · Mis generaciones sobre este mismo video: del azar al modelo final</h2>
<div class="nota">Qué habría elegido cada versión del sistema en este podcast (misma línea de tiempo, 0 a {DUR / 60:.0f} min). Sin curva real no se puede decir cuál retiene más en este video: la comparación medida está en la sección siguiente.</div>{gen_html}
<h2>5 · Lo que mide la tesis: sistema frente a azar</h2>
<div class="nota">Acierto = al menos 1 de los 5 clips cae sobre un pico real de repetición de YouTube. Medido en la cohorte fresca 1 (93 videos que no se usaron para diseñar el método).</div>{barras_tesis}
<h2>6 · Cómo comenzó la tesis</h2><ul class="tm">{hitos_html}</ul></div></div>
<script>
const pasos=[...document.querySelectorAll("ol.pasos li")],tl1=document.getElementById("tl1"),tl2=document.getElementById("tl2"),scan=document.getElementById("scan");
function reset(){{pasos.forEach(p=>p.className="");tl1.classList.remove("show");tl2.classList.remove("show");scan.style.left="0"}}
reset();
document.getElementById("sim").onclick=async()=>{{reset();tl2.style.opacity=0;
  for(let k=0;k<pasos.length;k++){{pasos[k].className="on";
    if(k>=1&&k<=3){{scan.style.transition="left 1.6s linear";scan.style.left=((k)/4*100)+"%"}}
    if(k==4){{scan.style.left="100%"}}
    await new Promise(r=>setTimeout(r,1300));pasos[k].className="ok";
    if(k==4)tl1.classList.add("show");}}
  tl2.style.transition="opacity .6s";tl2.style.opacity=1;tl2.classList.add("show");const r=document.getElementById("res");r.style.display="block";r.scrollIntoView({{behavior:"smooth"}});document.getElementById("sim").textContent="↻ Repetir proceso";}};
</script></body></html>""", encoding="utf-8")

# ---------------- pantalla de inicio
(SITE / "inicio.html").write_text("""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Generador de clips - tesis</title>
<style>:root{--bg:#0f1015;--s:#171923;--l:#272b3a;--f:#e9eaf0;--m:#8e93a6;--a:#8b73ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--f);font:16px/1.5 Segoe UI,system-ui,sans-serif;min-height:100vh;display:grid;place-items:center}
.w{max-width:900px;padding:28px}h1{margin:0 0 4px;font-size:28px}p{color:var(--m)}.c{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:22px}a.k{display:block;background:var(--s);border:1px solid var(--l);border-radius:16px;padding:22px;color:var(--f);text-decoration:none}
a.k:hover{border-color:var(--a)}a.k b{font-size:19px;display:block;margin-bottom:6px}a.k span{color:var(--m);font-size:14px}.tag{display:inline-block;background:var(--a);color:#0f1015;border-radius:8px;padding:2px 9px;font-size:12px;font-weight:700;margin-bottom:10px}
@media(max-width:700px){.c{grid-template-columns:1fr}}</style></head><body><div class="w"><h1>Generador de clips 9:16</h1>
<p>Selección automática de clips con puntaje de potencial de retención (0–99) a partir de audio y texto. Tesis de José Francisco Núñez del Prado Vega, Universidad de Lima.</p>
<div class="c"><a class="k" href="demo3/index.html"><span class="tag">DEMO</span><b>Interfaz con 3 videos de ejemplo</b><span>Simulación completa: de la transcripción al puntaje, con validación contra el mapa de calor real de YouTube.</span></a>
<a class="k" href="mi_podcast/index.html"><span class="tag">RESULTADO REAL</span><b>Mi podcast: 5 clips generados</b><span>Los 5 clips verticales que el sistema produjo de un video propio, con puntaje, desglose y texto.</span></a></div></div></body></html>""", encoding="utf-8")

# ---------------- ejecutable
lanz = ROOT / "scripts" / "lanzador_demo.py"
txt = lanz.read_text(encoding="utf-8").replace('/ "demo"', '/ "site"').replace('(BASE / "index.html")', '(BASE / "inicio.html")').replace("/index.html", "/inicio.html")
(TMP / "lanzador_demo.py").write_text(txt, encoding="utf-8")
subprocess.run([str(PY), "-m", "PyInstaller", "--onefile", "--noconfirm", "--name", "Demo_Tesis_Clips", "--add-data", f"{SITE};site", "--distpath", str(TMP / "dist"),
                "--workpath", str(TMP / "work"), "--specpath", str(TMP), "--exclude-module", "numpy", "--exclude-module", "pandas", "--exclude-module", "torch",
                "--exclude-module", "matplotlib", str(TMP / "lanzador_demo.py")], check=True, capture_output=True)
shutil.copy(TMP / "dist" / "Demo_Tesis_Clips.exe", BASE / "Demo_Tesis_Clips.exe")
print("exe:", (BASE / "Demo_Tesis_Clips.exe").stat().st_size // 1_000_000, "MB")
