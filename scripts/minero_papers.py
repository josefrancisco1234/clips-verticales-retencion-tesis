"""Minero de papers (D-093): busca en OpenAlex articulos recientes sobre deteccion de momentos / retencion / engagement con audio y habla,
extrae las SENALES medibles que mencionan, las compara con las 71 variables que ya tiene el sistema y propone variables nuevas.

Es mineria por patrones sobre titulo y resumen (no lectura semantica): sirve para encontrar candidatos, que luego se prueban con el
mismo protocolo (preregistro, validacion por canal). Fuente: OpenAlex (API abierta). Salida: reports/minero_papers/.
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "minero_papers"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}
QUERIES = [
    "podcast highlight detection", "video highlight detection audio speech", "most replayed audience retention prediction",
    "audience engagement prediction from speech prosody", "viral short video clip selection from long video",
    "important moment detection in spoken conversation", "podcast segment importance transcript",
    "laughter and applause detection engagement", "turn-taking speaker change engagement conversation",
    "pause silence disfluency listener attention", "speech emotion arousal engagement highlights",
    "lecture video engagement speech rate pitch", "talk show interview key moment detection",
    "lexical surprise perplexity engagement text", "keyword novelty topic shift segmentation spoken content",
]

# Senales medibles que suelen aparecer en estos trabajos: patron -> (nombre, variable del sistema que ya la cubre o None si es nueva)
SENALES = [
    (r"\bpause|silence|silent", "pausas y silencio", "a_pause_ratio, a_long_pauses_pm, l_silence"),
    (r"\bpitch|\bf0\b|fundamental frequency|prosod|intonation", "tono / prosodia", "a_pitch_std, a_pitch_range"),
    (r"speech rate|speaking rate|speaking speed|tempo|words per minute", "velocidad del habla", "a_speech_rate"),
    (r"\benergy|loudness|volume|\brms\b|intensity", "energia / volumen", "a_rms_mean, a_rms_std"),
    (r"laugh", "risa", "e_laughter (PANNs)"),
    (r"applause|cheer", "aplauso / vitores", "e_applause (PANNs)"),
    (r"\bmusic", "musica de fondo", "e_music_*"),
    (r"emotion|arousal|valence|sentiment|affect", "emocion / sentimiento", "s_* (texto); sin emocion del audio"),
    (r"speaker (change|turn)|turn[- ]taking|diariz|overlap|interrupt", "cambio de hablante / turnos", None),
    (r"disfluen|filler|hesitation|\buh\b|\bum\b|repetition", "muletillas / disfluencias / repeticion", None),
    (r"perplexity|surprisal|surprise|unexpected|novelty|information content|entropy", "sorpresa lexica / perplejidad", "l_entropy, k_novelty (parcial)"),
    (r"question|interrogat", "preguntas", "s_questions_pm, h_*"),
    (r"keyword|topic|semantic similarity|embedding", "tema / palabras clave", "k_*"),
    (r"named entit|proper noun", "entidades nombradas", None),
    (r"first[- ]person|second[- ]person|pronoun", "pronombres", "s_second_person, s_first_person"),
    (r"number|numeral|statistic|quantif", "numeros / cifras", "h_* (parcial)"),
    (r"discourse|coherence|connective|cohesion|transition", "discurso / conectores", "f_* (parcial)"),
    (r"chapter|timestamp|segment boundar", "capitulos / fronteras de segmento", "b_* (D-076, no aporto)"),
    (r"readability|complexity|lexical diversity|type[- ]token", "complejidad / diversidad lexica", "l_* (parcial)"),
    (r"speaker (identity|embedding|role)|host|guest", "rol del hablante (anfitrion / invitado)", None),
    (r"visual|face|facial|scene|gesture", "senal visual", "descartada por alcance (D-083)"),
]


def abstract(inv):
    if not inv:
        return ""
    pos = {}
    for w, idx in inv.items():
        for i in idx:
            pos[i] = w
    return " ".join(pos[i] for i in sorted(pos))


def fetch(q, pages=2):
    res = []
    for pg in range(1, pages + 1):
        u = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q) + "&filter=from_publication_date:2020-01-01,type:article|preprint|proceedings-article"
             "&per-page=50&page=%d&select=id,title,publication_year,doi,abstract_inverted_index,cited_by_count,primary_location" % pg)
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40))
        except Exception as e:  # noqa: BLE001
            print("fallo", q, pg, str(e)[:80])
            continue
        res += r["results"]
        time.sleep(0.4)
    return res


obras = {}
for q in QUERIES:
    for w in fetch(q):
        a = abstract(w.get("abstract_inverted_index"))
        if len(a.split()) < 40 or w["id"] in obras:
            continue
        obras[w["id"]] = {"id": w["id"], "titulo": w["title"], "anio": w["publication_year"], "doi": w.get("doi"), "citas": w.get("cited_by_count", 0),
                          "consulta": q, "resumen": a}
    print(f"{q[:55]:55s} -> acumulados {len(obras)}", flush=True)

with open(OUT / "papers.csv", "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.DictWriter(f, fieldnames=["id", "titulo", "anio", "doi", "citas", "consulta", "resumen"])
    wr.writeheader()
    wr.writerows(obras.values())

cnt, ej = defaultdict(int), defaultdict(list)
for o in obras.values():
    txt = (o["titulo"] + " " + o["resumen"]).lower()
    for pat, nombre, _ in SENALES:
        if re.search(pat, txt):
            cnt[nombre] += 1
            ej[nombre].append((o["citas"], o["titulo"], o["doi"], o["anio"]))
filas = []
for pat, nombre, cubierta in SENALES:
    top = sorted(ej[nombre], key=lambda t: -(t[0] or 0))[:3]
    filas.append({"senal": nombre, "papers_que_la_mencionan": cnt[nombre], "variable_actual": cubierta or "NINGUNA (candidata nueva)",
                  "ejemplos": " | ".join(f"{t[:70]} ({a}, {d})" for c, t, d, a in top)})
filas.sort(key=lambda r: -r["papers_que_la_mencionan"])
with open(OUT / "senales.csv", "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.DictWriter(f, fieldnames=list(filas[0]))
    wr.writeheader()
    wr.writerows(filas)
print(f"\n{len(obras)} papers con resumen | senales mencionadas:")
for r in filas:
    marca = "NUEVA " if r["variable_actual"].startswith("NINGUNA") else "tenemos"
    print(f"  {r['papers_que_la_mencionan']:4d}  {marca}  {r['senal']}")
(OUT / "resumen.json").write_text(json.dumps({"n_papers": len(obras), "fecha": time.strftime("%Y-%m-%d %H:%M"), "consultas": QUERIES}, ensure_ascii=False, indent=1), encoding="utf-8")
