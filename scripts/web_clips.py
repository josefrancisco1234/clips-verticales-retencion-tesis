"""Mini pagina web local (solo libreria estandar): pegas el link de YouTube -> clips 9:16, por que se eligieron
y validacion contra el mapa de calor real.

Uso:  python scripts/web_clips.py        y abrir http://localhost:8765
El sistema elige SOLO con el contenido; la curva de YouTube se usa despues, unicamente para calificar.
"""
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
HOME = Path(os.environ.get("TESIS_HOME", r"F:\TESISJF"))                    # carpeta que contiene tesis_data, MIS_VIDEOS, SECRETOS...
DATA = Path(os.environ.get("TESIS_DATA", str(HOME / "tesis_data")))
OUTPUTS = DATA / "outputs"
HEATMAPS = DATA / "data" / "interim" / "heatmaps"
_VENV = DATA / ".venv" / "Scripts" / "python.exe"
PY = os.environ.get("TESIS_PYTHON") or (str(_VENV) if _VENV.is_file() else sys.executable)
PORT = int(os.environ.get("PORT", "8765"))
COOKIES = HOME / "SECRETOS" / "yt_cookies.txt"   # opcional; no se sube a ningun zip ni repositorio
ACCESS_KEY = os.environ.get("ACCESS_KEY", "")   # clave opcional para acceso remoto (tunel)
HOST = os.environ.get("HOST", "127.0.0.1")
MIS_VIDEOS = HOME / "MIS_VIDEOS"        # aqui pones tu podcast
SALIDA = HOME / "CLIPS_GENERADOS"       # copia de los resultados
EXT_VIDEO = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".flv", ".wmv"}
MAX_UPLOAD = 4 * 1024 ** 3                         # 4 GB por video subido
VAL = HOME / "validacion"                 # respuestas de los 5 participantes (una linea JSON por envio)
VAL_F = VAL / "respuestas.jsonl"
ITEMS_VAL = ["Los cinco clips elegidos me parecen momentos interesantes del episodio.", "Publicaría estos clips en mis redes con poca o ninguna edición.",
             "La explicación del puntaje (banderas 0/1 por variable) es fácil de entender.", "El puntaje de 0 a 99 me ayuda a decidir qué clip publicar primero.",
             "La página web es fácil de usar.", "Este sistema me ahorraría tiempo frente a elegir los clips manualmente."]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import glosario_variables as GL
YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|live/)([\w-]{11})")
JOBS: dict[str, dict] = {}
EXAMPLES = [
    {"id": "l_-igAkbVII", "lang": "ES", "note": "ejemplo 1 (4/5)"},
    {"id": "UIC10AA34YU", "lang": "EN", "note": "ejemplo 2 (3/5)"},
    {"id": "3KfZ30O2fEQ", "lang": "EN", "note": "ejemplo 3 (5/5 en evaluacion)"},
]


def latest_dir(vid: str):
    best = None
    for d in OUTPUTS.glob(f"{vid}_*"):
        if (d / "clips.json").exists() and (best is None or (d / "clips.json").stat().st_mtime > (best / "clips.json").stat().st_mtime):
            best = d
    return best


def get_heatmap(vid: str):
    p = HEATMAPS / f"{vid}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("heatmap")
    try:   # video fuera del dataset: intento pedirla a YouTube (puede fallar por anti-bot; entonces no hay validacion)
        from src.ingest import youtube
        meta = youtube.fetch_metadata(vid)
        hm = (meta or {}).get("heatmap")
        if hm:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        return hm
    except Exception:  # noqa: BLE001
        return None


def build_result(d: Path) -> dict:
    j = json.loads((d / "clips.json").read_text(encoding="utf-8"))
    m = YT_ID.search(d.name.replace("_", "&v=", 1)) or re.match(r"([\w-]{11})_", d.name)
    vid = d.name[:11]
    res = {"dir": d.name, "vid": vid, "duration": j["duration_s"], "language": j["language"], "model": j["model"],
           "elapsed": j.get("elapsed_s"), "keywords": [k["term"] for k in j.get("video_keywords", [])][:10], "clips": [],
           "heat": None, "hot": [], "hits": None}
    res["local"] = (d / "local.flag").exists()
    hm = None if res["local"] else get_heatmap(vid)   # un video propio no tiene curva de YouTube
    st = en = vals = None
    if hm:
        import numpy as np
        st = np.array([b["start_time"] for b in hm]); en = np.array([b["end_time"] for b in hm])
        vals = np.array([b["value"] for b in hm], float)
        if len(vals) > 1:
            vals[0] = vals[1]
        idx = np.nonzero(vals > 0.5)[0]
        idx = idx[np.argsort(vals[idx])[::-1]][:20]
        if len(idx) == 0:
            idx = np.argsort(vals)[::-1][:5]
        hot = [(float(st[i]), float(en[i])) for i in idx]
        res["heat"] = [{"t": float((a + b) / 2), "v": float(v)} for a, b, v in zip(st, en, vals)]
        res["hot"] = [{"a": a, "b": b} for a, b in hot]
        res["peak"] = {"a": float(st[int(vals.argmax())]), "b": float(en[int(vals.argmax())]), "v": float(vals.max())}
        res["mean_heat"] = float(vals.mean())
    hits = 0

    def mk_item(c):
        f = d / Path(c.get("render", {}).get("path", "")).name if c.get("render") else None
        item = {"rank": c.get("rank"), "start": c["start"], "end": c["end"], "score": c["score_final"],
                "hook": c["score_breakdown"]["hook"], "flow": c["score_breakdown"]["flow"], "value": c["score_breakdown"]["value"],
                "title": c["context"]["title"], "hookText": c["context"].get("hook"), "text": c["text"],
                "terms": c.get("highlighted_terms", [])[:8], "keywords": [k["term"] for k in c.get("keywords", [])][:6],
                "file": f.name if f and f.exists() else None, "explain": c.get("explain"), "dim_vars": c.get("dim_vars"), "touch": None, "heat": None,
                "chapter": (c.get("chapter") or {}).get("title")}
        if vals is not None:
            msk = (en > c["start"]) & (st < c["end"])
            item["heat"] = float(vals[msk].mean()) if msk.any() else None
            item["touch"] = any(min(c["end"], b) - max(c["start"], a) > 0 for a, b in hot)
        return item

    for c in j["clips"]:
        item = mk_item(c)
        hits += int(bool(item["touch"]))
        res["clips"].append(item)
    res["chapters"] = [{"index": ch["index"], "title": ch["title"], "start": ch["start"], "end": ch["end"], "auto": ch.get("auto", False),
                        "clips": [mk_item(c) for c in ch.get("clips", [])]} for ch in j.get("chapters", [])]
    if vals is not None:
        res["hits"] = hits
    return res


def run_job(job_id: str, url: str, curva: bool, local: str | None = None):
    job = JOBS[job_id]
    cmd = [PY, "-u", str(ROOT / "scripts" / "generar_clips.py"), url] + (["curva"] if curva else [])
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", NO_ABRIR_CARPETA="1")
    if COOKIES.is_file():   # cookies de una cuenta SECUNDARIA exportadas por el usuario (nunca la cuenta principal)
        env["YT_COOKIES_FILE"] = str(COOKIES)
    p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    for line in p.stdout:
        job["log"].append(line.rstrip())
        m = re.search(r"Clips en:\s*(.+)", line)
        if m:
            job["dir"] = Path(m.group(1).strip()).name
    job["code"] = p.wait()
    if local and job["code"] == 0 and job["dir"]:
        d = OUTPUTS / job["dir"]
        (d / "local.flag").write_text(local, encoding="utf-8")
        try:   # copia ordenada en CLIPS_GENERADOS/<nombre del video>
            dest = SALIDA / Path(local).stem
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(d, dest)
        except Exception:  # noqa: BLE001
            pass
    job["done"] = True


ITEMS_SUS = ["Creo que me gustaría usar este sistema con frecuencia.", "Encontré el sistema innecesariamente complejo.", "Pensé que el sistema era fácil de usar.",
             "Creo que necesitaría el apoyo de un técnico para poder usar este sistema.", "Encontré que las diversas funciones del sistema estaban bien integradas.",
             "Pensé que había demasiada inconsistencia en este sistema.", "Imagino que la mayoría de las personas aprendería a usar este sistema muy rápidamente.",
             "Encontré el sistema muy incómodo de usar.", "Me sentí muy seguro/a usando el sistema.", "Necesité aprender muchas cosas antes de poder usar el sistema."]


def puntaje_sus(r: list[int]) -> float:
    """SUS (Brooke, 1996; Bangor et al., 2008): impares restan 1, pares restan de 5; suma x 2.5 (0 a 100)."""
    return sum((x - 1) if i % 2 == 0 else (5 - x) for i, x in enumerate(r)) * 2.5


def perfil_val(b: dict) -> dict:
    """Datos descriptivos de la muestra (opcionales): experiencia, plataformas, tiempo manual y duracion del episodio."""
    def num(x, hi):
        try:
            v = float(x)
            return v if 0 <= v <= hi else None
        except (TypeError, ValueError):
            return None
    return {"anios_creando": num(b.get("anios_creando"), 60), "plataformas": str(b.get("plataformas", ""))[:200],
            "min_manual": num(b.get("min_manual"), 1000), "duracion_episodio_min": num(b.get("duracion_episodio_min"), 1000)}


def guardar_validacion(b: dict) -> tuple[bool, str]:
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
    sus = b.get("sus") or []
    if len(sus) != 10 or any(not isinstance(x, int) or not 1 <= x <= 5 for x in sus):
        return False, "Responde los 10 ítems de usabilidad (SUS) con una nota de 1 a 5."
    VAL.mkdir(parents=True, exist_ok=True)
    reg = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "participante": b["participante"], "consentimiento": True, "video": str(b.get("dir", "")), "items": items,
           "sus": sus, "sus_puntaje": puntaje_sus(sus), "perfil": perfil_val(b),
           "clips": [{"rank": c.get("rank"), "rating": c["rating"]} for c in clips], "comentario_1": str(b.get("comentario_1", ""))[:2000], "comentario_2": str(b.get("comentario_2", ""))[:2000]}
    with open(VAL_F, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
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
    ss = [r["sus_puntaje"] for r in R if "sus_puntaje" in r]
    return {"participantes": [r["participante"] for r in R], "n": len(R), "items": filas, "clips_mediana": statistics.median(cl) if cl else None,
            "perfil": {k: ([r["perfil"][k] for r in R if r.get("perfil", {}).get(k) is not None]) for k in ("anios_creando", "min_manual", "duracion_episodio_min")},
            "sus_media": round(sum(ss) / len(ss), 1) if ss else None, "sus_min": min(ss) if ss else None, "sus_max": max(ss) if ss else None,
            "comentarios": [{"participante": r["participante"], "c1": r["comentario_1"], "c2": r["comentario_2"]} for r in R],
            "nota": "Con n = 5 es estadistica descriptiva (mediana y rango); no se hacen inferencias."}


def excel_validacion() -> bytes:
    import io
    import pandas as pd
    R, S = leer_validacion(), resumen_validacion()
    filas = [{"participante": r["participante"], "fecha": r["fecha"], "video": r["video"], **{f"afirmacion_{i + 1}": x for i, x in enumerate(r["items"])},
              **{f"sus_{i + 1}": x for i, x in enumerate(r.get("sus", []))}, "sus_puntaje": r.get("sus_puntaje"), **{f"perfil_{k}": v for k, v in r.get("perfil", {}).items()},
              **{f"clip_{c['rank']}": c["rating"] for c in r["clips"]}, "comentario_1": r["comentario_1"], "comentario_2": r["comentario_2"]} for r in R]
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as xw:
        pd.DataFrame(filas).to_excel(xw, sheet_name="respuestas", index=False)
        extra = [{"afirmacion": "SUS (0 a 100): media y rango", "n": S["n"], "mediana": S["sus_media"], "min": S["sus_min"], "max": S["sus_max"]}]
        pd.DataFrame(S["items"] + extra).to_excel(xw, sheet_name="resumen_descriptivo", index=False)
    return bio.getvalue()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _auth(self):
        """Si ACCESS_KEY esta definida, exige la clave (cookie 'tk' o ?k=). Devuelve True si puede seguir."""
        if not ACCESS_KEY:
            return True
        ck = self.headers.get("Cookie", "")
        if f"tk={ACCESS_KEY}" in [c.strip() for c in ck.split(";")]:
            return True
        if parse_qs(urlparse(self.path).query).get("k", [""])[0] == ACCESS_KEY:
            self.send_response(302)
            self.send_header("Set-Cookie", f"tk={ACCESS_KEY}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return False
        self.send_json({"error": "Acceso restringido: abre el enlace con la clave que te dio el investigador"}, 401)
        return False

    def do_POST(self):
        if self._auth():
            self._post()

    def do_GET(self):
        if self._auth():
            self._get()

    def _post(self):
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
        if urlparse(self.path).path == "/api/run_local":
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            name = Path(str(body.get("name", ""))).name
            f = MIS_VIDEOS / name
            if not name or not f.is_file() or f.suffix.lower() not in EXT_VIDEO:
                return self.send_json({"error": "Ese video no esta en la carpeta MIS_VIDEOS"}, 400)
            jid = uuid.uuid4().hex[:8]
            JOBS[jid] = {"log": [], "done": False, "dir": None, "code": None, "vid": name, "t0": time.time()}
            threading.Thread(target=run_job, args=(jid, str(f), False, str(f)), daemon=True).start()
            return self.send_json({"job": jid})
        if urlparse(self.path).path != "/api/run":
            return self.send_json({"error": "no"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        url = str(body.get("url", "")).strip()
        m = YT_ID.search(url)
        if not m:
            return self.send_json({"error": "Pega un link de YouTube valido"}, 400)
        vid = m.group(1)
        jid = uuid.uuid4().hex[:8]
        JOBS[jid] = {"log": [], "done": False, "dir": None, "code": None, "vid": vid, "t0": time.time()}
        threading.Thread(target=run_job, args=(jid, f"https://www.youtube.com/watch?v={vid}", bool(body.get("curva"))),
                         daemon=True).start()
        self.send_json({"job": jid})

    def _get(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            b = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if u.path == "/static/flujo_scoring.png":
            f = ROOT / "web_assets" / "flujo_scoring.png"
            if not f.is_file():
                return self.send_error(404)
            b = f.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if u.path == "/api/glossary":
            return self.send_json({"order": GL.ORDER, "vars": {k: {"group": v[0], "formula": v[1], "info": v[2], "loc": GL.LOC.get(k)} for k, v in GL.G.items()},
                                   "formulas": [{"name": a, "formula": b, "info": c} for a, b, c in GL.FORMULAS]})
        if u.path == "/api/validacion/resumen":
            return self.send_json(resumen_validacion())
        if u.path == "/api/validacion/export.xlsx":
            b = excel_validacion()
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", 'attachment; filename="validacion_5_participantes.xlsx"')
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if u.path == "/api/mis_videos":
            MIS_VIDEOS.mkdir(parents=True, exist_ok=True)
            return self.send_json([{"name": p.name, "mb": round(p.stat().st_size / 1e6, 1), "mt": p.stat().st_mtime, "listo": (SALIDA / p.stem / "clips.json").exists()}
                                   for p in sorted(MIS_VIDEOS.iterdir()) if p.is_file() and p.suffix.lower() in EXT_VIDEO])
        if u.path == "/api/open_mis_videos":
            MIS_VIDEOS.mkdir(parents=True, exist_ok=True)
            os.startfile(str(MIS_VIDEOS))  # type: ignore[attr-defined]
            return self.send_json({"ok": True})
        if u.path == "/api/examples":
            return self.send_json([{**e, "ready": bool(latest_dir(e["id"]))} for e in EXAMPLES])
        if u.path == "/api/status":
            j = JOBS.get(q.get("job", [""])[0])
            if not j:
                return self.send_json({"error": "job"}, 404)
            full = " | ".join(j["log"]).lower()
            stage = 0
            for k, pat in enumerate(("video descargado", "faster_whisper", "oraciones", "cargando modelo de embeddings",
                                     "metodo de seleccion", "clip exportado", "listo:"), 1):
                if re.search(pat, full):
                    stage = k
            if "se reutiliza" in full:
                stage = max(stage, 1)
            rendered = len(re.findall(r"clip exportado", full))
            return self.send_json({"done": j["done"], "code": j["code"], "dir": j["dir"], "log": j["log"][-12:],
                                   "secs": int(time.time() - j["t0"]), "stage": stage, "rendered": rendered, "vid": j["vid"]})
        if u.path == "/api/result":
            vid, dname = q.get("vid", [None])[0], q.get("dir", [None])[0]
            d = (OUTPUTS / dname) if dname else (latest_dir(vid) if vid else None)
            if not d or not (d / "clips.json").exists():
                return self.send_json({"error": "sin resultado"}, 404)
            return self.send_json(build_result(d))
        if u.path == "/media":
            d, f = q.get("d", [""])[0], q.get("f", [""])[0]
            p = (OUTPUTS / d / f).resolve()
            if OUTPUTS.resolve() not in p.parents or not p.is_file():
                return self.send_json({"error": "no"}, 404)
            size = p.stat().st_size
            rng = self.headers.get("Range")
            a, b = 0, size - 1
            code = 200
            if rng and (mm := re.match(r"bytes=(\d*)-(\d*)", rng)):
                a = int(mm.group(1) or 0)
                b = int(mm.group(2)) if mm.group(2) else size - 1
                code = 206
            self.send_response(code)
            self.send_header("Content-Type", mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(b - a + 1))
            if code == 206:
                self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
            self.end_headers()
            with open(p, "rb") as fh:
                fh.seek(a)
                left = b - a + 1
                while left > 0:
                    chunk = fh.read(min(1 << 16, left))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    left -= len(chunk)
            return
        self.send_json({"error": "no"}, 404)


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Generador de clips</title>
<style>
:root{--bg:#0f1115;--card:#171a21;--line:#262b36;--tx:#e8ebf0;--mut:#8b93a3;--ok:#22c55e;--acc:#7c5cff;--hot:#ef4444}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.5 "Segoe UI",system-ui,sans-serif}
header{display:flex;gap:12px;align-items:center;padding:14px 24px;border-bottom:1px solid var(--line)}
.logo{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#7c5cff,#22c55e)}header span{color:var(--mut)}
.wrap{max-width:1300px;margin:0 auto;padding:18px 24px}
.row{display:flex;gap:10px;flex-wrap:wrap}
input[type=text]{flex:1;min-width:280px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 14px;color:var(--tx);font-size:14px}
button{background:var(--acc);color:#fff;border:0;border-radius:10px;padding:10px 18px;font-weight:600;cursor:pointer}
button.ghost{background:var(--card);border:1px solid var(--line);color:var(--tx);font-weight:500;padding:7px 12px;font-size:13px}
button:disabled{opacity:.5;cursor:default}
.ex{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap;align-items:center;color:var(--mut)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:14px 0}
.mut{color:var(--mut)}.sub{color:var(--mut);font-size:12.5px}
pre{background:#0b0d11;border:1px solid var(--line);border-radius:10px;padding:10px;max-height:190px;overflow:auto;font-size:11.5px;color:#b7c0cc;margin:8px 0 0;white-space:pre-wrap}
.bar{height:6px;background:var(--line);border-radius:4px;overflow:hidden;margin-top:8px}.bar i{display:block;height:100%;width:30%;background:var(--acc);animation:m 1.2s infinite}
@keyframes m{0%{margin-left:-30%}100%{margin-left:100%}}
.big{font-size:30px;font-weight:700}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px}
.clip{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.clip video{width:100%;aspect-ratio:9/16;background:#000;display:block;object-fit:cover}
.pad{padding:12px 14px}.top{display:flex;justify-content:space-between;gap:10px}
.score{min-width:50px;height:50px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:17px;border:3px solid}
.chip{display:inline-block;padding:3px 9px;border-radius:99px;font-size:12px;font-weight:600;margin:6px 0}
.y{background:#10341f;color:#7ff0a8}.n{background:#2a2a30;color:#aab}
.t{color:var(--mut);font-size:12.5px;max-height:4.4em;overflow:hidden}
details{margin-top:8px}summary{cursor:pointer;color:#b6a8ff;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:6px}
th,td{border-bottom:1px solid var(--line);padding:3px 4px;text-align:left}th{color:var(--mut);font-weight:500}
.vi{color:#8b93a3;font-size:10.5px;line-height:1.25;font-weight:400}
.pos{color:#7ff0a8}.neg{color:#ff9a9a}
.cb{height:6px;background:var(--line);position:relative}.cb i{position:absolute;top:0;height:100%}
.mini{display:grid;grid-template-columns:42px 1fr 24px;gap:6px;font-size:11.5px;color:var(--mut);align-items:center;margin-top:3px}
.mini div{height:6px;background:var(--line);border-radius:3px;overflow:hidden}.mini div i{display:block;height:100%;background:var(--acc)}
.verdict{margin-top:10px;padding:10px 12px;border-radius:10px;background:#0f2a1a;border:1px solid #1f6b3a;color:#b9f3cd}
.warn{background:#2a220f;border-color:#6b5a1f;color:#f3e2b9}
.flag{display:inline-block;min-width:24px;text-align:center;border-radius:6px;padding:0 6px;font-weight:700}.f1{background:#1f6b3a;color:#fff}.f0{background:#2a2e3b;color:#8b93a3}
#hero{max-width:760px;margin:26px auto 10px;text-align:center}
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
</style></head><body>
<header><div class="logo"></div><b>Generador de clips 9:16</b><span>· puntaje de retención 0–99 · solo audio y texto</span></header>
<div class="wrap">
 <section id="hero">
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
   <div class="sub" style="text-align:center;margin-top:10px">Si el link de YouTube falla (a veces YouTube bloquea la descarga), sube el archivo del video.</div>
   <div class="bar" id="upbar" style="display:none"><i></i></div><div id="upmsg" class="sub" style="margin-top:8px;text-align:center"></div>
  </div>
  <div class="feats"><div><b>1 · Detecta</b><span>Transcribe y puntúa cada pasaje con 71 variables de audio y texto.</span></div>
   <div><b>2 · Elige</b><span>Los 5 momentos con mayor puntaje; dos clips no comparten más de 30 % de su duración.</span></div>
   <div><b>3 · Explica</b><span>Cada clip trae su puntaje 0–99 y las variables que lo explican.</span></div></div>
  <details class="card" style="margin-top:14px"><summary><b>Ver cómo un video recibe su puntaje (flujo completo, con un ejemplo real)</b></summary>
   <img src="/static/flujo_scoring.png" alt="Flujo del puntaje" style="width:100%;margin-top:10px;border-radius:8px;background:#fff">
   <div class="sub" style="margin-top:6px">Variables → percentil dentro del video → bandera 0/1 → suma de pesos × bandera (raw) → escala de 0 a 99 entre el mínimo y el máximo posibles → orden y selección de 5 clips.</div></details>
 </section>
 <div id="newrow" style="display:none"><button id="newbtn" class="ghost">← Nuevo video</button></div>
 <div id="tabs" class="ex"></div>
 <div id="prog" class="panel" style="display:none"><b id="pst">Procesando…</b> <span class="sub" id="psec"></span><div class="bar"><i></i></div>
  <div id="steps" style="margin-top:10px;line-height:1.7"></div><pre id="plog"></pre></div>
 <div id="out"></div>
</div>
<script>
const $=id=>document.getElementById(id);
const fmt=s=>{s=Math.round(s);const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;return (h?h+":":"")+String(m).padStart(h?2:1,"0")+":"+String(x).padStart(2,"0")};
const col=s=>s>=85?"#22c55e":s>=60?"#eab308":"#9ca3af";
const vid=u=>{const m=u.match(/(?:v=|youtu\.be\/|shorts\/|live\/)([\w-]{11})/);return m?m[1]:null};
let poll=null;
const STEPS=["Descargar video","Transcribir (Whisper local)","Segmentar en candidatos","Calcular variables","Puntuar con la fórmula","Recortar 9:16 + subtítulos","Listo"];
const DONE=[];   // resultados de esta sesión: [{vid,dir,label}]
function tabs(active){
  const t=$("tabs");t.innerHTML="";
  if(!DONE.length)return;
  t.insertAdjacentHTML("beforeend",'<span class="sub">Resultados de esta sesión:</span>');
  DONE.forEach(d=>{const b=document.createElement("button");b.className="ghost";
    b.style.cssText=d.dir===active?"border-color:#7c5cff;color:#fff":"";b.textContent="✓ "+d.label;
    b.onclick=()=>{show({dir:d.dir});};t.appendChild(b);});
}
function steps(stage,rendered,fail){
  return STEPS.map((n,i)=>{const k=i+1;const st=stage>=k&&k<7?"✓":(stage+1===k?"…":"·");
    const ex=(k===6&&stage>=5&&stage<7)?` (${rendered}/5)`:"";
    const c=stage>=k?"#7ff0a8":(stage+1===k?"#fff":"#8b93a3");
    return `<div style="color:${c}">${stage>=k||k===7&&stage>=7?"✓":(stage+1===k?(fail?"✗":"⟳"):"○")} ${n}${ex}</div>`;}).join("");
}
async function start(local){
  const url=local||$("url").value.trim(); $("out").innerHTML="";
  const r=await fetch(local?"/api/run_local":"/api/run",{method:"POST",body:JSON.stringify(local?{name:local}:{url})}); const j=await r.json();
  if(j.error){alert(j.error);return}
  $("go").disabled=true;$("hero").style.display="none";$("newrow").style.display="block";
  $("prog").style.display="block";document.querySelector("#prog .bar").style.display="";$("pst").textContent=local?"Generando clips de tu video: "+local:"Simulación en curso: "+url;
  $("steps").innerHTML=steps(0,0);
  clearInterval(poll);
  poll=setInterval(async()=>{
    const s=await (await fetch("/api/status?job="+j.job)).json();
    $("plog").textContent=s.log.join(String.fromCharCode(10));$("plog").scrollTop=1e9;$("psec").textContent=Math.floor(s.secs/60)+" min "+(s.secs%60)+" s";
    $("steps").innerHTML=steps(s.stage,s.rendered);
    if(s.done){clearInterval(poll);$("go").disabled=false;
      if(s.code===0&&s.dir){$("pst").textContent="Listo";
        if(!DONE.find(d=>d.dir===s.dir))DONE.push({vid:s.vid,dir:s.dir,label:"video "+s.vid});
        $("steps").innerHTML=steps(7,5);show({dir:s.dir});}
      else{const bloq=/not a bot|Sign in to confirm/i.test(s.log.join(" "));
        $("pst").textContent=bloq?"YouTube bloqueó la descarga desde este equipo. Sube el video como archivo: ese camino no depende de YouTube.":"Falló: revisa el registro.";
        $("steps").innerHTML=steps(s.stage,s.rendered,true);document.querySelector("#prog .bar").style.display="none";}
    }},2000);
}
async function show(q){
  const qs=q.dir?"dir="+encodeURIComponent(q.dir):"vid="+q.vid;
  const r=await fetch("/api/result?"+qs); if(!r.ok){$("out").innerHTML='<div class="panel">Sin resultado.</div>';return}
  const R=await r.json();$("prog").style.display="none";tabs(R.dir);render(R);valPanel(R);
}
function chart(R){
  const cv=document.createElement("canvas");cv.style.width="100%";cv.height=210;
  setTimeout(()=>{
    const dpr=devicePixelRatio||1,W=cv.clientWidth,H=210;cv.width=W*dpr;cv.height=H*dpr;const x=cv.getContext("2d");x.scale(dpr,dpr);
    const D=R.duration,px=t=>42+(W-54)*t/D,py=v=>H-26-(H-48)*v;
    x.font="11px Segoe UI";x.fillStyle="#8b93a3";x.strokeStyle="#262b36";
    [0,.5,1].forEach(v=>{x.beginPath();x.moveTo(42,py(v));x.lineTo(W-10,py(v));x.setLineDash(v==.5?[3,3]:[]);x.stroke();x.fillText(v.toFixed(1),10,py(v)+4)});x.setLineDash([]);
    for(let m=0;m<=D/60;m+=10)x.fillText(m+" min",px(m*60)-14,H-8);
    if(R.heat){
      R.hot.forEach(h=>{x.fillStyle="rgba(239,68,68,.22)";x.fillRect(px(h.a),8,Math.max(px(h.b)-px(h.a),3),H-34)});
      x.beginPath();R.heat.forEach((p,i)=>i?x.lineTo(px(p.t),py(p.v)):x.moveTo(px(p.t),py(p.v)));
      x.lineTo(px(R.heat[R.heat.length-1].t),py(0));x.lineTo(px(R.heat[0].t),py(0));x.closePath();x.fillStyle="rgba(180,185,196,.33)";x.fill();
      x.beginPath();R.heat.forEach((p,i)=>i?x.lineTo(px(p.t),py(p.v)):x.moveTo(px(p.t),py(p.v)));x.strokeStyle="#9aa1ae";x.lineWidth=1.3;x.stroke();
    }
    (R.chapters||[]).forEach(ch=>{x.strokeStyle="rgba(255,255,255,.35)";x.setLineDash([3,3]);x.beginPath();x.moveTo(px(ch.start),6);x.lineTo(px(ch.start),H-24);x.stroke();x.setLineDash([]);
      x.fillStyle="rgba(255,255,255,.75)";x.font="10px Segoe UI";x.fillText(ch.title.length>16?ch.title.slice(0,15)+"…":ch.title,px(ch.start)+3,H-28)});
    R.clips.forEach(c=>{x.fillStyle=c.touch===false?"rgba(124,92,255,.55)":"rgba(34,197,94,.55)";
      const w=Math.max(px(c.end)-px(c.start),4);x.fillRect(px(c.start),8,w,H-34);
      x.fillStyle="#fff";x.font="bold 11px Segoe UI";x.fillText("#"+c.rank,px(c.start)+2,20)});
  },0);
  return cv;
}
function render(R){
  const o=$("out");o.innerHTML="";
  const hasHeat=R.heat!=null;
  let v=`<div class="panel"><div class="row" style="justify-content:space-between"><div><div class="big">${R.clips.length} clips</div>
  <div class="sub">${fmt(R.duration)} · idioma ${R.language} · método: ${R.model} · tardó ${R.elapsed?Math.round(R.elapsed/60*10)/10+" min":"—"} · ${R.local?"video propio (carpeta CLIPS_GENERADOS)":`<a style="color:#b6a8ff" href="https://youtu.be/${R.vid}" target="_blank">youtu.be/${R.vid}</a>`}</div></div>`;
  if(hasHeat) v+=`<div style="text-align:right"><div class="big" style="color:${R.hits>=3?"#22c55e":"#eab308"}">${R.hits}/${R.clips.length}</div><div class="sub">clips que caen sobre un pico real</div></div>`;
  v+=`</div></div>`;
  o.insertAdjacentHTML("beforeend",v);
  const p=document.createElement("div");p.className="panel";
  p.innerHTML=`<b>Mapa de calor real de YouTube vs. clips elegidos</b><div class="sub">${hasHeat?"Gris = calor real (Most Replayed). Rojo = picos de retención (&gt; 0.5). Verde = clip que cae en un pico; morado = clip fuera de pico.":"No hay mapa de calor disponible para este video (YouTube no lo publica o está bloqueado): solo se muestran los clips."}</div>`;
  p.appendChild(chart(R));
  if(hasHeat){const d=document.createElement("div");d.className="verdict";
    d.innerHTML=`<b>Validación:</b> el sistema eligió los clips <i>sin ver</i> esta curva, solo con audio y texto. Después se compara: <b>${R.hits} de ${R.clips.length}</b> caen sobre un pico real (el azar acierta ~1.5 de 5). El pico más alto está en <b>${fmt(R.peak.a)}–${fmt(R.peak.b)}</b>.`;p.appendChild(d);}
  o.appendChild(p);
  const g=document.createElement("div");g.className="grid";
  const mkCard=(c)=>{
    const e=document.createElement("div");e.className="clip";
    const ex=c.explain;
    let tb="";
    if(ex){
      const mx=Math.max(...ex.vars.map(r=>Math.abs(r.contrib)),1e-6);
      tb=`<details><summary><b>¿Por qué se eligió? Score global: 17 variables · puesto ${ex.rank} de ${ex.n_candidates} ventanas</b></summary>
      <div class="sub" style="margin-top:6px">${ex.binario?"raw = suma de (peso × bandera 0/1 de cada variable): cada variable vale 1 solo si está en el 25 % más alto de su video.":"raw = suma de (peso × puntaje/99 de cada variable)."} Verde suma al score, rojo resta.</div>
      <div class="sub" style="margin-top:4px"><b>Banderas 0/1</b> (1 = la variable está en el 25 % más alto de este video): <b>${ex.vars.filter(r=>r.pct>=0.75).length} de ${ex.vars.length}</b> en 1 → ${ex.vars.filter(r=>r.pct>=0.75).map(r=>r.var).join(", ")||"ninguna"}. ${ex.binario?"El puntaje usa solo estas banderas (un empate se desempata con el percentil completo).":"El puntaje usa el percentil completo; la bandera solo ayuda a leerlo."}</div>
      ${flujoRaw(ex)}
      <table><tr><th>variable (orden del código)</th><th>valor</th><th>puntaje 0–99</th><th title="1 = está en el 25 % más alto de su video">0/1</th><th>peso</th><th>aporte al score</th></tr>`+
      byCode(ex.vars).map(r=>`<tr><td><b>${r.var}</b>${vinfo(r.var)}</td><td>${r.value==null?"—":(+r.value).toPrecision(3)}</td><td>${Math.round(r.pct*99)}</td><td><span class="flag ${r.pct>=0.75?"f1":"f0"}">${r.pct>=0.75?1:0}</span></td><td>${r.weight>0?"+":""}${r.weight.toFixed(4)}</td>
      <td class="${r.contrib>=0?"pos":"neg"}">${r.contrib>=0?"+":""}${r.contrib.toFixed(4)}</td></tr>`).join("")+`</table></details>`;
    }
    let dv="";
    if(c.dim_vars){
      const nm={hook:"Hook · gancho",flow:"Flow · fluidez",value:"Value · contenido, audio, emoción"};
      const sg=["hook","flow","value"].map(d=>{
        const rows=c.dim_vars[d]||[];const tot=rows.reduce((a,r)=>a+r.shap,0);const ab=rows.reduce((a,r)=>a+Math.abs(r.shap),0)||1;
        const tr=(r)=>`<tr><td><b>${r.var}</b>${vinfo(r.var)}</td><td>${r.value==null?"—":(+r.value).toPrecision(3)}</td><td>${Math.round((r.pct??0.5)*99)}</td><td><span class="flag ${(r.pct??0.5)>=0.75?"f1":"f0"}">${(r.pct??0.5)>=0.75?1:0}</span></td>
          <td class="${r.shap>=0?"pos":"neg"}">${r.shap>=0?"+":""}${r.shap.toFixed(3)}</td><td>${Math.round(Math.abs(r.shap)/ab*100)}%</td></tr>`;
        return `<div style="margin-top:10px"><b>${nm[d]}</b> · puntaje de la dimensión <b>${c[d]}</b>/99 · suma de aportes ${tot>=0?"+":""}${tot.toFixed(2)}
        <div style="max-height:360px;overflow:auto"><table><tr><th>variable (en el orden del código)</th><th>valor</th><th>puntaje 0–99</th><th>0/1</th><th>aporte a ${d.toUpperCase()}</th><th>peso en ${d}</th></tr>`+
        byCode(rows).map(tr).join("")+`</table></div></div>`;}).join("");
      dv=`<details open><summary><b>Desglose por variable: cuánto sacó cada una y cuánto aportó a Hook, Flow y Value</b></summary>
      <div class="sub" style="margin-top:6px"><b>puntaje 0–99</b> = qué tan alta es esta variable en este clip frente a las demás ventanas del mismo video.
      <b>aporte</b> = cuánto sumó o restó a la dimensión (verde suma, rojo resta). Cómo se calcula cada variable: ver el <a href="#glosario" style="color:#b6a8ff">glosario al final de la página</a>.
      <b>Ojo:</b> estas tres dimensiones explican el clip; la selección y el score global salen de la fórmula de 17 variables (tabla de abajo).</div>${sg}</details>`;
    }
    e.innerHTML=(c.file?`<video src="/media?d=${encodeURIComponent(R.dir)}&f=${encodeURIComponent(c.file)}" controls preload="metadata"></video>`:`<div class="pad mut">sin mp4</div>`)+
    `<div class="pad"><div class="top"><div><div class="sub">${c.rank?`Clip #${c.rank}`:"Clip del capítulo"} · ${fmt(c.start)}–${fmt(c.end)} · ${Math.round(c.end-c.start)} s${c.chapter?` · <b style="color:#b6a8ff">capítulo: ${c.chapter}</b>`:""}</div>
    <b>${c.title||""}</b></div><div class="score" style="color:${col(c.score)};border-color:${col(c.score)}">${c.score}</div></div>
    ${c.touch===null?"":`<span class="chip ${c.touch?"y":"n"}">${c.touch?"✓ cae en un pico de YouTube":"fuera del pico"} · calor ${c.heat==null?"—":c.heat.toFixed(2)}</span>`}
    <div class="t">“${(c.hookText||c.text).slice(0,200)}”</div>
    <div class="mini">Hook<div><i style="width:${c.hook}%"></i></div>${c.hook}</div>
    <div class="mini">Flow<div><i style="width:${c.flow}%"></i></div>${c.flow}</div>
    <div class="mini">Value<div><i style="width:${c.value}%"></i></div>${c.value}</div>
    ${tb}${dv}<details><summary>Texto completo y palabras clave</summary><div class="t" style="max-height:none">${c.text}</div>
    <div class="sub">Palabras clave: ${c.keywords.join(", ")}</div></details></div>`;
    return e;};
  R.clips.forEach(c=>g.appendChild(mkCard(c)));
  o.appendChild(g);
  if(R.chapters&&R.chapters.length){
    const pc=document.createElement("div");pc.className="panel";
    pc.innerHTML=`<b>Mejor clip de cada capítulo</b><div class="sub">${R.chapters.some(x=>!x.auto)?"El video se divide en los capítulos que YouTube muestra sobre la barra de reproducción; en cada uno se elige el clip con mayor puntaje.":"Este video no trae capítulos: se divide en bloques de duración fija y en cada bloque se elige el clip con mayor puntaje."} El top 5 general de arriba se elige sobre todo el video.</div>`;
    o.appendChild(pc);
    R.chapters.forEach(ch=>{
      const h=document.createElement("div");h.className="sub";h.style.margin="14px 4px 6px";
      h.innerHTML=`<b>${ch.title}${ch.auto?" (bloque automático)":""}</b> · ${fmt(ch.start)}–${fmt(ch.end)}`+(ch.clips.length?"":" · sin clip elegible");
      o.appendChild(h);
      if(ch.clips.length){const gc=document.createElement("div");gc.className="grid";ch.clips.forEach(c=>gc.appendChild(mkCard(c)));o.appendChild(gc);}
    });
  }
  glosario(o);
}

function flujoRaw(ex){
  // del raw (suma de aportes) al puntaje 0-99: mínimo y máximo posibles salen de los pesos de la fórmula
  const f=x=>(x>=0?"+":"")+x.toFixed(4);
  const neg=ex.vars.filter(r=>r.weight<0),pos=ex.vars.filter(r=>r.weight>0);
  const lo=neg.reduce((a,r)=>a+r.weight,0),hi=pos.reduce((a,r)=>a+r.weight,0);
  const raw=ex.vars.reduce((a,r)=>a+r.contrib,0),rng=hi-lo,fr=Math.min(1,Math.max(0,(raw-lo)/rng)),sc=Math.round(fr*99);
  const box=(t,b)=>`<div style="flex:1 1 150px;border:1px solid #d489a2;border-radius:8px;padding:6px 8px;background:rgba(212,137,162,.08)"><b style="color:#d489a2">${t}</b><div class="sub">${b}</div></div>`;
  return `<div style="margin-top:8px"><b>Del raw al puntaje 0–99</b>
  <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">
  ${box("1 · Entrada","raw = suma de aportes = <b>"+f(raw)+"</b>")}
  ${box("2 · Mínimo posible","suma de los "+neg.length+" pesos negativos = <b>"+f(lo)+"</b> (peor clip: solo ellos en 1; vale 0)")}
  ${box("3 · Máximo posible","suma de los "+pos.length+" pesos positivos = <b>"+f(hi)+"</b> (mejor clip: solo ellos en 1; vale 99)")}
  ${box("4 · Posición","(raw − mín) / (máx − mín) = ("+raw.toFixed(4)+" + "+(-lo).toFixed(4)+") / "+rng.toFixed(4)+" = <b>"+fr.toFixed(4)+"</b>")}
  ${box("5 · Puntaje","× 99 = "+(fr*99).toFixed(1)+" → <b>"+sc+"</b>")}</div>
  <div style="position:relative;height:10px;border-radius:5px;background:#3a3f4d;margin-top:8px"><i style="position:absolute;left:0;top:0;height:10px;border-radius:5px;background:#d489a2;width:${(fr*100).toFixed(1)}%"></i></div>
  <div class="sub" style="display:flex;justify-content:space-between"><span>mín = 0</span><span>máx = 99</span></div></div>`;
}
let GLO=null;
const vinfo=k=>{const g=GLO&&GLO.vars[k];return g?`<div class="vi">${g.info}${g.loc?` · <code>${g.loc[0].split("/").pop()}:${g.loc[1]}</code>`:""}</div>`:""};
const ordIdx=k=>{const i=GLO&&GLO.order?GLO.order.indexOf(k):-1;return i<0?9999:i};
const byCode=rows=>rows.slice().sort((a,b)=>ordIdx(a.var)-ordIdx(b.var));
fetch("/api/glossary").then(r=>r.json()).then(g=>{GLO=g;});
async function glosario(o){
  if(!GLO)GLO=await (await fetch("/api/glossary")).json();
  const d=document.createElement("div");d.className="panel";d.id="glosario";
  const grp={};(GLO.order||Object.keys(GLO.vars)).forEach(k=>{const v=GLO.vars[k];if(v)(grp[v.group]=grp[v.group]||[]).push([k,v])});
  d.innerHTML=`<h3 style="margin:0 0 6px">Glosario: cómo se calcula cada fórmula y cada variable</h3>
  <div class="sub">Primero las fórmulas del sistema; después, las variables por grupo con su fórmula y qué significan.</div>
  <table style="margin-top:8px"><tr><th>fórmula</th><th>cómo se calcula</th><th>explicación</th></tr>`+
  GLO.formulas.map(f=>`<tr><td><b>${f.name}</b></td><td><code>${f.formula}</code></td><td>${f.info}</td></tr>`).join("")+`</table>`+
  Object.entries(grp).map(([g,arr])=>`<details style="margin-top:8px"><summary><b>${g}</b> · ${arr.length} variables</summary><table><tr><th>variable</th><th>fórmula</th><th>qué significa</th><th>en el código</th></tr>`+
    arr.map(([k,v])=>`<tr><td>${k}</td><td><code>${v.formula}</code></td><td>${v.info}</td><td>${v.loc?"<code>"+v.loc[0].split("/").pop()+":"+v.loc[1]+"</code>":""}</td></tr>`).join("")+`</table></details>`).join("");
  o.appendChild(d);
}
let FILE=null;
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
const ITEMS=["Los cinco clips elegidos me parecen momentos interesantes del episodio.", "Publicaría estos clips en mis redes con poca o ninguna edición.", "La explicación del puntaje (banderas 0/1 por variable) es fácil de entender.", "El puntaje de 0 a 99 me ayuda a decidir qué clip publicar primero.", "La página web es fácil de usar.", "Este sistema me ahorraría tiempo frente a elegir los clips manualmente."];
const SUS=["Creo que me gustaría usar este sistema con frecuencia.","Encontré el sistema innecesariamente complejo.","Pensé que el sistema era fácil de usar.","Creo que necesitaría el apoyo de un técnico para poder usar este sistema.","Encontré que las diversas funciones del sistema estaban bien integradas.","Pensé que había demasiada inconsistencia en este sistema.","Imagino que la mayoría de las personas aprendería a usar este sistema muy rápidamente.","Encontré el sistema muy incómodo de usar.","Me sentí muy seguro/a usando el sistema.","Necesité aprender muchas cosas antes de poder usar el sistema."];
function radios(n){return [1,2,3,4,5].map(k=>`<label style="margin-right:10px"><input type="radio" name="${n}" value="${k}"> ${k}</label>`).join("")}
function valPanel(R){
  const d=document.createElement("div");d.className="panel";d.id="valpanel";
  d.innerHTML=`<h3 style="margin:0 0 6px">Validación con usuarios (formato de 5 participantes)</h3>
  <div class="sub">Responde después de ver los 5 clips. 1 = totalmente en desacuerdo, 5 = totalmente de acuerdo. Es anónimo; el consentimiento firmado se entrega aparte, en papel.</div>
  <div class="row" style="margin-top:8px"><select id="vpart">${[1,2,3,4,5].map(n=>`<option value="P${n}">Participante ${n}</option>`).join("")}</select>
  <label><input type="checkbox" id="vcons"> Doy mi consentimiento informado para participar</label></div>
  <table style="margin-top:8px"><tr><th>Clip</th><th>¿Qué tan buen momento es? (1–5)</th></tr>${R.clips.map(c=>`<tr><td>#${c.rank} · ${c.title||""}</td><td>${radios("clip"+c.rank)}</td></tr>`).join("")}</table>
  <table style="margin-top:8px"><tr><th>Afirmación</th><th>1–5</th></tr>${ITEMS.map((t,i)=>`<tr><td>${i+1}. ${t}</td><td>${radios("item"+i)}</td></tr>`).join("")}</table>
  <div class="row" style="margin-top:8px"><input id="vanios" type="number" min="0" max="60" placeholder="Años creando contenido" style="width:210px"><input id="vplat" type="text" placeholder="Plataformas que usa (YouTube, TikTok…)" style="min-width:260px"><input id="vman" type="number" min="0" max="1000" placeholder="Min. que tarda hoy en elegir 5 clips a mano" style="width:300px"></div>
  <table style="margin-top:8px"><tr><th>Usabilidad (SUS)</th><th>1–5</th></tr>${SUS.map((t,i)=>`<tr><td>${i+1}. ${t}</td><td>${radios("sus"+i)}</td></tr>`).join("")}</table>
  <textarea id="vc1" placeholder="¿Qué clip cambiaría o descartaría, y por qué?" style="width:100%;margin-top:8px"></textarea>
  <textarea id="vc2" placeholder="¿Qué mejoraría de la página o de la explicación del puntaje?" style="width:100%;margin-top:6px"></textarea>
  <div class="row" style="margin-top:8px"><button id="vsend">Enviar respuestas</button><button id="vres" class="ghost">Ver resumen de los participantes</button><a href="/api/validacion/export.xlsx" style="color:#b6a8ff">Descargar Excel</a></div>
  <div id="vmsg" class="sub" style="margin-top:6px"></div><div id="vsum"></div>`;
  $("out").appendChild(d);
  const val=n=>{const e=document.querySelector(`input[name="${n}"]:checked`);return e?+e.value:null};
  $("vsend").onclick=async()=>{
    const items=ITEMS.map((_,i)=>val("item"+i)),clips=R.clips.map(c=>({rank:c.rank,rating:val("clip"+c.rank)}));
    const r=await fetch("/api/validacion/registrar",{method:"POST",body:JSON.stringify({participante:$("vpart").value,consentimiento:$("vcons").checked,dir:R.dir,anios_creando:$("vanios").value,plataformas:$("vplat").value,min_manual:$("vman").value,duracion_episodio_min:Math.round((R.duration||0)/60),items,sus:SUS.map((_,i)=>val("sus"+i)),clips,comentario_1:$("vc1").value,comentario_2:$("vc2").value})});
    const j=await r.json();$("vmsg").textContent=j.mensaje||j.error||"";if(j.ok)resumenVal();};
  $("vres").onclick=resumenVal;
}
async function resumenVal(){
  const S=await (await fetch("/api/validacion/resumen")).json();
  $("vsum").innerHTML=`<div class="sub" style="margin-top:8px"><b>${S.n} de 5 participantes</b> (${S.participantes.join(", ")||"ninguno"}) · mediana de los clips: ${S.clips_mediana??"—"} · SUS: media ${S.sus_media??"—"} (${S.sus_min??"—"}–${S.sus_max??"—"}) · ${S.nota}</div>
  <table><tr><th>Afirmación</th><th>n</th><th>mediana</th><th>mín–máx</th></tr>${S.items.map(i=>`<tr><td>${i.afirmacion}</td><td>${i.n}</td><td>${i.mediana??"—"}</td><td>${i.min??"—"}–${i.max??"—"}</td></tr>`).join("")}</table>`;
}
</script></body></html>"""

if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), H)
    print(f"Listo: http://localhost:{PORT}  (Ctrl+C para cerrar)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
