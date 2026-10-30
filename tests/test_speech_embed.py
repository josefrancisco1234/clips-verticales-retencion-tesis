"""Grupo U: el procesamiento por lotes debe dar lo mismo que trozo a trozo (D-035). Sin red ni GPU."""
from types import SimpleNamespace

import numpy as np
import torch

from src.features import speech_embed as se


def _fake_model(x, output_hidden_states=True):
    # Salida que depende de cada muestra por separado: (B, T, 2) = [media, máximo] de la señal.
    hs = torch.stack([x, x.abs()], dim=-1).float()
    return SimpleNamespace(hidden_states=[hs] * 11)


def _run(monkeypatch, tmp_path, y, batch_size, name):
    monkeypatch.setattr(se, "_model", lambda n, d: (_fake_model, "cpu", torch))
    monkeypatch.setattr("src.ingest.media.load_wav", lambda p, sr: y)
    return se.chunk_embeddings(tmp_path / "x.wav", tmp_path / f"{name}.npz", 100, 10.0, 10, "cpu", "fake", batch_size)


def test_lotes_equivalen_a_trozo_a_trozo(monkeypatch, tmp_path):
    rng = np.random.default_rng(0)
    y = rng.standard_normal(100 * 55 + 37).astype("float32")  # 5 trozos completos + uno más corto
    t1, e1 = _run(monkeypatch, tmp_path, y, 1, "uno")
    t3, e3 = _run(monkeypatch, tmp_path, y, 3, "tres")
    t16, e16 = _run(monkeypatch, tmp_path, y, 16, "dieciseis")
    assert len(t1) == 6
    assert np.array_equal(t1, t3) and np.array_equal(t1, t16)
    assert np.allclose(e1, e3) and np.allclose(e1, e16)
    assert np.allclose(t1, [5, 15, 25, 35, 45, 55])


def test_trozo_final_menor_de_un_segundo_se_descarta(monkeypatch, tmp_path):
    y = np.ones(100 * 20 + 40, dtype="float32")  # 2 trozos completos + resto de 0.4 s
    t, e = _run(monkeypatch, tmp_path, y, 16, "corto")
    assert len(t) == 2 and e.shape[0] == 2


def test_embeddings_no_finitos_se_rechazan(monkeypatch, tmp_path):
    import pytest

    def nan_model(x, output_hidden_states=True):
        return SimpleNamespace(hidden_states=[torch.full((x.shape[0], 5, 2), float("nan"))] * 11)

    monkeypatch.setattr(se, "_model", lambda n, d: (nan_model, "cpu", torch))
    monkeypatch.setattr("src.ingest.media.load_wav", lambda p, sr: np.ones(100 * 20, dtype="float32"))
    with pytest.raises(RuntimeError, match="no finitos"):
        se.chunk_embeddings(tmp_path / "x.wav", tmp_path / "n.npz", 100, 10.0, 10, "cpu", "fake", 4)
    assert not (tmp_path / "n.npz").exists()
