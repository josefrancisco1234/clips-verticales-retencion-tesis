"""D-042: detección de bloqueo anti-bot y pausa tras bloqueos consecutivos. Sin red."""
import pandas as pd

from src.data import youtube_dataset as yd
from src.ingest import youtube


def test_es_bloqueo_reconoce_los_mensajes_de_youtube():
    assert youtube.es_bloqueo("ERROR: [youtube] abc: Sign in to confirm you’re not a bot")
    assert youtube.es_bloqueo("HTTP Error 429: Too Many Requests")
    assert not youtube.es_bloqueo("Video unavailable. This video is private")
    assert not youtube.es_bloqueo("") and not youtube.es_bloqueo(None)


def _cfg(tmp_path):
    from src.common.config import load_config

    return load_config("configs/gpu.yaml")


def _preparar(monkeypatch, tmp_path, errores):
    """`errores`: lista con el mensaje de error de cada descarga (uno por video)."""
    cola = list(errores)
    pausas = []
    monkeypatch.setattr(yd, "transcript_path", lambda cfg, vid, m: tmp_path / f"{vid}.json")
    monkeypatch.setattr(yd, "heatmap_path", lambda cfg, vid: tmp_path / f"{vid}_h.json")
    monkeypatch.setattr(yd, "wav_path", lambda cfg, vid: tmp_path / f"{vid}.wav")
    monkeypatch.setattr(yd, "write_json", lambda *a, **k: None)
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: None)
    monkeypatch.setattr(youtube, "polite_sleep", lambda s, jitter=0.0: pausas.append(round(s)))

    def descarga(vid, out_dir, fmt):
        youtube.ultimo_error = cola.pop(0)
        return None

    monkeypatch.setattr(youtube, "download_audio", descarga)
    return pausas


def test_dos_bloqueos_seguidos_pausan_30_minutos(monkeypatch, tmp_path):
    bloqueo = "Sign in to confirm you're not a bot"
    pausas = _preparar(monkeypatch, tmp_path, [bloqueo, bloqueo, bloqueo])
    man = pd.DataFrame({"video_id": ["a", "b", "c"], "query_lang": ["es"] * 3})
    yd.acquire(_cfg(tmp_path), man, "base")
    assert pausas.count(1800) == 1          # tras el 2.º bloqueo; el 3.º reinicia la cuenta


def test_un_video_no_disponible_reinicia_la_cuenta(monkeypatch, tmp_path):
    bloqueo, privado = "HTTP Error 429", "Video unavailable"
    pausas = _preparar(monkeypatch, tmp_path, [bloqueo, privado, bloqueo])
    man = pd.DataFrame({"video_id": ["a", "b", "c"], "query_lang": ["es"] * 3})
    yd.acquire(_cfg(tmp_path), man, "base")
    assert 1800 not in pausas               # nunca hubo dos bloqueos consecutivos


def test_pausa_entre_descargas_es_de_4_a_6_segundos(monkeypatch, tmp_path):
    pausas = _preparar(monkeypatch, tmp_path, ["Video unavailable"])
    yd.acquire(_cfg(tmp_path), pd.DataFrame({"video_id": ["a"], "query_lang": ["es"]}), "base")
    assert pausas == [4]                    # base * 2; el jitter (hasta +2 s) se pasa aparte
