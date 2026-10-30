"""D-099: fuentes 2021+ de la Tabla 3 (metadatos de Crossref y arXiv). Salida: reports/refs_apa_tabla3_2021_D099.json"""
import json, re, sys
import requests
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
def ini(g):
    out = []
    for w in g.replace(".", " ").split():
        out.append("-".join(x[0] + "." for x in w.split("-") if x).replace(".-", ".-"))
    return " ".join(out)
def fmt(lst):
    a = [f"{f}, {ini(g)}".strip(", ") for f, g in lst]
    return a[0] if len(a) == 1 else (", ".join(a[:-1]) + ", & " + a[-1] if len(a) <= 20 else ", ".join(a[:19]) + ", ... " + a[-1])
CR = {"tfidf24": "10.36548/jitdw.2024.1.008", "atad": "10.1177/14648849231169886", "braun": "10.3390/languages8030155", "lequere": "10.1038/s41598-024-81575-9",
      "gkikas": "10.1016/j.jjimei.2022.100067", "feng": "10.3390/bs13010034", "ringler": "10.1016/j.jbusres.2025.115345", "wangg": "10.1177/00238309241252983", "gu": "10.3389/fpsyg.2024.1267516"}
AX = {"solbiati": "2106.12978", "mueller": "2305.09485", "glazkova": "2209.03791"}
OUT = {}
for k, doi in CR.items():
    r = requests.get("https://api.crossref.org/works/" + doi, timeout=40).json()["message"]
    au = fmt([(a.get("family", ""), a.get("given", "")) for a in r["author"]])
    ct = r["container-title"][0].replace("&amp;", "&")
    vol, iss, pg = r.get("volume", ""), r.get("issue", ""), r.get("page", "") or r.get("article-number", "")
    tail = ct + (f", {vol}" if vol else "") + (f"({iss})" if iss else "") + (f", {pg}" if pg else "")
    OUT[k] = {"apa": f"{au} ({r['issued']['date-parts'][0][0]}). {r['title'][0].replace('&amp;', '&')}. {tail}. https://doi.org/{doi}", "autor": r["author"][0]["family"], "anio": r["issued"]["date-parts"][0][0], "doi": doi}
ns = {"a": "http://www.w3.org/2005/Atom"}
for k, aid in AX.items():
    e = ET.fromstring(requests.get("http://export.arxiv.org/api/query?id_list=" + aid, timeout=40).text).find("a:entry", ns)
    au = []
    for a in e.findall("a:author", ns):
        n = a.find("a:name", ns).text.split(); au.append((n[-1], " ".join(n[:-1])))
    OUT[k] = {"apa": f"{fmt(au)} ({e.find('a:published', ns).text[:4]}). {' '.join(e.find('a:title', ns).text.split())}. arXiv. https://doi.org/10.48550/arXiv.{aid}", "autor": au[0][0], "anio": int(e.find("a:published", ns).text[:4]), "doi": "10.48550/arXiv." + aid}
json.dump(OUT, open(ROOT / "reports" / "refs_apa_tabla3_2021_D099.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in OUT.items(): print(k, "|", v["apa"])
