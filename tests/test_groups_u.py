"""D-038: la línea base (D-027) nunca debe ver columnas del grupo U; las variantes *_U sí."""
import pandas as pd

from src.features.builder import feature_columns


def test_linea_base_excluye_u_y_variantes_la_incluyen():
    df = pd.DataFrame(columns=["a_rms", "h_x", "k_x", "u_00", "u_31", "e_laugh", "video_id"])
    todos = ["K", "S", "A", "H", "F", "E", "L", "U"]
    base = [g for g in todos if g != "U"]
    assert not any(c.startswith("u_") for c in feature_columns(df, base))
    assert feature_columns(df, ["U"]) == ["u_00", "u_31"]
    assert {"a_rms", "u_00"} <= set(feature_columns(df, ["A", "U"]))
    assert set(feature_columns(df, todos)) == set(feature_columns(df, base)) | {"u_00", "u_31"}
