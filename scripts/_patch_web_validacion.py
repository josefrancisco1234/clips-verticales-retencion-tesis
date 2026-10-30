"""Agrega a scripts/web_clips.py: subida del podcast desde el navegador y el formato de validación con 5 participantes (API + panel + resumen + Excel)."""
import sys
from pathlib import Path

f = Path(__file__).resolve().parent / "web_clips.py"
s = f.read_text(encoding="utf-8").replace("\r\n", "\n")
ITEMS_LISTA = ["Los cinco clips elegidos me parecen momentos interesantes del episodio.", "Publicaría estos clips en mis redes con poca o ninguna edición.", "La explicación del puntaje (banderas 0/1 por variable) es fácil de entender.", "El puntaje de 0 a 99 me ayuda a decidir qué clip publicar primero.", "La página web es fácil de usar.", "Este sistema me ahorraría tiempo frente a elegir los clips manualmente."]


def rep(a, b):
    global s
    assert s.count(a) == 1, (a[:70], s.count(a))
    s = s.replace(a, b)


# ---------------- servidor: constantes y funciones de validacion
rep('EXT_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv"}\n', '''EXT_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv"}
MAX_UPLOAD = 4 * 1024 ** 3                         # 4 GB por video subido
VAL = Path(r"F:\\TESISJF\\validacion")               # respuestas de los 5 participantes (una linea JSON por envio)
VAL_F = VAL / "respuestas.jsonl"
ITEMS_VAL = ["Los cinco clips elegidos me parecen momentos interesantes del episodio.", "Publicaría estos clips en mis redes con poca o ninguna edición.",
             "La explicación del puntaje (banderas 0/1 por variable) es fácil de entender.", "El puntaje de 0 a 99 me ayuda a decidir qué clip publicar primero.",
             "La página web es fácil de usar.", "Este sistema me ahorraría tiempo frente a elegir los clips manualmente."]
''')
rep("class H(BaseHTTPRequestHandler):", '''def guardar_validacion(b: dict) -> tuple[bool, str]:
    """Valida y guarda una respuesta del formato de 5 participantes (consentimiento + 6 afirmaciones Likert + calificacion de cada clip)."""
    if b.get("participante") not in {f"P{i}" for i in range(1, 6)}:
        return False, "Elige el participante (P1 a P5)."
    if b.get("consentimiento") is not True:
        return False, "Falta marcar el consentimiento informado."
    items, clips = b.get("items") or [], b.get("clips") or []
    if len(items) != len(ITEMS_VAL) or any(not isinstance(x, int) or not 1 <= x <= 5 for x in items):
        return False, "Responde las 6 afirmaciones con una nota de 1 a 5."
    if not clips or any(not isinstance(c.get("rating"), int) or not 1 <= c["rating"] <= 5 for c in clips):
        return False, "Califica cada clip de 1 a 5."
    VAL.mkdir(parents=True, exist_ok=True)
    reg = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "participante": b["participante"], "consentimiento": True, "video": str(b.get("dir", "")), "items": items,
           "clips": [{"rank": c.get("rank"), "rating": c["rating"]} for c in clips], "comentario_1": str(b.get("comentario_1", ""))[:2000], "comentario_2": str(b.get("comentario_2", ""))[:2000]}
    with open(VAL_F, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\\n")
    return True, f"Gracias, {b['participante']}: respuesta guardada."


def leer_validacion() -> list[dict]:
    """Ultima respuesta de cada participante (si repite, vale la ultima)."""
    if not VAL_F.exists():
        return []
    ult = {}
    for ln in VAL_F.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            r = json.loads(ln)
            ult[r["participante"]] = r
    return [ult[k] for k in sorted(ult)]


def resumen_validacion() -> dict:
    import statistics
    R = leer_validacion()
    filas = []
    for i, t in enumerate(ITEMS_VAL):
        v = [r["items"][i] for r in R]
        filas.append({"afirmacion": t, "n": len(v), "mediana": statistics.median(v) if v else None, "min": min(v) if v else None, "max": max(v) if v else None})
    cl = [c["rating"] for r in R for c in r["clips"]]
    return {"participantes": [r["participante"] for r in R], "n": len(R), "items": filas, "clips_mediana": statistics.median(cl) if cl else None,
            "comentarios": [{"participante": r["participante"], "c1": r["comentario_1"], "c2": r["comentario_2"]} for r in R],
            "nota": "Con n = 5 es estadistica descriptiva (mediana y rango); no se hacen inferencias."}


def excel_validacion() -> bytes:
    import io
    import pandas as pd
    R, S = leer_validacion(), resumen_validacion()
    filas = [{"participante": r["participante"], "fecha": r["fecha"], "video": r["video"], **{f"afirmacion_{i + 1}": x for i, x in enumerate(r["items"])},
              **{f"clip_{c['rank']}": c["rating"] for c in r["clips"]}, "comentario_1": r["comentario_1"], "comentario_2": r["comentario_2"]} for r in R]
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        pd.DataFrame(filas).to_excel(xw, sheet_name="respuestas", index=False)
        pd.DataFrame(S["items"]).to_excel(xw, sheet_name="resumen_descriptivo", index=False)
    return bio.getvalue()


class H(BaseHTTPRequestHandler):''')
# ---------------- POST: subida y registro
rep('''    def do_POST(self):
        if urlparse(self.path).path == "/api/run_local":''', '''    def do_POST(self):
        if urlparse(self.path).path == "/api/upload":   # el video llega como cuerpo crudo (sin multipart) para poder subir archivos grandes
            name = Path(parse_qs(urlparse(self.path).query).get("name", [""])[0]).name
            n = int(self.headers.get("Content-Length", 0))
            if not name or Path(name).suffix.lower() not in EXT_VIDEO:
                return self.send_json({"error": "Formato no admitido (usa mp4, mkv, mov, avi, webm...)"}, 400)
            if n <= 0 or n > MAX_UPLOAD:
                return self.send_json({"error": "El archivo esta vacio o pesa mas de 4 GB"}, 400)
            MIS_VIDEOS.mkdir(parents=True, exist_ok=True)
            dest = MIS_VIDEOS / name
            tmp = dest.with_name(dest.name + ".part")
            left = n
            with open(tmp, "wb") as fh:
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    fh.write(chunk)
                    left -= len(chunk)
            if left:
                tmp.unlink(missing_ok=True)
                return self.send_json({"error": "La subida se interrumpio"}, 400)
            tmp.replace(dest)
            return self.send_json({"name": name, "mb": round(n / 1e6, 1)})
        if urlparse(self.path).path == "/api/validacion/registrar":
            n = int(self.headers.get("Content-Length", 0))
            ok, msg = guardar_validacion(json.loads(self.rfile.read(n) or b"{}"))
            return self.send_json({"ok": ok, "mensaje": msg}, 200 if ok else 400)
        if urlparse(self.path).path == "/api/run_local":''')
# ---------------- GET: resumen y excel
rep('        if u.path == "/api/mis_videos":', '''        if u.path == "/api/validacion/resumen":
            return self.send_json(resumen_validacion())
        if u.path == "/api/validacion/export.xlsx":
            b = excel_validacion()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", 'attachment; filename="validacion_5_participantes.xlsx"')
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if u.path == "/api/mis_videos":''')
# ---------------- interfaz: panel de subida
rep(' <div class="panel" id="mispanel">', ''' <div class="panel" id="upl"><b>Sube tu podcast</b> <span class="sub">· mp4, mkv, mov… (hasta 4 GB): se procesa solo y devuelve los 5 mejores momentos</span>
  <div class="row" style="margin-top:8px"><input type="file" id="fup" accept="video/*"><button id="upbtn">Subir y generar mis 5 clips</button></div>
  <div class="bar" id="upbar" style="display:none"><i></i></div><div id="upmsg" class="sub" style="margin-top:6px"></div></div>
 <div class="panel" id="mispanel">''')
# ---------------- interfaz: panel de validacion tras los resultados
rep('tabs(R.dir);render(R);', 'tabs(R.dir);render(R);valPanel(R);')
rep('examples();mis();', '''const ITEMS=__ITEMS__;
function radios(n){return [1,2,3,4,5].map(k=>`<label style="margin-right:10px"><input type="radio" name="${n}" value="${k}"> ${k}</label>`).join("")}
function valPanel(R){
  const d=document.createElement("div");d.className="panel";d.id="valpanel";
  d.innerHTML=`<h3 style="margin:0 0 6px">Validación con usuarios (formato de 5 participantes)</h3>
  <div class="sub">Responde después de ver los 5 clips. 1 = totalmente en desacuerdo, 5 = totalmente de acuerdo. Es anónimo; el consentimiento firmado se entrega aparte, en papel.</div>
  <div class="row" style="margin-top:8px"><select id="vpart">${[1,2,3,4,5].map(n=>`<option value="P${n}">Participante ${n}</option>`).join("")}</select>
  <label><input type="checkbox" id="vcons"> Doy mi consentimiento informado para participar</label></div>
  <table style="margin-top:8px"><tr><th>Clip</th><th>¿Qué tan buen momento es? (1–5)</th></tr>${R.clips.map(c=>`<tr><td>#${c.rank} · ${c.title||""}</td><td>${radios("clip"+c.rank)}</td></tr>`).join("")}</table>
  <table style="margin-top:8px"><tr><th>Afirmación</th><th>1–5</th></tr>${ITEMS.map((t,i)=>`<tr><td>${i+1}. ${t}</td><td>${radios("item"+i)}</td></tr>`).join("")}</table>
  <textarea id="vc1" placeholder="¿Qué clip cambiaría o descartaría, y por qué?" style="width:100%;margin-top:8px"></textarea>
  <textarea id="vc2" placeholder="¿Qué mejoraría de la página o de la explicación del puntaje?" style="width:100%;margin-top:6px"></textarea>
  <div class="row" style="margin-top:8px"><button id="vsend">Enviar respuestas</button><button id="vres" class="ghost">Ver resumen de los participantes</button><a href="/api/validacion/export.xlsx" style="color:#b6a8ff">Descargar Excel</a></div>
  <div id="vmsg" class="sub" style="margin-top:6px"></div><div id="vsum"></div>`;
  $("out").appendChild(d);
  const val=n=>{const e=document.querySelector(`input[name="${n}"]:checked`);return e?+e.value:null};
  $("vsend").onclick=async()=>{
    const items=ITEMS.map((_,i)=>val("item"+i)),clips=R.clips.map(c=>({rank:c.rank,rating:val("clip"+c.rank)}));
    const r=await fetch("/api/validacion/registrar",{method:"POST",body:JSON.stringify({participante:$("vpart").value,consentimiento:$("vcons").checked,dir:R.dir,items,clips,comentario_1:$("vc1").value,comentario_2:$("vc2").value})});
    const j=await r.json();$("vmsg").textContent=j.mensaje||j.error||"";if(j.ok)resumenVal();};
  $("vres").onclick=resumenVal;
}
async function resumenVal(){
  const S=await (await fetch("/api/validacion/resumen")).json();
  $("vsum").innerHTML=`<div class="sub" style="margin-top:8px"><b>${S.n} de 5 participantes</b> (${S.participantes.join(", ")||"ninguno"}) · mediana de los clips: ${S.clips_mediana??"—"} · ${S.nota}</div>
  <table><tr><th>Afirmación</th><th>n</th><th>mediana</th><th>mín–máx</th></tr>${S.items.map(i=>`<tr><td>${i.afirmacion}</td><td>${i.n}</td><td>${i.mediana??"—"}</td><td>${i.min??"—"}–${i.max??"—"}</td></tr>`).join("")}</table>`;
}
$("upbtn").onclick=()=>{
  const f=$("fup").files[0];if(!f){alert("Elige primero un video");return}
  const x=new XMLHttpRequest();x.open("POST","/api/upload?name="+encodeURIComponent(f.name));$("upbar").style.display="block";
  x.upload.onprogress=e=>{if(e.lengthComputable){const p=Math.round(e.loaded/e.total*100);$("upbar").firstElementChild.style.width=p+"%";$("upmsg").textContent="Subiendo… "+p+" %"}};
  x.onload=()=>{let j={};try{j=JSON.parse(x.responseText)}catch(e){}
    if(x.status===200){$("upmsg").textContent="Subido: "+j.name+" ("+j.mb+" MB). Generando los 5 clips…";mis();start(j.name)}else $("upmsg").textContent=j.error||"Error al subir";};
  x.onerror=()=>{$("upmsg").textContent="Error de red al subir"};x.send(f);};
examples();mis();'''.replace("__ITEMS__", __import__("json").dumps(ITEMS_LISTA, ensure_ascii=False)))
f.write_text(s, encoding="utf-8")
print("ok")
