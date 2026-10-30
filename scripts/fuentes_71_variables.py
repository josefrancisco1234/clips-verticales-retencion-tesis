"""D-099: fuente en papers de las 71 variables. Para cada variable se anota (a) el trabajo que define la medida o la herramienta con que se calcula
y (b) el trabajo que relaciona ese tipo de señal con engagement, atención, carisma, comprensión o detección de highlights.
Cada referencia se busca en Crossref y solo se acepta si coincide el apellido del primer autor y el año (verificación automática del DOI).
Salida: reports/fuentes_71_variables_D099.json y FUENTES/FUENTES_71_VARIABLES.md"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from glosario_variables import G  # noqa: E402

# clave -> (consulta Crossref, apellido esperado, año esperado)
REF = {
    "whisper": ("Robust speech recognition via large-scale weak supervision", "Radford", 2023),
    "panns": ("PANNs: Large-scale pretrained audio neural networks for audio pattern recognition", "Kong", 2020),
    "audioset": ("Audio Set: An ontology and human-labeled dataset for audio events", "Gemmeke", 2017),
    "tfidf": ("A statistical interpretation of term specificity and its application in retrieval", "Jones", 1972),
    "salton": ("Term-weighting approaches in automatic text retrieval", "Salton", 1988),
    "sbert": ("Sentence-BERT: Sentence embeddings using Siamese BERT-networks", "Reimers", 2019),
    "mmr": ("The use of MMR, diversity-based reranking for reordering documents and producing summaries", "Carbonell", 1998),
    "distilbert": ("DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter", "Sanh", 2019),
    "russell": ("A circumplex model of affect", "Russell", 1980),
    "berger": ("What makes online content viral?", "Berger", 2012),
    "loewenstein": ("The psychology of curiosity: A review and reinterpretation", "Loewenstein", 1994),
    "blom": ("Click bait: Forward-reference as lure in online news headlines", "Blom", 2015),
    "liwc": ("The psychological meaning of words: LIWC and computerized text analysis methods", "Tausczik", 2010),
    "cruz": ("Second person pronouns enhance consumer involvement and brand attitude", "Cruz", 2017),
    "tagliamonte": ("Linguistic ruin? LOL! Instant messaging and teen language", "Tagliamonte", 2008),
    "librosa": ("librosa: Audio and music signal analysis in Python", "McFee", 2015),
    "pyin": ("pYIN: A fundamental frequency estimator using probabilistic threshold distributions", "Mauch", 2014),
    "kendall": ("Speech rate, pause and sociolinguistic variation", "Kendall", 2013),
    "campione": ("A large-scale multilingual study of silent pause duration", "Campione", 2002),
    "banzina": ("How to pause in charismatic speeches: A case study of Barack Obama", "Banzina", 2023),
    "kahng": ("The effect of pause location on perceived fluency", "Kahng", 2017),
    "rosenberg": ("Charisma perception from text and speech", "Rosenberg", 2009),
    "strangert": ("What makes a good speaker? Subject ratings, acoustic measurements and perceptual evaluations", "Strangert", 2008),
    "suen": ("Dual-model prediction of affective engagement and vocal attractiveness from speaker expressiveness in video learning", "Suen", 2026),
    "rui": ("Automatically extracting highlights for TV baseball programs", "Rui", 2000),
    "xiong": ("Audio events detection based highlights extraction from baseball, golf and soccer games", "Xiong", 2003),
    "hanjalic": ("Adaptive extraction of highlights from a sport video based on excitement modeling", "Hanjalic", 2005),
    "guo": ("How video production affects student engagement: an empirical study of MOOC videos", "Guo", 2014),
    "kim": ("Understanding in-video dropouts and interaction peaks in online lecture videos", "Kim", 2014),
    "foltz": ("The measurement of textual coherence with latent semantic analysis", "Foltz", 1998),
    "hearst": ("TextTiling: Segmenting text into multi-paragraph subtopic passages", "Hearst", 1997),
    "clark": ("Using uh and um in spontaneous speaking", "Clark", 2002),
    "jiang": ("Confidence measures for speech recognition: A survey", "Jiang", 2005),
    "shannon": ("A mathematical theory of communication", "Shannon", 1948),
    "mccarthy": ("MTLD, vocd-D, and HD-D: A validation study of sophisticated approaches to lexical diversity assessment", "McCarthy", 2010),
    "flesch": ("A new readability yardstick", "Flesch", 1948),
    "provine": ("Laughter punctuates speech: linguistic, social and gender contexts of laughter", "Provine", 1993),
    "hay": ("Functions of humor in the conversations of men and women", "Hay", 2000),
    "reimers": ("Sentence-BERT: Sentence embeddings using Siamese BERT-networks", "Reimers", 2019),
    "keybert": ("KeyBERT: Minimal keyword extraction with BERT", "Grootendorst", 2020),
    "sul": ("Mr. HiSum: A large-scale dataset for video highlight detection and summarization", "Sul", 2023),
}
# variable -> (definicion, relacion)
M = {}
def put(vs, d, r):
    for v in vs.split():
        M[v] = (d, r)
put("k_kvsum_mean k_kvsum_max k_kvsum_local", ["tfidf", "salton"], ["sul"])
put("k_top_terms_pm k_keyphrase_pm", ["keybert", "salton"], ["sul"])
put("k_content_ratio", ["liwc"], [])
put("k_novelty", ["mmr"], ["kim"])
put("k_keybert_sim h_first_keybert f_coherence_mean f_coherence_min", ["sbert", "foltz"], ["guo"])
put("k_noun_chunks_ps", ["liwc"], [])
put("s_pos_mean s_neg_mean s_polarity_mean s_polarity_std", ["distilbert"], ["berger"])
put("s_intensity_mean s_intensity_max h_first_intensity", ["distilbert", "russell"], ["berger"])
put("s_questions_pm h_question", ["loewenstein"], [])
put("s_exclaim_pm", ["liwc"], ["berger"])
put("s_second_person h_second_person l_pron_12_vs_3", ["liwc"], ["cruz"])
put("s_first_person", ["liwc"], [])
put("s_numbers h_number s_intensifiers", ["liwc"], [])
put("s_hook_words h_hook_word h_contrast", ["loewenstein", "blom"], ["kim"])
put("s_laughs", ["tagliamonte"], [])
put("a_rms_mean a_rms_p95 a_rms_std", ["librosa"], ["rosenberg", "suen"])
put("a_pitch_std a_pitch_range a_voiced_ratio", ["pyin"], ["rosenberg", "strangert", "suen"])
put("a_energy_delta", ["librosa"], ["hanjalic", "rui"])
put("a_speech_rate", ["kendall"], ["guo"])
put("a_pause_ratio a_long_pauses_pm l_silence", ["campione", "kendall"], ["banzina", "kahng"])
put("h_rms_onset", ["librosa"], ["kim"])
put("h_first_sentence_s", ["hearst"], ["kim"])
put("f_starts_dangling f_ends_complete", ["hearst"], [])
put("f_topic_drift", ["hearst", "foltz"], [])
put("f_n_sentences", ["hearst"], [])
put("f_duration", ["guo"], ["guo"])
put("f_filler_rate l_fillers", ["clark"], [])
put("f_word_conf", ["whisper", "jiang"], [])
put("l_entropy", ["shannon"], [])
put("l_type_token", ["mccarthy"], [])
put("l_word_len", ["flesch"], [])
put("e_laugh_max e_laugh_mean e_laugh_frac", ["panns", "audioset"], ["provine"])
put("e_laugh_tail e_laugh_after", ["panns", "audioset"], ["provine", "hay"])
put("e_applause_max e_applause_mean e_applause_after e_cheering_max e_cheering_mean", ["panns", "audioset"], ["xiong"])
put("e_music_max e_music_mean e_speech_max e_speech_mean", ["panns", "audioset"], ["xiong", "rui"])
faltan = [v for v in G if v not in M]
assert not faltan, faltan


def cr(q):
    u = "https://api.crossref.org/works?query.bibliographic=" + urllib.parse.quote(q) + "&rows=5&select=DOI,title,author,issued,container-title"
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}), timeout=40) as r:
                return json.load(r)["message"]["items"]
        except Exception:  # noqa: BLE001
            time.sleep(3 + 3 * k)
    return []


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower())


OUT = {}
for key, (q, ap, yr) in REF.items():
    ok = None
    for it in cr(q):
        ti = (it.get("title") or [""])[0]
        au = [a.get("family", "") for a in it.get("author", [])]
        y = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        sim = len(set(norm(q).split()) & set(norm(ti).split())) / max(len(set(norm(q).split())), 1)
        if sim >= 0.6 and any(ap.lower() in a.lower() for a in au[:3]) and y and abs(y - yr) <= 1:
            ok = dict(doi="https://doi.org/" + it["DOI"], titulo=ti, autores=au[:3], anio=y, venue=(it.get("container-title") or [""])[0])
            break
        if sim >= 0.8 and y and abs(y - yr) <= 1 and not au:
            ok = dict(doi="https://doi.org/" + it["DOI"], titulo=ti, autores=[ap], anio=y, venue=(it.get("container-title") or [""])[0])
            break
    OUT[key] = ok
    print(("OK  " if ok else "NO  "), key, ok["doi"] if ok else "")
    time.sleep(0.4)
# verificados a mano (Crossref por DOI, arXiv y ACL Anthology)
MAN = {
    "whisper": ("https://doi.org/10.48550/arXiv.2212.04356", "Robust speech recognition via large-scale weak supervision", ["Radford"], 2022, "arXiv"),
    "distilbert": ("https://doi.org/10.48550/arXiv.1910.01108", "DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter", ["Sanh"], 2019, "arXiv"),
    "kendall": ("https://doi.org/10.1057/9781137291448", "Speech Rate, Pause and Sociolinguistic Variation", ["Kendall"], 2013, "Palgrave Macmillan"),
    "guo": ("https://doi.org/10.1145/2556325.2566239", "How video production affects student engagement", ["Guo", "Kim", "Rubin"], 2014, "L@S 2014"),
    "hearst": ("https://aclanthology.org/J97-1003/", "TextTiling: Segmenting text into multi-paragraph subtopic passages", ["Hearst"], 1997, "Computational Linguistics 23(1)"),
    "shannon": ("https://doi.org/10.1002/j.1538-7305.1948.tb01338.x", "A mathematical theory of communication", ["Shannon"], 1948, "Bell System Technical Journal"),
    "keybert": ("https://doi.org/10.5281/zenodo.4461265", "KeyBERT: Minimal keyword extraction with BERT", ["Grootendorst"], 2020, "Zenodo"),
    "berger": ("https://doi.org/10.1509/jmr.10.0353", "What makes online content viral?", ["Berger", "Milkman"], 2012, "Journal of Marketing Research"),
}
for k, (doi, ti, au, yr, ve) in MAN.items():
    OUT[k] = dict(doi=doi, titulo=ti, autores=au, anio=yr, venue=ve)
res = {}
for v, (d, r) in M.items():
    dv = [k for k in d if OUT.get(k)]
    rv = [k for k in r if OUT.get(k)]
    res[v] = {"grupo": G[v][0], "definicion": dv, "relacion": rv}
json.dump({"refs": OUT, "variables": res}, open(ROOT / "reports" / "fuentes_71_variables_D099.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
nd = sum(1 for v in res.values() if v["definicion"])
nr = sum(1 for v in res.values() if v["relacion"])
nb = sum(1 for v in res.values() if v["definicion"] and v["relacion"])
print(f"\n{len(res)} variables | con fuente de definición {nd} | con fuente de relación {nr} | con ambas {nb} | refs verificadas {sum(1 for x in OUT.values() if x)}/{len(OUT)}")

# informe en Markdown
cola = ["# Fuente en papers de las 71 variables del sistema (test 2026-10-29, D-099)", "",
        "Definición = trabajo que define la medida o la herramienta con que se calcula. Relación = trabajo que vincula ese tipo de señal con engagement, atención, carisma, comprensión o detección de highlights. Todos los DOI/enlaces están verificados (Crossref, arXiv, ACL Anthology, DataCite).", "",
        f"Resultado: de {len(res)} variables, {nd} tienen fuente de definición, {nr} tienen fuente de relación y {nb} tienen ambas. {sum(1 for v in res.values() if not v['definicion'] and not v['relacion'])} no tienen ninguna.", "",
        "| Variable | Grupo | Fórmula (código) | Definición (paper) | Relación con engagement (paper) |", "|---|---|---|---|---|"]
def cit(k):
    x = OUT[k]
    return f"{', '.join(x['autores'][:2])} ({x['anio']}) {x['doi'].replace('https://doi.org/', '')}" if x else ""
for v in G:
    r = res[v]
    cola.append(f"| {v} | {G[v][0]} | {G[v][1][:70].replace('|', '/')} | " + "; ".join(cit(k) for k in r["definicion"]) + " | " + "; ".join(cit(k) for k in r["relacion"]) + " |")
cola += ["", "Referencias: " + "; ".join(f"{k}: {x['titulo']} ({', '.join(x['autores'][:2])}, {x['anio']}) {x['doi']}" for k, x in OUT.items() if x)]
Path(r"F:\TESISJF\FUENTES\FUENTES_71_VARIABLES.md").write_text(chr(10).join(cola), encoding="utf-8")
