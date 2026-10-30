"""Arma las referencias APA de las fuentes de las 71 variables (datos de Crossref/DataCite) -> reports/refs_apa_71_D099.json"""
import json, re, sys, urllib.request, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
R = json.loads((ROOT / "reports" / "fuentes_71_variables_D099.json").read_text(encoding="utf-8"))["refs"]
def ini(given):
    return " ".join(p[0] + "." for p in re.split(r"[ \-]+", given.strip()) if p and p[0].isalpha())
out = {}
for k, x in R.items():
    if not x: continue
    doi = x["doi"].replace("https://doi.org/", "")
    if x["doi"].startswith("https://aclanthology") or "arXiv" in doi or "zenodo" in doi or doi == "10.1057/9781137291448":
        continue
    try:
        m = json.load(urllib.request.urlopen(urllib.request.Request("https://api.crossref.org/works/" + doi, headers={"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}), timeout=40))["message"]
    except Exception as e:
        print("ERR", k, e); continue
    au = [f"{a.get('family','')}, {ini(a.get('given',''))}".strip().rstrip(",") for a in m.get("author", [])][:20]
    a = ", ".join(au[:-1]) + (", & " if len(au) > 2 else " & ") + au[-1] if len(au) > 1 else (au[0] if au else "")
    ti = re.sub(r"\s+", " ", m["title"][0]).strip()
    ve = (m.get("container-title") or [""])[0]
    vol, iss, pg = m.get("volume"), m.get("issue"), m.get("page")
    yr = m["issued"]["date-parts"][0][0]
    s = f"{a} ({yr}). {ti}. " + (f"{ve}" if ve else "") + (f", {vol}" if vol else "") + (f"({iss})" if iss else "") + (f", {pg}" if pg else "") + f". https://doi.org/{doi}"
    out[k] = re.sub(r"\.\.", ".", s.replace(" . ", " ")).replace(", .", ".")
    time.sleep(0.3)
MAN = {
 "whisper": "Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2022). Robust speech recognition via large-scale weak supervision. arXiv. https://doi.org/10.48550/arXiv.2212.04356",
 "distilbert": "Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter. arXiv. https://doi.org/10.48550/arXiv.1910.01108",
 "kendall": "Kendall, T. (2013). Speech rate, pause and sociolinguistic variation. Palgrave Macmillan. https://doi.org/10.1057/9781137291448",
 "hearst": "Hearst, M. A. (1997). TextTiling: Segmenting text into multi-paragraph subtopic passages. Computational Linguistics, 23(1), 33-64. https://aclanthology.org/J97-1003/",
 "keybert": "Grootendorst, M. (2020). KeyBERT: Minimal keyword extraction with BERT. Zenodo. https://doi.org/10.5281/zenodo.4461265",
}
out.update(MAN)
json.dump(out, open(ROOT / "reports" / "refs_apa_71_D099.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "referencias")
for k, v in list(out.items())[:8]: print(k, "|", v[:200])
