import numpy as np

from src.common.config import load_config
from src.context.llm import LLMClient, parse_json
from src.context.refine import llm_select_topk, refine, template_context
from src.pipeline import snap_to_cuts
from src.render.captions import build_ass, word_class
from src.render.reframe import _fit, smooth


def test_config_paths():
    cfg = load_config()
    assert str(cfg.path("raw")).replace("\\", "/").endswith("tesis_data/data/raw")
    assert cfg.path("models").name == "models"
    assert cfg.seed == 42


def test_llm_none_and_template():
    llm = LLMClient("none", None)
    assert not llm.enabled and llm.complete("s", "u") is None
    assert llm_select_topk(["a", "b"], llm, 1) is None
    clips = refine([{"start": 0, "end": 30, "text": "¿Sabías esto? Es clave.", "keywords": [{"term": "clave"}],
                     "concepts": ["la clave"], "features": {"h_question": 1, "f_ends_complete": 1}}], llm, "es")
    ctx = clips[0]["context"]
    assert ctx["source"] == "template" and ctx["style"] == "curiosidad" and ctx["self_contained"] is True
    assert template_context({"text": "y eso.", "features": {"f_starts_dangling": 1}}, "es")["trim_start_sentences"] == 1


def test_parse_json():
    assert parse_json('bla {"title": "x"} bla') == {"title": "x"}
    assert parse_json("[3, 1]") == [3, 1]
    assert parse_json("nada") is None


def test_captions_highlight(transcript):
    cfg = load_config().render["captions"]
    assert word_class(" disciplina", {"disciplina"}, "es") == "primary"
    assert word_class(" tres", set(), "es") == "base"
    assert word_class(" 3", set(), "es") == "secondary"
    ass = build_ass(transcript.words, 0.0, 20.0, {"disciplina"}, "es", cfg, 1080, 1920, "Hook de prueba")
    assert "Style: Cap" in ass and "Hook de prueba" in ass
    assert cfg["primary_color"] in ass and "DISCIPLINA" in ass
    assert ass.count("Dialogue:") > 10


def test_smooth_deadzone_and_fit():
    x = np.array([0.5, 0.52, 0.51, 0.9, 0.9, 0.9])
    y = smooth(x, 0.5, 0.05)
    assert y[1] == 0.5 and y[2] == 0.5  # dentro de la zona muerta no se mueve
    assert 0.5 < y[-1] < 0.9
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    assert _fit(frame, 108, 192).shape == (192, 108, 3)


def test_snap_only_in_pauses():
    gaps = [(9.8, 10.3)]
    assert snap_to_cuts(10.5, 40.0, [10.1], gaps, 1.5) == (10.1, 40.0)
    assert snap_to_cuts(10.5, 40.0, [11.5], gaps, 1.5) == (10.5, 40.0)  # el corte cae sobre habla


def test_perfil_gpu_hereda_de_default():
    """configs/gpu.yaml sólo redefine algunas claves: el resto debe venir de default.yaml (extends)."""
    gpu = load_config("configs/gpu.yaml")
    # D-033: el ASR del dataset sigue en "base" hasta el barrido único con "small"
    assert gpu.transcribe["device"] == "cuda" and gpu.transcribe["model_dataset"] == "base"
    assert gpu.features["speech_embed"]["enabled"] is True
    assert "U" in gpu.features["groups"]
    # heredado de default.yaml
    assert gpu.seed == 42 and gpu.ranking["nms_iou"] == 0.5 and gpu.path("models").name == "models"
    assert gpu.render["width"] == 1080 and gpu.labels["gt_threshold"] == 0.5
