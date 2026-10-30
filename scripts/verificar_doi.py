"""Consulta Crossref y muestra título, autores, revista, volumen y páginas de cada DOI (verificación de referencias)."""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for doi in sys.argv[1:]:
    req = urllib.request.Request("https://api.crossref.org/works/" + doi, headers={"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"})
    m = json.load(urllib.request.urlopen(req, timeout=30))["message"]
    au = "; ".join(f"{a.get('family')}, {a.get('given')}" for a in m.get("author", []))
    print(doi, "|", m["title"][0], "|", (m.get("container-title") or [""])[0], "| vol", m.get("volume"), "| n", m.get("issue"), "|", m.get("page"), "|",
          m["issued"]["date-parts"][0][0])
    print("   ", au)
