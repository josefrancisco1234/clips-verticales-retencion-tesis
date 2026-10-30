"""Features sobre un contexto sintético (sin descargar modelos de embeddings/sentimiento)."""
import numpy as np

from src.features.audio import compute_frames, window_audio
from src.features.builder import VideoContext, feature_columns, window_features, windows_frame
from src.keywords.extractor import KeywordIndex, kvsum_weights
from src.keywords.text import content_token, tokenize
from src.segment.candidates import sentence_candidates
from src.segment.sentences import split_sentences


def fake_context(tr, audio=None):
    sents = split_sentences(tr)
    toks = [content_token(w.text, "es") for w in tr.words]
    by_p = [[] for _ in range(int(tr.duration // 60) + 1)]
    for w, t in zip(tr.words, toks):
        if t:
            by_p[int(w.start // 60)].append(t)
    pw, tw = kvsum_weights(by_p)
    rng = np.random.default_rng(0)
    emb = rng.normal(size=(len(sents), 8))
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    doc = emb.mean(0) / np.linalg.norm(emb.mean(0))
    kw = KeywordIndex("es", toks, tw, pw, 60.0, sorted(tw, key=lambda t: -tw[t])[:5], [("disciplina", 0.9)], emb, doc,
                      [["la disciplina"]] * len(sents))
    sent = np.tile([0.6, 0.3, 0.1], (len(sents), 1))
    ws = np.array([w.start for w in tr.words])
    we = np.array([w.end for w in tr.words])
    return VideoContext(tr, sents, kw, sent, audio, "es", ws, we, [tokenize(w.text) for w in tr.words],
                        np.zeros(len(tr.words), dtype=np.int8), (emb[:-1] * emb[1:]).sum(1)), sents


def test_window_features_groups(transcript):
    ctx, sents = fake_context(transcript)
    wins = sentence_candidates(sents, 15, 90, [20, 40])
    df = windows_frame(ctx, wins, 3.0, 15, {"video_id": "v"})
    for g in ["K", "S", "A", "H", "F", "P"]:
        assert feature_columns(df, [g]), f"grupo {g} vacío"
    first = df.iloc[0]
    assert first["h_question"] == 1.0 and first["h_second_person"] == 1.0 and first["h_hook_word"] == 1.0
    assert np.isnan(first["a_rms_mean"])  # sin audio → NaN (LightGBM lo maneja)
    assert 0 < first["a_speech_rate"] < 5
    assert first["f_ends_complete"] == 1.0


def test_dangling_start_detected(transcript):
    ctx, sents = fake_context(transcript)
    i = next(k for k, s in enumerate(sents) if s.text.startswith("Entonces"))
    from src.segment.candidates import Window

    f = window_features(ctx, Window(sents[i].start, sents[i + 4].end, i, i + 5), 3.0, 15)
    assert f["f_starts_dangling"] == 1.0


def test_audio_frames_emphasis():
    sr = 16000
    t = np.arange(sr * 20) / sr
    y = 0.05 * np.sin(2 * np.pi * 150 * t)
    y[sr * 10: sr * 15] *= 8  # tramo enfatizado
    fr = compute_frames(y.astype(np.float32), sr)
    loud = window_audio(fr, 10, 15, 3.0)
    quiet = window_audio(fr, 2, 7, 3.0)
    assert loud["a_rms_mean"] > quiet["a_rms_mean"] + 1.0
    assert loud["a_energy_delta"] > 0


def test_local_novelty_window():
    from src.features.builder import local_seen

    starts = np.array([0.0, 10.0, 400.0, 410.0])
    seen = local_seen(starts, ["ley", "ley", "ley", None], 300.0)
    assert seen.tolist() == [0, 1, 0, 0]  # a los 400 s "ley" vuelve a ser nueva: pasó > 300 s


def test_relative_features():
    import pandas as pd

    from src.features.relative import add_relative

    df = pd.DataFrame({"video_id": ["a"] * 4 + ["b"] * 2, "start": [0, 10, 200, 210, 0, 10],
                       "end": [10, 20, 210, 220, 10, 20], "a_x": [1.0, 3.0, 10.0, 12.0, 5.0, 5.0]})
    out = add_relative(df, radius_s=50, cols=["a_x"])
    assert out.loc[3, "a_x__rk"] == 1.0 and out.loc[0, "a_x__rk"] == 0.25
    assert out.loc[0, "a_x__cx"] == -1.0 and out.loc[3, "a_x__cx"] == 1.0  # contraste sólo con vecinos ≤50 s
    assert out.loc[4, "a_x__cx"] == 0.0


def test_linguistic_and_event_features(transcript):
    import pandas as pd

    from src.data.augment import human_overlap
    from src.features.extra import event_features, linguistic_features

    f = linguistic_features(transcript, 0, 30)
    assert 0 < f["l_type_token"] <= 1 and f["l_entropy"] > 0 and 0 <= f["l_silence"] < 1
    ev = pd.DataFrame({"t": [1.5, 4.5, 7.5, 10.5], "laugh": [0.0, 0.9, 0.0, 0.8], "applause": [0, 0, 0, 0.7],
                       "cheering": 0.0, "music": 0.0, "speech": 0.9})
    e = event_features(ev, 0, 6)
    assert e["e_laugh_max"] == 0.9 and e["e_laugh_after"] == 0.8 and e["e_applause_after"] == 0.7
    df = pd.DataFrame({"start": [0.0, 20.0], "end": [10.0, 30.0]})
    assert human_overlap(df, [[5.0, 25.0]]).tolist() == [0.5, 0.5]
