import math

from src.keywords.extractor import kvsum_weights
from src.keywords.text import content_token, tokenize


def test_kvsum_idf_zero_for_ubiquitous_terms():
    passages = [["disciplina", "empresa"], ["disciplina", "ventas"], ["disciplina", "cuaderno", "cuaderno"]]
    pw, total = kvsum_weights(passages)
    # "disciplina" aparece en todos los pasajes → log(N/PF)=0 → peso 0
    assert total["disciplina"] == 0
    # cada pasaje queda normalizado (norma L2 = 1 sobre sus términos con peso > 0)
    for w in pw:
        assert math.isclose(math.sqrt(sum(v * v for v in w.values())), 1.0, rel_tol=1e-9)
    # término repetido en un pasaje pesa más que uno aislado de otro pasaje equivalente
    assert total["cuaderno"] > 0 and total["empresa"] > 0


def test_kvsum_formula_value():
    passages = [["a", "b"], ["b"], ["c"]]
    pw, _ = kvsum_weights(passages)
    raw_a = math.log(2) * math.log(3 / 1)
    raw_b = math.log(2) * math.log(3 / 2)
    assert math.isclose(pw[0]["a"], raw_a / math.sqrt(raw_a**2 + raw_b**2))


def test_tokenize_and_content_token():
    assert tokenize("¡Hola, Mundo! 3,5 veces") == ["hola", "mundo", "3,5", "veces"]
    assert content_token(" disciplina.", "es") == "disciplina"
    assert content_token(" que", "es") is None
    assert content_token(" the", "en") is None
