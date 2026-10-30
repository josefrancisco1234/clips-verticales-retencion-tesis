"""Test de respaldo bibliográfico de cada variable del sistema (D-099).
Para cada una de las 71 variables consulta OpenAlex (API abierta) con búsquedas en inglés, reconstruye los resúmenes y cuenta los trabajos cuyo
resumen menciona el CONCEPTO de la variable y un RESULTADO de interés (engagement, retención, atención, highlights, popularidad, comprensión...).
Salida: reports/respaldo_variables_D099.json y .csv. La revisión final de las coincidencias es manual (ver informe)."""
from __future__ import annotations

import csv
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

MAIL = "mailto=jfrancisco.ndp@gmail.com"
ANIO_MIN = int(__import__("os").environ.get("ANIO_MIN", "0"))
SUF = f"_{ANIO_MIN}" if ANIO_MIN else ""
OUTCOME = re.compile(r"engag|retention|attention|highlight|popular|viral|viewer|view count|watch|replay|interest|comprehension|persuas|credib|"
                     r"likab|trust|charisma|audience|listener|learning gain|memorab|virality|click|summari[sz]", re.I)

# variable -> (consultas, regex del concepto que debe aparecer en el resumen)
S = {
    "k_kvsum_mean": (["keyword weighting tf-idf transcript video summarization", "keyword-based importance lecture video segments"], r"tf-?idf|keyword|term weight"),
    "k_kvsum_max": (["keyword weighting tf-idf transcript video summarization"], r"tf-?idf|keyword|term weight"),
    "k_kvsum_local": (["local term importance tf-idf transcript segments highlights"], r"tf-?idf|keyword|term weight"),
    "k_top_terms_pm": (["topic keywords density spoken content engagement", "keyword density transcript video popularity"], r"keyword|key term|topic word"),
    "k_content_ratio": (["lexical density content words engagement speech", "content word ratio spoken language comprehension"], r"lexical density|content word"),
    "k_novelty": (["novelty information new content engagement video", "semantic novelty segments highlight video transcript"], r"novelty|novel"),
    "k_keybert_sim": (["semantic similarity to video topic embeddings highlight detection", "sentence embeddings relevance transcript video summarization"], r"embedding|semantic similarity|sentence-bert|cosine"),
    "k_keyphrase_pm": (["keyphrase extraction video summarization transcript", "keyphrases highlight detection video"], r"keyphrase|key phrase|keybert"),
    "k_noun_chunks_ps": (["noun phrase density spoken text complexity engagement", "noun phrases informativeness video transcripts"], r"noun phrase|noun chunk"),
    "s_pos_mean": (["sentiment positive emotion video engagement transcripts", "sentiment analysis audience engagement video content"], r"sentiment|positive emotion|valence"),
    "s_neg_mean": (["negative sentiment video engagement popularity", "negativity content virality sharing"], r"negativ"),
    "s_polarity_mean": (["sentiment polarity video popularity engagement", "emotional valence content virality"], r"polarity|valence|sentiment"),
    "s_polarity_std": (["sentiment variation emotional arc video engagement", "emotional trajectory narrative engagement"], r"emotional arc|sentiment (variation|variance|trajectory)|emotional trajectory|fluctuat"),
    "s_intensity_mean": (["emotional intensity arousal video engagement sharing", "high arousal emotion virality content"], r"arousal|intensity"),
    "s_intensity_max": (["peak emotional intensity video highlights", "emotional peaks highlight detection video"], r"peak|arousal|intensity"),
    "s_questions_pm": (["questions rhetorical engagement audience speech", "question asking speaker audience attention podcast lecture"], r"question"),
    "s_exclaim_pm": (["exclamation marks emotion expressiveness engagement text", "exclamations social media engagement"], r"exclam"),
    "s_second_person": (["second person pronoun you audience engagement", "direct address pronouns audience engagement speech lecture"], r"second.person|pronoun|direct address|\byou\b"),
    "s_first_person": (["first person pronouns personal storytelling engagement", "self-disclosure personal narrative audience engagement"], r"first.person|pronoun|self-disclos|personal narrative"),
    "s_numbers": (["numbers in headlines engagement click", "numerals specificity content popularity"], r"number|numeral|digit"),
    "s_intensifiers": (["intensifiers emphatic language persuasion engagement", "linguistic intensity words credibility audience"], r"intensif|emphatic|hedg"),
    "s_hook_words": (["hook opening attention curiosity gap headline engagement", "curiosity gap clickbait attention"], r"curiosity|hook|clickbait"),
    "s_laughs": (["laughter humor engagement video audience", "humor laughter podcast audience"], r"laugh|humou?r"),
    "a_rms_mean": (["speech loudness intensity engagement audience", "vocal intensity speaker charisma perceived"], r"loudness|intensity|volume|energy"),
    "a_rms_p95": (["vocal loudness peaks emphasis speech perception", "speech energy peaks highlights"], r"loudness|energy|intensity"),
    "a_rms_std": (["vocal dynamics loudness variation engaging speakers", "amplitude variation speech perceived charisma engagement"], r"loudness|amplitude|intensity|dynamic"),
    "a_pitch_std": (["pitch variation intonation engagement speakers lecture", "prosody pitch variability perceived charisma audience"], r"pitch|intonation|prosod|f0"),
    "a_pitch_range": (["pitch range expressive voice charisma engagement", "fundamental frequency range speaker persuasiveness"], r"pitch|f0|fundamental frequency"),
    "a_voiced_ratio": (["voiced speech proportion speaking time fluency engagement", "voicing ratio speech activity detection engagement"], r"voiced|voicing|speech activity|phonation"),
    "a_energy_delta": (["energy change speech excitement detection highlights", "excitement detection audio energy increase"], r"excite|energy|arousal"),
    "a_speech_rate": (["speech rate speaking rate engagement lecture", "speaking rate listener comprehension attention podcast"], r"speech rate|speaking rate|words per minute|tempo"),
    "a_pause_ratio": (["pauses silence speech engagement listener attention", "pause duration speaker perceived fluency charisma"], r"pause|silence"),
    "a_long_pauses_pm": (["long pauses dramatic pause emphasis speech", "pause frequency lectures engagement"], r"pause"),
    "h_rms_onset": (["opening seconds energy first impression video retention", "first seconds video retention audience drop"], r"first (few )?seconds|opening|intro|first impression|beginning"),
    "h_question": (["opening question hook video audience attention", "starting with a question engagement"], r"question|opening|hook"),
    "h_number": (["opening with statistic number attention persuasion", "numbers start of video attention"], r"number|statistic"),
    "h_second_person": (["addressing the viewer directly engagement video", "direct address viewers parasocial engagement youtube"], r"direct address|parasocial|second.person|you"),
    "h_hook_word": (["hook words attention opening video", "attention-grabbing opening video retention"], r"hook|attention-grab|opening"),
    "h_contrast": (["contrast tension opening storytelling engagement", "narrative tension suspense engagement audience"], r"contrast|tension|suspense|conflict"),
    "h_first_sentence_s": (["first sentence length opening engagement", "video introduction length audience retention"], r"first sentence|intro|opening|beginning"),
    "h_first_intensity": (["emotional opening first impression engagement", "initial emotion video retention"], r"initial|opening|first"),
    "h_first_keybert": (["topic relevance of the introduction video retention", "relevant introduction audience retention video"], r"introduction|opening|first|relevan"),
    "f_starts_dangling": (["clip self-contained start incoherent beginning highlights", "context-free segment comprehensibility short clips"], r"self-contained|coheren|context"),
    "f_ends_complete": (["segment boundary sentence completeness video segmentation", "natural boundaries clip extraction transcripts"], r"boundar|segmentation|sentence"),
    "f_coherence_mean": (["discourse coherence sentence similarity engagement", "text coherence embeddings consecutive sentences quality"], r"coheren"),
    "f_coherence_min": (["coherence breaks topic shifts segmentation embeddings", "topic segmentation lecture transcripts cosine similarity"], r"coheren|topic segmentation|topic shift"),
    "f_topic_drift": (["topic drift within segment embeddings", "topic shift detection transcripts segmentation"], r"topic (drift|shift|segmentation|change)"),
    "f_n_sentences": (["number of sentences segment length summarization", "sentence count segment salience"], r"sentence"),
    "f_duration": (["optimal video length engagement short clips", "video duration audience retention watch time"], r"duration|length"),
    "f_filler_rate": (["filler words disfluencies speaker perception engagement", "um uh disfluency perceived speaker competence"], r"filler|disfluen|hesitation|um\b|uh\b"),
    "f_word_conf": (["asr confidence scores speech quality downstream tasks", "word confidence automatic speech recognition reliability"], r"confidence"),
    "l_entropy": (["lexical diversity entropy text engagement", "vocabulary richness entropy language complexity"], r"entropy|lexical diversity|vocabulary"),
    "l_type_token": (["type-token ratio lexical diversity engagement", "lexical diversity speech quality perception"], r"type.token|lexical diversity|ttr"),
    "l_pron_12_vs_3": (["pronoun use first second person versus third person audience engagement", "pronouns conversational style interpersonal engagement"], r"pronoun"),
    "l_fillers": (["filler words speech fluency audience perception", "disfluencies public speaking evaluation"], r"filler|disfluen"),
    "l_silence": (["silence in speech interaction engagement", "silence pauses conversation attention listeners"], r"silence|pause"),
    "l_word_len": (["word length readability spoken content engagement", "linguistic complexity audience engagement video"], r"word length|readability|complexity"),
    "e_laugh_max": (["laughter detection audio highlights", "laughter audience reaction highlight detection video"], r"laugh"),
    "e_laugh_mean": (["laughter detection audio highlights", "laughter podcast audience engagement"], r"laugh"),
    "e_applause_max": (["applause detection highlights audio events", "applause cheering audio highlights sports video"], r"applause|cheer"),
    "e_applause_mean": (["applause detection highlights audio events"], r"applause|cheer"),
    "e_cheering_max": (["cheering crowd noise excitement highlight detection", "audience cheering excitement sports highlights audio"], r"cheer|crowd|excite"),
    "e_cheering_mean": (["cheering crowd noise excitement highlight detection"], r"cheer|crowd|excite"),
    "e_music_max": (["background music engagement video retention", "music in videos audience attention"], r"music"),
    "e_music_mean": (["background music speech videos engagement", "music presence video popularity"], r"music"),
    "e_speech_max": (["speech presence audio event detection highlights", "speech detection audio tagging"], r"speech"),
    "e_speech_mean": (["speech proportion audio events video highlights", "speech music ratio audio classification videos"], r"speech"),
    "e_laugh_tail": (["laughter after punchline humor detection", "punchline detection laughter humor audio"], r"punchline|laugh"),
    "e_laugh_after": (["audience laughter reaction after joke detection", "laughter reaction humor recognition audio"], r"laugh"),
    "e_applause_after": (["applause after speech segment applause reaction", "applause detection speech segments"], r"applause"),
    "e_laugh_frac": (["laughter proportion conversation engagement", "laughter frequency conversations podcast"], r"laugh"),
}


def abstract(w: dict) -> str:
    return w.get("abs") or ""


def _get(url: str):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "tesis-ulima/1.0 (mailto:jfrancisco.ndp@gmail.com)"}), timeout=40) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            print("   reintento", k + 1, str(e)[:60], flush=True)
            time.sleep(4 + 6 * k)
    return None


def query(q: str, n: int = 15) -> list[dict]:
    """Crossref (DOI verificados, con resumen cuando el editor lo da) + arXiv (resumen siempre)."""
    res = []
    raw = _get("https://api.crossref.org/works?query.bibliographic=" + urllib.parse.quote(q) + f"&rows={n}&select=DOI,title,abstract,issued,is-referenced-by-count,container-title,type" + (f"&filter=from-pub-date:{ANIO_MIN}-01-01" if ANIO_MIN else ""))
    if raw:
        for it in json.loads(raw)["message"]["items"]:
            ab = re.sub(r"<[^>]+>", " ", it.get("abstract") or "")
            yr = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
            res.append(dict(doi="https://doi.org/" + it["DOI"], title=(it.get("title") or [""])[0], publication_year=yr, cited_by_count=it.get("is-referenced-by-count"),
                            abs=re.sub(r"\s+", " ", ab).strip(), type=it.get("type"), venue=(it.get("container-title") or [""])[0]))
    raw = _get("http://export.arxiv.org/api/query?search_query=all:" + urllib.parse.quote(q.replace(" ", "+")).replace("%2B", "+") + "&max_results=8")
    if raw:
        txt = raw.decode("utf-8", "replace")
        for e in re.findall(r"<entry>(.*?)</entry>", txt, re.S):
            idm = re.search(r"<id>http://arxiv.org/abs/([^<]+?)(v\d+)?</id>", e)
            ti = re.search(r"<title>(.*?)</title>", e, re.S)
            su = re.search(r"<summary>(.*?)</summary>", e, re.S)
            yr = re.search(r"<published>(\d{4})", e)
            if idm and ti and su and (not ANIO_MIN or (yr and int(yr.group(1)) >= ANIO_MIN)):
                res.append(dict(doi="https://doi.org/10.48550/arXiv." + idm.group(1), title=re.sub(r"\s+", " ", ti.group(1)).strip(), publication_year=int(yr.group(1)) if yr else None,
                                cited_by_count=None, abs=re.sub(r"\s+", " ", su.group(1)).strip(), type="preprint", venue="arXiv"))
        time.sleep(3)
    return res


def main():
    fj = ROOT / "reports" / f"respaldo_variables{SUF}_D099.json"
    out = json.loads(fj.read_text(encoding="utf-8")) if fj.exists() else {}
    for var, (qs, concept) in S.items():
        if var in out and (out[var]["n_coincidencias"] > 0 or "--rehacer" not in sys.argv):
            continue
        cre = re.compile(concept, re.I)
        seen = {}
        for q in qs:
            for w in query(q):
                ab = abstract(w)
                title = w.get("title") or ""
                text = f"{title}. {ab}"
                if not w.get("doi") or not cre.search(text) or (ab and not OUTCOME.search(text)) or (not ab and not OUTCOME.search(title)):
                    continue
                # frase del resumen que une concepto y resultado
                snip = ""
                for s in re.split(r"(?<=[.!?]) ", text):
                    if cre.search(s) and OUTCOME.search(s):
                        snip = s.strip()
                        break
                score = (2 if snip else 0) + (1 if w["publication_year"] and w["publication_year"] >= 2015 else 0) + min((w.get("cited_by_count") or 0) / 200, 2)
                seen[w["doi"]] = dict(doi=w["doi"], title=title, year=w["publication_year"], cites=w.get("cited_by_count"), tipo=w.get("type"),
                                      venue=w.get("venue"), snippet=snip[:400], con_resumen=bool(ab), score=round(score - (0 if ab else 1), 2))
            time.sleep(0.6)
        cand = sorted(seen.values(), key=lambda d: -d["score"])[:4]
        out[var] = {"grupo": G[var][0], "n_coincidencias": len(seen), "candidatos": cand}
        fj.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{var:20s} coincidencias={len(seen):2d}  mejor: {cand[0]['title'][:70] if cand else '-'}", flush=True)
    (ROOT / "reports" / "respaldo_variables_D099.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(ROOT / "reports" / f"respaldo_variables{SUF}_D099.csv", "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["variable", "grupo", "n_coincidencias", "doi", "anio", "titulo", "citas", "frase_del_resumen"])
        for v, d in out.items():
            for c in d["candidatos"] or [dict(doi="", year="", title="", cites="", snippet="")]:
                wr.writerow([v, d["grupo"], d["n_coincidencias"], c["doi"], c["year"], c["title"], c["cites"], c["snippet"]])
    print("hecho")


if __name__ == "__main__":
    main()
