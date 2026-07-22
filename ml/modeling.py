"""Grouped training, calibration, baselines, and evaluation for ScenarioBench."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import FULL_FEATURES, PROCESS_FEATURES, SENSOR_LEVEL_FEATURES

MODEL_VERSION = "compound-zero-scenariobench-v1"
TARGET = "risk_within_horizon"


@dataclass(frozen=True)
class SplitFrames:
    train: pd.DataFrame
    calibration: pd.DataFrame
    test: pd.DataFrame
    train_seeds: tuple[int, ...]
    calibration_seeds: tuple[int, ...]
    test_seeds: tuple[int, ...]


def grouped_seed_split(frame: pd.DataFrame) -> SplitFrames:
    """Split whole replay groups by seed; no seed appears in two partitions."""

    seeds = sorted(int(seed) for seed in frame["seed"].unique())
    test_seeds = tuple(seed for seed in seeds if seed % 5 == 0)
    calibration_seeds = tuple(seed for seed in seeds if seed % 5 == 1)
    train_seeds = tuple(seed for seed in seeds if seed % 5 in {2, 3, 4})
    if not train_seeds or not calibration_seeds or not test_seeds:
        raise ValueError("At least five consecutive seeds are required for grouped splitting")

    partitions = {
        "train": frame[frame["seed"].isin(train_seeds)].copy(),
        "calibration": frame[frame["seed"].isin(calibration_seeds)].copy(),
        "test": frame[frame["seed"].isin(test_seeds)].copy(),
    }
    for name, partition in partitions.items():
        if partition[TARGET].nunique() != 2:
            raise ValueError(f"{name} partition must contain both target classes")
    return SplitFrames(
        train=partitions["train"],
        calibration=partitions["calibration"],
        test=partitions["test"],
        train_seeds=train_seeds,
        calibration_seeds=calibration_seeds,
        test_seeds=test_seeds,
    )


def _base_estimator(random_state: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    learning_rate=0.065,
                    max_iter=180,
                    max_leaf_nodes=15,
                    min_samples_leaf=24,
                    l2_regularization=0.35,
                    random_state=random_state,
                ),
            ),
        ]
    )


def fit_calibrated_model(
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    features: list[str],
    *,
    random_state: int,
) -> CalibratedClassifierCV:
    """Fit on training seeds, then calibrate on different held-out seeds."""

    base = _base_estimator(random_state)
    base.fit(train[features], train[TARGET])
    calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
    calibrated.fit(calibration[features], calibration[TARGET])
    return calibrated


def select_threshold(y_true: np.ndarray, probability: np.ndarray) -> float:
    """Choose a cost-sensitive threshold on calibration data only.

    The F2 objective weights recall more heavily than precision, appropriate for
    a safety-screening prototype. The test partition is never used here.
    """

    candidates = np.linspace(0.08, 0.92, 169)
    scored: list[tuple[float, float, float, float]] = []
    for threshold in candidates:
        prediction = probability >= threshold
        score = fbeta_score(y_true, prediction, beta=2, zero_division=0)
        recall = recall_score(y_true, prediction, zero_division=0)
        precision = precision_score(y_true, prediction, zero_division=0)
        scored.append((float(score), float(recall), float(precision), float(threshold)))
    best = max(scored, key=lambda item: (item[0], item[1], item[2], item[3]))
    return best[3]


def _safe_roc_auc(y_true: np.ndarray, probability: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, probability))


def row_metrics(
    y_true: np.ndarray,
    probability: np.ndarray,
    prediction: np.ndarray,
    *,
    threshold: float,
) -> dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y_true, prediction, labels=[0, 1]).ravel()
    false_positive_rate = fp / (fp + tn) if fp + tn else 0.0
    false_negative_rate = fn / (fn + tp) if fn + tp else 0.0
    return {
        "threshold": round(float(threshold), 6),
        "precision": round(float(precision_score(y_true, prediction, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, prediction, zero_division=0)), 6),
        "false_negative_rate": round(float(false_negative_rate), 6),
        "false_positive_rate": round(float(false_positive_rate), 6),
        "f1": round(float(f1_score(y_true, prediction, zero_division=0)), 6),
        "f2": round(float(fbeta_score(y_true, prediction, beta=2, zero_division=0)), 6),
        "average_precision": round(float(average_precision_score(y_true, probability)), 6),
        "roc_auc": None
        if (auc := _safe_roc_auc(y_true, probability)) is None
        else round(auc, 6),
        "brier_score": round(float(brier_score_loss(y_true, probability)), 6),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def _alarm_episode_count(prediction: np.ndarray) -> int:
    binary = prediction.astype(int)
    return int(np.sum((binary == 1) & (np.r_[0, binary[:-1]] == 0)))


def event_metrics(frame: pd.DataFrame, prediction: np.ndarray) -> dict[str, Any]:
    evaluated = frame[["scenario_id", "minute", "event_minute", TARGET]].copy()
    evaluated["prediction"] = prediction.astype(int)
    event_leads: list[float] = []
    event_count = 0
    detected_count = 0
    before_device_count = 0
    false_alarm_episodes = 0
    non_event_minutes = 0
    non_event_groups_with_alarm = 0

    sensor_by_index = frame["single_sensor_alarm"].to_numpy(dtype=bool)
    evaluated["single_sensor_alarm"] = sensor_by_index
    for _, group in evaluated.groupby("scenario_id", sort=False):
        event_minute = int(group["event_minute"].iloc[0])
        if event_minute >= 0:
            event_count += 1
            eligible = group[(group[TARGET] == 1) & (group["minute"] <= event_minute)]
            alerts = eligible[eligible["prediction"] == 1]
            if not alerts.empty:
                detected_count += 1
                first_alert = int(alerts["minute"].iloc[0])
                event_leads.append(float(event_minute - first_alert))
                device_alerts = eligible[eligible["single_sensor_alarm"] == 1]
                if device_alerts.empty or first_alert < int(device_alerts["minute"].iloc[0]):
                    before_device_count += 1
        else:
            group_predictions = group["prediction"].to_numpy(dtype=bool)
            episodes = _alarm_episode_count(group_predictions)
            false_alarm_episodes += episodes
            non_event_minutes += len(group)
            non_event_groups_with_alarm += int(episodes > 0)

    event_recall = detected_count / event_count if event_count else 0.0
    leads = np.asarray(event_leads, dtype=float)
    return {
        "event_groups": event_count,
        "detected_event_groups": detected_count,
        "event_recall": round(float(event_recall), 6),
        "event_false_negative_rate": round(float(1.0 - event_recall), 6),
        "median_warning_lead_minutes": None if not len(leads) else round(float(np.median(leads)), 3),
        "p10_warning_lead_minutes": None if not len(leads) else round(float(np.percentile(leads, 10)), 3),
        "detected_before_device_alarm_rate": 0.0
        if not detected_count
        else round(float(before_device_count / detected_count), 6),
        "non_event_groups_with_alarm": non_event_groups_with_alarm,
        "false_alarm_episodes_per_24h": 0.0
        if not non_event_minutes
        else round(float(false_alarm_episodes / non_event_minutes * 24 * 60), 6),
    }


def evaluate_method(
    frame: pd.DataFrame,
    probability: np.ndarray,
    prediction: np.ndarray,
    *,
    threshold: float,
) -> dict[str, Any]:
    y_true = frame[TARGET].to_numpy(dtype=int)
    return {
        "row": row_metrics(y_true, probability, prediction, threshold=threshold),
        "event": event_metrics(frame, prediction),
    }


def train_and_evaluate(frame: pd.DataFrame, *, random_state: int = 20260722) -> tuple[dict[str, Any], dict[str, Any]]:
    split = grouped_seed_split(frame)

    process_model = fit_calibrated_model(
        split.train,
        split.calibration,
        PROCESS_FEATURES,
        random_state=random_state,
    )
    full_model = fit_calibrated_model(
        split.train,
        split.calibration,
        FULL_FEATURES,
        random_state=random_state + 1,
    )

    process_cal_probability = process_model.predict_proba(split.calibration[PROCESS_FEATURES])[:, 1]
    full_cal_probability = full_model.predict_proba(split.calibration[FULL_FEATURES])[:, 1]
    process_threshold = select_threshold(
        split.calibration[TARGET].to_numpy(dtype=int), process_cal_probability
    )
    full_threshold = select_threshold(
        split.calibration[TARGET].to_numpy(dtype=int), full_cal_probability
    )

    test = split.test.reset_index(drop=True)
    sensor_probability = np.clip(
        test[SENSOR_LEVEL_FEATURES].max(axis=1).to_numpy(dtype=float), 0.0, 1.0
    )
    sensor_prediction = test["single_sensor_alarm"].to_numpy(dtype=bool)
    process_probability = process_model.predict_proba(test[PROCESS_FEATURES])[:, 1]
    full_probability = full_model.predict_proba(test[FULL_FEATURES])[:, 1]
    process_prediction = process_probability >= process_threshold
    full_prediction = full_probability >= full_threshold

    methods = {
        "single_sensor": evaluate_method(
            test, sensor_probability, sensor_prediction, threshold=1.0
        ),
        "process_only": evaluate_method(
            test, process_probability, process_prediction, threshold=process_threshold
        ),
        "full_fusion": evaluate_method(
            test, full_probability, full_prediction, threshold=full_threshold
        ),
    }
    single_fnr = methods["single_sensor"]["event"]["event_false_negative_rate"]
    full_fnr = methods["full_fusion"]["event"]["event_false_negative_rate"]
    process_fnr = methods["process_only"]["event"]["event_false_negative_rate"]

    metrics: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "data_classification": "SIMULATED",
        "decision_engine": "scikit-learn calibrated gradient boosting; no LLM in risk decisions",
        "target": TARGET,
        "split_policy": "Whole-seed holdout: seed mod 5 = 0 test, 1 calibration, 2/3/4 train.",
        "split": {
            "train_seeds": list(split.train_seeds),
            "calibration_seeds": list(split.calibration_seeds),
            "test_seeds": list(split.test_seeds),
            "train_rows": int(len(split.train)),
            "calibration_rows": int(len(split.calibration)),
            "test_rows": int(len(test)),
            "overlap_count": len(
                (set(split.train_seeds) & set(split.calibration_seeds))
                | (set(split.train_seeds) & set(split.test_seeds))
                | (set(split.calibration_seeds) & set(split.test_seeds))
            ),
        },
        "methods": methods,
        "ablation": {
            "full_vs_single_event_fnr_absolute_reduction": round(float(single_fnr - full_fnr), 6),
            "full_vs_process_event_fnr_absolute_reduction": round(float(process_fnr - full_fnr), 6),
            "full_vs_process_average_precision_gain": round(
                float(
                    methods["full_fusion"]["row"]["average_precision"]
                    - methods["process_only"]["row"]["average_precision"]
                ),
                6,
            ),
            "full_vs_process_row_fpr_absolute_reduction": round(
                float(
                    methods["process_only"]["row"]["false_positive_rate"]
                    - methods["full_fusion"]["row"]["false_positive_rate"]
                ),
                6,
            ),
            "full_vs_process_false_alarm_episodes_per_24h_reduction": round(
                float(
                    methods["process_only"]["event"]["false_alarm_episodes_per_24h"]
                    - methods["full_fusion"]["event"]["false_alarm_episodes_per_24h"]
                ),
                6,
            ),
            "full_vs_single_median_warning_lead_minutes_gain": round(
                float(
                    methods["full_fusion"]["event"]["median_warning_lead_minutes"]
                    - methods["single_sensor"]["event"]["median_warning_lead_minutes"]
                ),
                6,
            ),
        },
        "limitations": [
            "All benchmark scenarios are simulated and are not field validation.",
            "Context schedules and harmful-state equations are authored for controlled ablation testing.",
            "A site pilot requires local threshold calibration, shadow-mode validation, and safety review.",
        ],
    }
    bundle = {
        "model_version": MODEL_VERSION,
        "data_classification": "SIMULATED",
        "decision_engine": "scikit-learn calibrated gradient boosting; no LLM",
        "process_model": process_model,
        "full_model": full_model,
        "process_features": PROCESS_FEATURES,
        "full_features": FULL_FEATURES,
        "process_threshold": process_threshold,
        "full_threshold": full_threshold,
        "random_state": random_state,
    }
    return bundle, metrics
