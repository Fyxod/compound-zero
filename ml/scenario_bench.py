"""Deterministic, explicitly simulated industrial compound-risk benchmark.

ScenarioBench does not claim to represent field performance. It creates grouped
multivariate time-series replays that make it possible to test whether context
fusion detects hazardous combinations earlier than isolated device thresholds.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

from .features import FULL_FEATURES, enrich_feature_row, single_sensor_alarm

DATASET_NAME: Final = "ScenarioBench"
DATASET_VERSION: Final = "1.0.0"
DATA_CLASSIFICATION: Final = "SIMULATED"

SCENARIO_TYPES: Final[tuple[str, ...]] = (
    "normal_shift",
    "isolated_sensor_spike",
    "process_drift",
    "subthreshold_process_drift",
    "permit_only",
    "compound_hot_work",
    "compound_confined_space",
    "compound_handover",
    "barrier_loss_workers",
)

SCENARIO_DESCRIPTIONS: Final[dict[str, str]] = {
    "normal_shift": "Nominal correlated process noise with no active exposure.",
    "isolated_sensor_spike": "One brief device excursion without corroborating process or work context.",
    "process_drift": "A correlated process fault eventually reaches a configured device threshold.",
    "subthreshold_process_drift": "A correlated but contained process drift with no exposed work context.",
    "permit_only": "Hot work and personnel are present while process conditions remain normal.",
    "compound_hot_work": "Sub-threshold gas accumulation, impaired extraction, hot work, and exposed workers.",
    "compound_confined_space": "Sub-threshold oxygen/gas deterioration during occupied confined-space work.",
    "compound_handover": "Moderate drift overlaps hot work, impaired extraction, and a shift handover.",
    "barrier_loss_workers": "Loss of an extraction barrier exposes workers to a correlated gas trend.",
}


@dataclass(frozen=True)
class ScenarioBenchConfig:
    first_seed: int = 1000
    seed_count: int = 64
    duration_minutes: int = 48
    forecast_horizon_minutes: int = 12


def _ar_noise(rng: np.random.Generator, length: int, scale: float) -> np.ndarray:
    values = np.zeros(length, dtype=float)
    for index in range(1, length):
        values[index] = 0.68 * values[index - 1] + rng.normal(0.0, scale)
    return values


def _sigmoid_progress(minutes: np.ndarray, start: float, midpoint_after: float = 12.0) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(minutes - start - midpoint_after) / 4.0))


def _scenario_rng(seed: int, scenario_type: str) -> np.random.Generator:
    scenario_index = SCENARIO_TYPES.index(scenario_type)
    return np.random.default_rng(seed * 101 + scenario_index * 100_003)


def generate_scenario(
    seed: int,
    scenario_type: str,
    *,
    duration_minutes: int = 48,
    forecast_horizon_minutes: int = 12,
) -> pd.DataFrame:
    """Generate one deterministic grouped replay."""

    if scenario_type not in SCENARIO_TYPES:
        raise ValueError(f"Unknown scenario type: {scenario_type}")
    if duration_minutes < 24:
        raise ValueError("duration_minutes must be at least 24")
    if forecast_horizon_minutes < 1:
        raise ValueError("forecast_horizon_minutes must be positive")

    rng = _scenario_rng(seed, scenario_type)
    minute = np.arange(duration_minutes, dtype=float)
    start = float(rng.integers(6, 11))
    progress = _sigmoid_progress(minute, start)

    base = {
        "lel_ratio": 0.115 + rng.normal(0, 0.008),
        "h2s_ratio": 0.145 + rng.normal(0, 0.010),
        "co_ratio": 0.205 + rng.normal(0, 0.012),
        "oxygen_deficit_ratio": 0.075 + rng.normal(0, 0.006),
        "pressure_ratio": 0.535 + rng.normal(0, 0.010),
    }
    levels = {
        name: np.clip(value + _ar_noise(rng, duration_minutes, 0.010), 0.0, None)
        for name, value in base.items()
    }

    amplitudes: dict[str, float] = {name: 0.0 for name in base}
    if scenario_type == "process_drift":
        amplitudes.update(
            lel_ratio=1.02,
            h2s_ratio=0.90,
            co_ratio=0.78,
            oxygen_deficit_ratio=0.72,
            pressure_ratio=0.61,
        )
    elif scenario_type in {"subthreshold_process_drift", "compound_hot_work"}:
        amplitudes.update(
            lel_ratio=0.66,
            h2s_ratio=0.49,
            co_ratio=0.43,
            oxygen_deficit_ratio=0.31,
            pressure_ratio=0.29,
        )
    elif scenario_type == "compound_confined_space":
        amplitudes.update(
            lel_ratio=0.37,
            h2s_ratio=0.39,
            co_ratio=0.31,
            oxygen_deficit_ratio=0.73,
            pressure_ratio=0.18,
        )
    elif scenario_type == "compound_handover":
        amplitudes.update(
            lel_ratio=0.54,
            h2s_ratio=0.42,
            co_ratio=0.38,
            oxygen_deficit_ratio=0.27,
            pressure_ratio=0.31,
        )
    elif scenario_type == "barrier_loss_workers":
        amplitudes.update(
            lel_ratio=0.47,
            h2s_ratio=0.44,
            co_ratio=0.35,
            oxygen_deficit_ratio=0.29,
            pressure_ratio=0.21,
        )

    for name, amplitude in amplitudes.items():
        levels[name] = np.clip(levels[name] + amplitude * progress, 0.0, 1.45)

    if scenario_type == "isolated_sensor_spike":
        spike_center = int(rng.integers(25, 34))
        spike = 1.05 * np.exp(-0.5 * ((minute - spike_center) / 1.15) ** 2)
        channel = str(rng.choice(["lel_ratio", "h2s_ratio", "co_ratio"]))
        levels[channel] = np.clip(levels[channel] + spike, 0.0, 1.35)

    active_from = int(start + rng.integers(7, 11))
    workers_from = active_from + int(rng.integers(2, 5))
    hot_work_active = np.zeros(duration_minutes, dtype=float)
    confined_space_active = np.zeros(duration_minutes, dtype=float)
    workers_in_zone = np.zeros(duration_minutes, dtype=float)
    ventilation_impaired = np.zeros(duration_minutes, dtype=float)
    shift_handover = np.zeros(duration_minutes, dtype=float)
    permit_overlap_count = np.zeros(duration_minutes, dtype=float)
    isolation_active = np.zeros(duration_minutes, dtype=float)

    if scenario_type == "permit_only":
        hot_work_active[active_from:] = 1.0
        workers_in_zone[workers_from:] = 3.0
        permit_overlap_count[active_from:] = 1.0
    elif scenario_type == "compound_hot_work":
        ventilation_impaired[int(start) :] = 1.0
        isolation_active[int(start) :] = 1.0
        hot_work_active[active_from:] = 1.0
        workers_in_zone[workers_from:] = 4.0
        permit_overlap_count[active_from:] = 2.0
    elif scenario_type == "compound_confined_space":
        ventilation_impaired[int(start + 2) :] = 1.0
        confined_space_active[active_from:] = 1.0
        workers_in_zone[workers_from:] = 3.0
        permit_overlap_count[active_from:] = 1.0
    elif scenario_type == "compound_handover":
        ventilation_impaired[int(start) :] = 1.0
        isolation_active[int(start) :] = 1.0
        hot_work_active[active_from:] = 1.0
        workers_in_zone[workers_from:] = 3.0
        permit_overlap_count[active_from:] = 2.0
        handover_start = min(duration_minutes - 5, active_from + 4)
        shift_handover[handover_start : handover_start + 9] = 1.0
    elif scenario_type == "barrier_loss_workers":
        ventilation_impaired[int(start) :] = 1.0
        isolation_active[int(start) :] = 1.0
        workers_in_zone[workers_from:] = 4.0
        permit_overlap_count[active_from:] = 1.0

    min_worker_distance_m = np.full(duration_minutes, 120.0)
    worker_active = workers_in_zone > 0
    if worker_active.any():
        first_worker = int(np.flatnonzero(worker_active)[0])
        distance_progress = _sigmoid_progress(minute, first_worker, 4.0)
        min_worker_distance_m = 120.0 - 108.0 * distance_progress
        min_worker_distance_m[~worker_active] = 120.0

    stream_quality = np.clip(0.985 + _ar_noise(rng, duration_minutes, 0.004), 0.88, 1.0)
    if scenario_type == "isolated_sensor_spike":
        stream_quality = np.clip(stream_quality - 0.05 * (levels["lel_ratio"] > 0.95), 0.80, 1.0)

    slopes: dict[str, np.ndarray] = {}
    for name, series in levels.items():
        diff = pd.Series(series).diff().fillna(0.0).rolling(3, min_periods=1).mean()
        slope_name = "oxygen_slope" if name == "oxygen_deficit_ratio" else name.replace("_ratio", "_slope")
        slopes[slope_name] = diff.to_numpy(dtype=float)

    records: list[dict[str, float | int | str]] = []
    for index in range(duration_minutes):
        raw: dict[str, float] = {name: float(series[index]) for name, series in levels.items()}
        raw.update({name: float(series[index]) for name, series in slopes.items()})
        raw.update(
            {
                "ventilation_impaired": ventilation_impaired[index],
                "hot_work_active": hot_work_active[index],
                "confined_space_active": confined_space_active[index],
                "workers_in_zone": workers_in_zone[index],
                "min_worker_distance_m": min_worker_distance_m[index],
                "shift_handover": shift_handover[index],
                "permit_overlap_count": permit_overlap_count[index],
                "isolation_active": isolation_active[index],
                "stream_quality": stream_quality[index],
            }
        )
        enriched = enrich_feature_row(raw)
        records.append(
            {
                "scenario_id": f"{scenario_type}-{seed}",
                "scenario_type": scenario_type,
                "seed": seed,
                "minute": index,
                "data_classification": DATA_CLASSIFICATION,
                **enriched,
                "single_sensor_alarm": int(single_sensor_alarm(enriched)),
            }
        )

    frame = pd.DataFrame.from_records(records)
    worker_exposure = np.minimum(frame["workers_in_zone"] / 4.0, 1.0) * np.maximum(
        0.0, 1.0 - frame["min_worker_distance_m"] / 100.0
    )
    uncontrolled_process = 2.05 * np.maximum(0.0, frame["gas_burden"] - 0.72)
    hotwork_risk = (
        1.42
        * frame["hot_work_active"]
        * frame["ventilation_impaired"]
        * np.maximum(0.0, frame["gas_burden"] - 0.27)
    )
    confined_risk = (
        1.26
        * frame["confined_space_active"]
        * np.minimum(frame["workers_in_zone"], 1.0)
        * np.maximum(0.0, frame["oxygen_deficit_ratio"] - 0.27)
    )
    worker_risk = 1.80 * worker_exposure * frame["ventilation_impaired"] * np.maximum(
        0.0, frame["gas_burden"] - 0.24
    )
    handover_risk = (
        0.23
        * frame["shift_handover"]
        * frame["permit_overlap_count"]
        * np.maximum(0.0, frame["gas_burden"] - 0.22)
    )
    latent_risk = uncontrolled_process + hotwork_risk + confined_risk + worker_risk + handover_risk
    latent_risk += rng.normal(0.0, 0.018, duration_minutes)
    harmful_state = latent_risk >= 0.50

    event_indices = np.flatnonzero(harmful_state.to_numpy())
    event_minute = int(event_indices[0]) if len(event_indices) else -1
    target = np.zeros(duration_minutes, dtype=int)
    for index in range(duration_minutes):
        end = min(duration_minutes, index + forecast_horizon_minutes + 1)
        target[index] = int(bool(harmful_state.iloc[index:end].any()))

    frame["latent_risk"] = latent_risk.round(6)
    frame["harmful_state"] = harmful_state.astype(int)
    frame["risk_within_horizon"] = target
    frame["event_minute"] = event_minute
    return frame


def generate_benchmark(config: ScenarioBenchConfig = ScenarioBenchConfig()) -> pd.DataFrame:
    frames = [
        generate_scenario(
            seed,
            scenario_type,
            duration_minutes=config.duration_minutes,
            forecast_horizon_minutes=config.forecast_horizon_minutes,
        )
        for seed in range(config.first_seed, config.first_seed + config.seed_count)
        for scenario_type in SCENARIO_TYPES
    ]
    return pd.concat(frames, ignore_index=True)


def dataset_metadata(frame: pd.DataFrame, config: ScenarioBenchConfig) -> dict[str, object]:
    return {
        "name": DATASET_NAME,
        "version": DATASET_VERSION,
        "classification": DATA_CLASSIFICATION,
        "description": (
            "Deterministic simulated scenarios for evaluating compound-risk detection; "
            "not field validation and not evidence of production safety performance."
        ),
        "config": asdict(config),
        "rows": int(len(frame)),
        "scenario_groups": int(frame["scenario_id"].nunique()),
        "seeds": int(frame["seed"].nunique()),
        "scenario_types": list(SCENARIO_TYPES),
        "positive_rows": int(frame["risk_within_horizon"].sum()),
        "event_groups": int(
            frame.groupby("scenario_id", sort=False)["event_minute"].first().ge(0).sum()
        ),
        "features": list(FULL_FEATURES),
        "target": "risk_within_horizon",
        "forecast_horizon_minutes": config.forecast_horizon_minutes,
    }


def write_benchmark(
    output_dir: Path,
    config: ScenarioBenchConfig = ScenarioBenchConfig(),
) -> tuple[pd.DataFrame, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = generate_benchmark(config)
    csv_path = output_dir / "scenario_bench.csv"
    frame.to_csv(csv_path, index=False, float_format="%.8f")
    return frame, csv_path
