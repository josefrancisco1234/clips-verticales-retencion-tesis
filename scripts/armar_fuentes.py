"""Carpeta FUENTES: verifica cada referencia del artículo en Crossref, busca el PDF de acceso abierto en OpenAlex, lo descarga
(solo lectura) y cruza referencias con citas del texto. Salida: F:/TESISJF/FUENTES/{FUENTES.csv, pdfs/}."""
import csv
import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import docx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DOCX = Path(r"F:\TESISJF\Articulo_Investigacion_CIS2026_v20.docx")
OUT = Path(r"F:\TESISJF\FUENTES")
(OUT / "pdfs").mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}
d = docx.Document(str(DOCX))
ps = [p.text.strip() for p in d.paragraphs if p.text.strip()]
i0 = max(k for k, t in enumerate(ps) if t.startswith("REFERENCIAS"))
refs = ps[i0 + 1:]
cuerpo = "\n".join(ps[:i0]) + "\n" + "\n".join(t.text for tb in d.tables for r in tb.rows for t in r.cells)


def get(url, binary=False, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read() if binary else json.load(r)


rows = []
for k, r in enumerate(refs, 1):
    m = re.match(r"^([^,]+),.*?\((\d{4})([a-z]?)\)\.\s*(.+?)\.\s", r)
    autor, anio, suf = (m.group(1), m.group(2), m.group(3)) if m else (r.split(",")[0], "", "")
    titulo = m.group(4) if m else r[:80]
    if autor == "Sul":
        titulo = "Mr. HiSum: A large-scale dataset for video highlight detection and summarization"
    doi = re.search(r"10\.\d{4,9}/[^\s]+", r)
    doi = doi.group(0).rstrip(".") if doi else ""
    url = re.search(r"https?://\S+", r)
    url = url.group(0).rstrip(".") if url else ""
    citada = bool(re.search(re.escape(autor.split()[-1] if autor else "?") + r".{0,60}" + anio, cuerpo)) if anio else False
    fila = {"n": k, "clave": f"{re.sub(r'[^A-Za-z]', '', autor)}_{anio}{suf}", "cita_APA": r, "autor": autor, "anio": anio + suf, "titulo": titulo, "doi": doi, "url": url,
            "crossref": "", "titulo_crossref": "", "similitud": "", "acceso_abierto": "", "pdf_url": "", "pdf_local": "", "citada_en_texto": "si" if citada else "NO"}
    if doi:
        try:
            c = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
            tc = (c.get("title") or [""])[0]
            sim = difflib.SequenceMatcher(None, titulo.lower()[:80], tc.lower()[:80]).ratio()
            fila.update({"crossref": "verificado" if sim > 0.55 else "DOI existe pero el titulo no coincide", "titulo_crossref": tc, "similitud": round(sim, 2)})
        except Exception as e:  # noqa: BLE001
            fila["crossref"] = f"no verificable ({str(e)[:40]})"
        try:
            w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi) + "?select=open_access,best_oa_location,primary_location")
            loc = w.get("best_oa_location") or {}
            fila["acceso_abierto"] = "si" if w.get("open_access", {}).get("is_oa") else "no"
            fila["pdf_url"] = loc.get("pdf_url") or ""
        except Exception:  # noqa: BLE001
            pass
    elif url and "arxiv" in url:
        fila["crossref"] = "enlace arXiv"
    elif url:
        fila["crossref"] = "enlace web (sin DOI)"
    else:
        fila["crossref"] = "SIN DOI NI ENLACE"
    if (OUT / "pdfs" / f"{fila['clave']}.pdf").exists():
        fila["pdf_local"] = f"{fila['clave']}.pdf"
        fila["pdf_url"] = ""
    if fila["pdf_url"]:
        dest = OUT / "pdfs" / f"{fila['clave']}.pdf"
        try:
            b = get(fila["pdf_url"], True, 90)
            if b[:5] == b"%PDF-" and len(b) < 80_000_000:
                dest.write_bytes(b)
                fila["pdf_local"] = dest.name
        except Exception as e:  # noqa: BLE001
            fila["pdf_local"] = f"fallo ({str(e)[:40]})"
    rows.append(fila)
    print(k, fila["clave"], fila["crossref"], fila["acceso_abierto"], fila["pdf_local"], flush=True)
    time.sleep(0.3)
with open(OUT / "FUENTES.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print("\nreferencias:", len(rows), "| con PDF:", sum(1 for r in rows if r["pdf_local"].endswith(".pdf")), "| no citadas en texto:", [r["clave"] for r in rows if r["citada_en_texto"] == "NO"])
