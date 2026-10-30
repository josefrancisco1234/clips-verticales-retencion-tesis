import numpy as np

from src.segment.candidates import Window, bin_windows, fixed_windows, nms, sentence_candidates, temporal_iou
from src.segment.sentences import is_complete, split_sentences
from tests.conftest import make_transcript


def test_split_on_punctuation(transcript):
    sents = split_sentences(transcript, max_words=40, pause_split_s=5.0)
    assert len(sents) == 48
    assert sents[0].text.startswith("¿Sabías") and sents[0].text.endswith("?")
    assert all(s.end > s.start for s in sents)
    assert sents[1].w0 == sents[0].w1


def test_split_on_pause_and_length():
    tr = make_transcript(["uno dos tres cuatro cinco seis"], gap=0.0)
    tr.words[3].end = tr.words[3].start + 0.1
    tr.words[4].start += 2.0  # pausa larga
    sents = split_sentences(tr, max_words=40, pause_split_s=0.9)
    assert len(sents) == 2
    assert len(split_sentences(make_transcript(["a b c d e f g h"]), max_words=3)) == 3


def test_is_complete():
    assert is_complete("Hola mundo.") and not is_complete("y entonces")


def test_candidates_respect_bounds(transcript):
    sents = split_sentences(transcript)
    c = sentence_candidates(sents, 15, 90, [20, 40, 60])
    assert c, "debe haber candidatos"
    assert all(15 <= w.duration <= 90 for w in c)
    assert all(w.start == sents[w.s0].start and w.end == sents[w.s1 - 1].end for w in c)
    capped = sentence_candidates(sents, 15, 90, [20, 40, 60], max_n=10, seed=1)
    assert len(capped) == 10


def test_fixed_and_bins():
    fw = fixed_windows(65.0, 20)
    assert [round(w.start) for w in fw] == [0, 20, 40, 60] or [round(w.start) for w in fw] == [0, 20, 40]
    heat = [{"start_time": i * 10.0, "end_time": (i + 1) * 10.0, "value": 0.1} for i in range(100)]
    assert len(bin_windows(heat)) == 100


def test_iou_and_nms():
    a, b, c = Window(0, 10), Window(5, 15), Window(20, 30)
    assert abs(temporal_iou(a, b) - 5 / 15) < 1e-9
    keep = nms([a, b, c], np.array([0.9, 0.8, 0.7]), iou=0.3)
    assert keep == [0, 2]


def test_nms_iomin_rejects_contained_clips():
    big, inner, far = Window(0, 40), Window(5, 20), Window(50, 70)
    scores = np.array([0.9, 0.8, 0.7])
    assert nms([big, inner, far], scores, iou=0.5) == [0, 1, 2]  # IoU=15/40 no lo descarta
    assert nms([big, inner, far], scores, iou=0.3, mode="iomin") == [0, 2]
