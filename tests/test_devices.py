"""Elección del tipo de cómputo por tarjeta (D-036). Sin GPU real: se simula cuda_info."""
import pytest

from src.common import devices


@pytest.mark.parametrize("name,cc,esperado", [
    ("NVIDIA GeForce GTX 1660 SUPER", (7, 5), "float32"),   # Turing sin tensor cores: fp16 es más lento
    ("NVIDIA GeForce RTX 3060", (8, 6), "float16"),
    ("NVIDIA GeForce GTX 1080", (6, 1), "int8_float32"),    # Pascal
])
def test_compute_type_auto_por_tarjeta(monkeypatch, name, cc, esperado):
    monkeypatch.setattr(devices, "cuda_info", lambda: (True, name, cc))
    assert devices.resolve_compute_type("auto", "cuda") == esperado


def test_compute_type_explicito_y_cpu(monkeypatch):
    monkeypatch.setattr(devices, "cuda_info", lambda: (True, "NVIDIA GeForce GTX 1660 SUPER", (7, 5)))
    assert devices.resolve_compute_type("int8_float32", "cuda") == "int8_float32"
    assert devices.resolve_compute_type("auto", "cpu") == "int8"
