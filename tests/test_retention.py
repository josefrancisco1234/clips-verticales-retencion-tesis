"""Metodo guiado por retencion (D-045/D-047): formula, calidad, calor y calibrador. Sin red."""
import numpy as np
import pandas as pd

from src.ranking import retention as ret


def _df(n=6):
    return pd.DataFrame({
        "start": np.arange(n) * 30.0, "end": np.arange(n) * 30.0 + 25.0,
        "a_pause_ratio": [0.0, 0.1, 0.9, 0.2, 0.3, 0.4],
        "a_speech_rate": [3.0, 2.5, 1.0, 2.0, 2.2, 2.4],
        "f_starts_dangling": [0, 0, 1, 0, 0, 0], "f_ends_complete": [1, 1, 1, 1, 0, 1],
    })


def test_formula_sigue_el_signo_de_los_pesos():
    df = _df()
    raw = ret.formula_raw(df, {"a_pause_ratio": 0.2, "a_speech_rate": -0.1})
    assert int(np.argmax(raw)) == 2          # mas pausas y habla mas lenta
    assert int(np.argmin(raw)) == 0


def test_columna_ausente_no_rompe_y_aporta_neutro():
    raw = ret.formula_raw(_df(), {"no_existe": 1.0})
    assert np.allclose(raw, 0.5)


def test_calidad_excluye_inicio_colgado_y_final_incompleto():
    ok = ret.quality_ok(_df())
    assert ok.tolist() == [True, True, False, True, False, True]


def test_calibrador_monotono_y_en_rango():
    table = np.linspace(-1, 1, 100).tolist()
    s = ret.calibrate(np.array([-5.0, 0.0, 0.5, 5.0]), table)
    assert s.min() == 0 and s.max() == 99
    assert (np.diff(s) >= 0).all()


def test_id_de_youtube_desde_url():
    assert ret.video_id_from_url("https://www.youtube.com/watch?v=-Gzz2LZGowU&t=3271s") == "-Gzz2LZGowU"
    assert ret.video_id_from_url("https://youtu.be/-Gzz2LZGowU") == "-Gzz2LZGowU"
    assert ret.video_id_from_url("C:/videos/clase.mp4") is None


def test_calor_prefiere_la_ventana_sobre_el_pico():
    df = _df()
    heat = [{"start_time": i * 30.0, "end_time": (i + 1) * 30.0, "value": v}
            for i, v in enumerate([0.1, 0.2, 0.1, 1.0, 0.2, 0.1])]
    raw = ret.heat_raw(df, heat)
    assert int(np.argmax(raw)) == 3


def test_apply_calor_descarta_no_autocontenidos(monkeypatch):
    df = _df()
    heat = [{"start_time": i * 30.0, "end_time": (i + 1) * 30.0, "value": v}
            for i, v in enumerate([0.1, 0.2, 1.0, 0.4, 0.9, 0.1])]   # el pico cae en candidatos NO autocontenidos
    from src.ingest import youtube
    monkeypatch.setattr(youtube, "fetch_metadata", lambda vid: {"heatmap": heat})
    out, label = ret.apply(df, None, "https://youtu.be/-Gzz2LZGowU", "auto", "lgbm")
    assert "calor" in label
    assert int(np.argmax(out["raw"].to_numpy())) == 3     # mejor candidato autocontenido


def test_apply_formula_con_max_clip_s_solo_deja_clips_cortos(tmp_path):
    import json
    w = {"a_pause_ratio": 0.2}
    (tmp_path / "formula_calor_D045.json").write_text(
        json.dumps({"weights": w, "calibrator": np.linspace(0, 1, 100).tolist()}), encoding="utf-8")

    class Cfg:
        @staticmethod
        def path(key):
            return tmp_path

    df = _df()
    df["end"] = df["start"] + np.array([25, 25, 80, 25, 25, 25.0])   # el candidato 2 (mas pausas) dura 80 s
    out, label = ret.apply(df, Cfg, "C:/video.mp4", "formula", "lgbm", max_clip_s=45)
    assert "V1" in label
    assert int(np.argmax(out["raw"].to_numpy())) != 2


def test_formula_raw_binario_usa_banderas_y_desempata_con_el_percentil():
    """D-098: cada variable vale 1 solo si esta en el 25 % mas alto; los empates no dependen de la posicion."""
    from src.ranking.retention import formula_raw

    df = pd.DataFrame({"a": np.arange(100.0), "b": np.arange(100.0)[::-1]})
    w = {"a": 1.0, "b": 0.5}
    r = formula_raw(df, w, binario=True)
    assert np.round(r[0], 2) == 0.5                  # a bajo (0) y b alto (1): 0.5
    assert np.round(r[99], 2) == 1.0                 # a alto (1) y b bajo (0): 1.0
    assert np.round(r[50], 2) == 0.0                 # ambas bajas
    assert len(np.unique(r)) == 100     # el desempate continuo separa a todos
