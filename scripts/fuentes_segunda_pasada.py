import csv, difflib, re, sys, time, urllib.parse, urllib.request, ssl
from pathlib import Path
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"F:\TESISJF\FUENTES"); UA = {"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}
rows = list(csv.DictReader(open(OUT/"FUENTES.csv", encoding="utf-8-sig")))
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
def get(u, t=90):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t, context=ctx).read()
DIRECT = {
 "Ke_2017": "https://papers.nips.cc/paper_files/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf",
 "Lundberg_2017": "https://papers.nips.cc/paper_files/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf",
 "Radford_2023": "https://proceedings.mlr.press/v202/radford23a/radford23a.pdf",
 "Sahoo_2018": "https://proceedings.mlr.press/v80/sahoo18a/sahoo18a.pdf",
 "Burges_2010": "https://www.microsoft.com/en-us/research/uploads/prod/2016/02/MSR-TR-2010-82.pdf",
 "Friedman_2001": "https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-5/Greedy-function-approximation-A-gradient-boosting-machine/10.1214/aos/1013203451.pdf",
 "Javed_2025": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/eng2.70250",
 "Kwak_2025": "https://www.mdpi.com/2079-9292/14/18/3640/pdf",
 "Sul_2023": "https://proceedings.neurips.cc/paper_files/paper/2023/file/7f5a5b58b0e8bda7a55d3cb3ef3cb2bb-Paper-Datasets_and_Benchmarks.pdf",
}
def arxiv(title):
    q = urllib.parse.quote('ti:"' + re.sub(r'[^\w\s]', ' ', title)[:90] + '"')
    x = ET.fromstring(get("http://export.arxiv.org/api/query?max_results=3&search_query=" + q, 30))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in x.findall("a:entry", ns):
        t = " ".join(e.find("a:title", ns).text.split())
        if difflib.SequenceMatcher(None, title.lower()[:70], t.lower()[:70]).ratio() > 0.7:
            return e.find("a:id", ns).text.replace("/abs/", "/pdf/")
    return ""
for r in rows:
    if r["pdf_local"].endswith(".pdf") and (OUT/"pdfs"/r["pdf_local"]).exists(): continue
    if r["clave"].startswith(("Hern", "OpenAlex", "Opus", "Vizard", "McNemar", "Wilcoxon", "Schuster", "He_", "Jrvelin", "Cho_2024", "Grootendorst")): continue
    cand = [DIRECT[r["clave"]]] if r["clave"] in DIRECT else []
    try:
        a = arxiv(r["titulo"]); time.sleep(3)
        if a: cand.append(a)
    except Exception as e: print("arxiv fallo", r["clave"], str(e)[:50])
    for u in cand:
        try:
            b = get(u)
            if b[:5] == b"%PDF-":
                (OUT/"pdfs"/f"{r['clave']}.pdf").write_bytes(b); r["pdf_local"] = f"{r['clave']}.pdf"; r["pdf_url"] = u; r["acceso_abierto"] = "si"; break
        except Exception as e: r["pdf_local"] = f"fallo ({str(e)[:40]})"
    print(r["clave"], r["pdf_local"], flush=True)
with open(OUT/"FUENTES.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("con PDF:", sum(r["pdf_local"].endswith(".pdf") for r in rows), "de", len(rows))
