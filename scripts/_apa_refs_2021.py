"""D-099: referencias 2021+ que reemplazan a los 10 artículos anteriores a 2021 de la sección 2.5. Metadatos de Crossref y arXiv (verificados)."""
import json, re, sys
import requests
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
def ini(g): return " ".join(x[0] + "." for x in re.split(r"[\s]+", g.replace("-", " -").replace(".", " ")) if x.strip("-")) if g else ""
def fmt_auth(lst):
    a = [f"{f}, {ini(g)}".strip(", ") for f, g in lst]
    return a[0] if len(a) == 1 else ", ".join(a[:-1]) + ", & " + a[-1]
OUT = {}
for key, doi in {"tseng": "10.1186/s41239-021-00242-5", "zygis": "10.1515/phon-2024-0034", "patel": "10.1044/2023_jslhr-22-00618", "cao": "10.1108/jrim-04-2024-0212", "pei": "10.1609/aaai.v38i9.28880", "parker": "10.1016/j.compedu.2024.105148"}.items():
    r = requests.get("https://api.crossref.org/works/" + doi, timeout=40).json()["message"]
    au = fmt_auth([(a.get("family", ""), a.get("given", "")) for a in r["author"]])
    ct = r["container-title"][0].replace("&amp;", "&")
    vol = r.get("volume", ""); iss = r.get("issue", ""); pg = r.get("page", "")
    tail = f"{ct}, {vol}" + (f"({iss})" if iss else "") + (f", {pg}" if pg else "")
    title = r["title"][0].replace("&amp;", "&")
    OUT[key] = f"{au} ({r['issued']['date-parts'][0][0]}). {title}. {tail}. https://doi.org/{doi}".replace(", None", "")
ns = {"a": "http://www.w3.org/2005/Atom"}
for key, aid in {"reddy": "2106.06605", "suen2": "2605.17463", "sun": "2508.02516", "lei": "2107.09609"}.items():
    e = ET.fromstring(requests.get("http://export.arxiv.org/api/query?id_list=" + aid, timeout=40).text).find("a:entry", ns)
    au = []
    for a in e.findall("a:author", ns):
        n = a.find("a:name", ns).text.split(); au.append((n[-1], " ".join(n[:-1])))
    t = " ".join(e.find("a:title", ns).text.split())
    OUT[key] = f"{fmt_auth(au)} ({e.find('a:published', ns).text[:4]}). {t}. arXiv. https://doi.org/10.48550/arXiv.{aid}"
json.dump(OUT, open(ROOT / "reports" / "refs_apa_2021_D099.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in OUT.items(): print(k, "|", v)
