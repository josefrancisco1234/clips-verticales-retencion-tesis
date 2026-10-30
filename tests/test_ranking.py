import numpy as np
import pandas as pd

from src.ranking.model import MLPRanker, RankerBundle, ScoreCalibrator, make_bundle, train_lgbm

PARAMS = {"objective": "lambdarank", "metric": "ndcg", "eval_at": [5], "learning_rate": 0.1, "num_leaves": 7,
          "min_data_in_leaf": 5, "verbose": -1, "num_boost_round": 60, "early_stopping_rounds": 20}


def synthetic(n_videos=30, n=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for v in range(n_videos):
        x1, x2, noise = rng.normal(size=n), rng.normal(size=n), rng.normal(size=n)
        y = x1 + 0.5 * x2 + 0.3 * noise
        grade = pd.Series(y).rank(pct=True).mul(5).astype(int).clip(0, 4)
        for i in range(n):
            rows.append({"video_id": f"v{v}", "start": float(i * 30), "end": float(i * 30 + 25), "h_signal": x1[i], "k_signal": x2[i],
                         "s_noise": rng.normal(), "y_grade": int(grade[i]), "y_mr": y[i]})
    return pd.DataFrame(rows)


FEATS = ["h_signal", "k_signal", "s_noise"]


def _ndcg_like(df, col):
    from src.evaluation.metrics import group_ranking_metrics

    d = df.assign(y_relevant=(df["y_grade"] == 4).astype(int))
    return group_ranking_metrics(d, col)["NDCG@10"]


def test_lgbm_learns_and_bundle_roundtrip(tmp_path):
    tr, va, te = synthetic(30, seed=0), synthetic(8, seed=1), synthetic(8, seed=2)
    booster = train_lgbm(tr, va, FEATS, PARAMS, seed=42)
    te["pred"] = booster.predict(te[FEATS])
    te["rand"] = np.random.default_rng(0).random(len(te))
    assert _ndcg_like(te, "pred") > _ndcg_like(te, "rand") + 0.2
    bundle = make_bundle(booster, va, FEATS, {"test": True})
    s = bundle.score(te)
    assert s["score"].between(0, 99).all() and {"score_hook", "score_flow", "score_value"} <= set(s.columns)
    bundle.save(tmp_path)
    again = RankerBundle.load(tmp_path).score(te)
    assert (again["score"] == s["score"]).all()


def test_mlp_ranknet_learns():
    tr, te = synthetic(20, seed=3), synthetic(6, seed=4)
    m = MLPRanker(FEATS, [16], 0.0, 0.01, 15, 128, seed=0).fit(tr)
    te["pred"] = m.predict(te)
    te["rand"] = np.random.default_rng(0).random(len(te))
    assert _ndcg_like(te, "pred") > _ndcg_like(te, "rand") + 0.2


def test_calibrator_monotonic():
    cal = ScoreCalibrator(np.linspace(-1, 1, 500))
    out = cal(np.array([-5, -1, 0, 1, 5]))
    assert out[0] == 0 and out[-1] == 99 and np.all(np.diff(out) >= 0)
