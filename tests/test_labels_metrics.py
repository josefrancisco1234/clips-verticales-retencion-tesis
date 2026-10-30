import numpy as np
import pandas as pd

from src.evaluation.metrics import (ap, f1, group_ranking_metrics, hit, precision, precision_at_k, recall,
                                    reciprocal_rank, rhapsody_metrics, temporal_f1)
from src.ranking.labels import corrected_graph, grade_within, gt_bins, window_gt_overlap, window_mr
from src.segment.candidates import Window


def _heat(vals, step=10.0):
    return [{"start_time": i * step, "end_time": (i + 1) * step, "value": v} for i, v in enumerate(vals)]


def test_first_bin_correction_and_gt():
    s, e, v = corrected_graph(_heat([1.0, 0.2, 0.9, 0.6, 0.4]))
    assert v[0] == 0.2  # sesgo del primer bin corregido
    assert gt_bins(v, max_n=20, threshold=0.5) == [2, 3]
    assert gt_bins(v, max_n=1, threshold=0.5) == [2]


def test_window_labels():
    s, e, v = corrected_graph(_heat([0.0, 0.0, 1.0, 0.0]))
    assert window_mr(Window(15, 25), s, e, v) == 0.5
    assert window_gt_overlap(Window(15, 25), s, e, [2]) == 0.5


def test_grades_quantiles():
    g = grade_within(pd.Series(np.arange(10.0)), 5)
    assert g.tolist() == [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]


def test_rhapsody_metrics_match_reference():
    gt, pred = [1, 2, 3], [3, 9]
    assert hit(gt, pred) == 1 and precision(gt, pred) == 0.5 and abs(recall(gt, pred) - 1 / 3) < 1e-9
    assert abs(f1(gt, pred) - 0.4) < 1e-9
    assert abs(ap(gt, [3, 9, 1]) - (1 + 2 / 3) / 3) < 1e-9
    m = rhapsody_metrics([gt, [5]], [pred, [5]])
    assert m["hit"] == 1.0


def test_ranking_metrics():
    rel = np.array([0, 1, 0, 1])
    assert precision_at_k(rel, 2) == 0.5
    assert reciprocal_rank(rel) == 0.5
    df = pd.DataFrame({"video_id": ["a"] * 4, "s": [4, 3, 2, 1], "y_relevant": [1, 0, 0, 1],
                       "y_grade": [4, 0, 1, 3], "y_mr": [0.9, 0.1, 0.2, 0.8]})
    m = group_ranking_metrics(df, "s")
    assert m["P@1"] == 1.0 and m["MRR"] == 1.0


def test_temporal_f1():
    p, r, f = temporal_f1([(0, 10)], [(5, 15)])
    assert (p, r) == (0.5, 0.5) and abs(f - 0.5) < 1e-9
    assert temporal_f1([], [(0, 1)]) == (0.0, 0.0, 0.0)
