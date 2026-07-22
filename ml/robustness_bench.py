"""Reproducible robustness evidence for the simulated Compound Zero benchmark.

This module deliberately keeps its claims narrow.  Every result comes from the
authored ScenarioBench simulator; it is not field validation, a safety
certification, or evidence that the same performance will transfer to a site.

The evaluation adds four slices that are intentionally separate from model
training:

* true leave-one-scenario-type-out (LOSO) evaluation;
* deterministic missing-stream, packet-dropout, and sensor-noise stresses;
* expected calibration error (ECE); and
* replay-group bootstrap intervals for event recall, false-negative rate, and
  warning lead time.

Run from the repository root with::

    python -m ml.robustness_bench
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from threadpoolctl import threadpool_limits

from .features import (
    FULL_FEATURES,
    SENSOR_LEVEL_FEATURES,
    SENSOR_TREND_FEATURES,
    enrich_feature_row,
)
from .modeling import TARGET, fit_calibrated_model, grouped_seed_split, select_threshold
from .scenario_bench import DATA_CLASSIFICATION, SCENARIO_TYPES


ROBUSTNESS_BENCHMARK_VERSION = "1.0.0"
DEFAULT_RANDOM_STATE = 20_260_722
DEFAULT_BOOTSTRAP_ITERATIONS = 2_000
DEFAULT_ECE_BINS = 10
THREADPOOL_LIMIT = 1


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _round(value: float, digits: int = 6) -> float:
    rounded = round(float(value), digits)
    return 0.0 if rounded == 0 else rounded


def write_metrics(path: Path, payload: Mapping[str, Any]) -> None:
    """Write stable JSON: sorted keys, fixed indentation, and one final newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def expected_calibration_error(
    y_true: Sequence[int] | np.ndarray,
    probability: Sequence[float] | np.ndarray,
    *,
    bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    """Return equal-width ECE and auditable, non-empty bin summaries."""

    if bins < 2:
        raise ValueError("ECE requires at least two bins")
    labels = np.asarray(y_true, dtype=int)
    probabilities = np.asarray(probability, dtype=float)
    if labels.ndim != 1 or probabilities.ndim != 1 or len(labels) != len(probabilities):
        raise ValueError("labels and probabilities must be equal-length one-dimensional arrays")
    if not len(labels):
        raise ValueError("ECE requires at least one observation")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("probabilities must be finite values in [0, 1]")

    indices = np.minimum((probabilities * bins).astype(int), bins - 1)
    weighted_error = 0.0
    summaries: list[dict[str, Any]] = []
    for index in range(bins):
        mask = indices == index
        count = int(mask.sum())
        if not count:
            continue
        mean_confidence = float(probabilities[mask].mean())
        observed_rate = float(labels[mask].mean())
        gap = abs(mean_confidence - observed_rate)
        weighted_error += count / len(labels) * gap
        summaries.append(
            {
                "bin_index": index,
                "lower_inclusive": _round(index / bins),
                "upper_inclusive_only_for_last_bin": _round((index + 1) / bins),
                "count": count,
                "mean_probability": _round(mean_confidence),
                "observed_positive_rate": _round(observed_rate),
                "absolute_gap": _round(gap),
            }
        )
    return {
        "value": _round(weighted_error),
        "bins": bins,
        "binning": "equal-width over [0, 1]; right edge included only in final bin",
        "non_empty_bin_summaries": summaries,
    }


def _alarm_episode_count(prediction: np.ndarray) -> int:
    binary = np.asarray(prediction, dtype=int)
    return int(np.sum((binary == 1) & (np.r_[0, binary[:-1]] == 0)))


def event_outcomes(frame: pd.DataFrame, prediction: Sequence[bool] | np.ndarray) -> list[dict[str, Any]]:
    """Return one event-level outcome per replay with an authored harmful state.

    The device strata are explicit and disjoint.  ``device_eventually_alarms``
    considers the entire 48-minute replay, while model detection remains
    restricted to the pre-event forecast window.  This avoids treating
    "device never alarms" as if it meant "model detected before device alarm."
    """

    required = {"scenario_id", "scenario_type", "minute", "event_minute", TARGET, "single_sensor_alarm"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"event evaluation is missing columns: {sorted(missing)}")
    if len(frame) != len(prediction):
        raise ValueError("prediction length must equal frame length")

    evaluated = frame[
        ["scenario_id", "scenario_type", "minute", "event_minute", TARGET, "single_sensor_alarm"]
    ].copy()
    evaluated["prediction"] = np.asarray(prediction, dtype=bool)
    outcomes: list[dict[str, Any]] = []
    for scenario_id, group in evaluated.groupby("scenario_id", sort=True):
        group = group.sort_values("minute", kind="stable")
        event_minute = int(group["event_minute"].iloc[0])
        if event_minute < 0:
            continue
        eligible = group[(group[TARGET] == 1) & (group["minute"] <= event_minute)]
        model_alerts = eligible[eligible["prediction"]]
        device_alerts = group[group["single_sensor_alarm"].astype(bool)]
        first_model = None if model_alerts.empty else int(model_alerts["minute"].iloc[0])
        first_device = None if device_alerts.empty else int(device_alerts["minute"].iloc[0])
        detected = first_model is not None
        device_eventually_alarms = first_device is not None
        outcomes.append(
            {
                "scenario_id": str(scenario_id),
                "scenario_type": str(group["scenario_type"].iloc[0]),
                "event_minute": event_minute,
                "detected": detected,
                "first_model_alert_minute": first_model,
                "warning_lead_minutes": None if first_model is None else event_minute - first_model,
                "device_eventually_alarms": device_eventually_alarms,
                "first_device_alarm_minute": first_device,
                "device_alarms_by_event": bool(
                    first_device is not None and first_device <= event_minute
                ),
                "model_before_eventual_device_alarm": bool(
                    first_model is not None
                    and first_device is not None
                    and first_model < first_device
                ),
                "model_detects_when_device_never_alarms": bool(
                    first_model is not None and first_device is None
                ),
            }
        )
    return outcomes


def _median_or_none(values: Iterable[float]) -> float | None:
    array = np.asarray(list(values), dtype=float)
    return None if not len(array) else _round(float(np.median(array)), 3)


def _percentile_or_none(values: Iterable[float], percentile: float) -> float | None:
    array = np.asarray(list(values), dtype=float)
    return None if not len(array) else _round(float(np.percentile(array, percentile)), 3)


def summarize_event_outcomes(
    frame: pd.DataFrame,
    prediction: Sequence[bool] | np.ndarray,
) -> dict[str, Any]:
    outcomes = event_outcomes(frame, prediction)
    event_count = len(outcomes)
    detected_count = sum(int(outcome["detected"]) for outcome in outcomes)
    device_eventual = sum(int(outcome["device_eventually_alarms"]) for outcome in outcomes)
    device_never = event_count - device_eventual
    device_by_event = sum(int(outcome["device_alarms_by_event"]) for outcome in outcomes)
    before_device = sum(
        int(outcome["model_before_eventual_device_alarm"]) for outcome in outcomes
    )
    detects_without_device = sum(
        int(outcome["model_detects_when_device_never_alarms"]) for outcome in outcomes
    )
    leads = [
        float(outcome["warning_lead_minutes"])
        for outcome in outcomes
        if outcome["warning_lead_minutes"] is not None
    ]

    evaluated = frame[["scenario_id", "event_minute"]].copy()
    evaluated["prediction"] = np.asarray(prediction, dtype=bool)
    false_alarm_episodes = 0
    non_event_minutes = 0
    non_event_groups_with_alarm = 0
    for _, group in evaluated.groupby("scenario_id", sort=True):
        if int(group["event_minute"].iloc[0]) >= 0:
            continue
        episodes = _alarm_episode_count(group["prediction"].to_numpy(dtype=bool))
        false_alarm_episodes += episodes
        non_event_minutes += len(group)
        non_event_groups_with_alarm += int(episodes > 0)

    recall = detected_count / event_count if event_count else None
    return {
        "event_groups": event_count,
        "detected_event_groups": detected_count,
        "event_recall": None if recall is None else _round(recall),
        "event_false_negative_rate": None if recall is None else _round(1.0 - recall),
        "median_warning_lead_minutes": _median_or_none(leads),
        "p10_warning_lead_minutes": _percentile_or_none(leads, 10),
        "device_strata": {
            "device_eventually_alarm_groups": device_eventual,
            "device_alarm_by_event_groups": device_by_event,
            "device_never_alarm_groups": device_never,
            "model_detected_before_eventual_device_alarm_groups": before_device,
            "model_detected_before_eventual_device_alarm_rate": None
            if not device_eventual
            else _round(before_device / device_eventual),
            "model_detected_when_device_never_alarms_groups": detects_without_device,
            "model_detected_when_device_never_alarms_rate": None
            if not device_never
            else _round(detects_without_device / device_never),
            "comparison_rule": (
                "The before-device rate denominator contains only event replays where a device "
                "alarms at some point; never-alarm replays are reported in a separate stratum."
            ),
        },
        "non_event_groups_with_alarm": non_event_groups_with_alarm,
        "false_alarm_episodes_per_24h": None
        if not non_event_minutes
        else _round(false_alarm_episodes / non_event_minutes * 24 * 60),
    }


def row_metrics_with_ece(
    frame: pd.DataFrame,
    probability: Sequence[float] | np.ndarray,
    prediction: Sequence[bool] | np.ndarray,
    *,
    threshold: float | None,
    ece_bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    labels = frame[TARGET].to_numpy(dtype=int)
    probabilities = np.asarray(probability, dtype=float)
    predictions = np.asarray(prediction, dtype=bool)
    if len(labels) != len(probabilities) or len(labels) != len(predictions):
        raise ValueError("probabilities and predictions must align with the frame")
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    has_positive = bool((labels == 1).any())
    has_negative = bool((labels == 0).any())
    return {
        "threshold": None if threshold is None else _round(threshold),
        "precision": _round(precision_score(labels, predictions, zero_division=0)),
        "recall": None
        if not has_positive
        else _round(recall_score(labels, predictions, zero_division=0)),
        "false_negative_rate": None
        if not has_positive
        else _round(fn / (fn + tp)),
        "false_positive_rate": None
        if not has_negative
        else _round(fp / (fp + tn)),
        "f2": None
        if not has_positive
        else _round(fbeta_score(labels, predictions, beta=2, zero_division=0)),
        "average_precision": None
        if not has_positive
        else _round(average_precision_score(labels, probabilities)),
        "roc_auc": None
        if not (has_positive and has_negative)
        else _round(roc_auc_score(labels, probabilities)),
        "brier_score": _round(brier_score_loss(labels, probabilities)),
        "expected_calibration_error": expected_calibration_error(
            labels, probabilities, bins=ece_bins
        ),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def evaluate_predictions(
    frame: pd.DataFrame,
    probability: Sequence[float] | np.ndarray,
    prediction: Sequence[bool] | np.ndarray,
    *,
    threshold: float | None,
    ece_bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    return {
        "rows": int(len(frame)),
        "scenario_groups": int(frame["scenario_id"].nunique()),
        "row": row_metrics_with_ece(
            frame,
            probability,
            prediction,
            threshold=threshold,
            ece_bins=ece_bins,
        ),
        "event": summarize_event_outcomes(frame, prediction),
    }


def _recompute_features(frame: pd.DataFrame) -> pd.DataFrame:
    stressed = frame.copy()
    enriched = pd.DataFrame.from_records(
        (enrich_feature_row(record) for record in stressed.to_dict(orient="records")),
        index=stressed.index,
    )
    stressed.loc[:, FULL_FEATURES] = enriched[FULL_FEATURES]
    return stressed


def apply_missing_stream(
    frame: pd.DataFrame,
    *,
    stream: str,
    training_medians: Mapping[str, float],
    random_state: int = DEFAULT_RANDOM_STATE,
) -> pd.DataFrame:
    """Apply deterministic, explicitly simulated missing-data fallbacks."""

    stressed = frame.copy()
    if stream == "process_sensor_stream":
        for feature in SENSOR_LEVEL_FEATURES + SENSOR_TREND_FEATURES:
            stressed[feature] = float(training_medians[feature])
        stressed["stream_quality"] = 0.0
    elif stream == "permit_stream":
        stressed.loc[:, ["hot_work_active", "confined_space_active", "permit_overlap_count", "isolation_active"]] = 0.0
        stressed["stream_quality"] = np.minimum(stressed["stream_quality"], 0.65)
    elif stream == "worker_location_stream":
        stressed["workers_in_zone"] = 0.0
        stressed["min_worker_distance_m"] = 120.0
        stressed["stream_quality"] = np.minimum(stressed["stream_quality"], 0.65)
    elif stream == "barrier_and_shift_stream":
        stressed.loc[:, ["ventilation_impaired", "shift_handover"]] = 0.0
        stressed["stream_quality"] = np.minimum(stressed["stream_quality"], 0.65)
    elif stream == "process_sensor_packet_dropout_20pct":
        rng = np.random.default_rng(random_state + 8_117)
        dropout = rng.random(len(stressed)) < 0.20
        for feature in SENSOR_LEVEL_FEATURES + SENSOR_TREND_FEATURES:
            stressed.loc[dropout, feature] = float(training_medians[feature])
        stressed.loc[dropout, "stream_quality"] = 0.0
    else:
        raise ValueError(f"unknown missing stream stress: {stream}")
    return _recompute_features(stressed)


def apply_sensor_noise(
    frame: pd.DataFrame,
    *,
    sigma: float,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> pd.DataFrame:
    """Add deterministic Gaussian threshold-ratio noise and rebuild interactions."""

    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("sensor noise sigma must be positive and finite")
    stressed = frame.copy()
    rng = np.random.default_rng(random_state + int(round(sigma * 1_000_000)) + 19_991)
    level_noise = rng.normal(0.0, sigma, size=(len(stressed), len(SENSOR_LEVEL_FEATURES)))
    trend_noise = rng.normal(0.0, sigma / 3.0, size=(len(stressed), len(SENSOR_TREND_FEATURES)))
    stressed.loc[:, SENSOR_LEVEL_FEATURES] = np.clip(
        stressed[SENSOR_LEVEL_FEATURES].to_numpy(dtype=float) + level_noise,
        0.0,
        1.45,
    )
    stressed.loc[:, SENSOR_TREND_FEATURES] = np.clip(
        stressed[SENSOR_TREND_FEATURES].to_numpy(dtype=float) + trend_noise,
        -0.35,
        0.35,
    )
    stressed["stream_quality"] = np.clip(
        stressed["stream_quality"] - min(0.25, sigma * 2.0), 0.0, 1.0
    )
    return _recompute_features(stressed)


def bootstrap_event_intervals(
    outcomes: Sequence[Mapping[str, Any]],
    *,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    random_state: int = DEFAULT_RANDOM_STATE,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Percentile intervals from replay-group resampling of event replays."""

    if iterations < 100:
        raise ValueError("at least 100 bootstrap iterations are required")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    if not outcomes:
        raise ValueError("event bootstrap requires at least one event replay")
    rng = np.random.default_rng(random_state + 43_219)
    detected = np.asarray([bool(item["detected"]) for item in outcomes], dtype=bool)
    leads = np.asarray(
        [
            np.nan if item["warning_lead_minutes"] is None else float(item["warning_lead_minutes"])
            for item in outcomes
        ],
        dtype=float,
    )
    recalls = np.empty(iterations, dtype=float)
    false_negative_rates = np.empty(iterations, dtype=float)
    median_leads: list[float] = []
    for index in range(iterations):
        sample = rng.integers(0, len(outcomes), size=len(outcomes))
        sample_detected = detected[sample]
        recall = float(sample_detected.mean())
        recalls[index] = recall
        false_negative_rates[index] = 1.0 - recall
        sample_leads = leads[sample]
        valid_leads = sample_leads[np.isfinite(sample_leads)]
        if len(valid_leads):
            median_leads.append(float(np.median(valid_leads)))

    alpha = (1.0 - confidence) / 2.0

    def interval(values: np.ndarray, estimate: float | None) -> dict[str, Any]:
        return {
            "estimate": None if estimate is None else _round(estimate, 3),
            "lower": _round(np.quantile(values, alpha), 3),
            "upper": _round(np.quantile(values, 1.0 - alpha), 3),
        }

    detected_leads = leads[np.isfinite(leads)]
    lead_values = np.asarray(median_leads, dtype=float)
    return {
        "method": "percentile bootstrap; event replay is the resampling unit",
        "confidence_level": confidence,
        "iterations": iterations,
        "random_state": random_state + 43_219,
        "event_recall": interval(recalls, float(detected.mean())),
        "event_false_negative_rate": interval(
            false_negative_rates, 1.0 - float(detected.mean())
        ),
        "median_warning_lead_minutes": None
        if not len(lead_values)
        else {
            **interval(
                lead_values,
                None if not len(detected_leads) else float(np.median(detected_leads)),
            ),
            "valid_resamples": len(lead_values),
        },
        "interpretation_boundary": (
            "Sampling uncertainty across simulated event replays only; this does not include "
            "model-refit uncertainty or real-world/site uncertainty. Degenerate intervals are possible."
        ),
    }


def run_loso_evaluation(
    frame: pd.DataFrame,
    *,
    held_out_types: Sequence[str] = SCENARIO_TYPES,
    random_state: int = DEFAULT_RANDOM_STATE,
    ece_bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    """Train without each requested scenario type and evaluate only on that type."""

    unknown = set(held_out_types) - set(SCENARIO_TYPES)
    if unknown:
        raise ValueError(f"unknown held-out scenario types: {sorted(unknown)}")
    folds: dict[str, Any] = {}
    pooled_frames: list[pd.DataFrame] = []
    pooled_probabilities: list[np.ndarray] = []
    pooled_predictions: list[np.ndarray] = []
    for fold_index, held_out in enumerate(held_out_types):
        held_frame = frame[frame["scenario_type"] == held_out].copy().reset_index(drop=True)
        development = frame[frame["scenario_type"] != held_out].copy()
        calibration = development[development["seed"] % 5 == 1].copy()
        training = development[development["seed"] % 5 != 1].copy()
        if held_frame.empty:
            raise ValueError(f"no rows for held-out scenario type: {held_out}")
        if training[TARGET].nunique() != 2 or calibration[TARGET].nunique() != 2:
            raise ValueError("LOSO training and calibration partitions need both classes")

        with threadpool_limits(limits=THREADPOOL_LIMIT):
            model = fit_calibrated_model(
                training,
                calibration,
                FULL_FEATURES,
                random_state=random_state + 1_000 + fold_index,
            )
            calibration_probability = model.predict_proba(calibration[FULL_FEATURES])[:, 1]
            threshold = select_threshold(
                calibration[TARGET].to_numpy(dtype=int), calibration_probability
            )
            probability = model.predict_proba(held_frame[FULL_FEATURES])[:, 1]
        prediction = probability >= threshold
        training_types = sorted(str(item) for item in training["scenario_type"].unique())
        folds[held_out] = {
            "held_out_scenario_type": held_out,
            "held_out_absent_from_training": held_out not in training_types,
            "training_scenario_types": training_types,
            "training_rows": int(len(training)),
            "calibration_rows": int(len(calibration)),
            "threshold_selected_on_excluded-type-free_calibration": _round(threshold),
            "evaluation": evaluate_predictions(
                held_frame,
                probability,
                prediction,
                threshold=threshold,
                ece_bins=ece_bins,
            ),
        }
        pooled_frames.append(held_frame)
        pooled_probabilities.append(probability)
        pooled_predictions.append(prediction)

    pooled_frame = pd.concat(pooled_frames, ignore_index=True)
    pooled_probability = np.concatenate(pooled_probabilities)
    pooled_prediction = np.concatenate(pooled_predictions)
    event_fold_recalls = {
        name: fold["evaluation"]["event"]["event_recall"]
        for name, fold in folds.items()
        if fold["evaluation"]["event"]["event_groups"] > 0
    }
    return {
        "protocol": (
            "For each fold, every replay of one scenario type is excluded from model fitting and "
            "threshold calibration, then used only for evaluation."
        ),
        "fold_count": len(folds),
        "held_out_scenario_types": list(held_out_types),
        "each_row_evaluated_by_model_unseen_to_its_scenario_type": True,
        "folds": folds,
        "pooled_loso": evaluate_predictions(
            pooled_frame,
            pooled_probability,
            pooled_prediction,
            threshold=None,
            ece_bins=ece_bins,
        ),
        "event_fold_recall_summary": {
            "event_bearing_fold_count": len(event_fold_recalls),
            "macro_mean": None
            if not event_fold_recalls
            else _round(float(np.mean(list(event_fold_recalls.values())))),
            "minimum": None
            if not event_fold_recalls
            else _round(float(min(event_fold_recalls.values()))),
            "by_scenario_type": event_fold_recalls,
        },
    }


def run_stress_suite(
    test: pd.DataFrame,
    *,
    model: Any,
    threshold: float,
    training_medians: Mapping[str, float],
    random_state: int = DEFAULT_RANDOM_STATE,
    ece_bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    """Evaluate one frozen model against deterministic synthetic corruptions."""

    cases: list[tuple[str, str, pd.DataFrame]] = [("baseline", "No perturbation.", test.copy())]
    missing_stream_descriptions = {
        "process_sensor_stream": (
            "All sensor levels and trends replaced by development-training medians; stream quality set to zero."
        ),
        "permit_stream": (
            "Hot-work, confined-space, overlap, and isolation fields unavailable and imputed to a neutral zero for diagnosis only."
        ),
        "worker_location_stream": (
            "Worker count and proximity unavailable and imputed to zero workers / 120 m."
        ),
        "barrier_and_shift_stream": (
            "Ventilation-impairment and handover fields unavailable and imputed to zero."
        ),
        "process_sensor_packet_dropout_20pct": (
            "A fixed-seed 20% Bernoulli mask replaces affected sensor packets with development-training medians."
        ),
    }
    for stream, description in missing_stream_descriptions.items():
        cases.append(
            (
                f"missing__{stream}",
                description,
                apply_missing_stream(
                    test,
                    stream=stream,
                    training_medians=training_medians,
                    random_state=random_state,
                ),
            )
        )
    for sigma in (0.02, 0.05):
        cases.append(
            (
                f"sensor_noise__gaussian_sigma_{str(sigma).replace('.', '_')}",
                (
                    f"Fixed-seed Gaussian noise with sigma={sigma:.2f} of a device-threshold ratio "
                    f"on levels and sigma={sigma / 3:.6f} on slopes."
                ),
                apply_sensor_noise(test, sigma=sigma, random_state=random_state),
            )
        )

    results: dict[str, Any] = {}
    for name, description, stressed in cases:
        with threadpool_limits(limits=THREADPOOL_LIMIT):
            probability = model.predict_proba(stressed[FULL_FEATURES])[:, 1]
        prediction = probability >= threshold
        results[name] = {
            "description": description,
            "data_classification": DATA_CLASSIFICATION,
            "evaluation": evaluate_predictions(
                stressed,
                probability,
                prediction,
                threshold=threshold,
                ece_bins=ece_bins,
            ),
        }
    return {
        "frozen_model": True,
        "threshold_reselected_after_stress": False,
        "imputation_boundary": (
            "These deterministic imputations diagnose sensitivity; they are not a production "
            "missing-data or fail-safe policy."
        ),
        "cases": results,
    }


def build_robustness_metrics(
    frame: pd.DataFrame,
    bundle: Mapping[str, Any],
    *,
    dataset_sha256: str,
    model_artifact_sha256: str,
    random_state: int = DEFAULT_RANDOM_STATE,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    ece_bins: int = DEFAULT_ECE_BINS,
    held_out_types: Sequence[str] = SCENARIO_TYPES,
) -> dict[str, Any]:
    if set(frame["data_classification"].astype(str).unique()) != {DATA_CLASSIFICATION}:
        raise ValueError("robustness evidence accepts only SIMULATED ScenarioBench data")
    if list(bundle["full_features"]) != FULL_FEATURES:
        raise ValueError("persisted full-feature contract does not match this evaluator")
    if str(bundle.get("dataset_sha256")) != dataset_sha256:
        raise ValueError("persisted model and ScenarioBench dataset hashes do not match")

    split = grouped_seed_split(frame)
    test = split.test.reset_index(drop=True)
    training_medians = {
        feature: float(split.train[feature].median())
        for feature in SENSOR_LEVEL_FEATURES + SENSOR_TREND_FEATURES
    }
    with threadpool_limits(limits=THREADPOOL_LIMIT):
        stress = run_stress_suite(
            test,
            model=bundle["full_model"],
            threshold=float(bundle["full_threshold"]),
            training_medians=training_medians,
            random_state=random_state,
            ece_bins=ece_bins,
        )
        loso = run_loso_evaluation(
            frame,
            held_out_types=held_out_types,
            random_state=random_state,
            ece_bins=ece_bins,
        )

    with threadpool_limits(limits=THREADPOOL_LIMIT):
        baseline_probability = bundle["full_model"].predict_proba(test[FULL_FEATURES])[:, 1]
    baseline_prediction = baseline_probability >= float(bundle["full_threshold"])
    bootstrap = bootstrap_event_intervals(
        event_outcomes(test, baseline_prediction),
        iterations=bootstrap_iterations,
        random_state=random_state,
    )
    return {
        "benchmark": "Compound Zero robustness evidence",
        "version": ROBUSTNESS_BENCHMARK_VERSION,
        "data_classification": DATA_CLASSIFICATION,
        "claim_boundary": (
            "Controlled evaluation on authored simulated data only; not field validation, "
            "a safety certification, or evidence of site-transfer performance."
        ),
        "decision_engine": "scikit-learn calibrated gradient boosting; no LLM in risk decisions",
        "inputs": {
            "dataset_sha256": dataset_sha256,
            "model_artifact_sha256": model_artifact_sha256,
            "model_version": str(bundle["model_version"]),
            "rows": int(len(frame)),
            "scenario_groups": int(frame["scenario_id"].nunique()),
            "scenario_types": list(SCENARIO_TYPES),
        },
        "configuration": {
            "random_state": random_state,
            "threadpool_limit": THREADPOOL_LIMIT,
            "ece_bins": ece_bins,
            "bootstrap_iterations": bootstrap_iterations,
            "base_test_policy": "whole-seed holdout from grouped_seed_split",
        },
        "stress_suite": stress,
        "leave_one_scenario_type_out": loso,
        "base_test_group_bootstrap": bootstrap,
        "limitations": [
            "All data, events, corruptions, and missing-stream patterns are simulated and authored.",
            "LOSO is bounded to scenario types from one generator and is not evidence of real-world distribution shift performance.",
            "Sensor noise is Gaussian threshold-ratio noise and does not reproduce any specific instrument error model.",
            "Missing inputs are imputed for sensitivity measurement; a production system must define abstention and human escalation behavior.",
            "Bootstrap intervals resample simulated replay groups and exclude model-refit and field/site uncertainty.",
            "Local site calibration, shadow-mode trials, independent safety review, and field validation remain required.",
        ],
        "reproduction": {
            "command": "python -m ml.robustness_bench",
            "determinism": (
                "No wall-clock values are emitted; all pseudo-random operations use recorded seeds; "
                "JSON keys are sorted; numeric threadpools are limited to one."
            ),
        },
    }


def load_verified_inputs(
    *,
    dataset_path: Path,
    metadata_path: Path,
    model_path: Path,
    model_card_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], str, str]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    model_card = json.loads(model_card_path.read_text(encoding="utf-8"))
    dataset_sha256 = _sha256_file(dataset_path)
    model_sha256 = _sha256_file(model_path)
    if metadata.get("sha256") != dataset_sha256:
        raise ValueError("ScenarioBench dataset hash does not match metadata")
    if model_card.get("model_artifact_sha256") != model_sha256:
        raise ValueError("model artifact hash does not match model card")
    if model_card.get("dataset_sha256") != dataset_sha256:
        raise ValueError("model card and ScenarioBench dataset hashes do not match")
    frame = pd.read_csv(dataset_path)
    bundle = joblib.load(model_path)
    return frame, bundle, dataset_sha256, model_sha256


def generate_metrics(
    *,
    dataset_path: Path,
    metadata_path: Path,
    model_path: Path,
    model_card_path: Path,
    output_path: Path,
    random_state: int = DEFAULT_RANDOM_STATE,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
) -> dict[str, Any]:
    frame, bundle, dataset_sha256, model_sha256 = load_verified_inputs(
        dataset_path=dataset_path,
        metadata_path=metadata_path,
        model_path=model_path,
        model_card_path=model_card_path,
    )
    metrics = build_robustness_metrics(
        frame,
        bundle,
        dataset_sha256=dataset_sha256,
        model_artifact_sha256=model_sha256,
        random_state=random_state,
        bootstrap_iterations=bootstrap_iterations,
    )
    write_metrics(output_path, metrics)
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/scenario_bench/scenario_bench.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("data/scenario_bench/metadata.json"))
    parser.add_argument("--model", type=Path, default=Path("artifacts/compound_zero_model.joblib"))
    parser.add_argument("--model-card", type=Path, default=Path("artifacts/model_card.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/robustness_metrics.json"))
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    parser.add_argument(
        "--bootstrap-iterations", type=int, default=DEFAULT_BOOTSTRAP_ITERATIONS
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    metrics = generate_metrics(
        dataset_path=args.dataset,
        metadata_path=args.metadata,
        model_path=args.model,
        model_card_path=args.model_card,
        output_path=args.output,
        random_state=args.random_state,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    summary = {
        "output": str(args.output),
        "data_classification": metrics["data_classification"],
        "base_event": metrics["stress_suite"]["cases"]["baseline"]["evaluation"]["event"],
        "pooled_loso_event": metrics["leave_one_scenario_type_out"]["pooled_loso"]["event"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
