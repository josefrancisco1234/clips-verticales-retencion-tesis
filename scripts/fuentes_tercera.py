import csv, json, ssl, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = Path(r"F:\TESISJF\FUENTES"); UA = {"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}
rows = list(csv.DictReader(open(OUT/"FUENTES.csv", encoding="utf-8-sig")))
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
def get(u, t=90): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t, context=ctx).read()
EXTRA = {"Burges_2010": ["https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/MSR-TR-2010-82.pdf"],
         "Lundberg_2020": ["https://arxiv.org/pdf/1905.04610"], "Um_2025": ["https://arxiv.org/pdf/2501.01082"]}
for r in rows:
    if r["pdf_local"].endswith(".pdf"): continue
    if r["clave"].startswith(("Hern", "OpenAlex", "Opus", "Vizard", "McNemar", "Wilcoxon", "Schuster", "He_", "Jrvelin", "Cho_2024", "Grootendorst")): continue
    cand = list(EXTRA.get(r["clave"], []))
    if r["doi"]:
        try:
            s = json.loads(get("https://api.semanticscholar.org/graph/v1/paper/DOI:" + urllib.parse.quote(r["doi"]) + "?fields=openAccessPdf,externalIds,title", 30))
            if (s.get("openAccessPdf") or {}).get("url"): cand.append(s["openAccessPdf"]["url"])
            ax = (s.get("externalIds") or {}).get("ArXiv")
            if ax: cand.append("https://arxiv.org/pdf/" + ax)
            print(r["clave"], "S2:", s.get("title", "")[:60], "| arXiv:", ax)
        except Exception as e: print(r["clave"], "S2 fallo", str(e)[:40])
        time.sleep(1.5)
    for u in cand:
        try:
            b = get(u)
            if b[:5] == b"%PDF-": (OUT/"pdfs"/f"{r['clave']}.pdf").write_bytes(b); r["pdf_local"] = f"{r['clave']}.pdf"; r["pdf_url"] = u; r["acceso_abierto"] = "si"; break
        except Exception as e: r["pdf_local"] = f"fallo ({str(e)[:30]})"
    print("->", r["clave"], r["pdf_local"], flush=True)
with open(OUT/"FUENTES.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("con PDF:", sum(r["pdf_local"].endswith(".pdf") for r in rows))
