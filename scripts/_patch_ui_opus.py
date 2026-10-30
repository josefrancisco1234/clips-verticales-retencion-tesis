"""Rediseña la portada de web_clips.py: una sola entrada (archivo o link de YouTube), sin videos de ejemplo."""
from pathlib import Path

p = Path(__file__).with_name("web_clips.py")
s = p.read_text(encoding="utf-8")

# 1) HTML de la portada
a = s.index(' <div class="panel" id="upl">')
b = s.index(' <div id="tabs" class="ex"></div>')
HERO = ''' <section id="hero">
  <h1>Convierte tu podcast en <span class="grad">5 clips verticales</span> listos para publicar</h1>
  <p class="lead">Sube un video o pega un link de YouTube. Elegimos los 5 mejores momentos, los recortamos en 9:16 con subtítulos y te mostramos por qué obtuvieron su puntaje de 0 a 99.</p>
  <div class="card">
   <div id="drop" class="drop" tabindex="0">
    <div class="ico">⬆</div>
    <div class="t1" id="dtxt">Arrastra tu video aquí o <u>elige un archivo</u></div>
    <div class="sub">mp4, mkv, mov, webm… hasta 4 GB</div>
    <input type="file" id="fup" accept="video/*" hidden>
   </div>
   <div class="or"><span>o pega un link de YouTube</span></div>
   <div class="urlrow"><input id="url" type="text" placeholder="https://www.youtube.com/watch?v=…"></div>
   <button id="go" class="cta">✨ Generar mis 5 clips</button>
   <div class="bar" id="upbar" style="display:none"><i></i></div><div id="upmsg" class="sub" style="margin-top:8px;text-align:center"></div>
  </div>
  <div class="feats"><div><b>1 · Detecta</b><span>Transcribe y puntúa cada pasaje con 71 variables de audio y texto.</span></div>
   <div><b>2 · Elige</b><span>Los 5 momentos con mayor puntaje, sin solaparse.</span></div>
   <div><b>3 · Explica</b><span>Cada clip trae su puntaje 0–99 y las variables que lo explican.</span></div></div>
 </section>
 <div id="newrow" style="display:none"><button id="newbtn" class="ghost">← Nuevo video</button></div>
'''
s = s[:a] + HERO + s[b:]

# 2) CSS
CSS = '''#hero{max-width:760px;margin:26px auto 10px;text-align:center}
#hero h1{font-size:34px;line-height:1.15;margin:0 0 12px;letter-spacing:-.5px}
.grad{background:linear-gradient(90deg,#9b83ff,#22c55e);-webkit-background-clip:text;background-clip:text;color:transparent}
.lead{color:var(--mut);font-size:15.5px;margin:0 auto 22px;max-width:620px}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;text-align:left;box-shadow:0 10px 40px #0006}
.drop{border:2px dashed #3a4156;border-radius:14px;padding:30px 16px;text-align:center;cursor:pointer;transition:.15s;background:#12151c}
.drop:hover,.drop.on{border-color:var(--acc);background:#171533}
.drop .ico{font-size:30px;color:var(--acc)}.drop .t1{font-size:16px;font-weight:600;margin-top:4px}
.drop.has{border-style:solid;border-color:#1f6b3a;background:#0f2a1a}
.or{display:flex;align-items:center;gap:12px;color:var(--mut);font-size:12.5px;margin:16px 0 12px}
.or:before,.or:after{content:"";flex:1;height:1px;background:var(--line)}
.urlrow input{width:100%;min-width:0}
.cta{width:100%;margin-top:14px;font-size:16px;padding:14px;border-radius:12px;background:linear-gradient(90deg,#7c5cff,#5b8cff)}
.feats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:22px;text-align:left}
.feats div{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.feats b{display:block;margin-bottom:3px}.feats span{color:var(--mut);font-size:12.5px}
@media(max-width:600px){#hero h1{font-size:25px}}
'''
s = s.replace("</style></head><body>", CSS + "</style></head><body>", 1)

# 3) cabecera más sobria
s = s.replace("<span>· potencial de retención 0–99 · solo contenido · Tesis Núñez del Prado (U. de Lima)</span>",
              "<span>· puntaje de retención 0–99 · solo audio y texto</span>", 1)

# 4) JS: quitar ejemplos y panel "Mis videos"; lógica unificada
a = s.index("async function examples(){")
b = s.index("function tabs(active){")
s = s[:a] + s[b:]
a = s.index("async function mis(){")
b = s.index("const ITEMS=[")
NEW = '''let FILE=null;
function setFile(f){FILE=f;$("drop").classList.toggle("has",!!f);$("dtxt").innerHTML=f?"✓ "+f.name+" ("+(f.size/1e6).toFixed(0)+" MB)":"Arrastra tu video aquí o <u>elige un archivo</u>";}
$("drop").onclick=()=>$("fup").click();
$("fup").onchange=e=>setFile(e.target.files[0]||null);
["dragover","dragenter"].forEach(n=>$("drop").addEventListener(n,e=>{e.preventDefault();$("drop").classList.add("on")}));
["dragleave","drop"].forEach(n=>$("drop").addEventListener(n,e=>{e.preventDefault();$("drop").classList.remove("on")}));
$("drop").addEventListener("drop",e=>{const f=e.dataTransfer.files[0];if(f)setFile(f)});
function subir(f){
  $("go").disabled=true;
  const x=new XMLHttpRequest();x.open("POST","/api/upload?name="+encodeURIComponent(f.name));$("upbar").style.display="block";
  x.upload.onprogress=e=>{if(e.lengthComputable){const p=Math.round(e.loaded/e.total*100);$("upbar").firstElementChild.style.cssText="width:"+p+"%;animation:none";$("upmsg").textContent="Subiendo… "+p+" %"}};
  x.onload=()=>{let j={};try{j=JSON.parse(x.responseText)}catch(e){}
    $("upbar").style.display="none";$("go").disabled=false;
    if(x.status===200){$("upmsg").textContent="";start(j.name)}else $("upmsg").textContent=j.error||"Error al subir";};
  x.onerror=()=>{$("go").disabled=false;$("upmsg").textContent="Error de red al subir"};x.send(f);
}
$("go").onclick=()=>{
  if(FILE)return subir(FILE);
  if($("url").value.trim())return start();
  $("upmsg").textContent="Sube un video o pega un link de YouTube.";
};
$("newbtn").onclick=()=>{$("hero").style.display="";$("newrow").style.display="none";$("out").innerHTML="";$("prog").style.display="none";$("tabs").innerHTML="";setFile(null);$("fup").value="";$("url").value="";$("upmsg").textContent="";window.scrollTo(0,0)};
$("url").addEventListener("keydown",e=>{if(e.key==="Enter"&&!FILE)start()});
'''
s = s[:a] + NEW + s[b:]

# eliminar el manejador antiguo de subida y las llamadas finales
a = s.index('$("upbtn").onclick=()=>{')
b = s.index("</script></body></html>")
s = s[:a] + s[b:]

s = s.replace('$("go").disabled=true;document.querySelectorAll("#exs button,#mis button,#misgo").forEach(b=>b.disabled=true);',
              '$("go").disabled=true;$("hero").style.display="none";$("newrow").style.display="block";', 1)
s = s.replace('$("go").disabled=false;document.querySelectorAll("#exs button,#mis button,#misgo").forEach(b=>b.disabled=false);',
              '$("go").disabled=false;', 1)
p.write_text(s, encoding="utf-8")
print("ok")
