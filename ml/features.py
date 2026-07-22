"""Feature contracts shared by training and online inference.

All safety decisions use these numeric features and the persisted scikit-learn
model. No language model participates in the risk path.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

SENSOR_LEVEL_FEATURES = [
    "lel_ratio",
    "h2s_ratio",
    "co_ratio",
    "oxygen_deficit_ratio",
    "pressure_ratio",
]

SENSOR_TREND_FEATURES = [
    "lel_slope",
    "h2s_slope",
    "co_slope",
    "oxygen_slope",
    "pressure_slope",
]

DERIVED_PROCESS_FEATURES = [
    "gas_burden",
    "max_sensor_ratio",
    "mean_positive_slope",
    "correlated_rise",
]

CONTEXT_FEATURES = [
    "ventilation_impaired",
    "hot_work_active",
    "confined_space_active",
    "workers_in_zone",
    "min_worker_distance_m",
    "shift_handover",
    "permit_overlap_count",
    "isolation_active",
    "stream_quality",
]

INTERACTION_FEATURES = [
    "hotwork_gas_interaction",
    "worker_gas_interaction",
    "confined_oxygen_interaction",
    "barrier_gas_interaction",
    "handover_permit_interaction",
]

PROCESS_FEATURES = SENSOR_LEVEL_FEATURES + SENSOR_TREND_FEATURES + DERIVED_PROCESS_FEATURES
FULL_FEATURES = PROCESS_FEATURES + CONTEXT_FEATURES + INTERACTION_FEATURES


def enrich_feature_row(row: Mapping[str, Any]) -> dict[str, float]:
    """Return a complete numeric feature row from raw levels, trends, and context.

    Ratios are relative to site-configured device thresholds. This keeps the
    model independent of any particular regulatory limit or sensor unit.
    """

    values = {name: float(row.get(name, 0.0)) for name in SENSOR_LEVEL_FEATURES}
    values.update({name: float(row.get(name, 0.0)) for name in SENSOR_TREND_FEATURES})

    gas_burden = (
        0.32 * values["lel_ratio"]
        + 0.22 * values["h2s_ratio"]
        + 0.18 * values["co_ratio"]
        + 0.16 * values["oxygen_deficit_ratio"]
        + 0.12 * values["pressure_ratio"]
    )
    positive_slopes = np.clip(
        np.asarray(
            [
                values["lel_slope"],
                values["h2s_slope"],
                values["co_slope"],
                values["oxygen_slope"],
                values["pressure_slope"],
            ],
            dtype=float,
        ),
        0.0,
        None,
    )
    correlated_rise = float(np.mean(positive_slopes > 0.008) * np.mean(positive_slopes))

    values.update(
        {
            "gas_burden": float(gas_burden),
            "max_sensor_ratio": float(max(values[name] for name in SENSOR_LEVEL_FEATURES)),
            "mean_positive_slope": float(np.mean(positive_slopes)),
            "correlated_rise": correlated_rise,
        }
    )

    context_defaults = {
        "ventilation_impaired": 0.0,
        "hot_work_active": 0.0,
        "confined_space_active": 0.0,
        "workers_in_zone": 0.0,
        "min_worker_distance_m": 120.0,
        "shift_handover": 0.0,
        "permit_overlap_count": 0.0,
        "isolation_active": 0.0,
        "stream_quality": 1.0,
    }
    for name, default in context_defaults.items():
        values[name] = float(row.get(name, default))

    worker_exposure = min(values["workers_in_zone"] / 4.0, 1.5) * max(
        0.0, 1.0 - values["min_worker_distance_m"] / 100.0
    )
    values.update(
        {
            "hotwork_gas_interaction": values["hot_work_active"]
            * values["gas_burden"],
            "worker_gas_interaction": worker_exposure * values["gas_burden"],
            "confined_oxygen_interaction": values["confined_space_active"]
            * values["oxygen_deficit_ratio"]
            * min(values["workers_in_zone"], 1.0),
            "barrier_gas_interaction": values["ventilation_impaired"]
            * values["gas_burden"],
            "handover_permit_interaction": values["shift_handover"]
            * values["permit_overlap_count"],
        }
    )
    return {name: float(values[name]) for name in FULL_FEATURES}


def single_sensor_alarm(row: Mapping[str, Any]) -> bool:
    """Legacy baseline: any one site-configured device threshold is crossed."""

    return any(float(row.get(name, 0.0)) >= 1.0 for name in SENSOR_LEVEL_FEATURES)

