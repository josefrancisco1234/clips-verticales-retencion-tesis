import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.transcribe.whisper import Transcript, Word  # noqa: E402


def make_transcript(sentences: list[str], words_per_s: float = 2.5, gap: float = 0.4, lang: str = "es") -> Transcript:
    words, t = [], 0.0
    for s in sentences:
        for tok in s.split():
            d = 1.0 / words_per_s
            words.append(Word(" " + tok, t, t + d * 0.9, 0.9))
            t += d
        t += gap
    return Transcript(language=lang, duration=t, words=words, model="test")


@pytest.fixture
def transcript() -> Transcript:
    base = [
        "¿Sabías que nadie te cuenta el secreto más importante del éxito?",
        "La disciplina diaria vale más que la motivación.",
        "Yo aprendí esto después de fracasar tres veces con mi empresa.",
        "Entonces empecé a medir cada hábito con un cuaderno.",
        "El cuaderno me mostró que perdía cuatro horas al día.",
        "Pero lo increíble fue lo que pasó cuando cambié la rutina.",
        "En seis meses la empresa duplicó sus ventas.",
        "Y eso no fue suerte, fue método y disciplina.",
    ]
    return make_transcript(base * 6)


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)
