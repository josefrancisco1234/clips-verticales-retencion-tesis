"""D-101: el margen de respiración no invade palabras vecinas."""
from types import SimpleNamespace as W

from src.pipeline import breathing_margin

PAL = [W(start=0.0, end=0.4), W(start=0.5, end=0.9), W(start=2.0, end=2.5), W(start=2.55, end=3.0), W(start=5.0, end=5.4)]


def test_margen_con_pausas_largas():
    s, e = breathing_margin(2.0, 3.0, PAL, 10.0)
    assert 1.85 <= s < 2.0 and 3.0 < e <= 3.35


def test_margen_no_invade_palabras_pegadas():
    s, e = breathing_margin(0.5, 0.9, PAL, 10.0)
    assert s >= 0.4 + 0.03 - 1e-9 and e <= 2.0 - 0.03 + 1e-9 and e >= 0.9


def test_bordes_del_video():
    s, e = breathing_margin(0.0, 0.4, PAL, 10.0)
    assert s == 0.0 and e <= 0.5 - 0.03 + 1e-9
    s, e = breathing_margin(5.0, 5.4, PAL, 5.5)
    assert e <= 5.5
