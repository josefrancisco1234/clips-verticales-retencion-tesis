"""D-100: capítulos del video y mejor clip de cada capítulo (datos sintéticos, sin red)."""
import numpy as np

from src.segment.candidates import Window
from src.segment.chapters import auto_blocks, chapter_of, from_youtube, pick_per_chapter

RAW = [{"start_time": 0, "end_time": 100, "title": "Intro"}, {"start_time": 100, "end_time": 300, "title": "Tema"},
       {"start_time": 300, "end_time": 360, "title": "Cierre"}]


def test_from_youtube_ordena_y_recorta():
    chs = from_youtube(list(reversed(RAW)), duration=330)
    assert [c.title for c in chs] == ["Intro", "Tema", "Cierre"]
    assert chs[-1].end == 330 and [c.index for c in chs] == [0, 1, 2]
    assert from_youtube(None, 100) == [] and from_youtube([{"start_time": 5, "end_time": 5.5, "title": "x"}], 100) == []


def test_auto_blocks_une_el_ultimo_bloque_corto():
    bl = auto_blocks(1250, 600, 120)
    assert [(b.start, b.end) for b in bl] == [(0, 600), (600, 1250)] and all(b.auto for b in bl)
    assert len(auto_blocks(1900, 600, 120)) == 3 and auto_blocks(300, 600)[0].end == 300
    assert len(auto_blocks(1250 + 600, 600, 120)) == 3 and auto_blocks(1230, 600, 120)[-1].end == 1230 and len(auto_blocks(1230, 600, 120)) == 2


def test_chapter_of_por_mayor_solape():
    chs = from_youtube(RAW, 360)
    assert chapter_of(90, 130, chs) == 1 and chapter_of(95, 105, chs) == 0 and chapter_of(10, 40, chs) == 0


def test_pick_per_chapter_mejor_elegible_y_sin_cruzar_capitulos():
    chs = from_youtube(RAW, 360)
    wins = [Window(10, 40), Window(50, 80), Window(110, 150), Window(120, 160), Window(200, 240), Window(95, 130), Window(310, 350)]
    sc = np.array([0.2, 0.9, 0.5, 0.6, 0.1, 5.0, 0.3])   # la ventana 5 cruza Intro/Tema (mayoría en Tema, 35 s: 5 en Intro)
    ok = np.array([1, 1, 1, 1, 1, 1, 0], bool)            # la 6 no es elegible
    out = pick_per_chapter(wins, sc, ok, chs, k=1, overlap=0.3, min_inside=0.9)
    assert out[0] == [1]                                   # Intro: la 5 no cuenta (solo 5/35 dentro del capítulo... pertenece a Tema pero 30/35 < 0.9)
    assert out[1] == [3]                                   # Tema: 0.6 gana a 0.5
    assert 2 not in out                                    # Cierre: su única ventana no es elegible
    dos = pick_per_chapter(wins, sc, ok, chs, k=2, overlap=0.3, min_inside=0.9)
    assert dos[1] == [3, 4]                                # 2 y 3 se solapan más de 30 %: queda la mejor y luego la de 200-240
    assert pick_per_chapter(wins, sc, ok, chs, 1, 0.3, min_chapter_s=150).get(0) is None   # Intro dura 100 s: no llega al mínimo
