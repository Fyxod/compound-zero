"""Deterministic fusion of privacy-preserving CCTV metadata into model inputs."""

from __future__ import annotations

from collections import Counter
from statistics import fmean
from typing import Any

from .brief_schemas import ContextualRiskScoreRequest, VisionContextSummary

PEOPLE_EVENT_TYPES = {
    "occupancy",
    "restricted_zone_entry",
    "unsafe_proximity",
    "ppe_nonconformance",
    "worker_down",
}


def derive_vision_context(
    request: ContextualRiskScoreRequest,
) -> tuple[dict[str, Any], VisionContextSummary]:
    """Return model-ready inputs plus a transparent aggregation record.

    Counts are combined using a maximum, not a sum, because anonymous people
    detections can overlap across cameras. This avoids cross-camera identity
    tracking and limits double counting.
    """

    used = []
    for observation in request.observations:
        age_seconds = (request.evaluation_time - observation.observed_at).total_seconds()
        if (
            observation.zone_id == request.target_zone_id
            and 0 <= age_seconds <= request.max_observation_age_seconds
        ):
            used.append(observation)

    people_counts = [
        observation.entity_count
        for observation in used
        if observation.event_type in PEOPLE_EVENT_TYPES
    ]
    distances = [
        observation.min_hazard_distance_m
        for observation in used
        if observation.min_hazard_distance_m is not None
    ]
    confidences = [observation.confidence for observation in used]
    event_counts = Counter(observation.event_type for observation in used)

    raw = request.process.model_dump(exclude={"scenario_id", "data_classification"})
    max_observed_people = max(people_counts, default=0)
    min_observed_distance = min(distances, default=None)
    mean_confidence = fmean(confidences) if confidences else None

    raw["workers_in_zone"] = max(int(raw["workers_in_zone"]), max_observed_people)
    if min_observed_distance is not None:
        raw["min_worker_distance_m"] = min(
            float(raw["min_worker_distance_m"]), float(min_observed_distance)
        )
    if mean_confidence is not None:
        raw["stream_quality"] = min(float(raw["stream_quality"]), mean_confidence)

    summary = VisionContextSummary(
        data_classification="SIMULATED",
        target_zone_id=request.target_zone_id,
        observations_received=len(request.observations),
        observations_used=len(used),
        observations_discarded=len(request.observations) - len(used),
        max_observed_people=max_observed_people,
        min_observed_hazard_distance_m=(
            round(float(min_observed_distance), 3)
            if min_observed_distance is not None
            else None
        ),
        mean_confidence=round(float(mean_confidence), 6) if mean_confidence is not None else None,
        event_counts=dict(sorted(event_counts.items())),
        derived_model_inputs={
            "workers_in_zone": float(raw["workers_in_zone"]),
            "min_worker_distance_m": round(float(raw["min_worker_distance_m"]), 3),
            "stream_quality": round(float(raw["stream_quality"]), 6),
        },
        privacy_contract={
            "raw_frames_accepted": False,
            "biometrics_accepted": False,
            "identity_tracking_accepted": False,
            "accepted_payload": "event metadata only",
            "persistence": "none in this stateless prototype endpoint",
            "cross_camera_count_method": "maximum, not sum",
        },
        caveats=[
            "All observations in this prototype are SIMULATED metadata.",
            "Computer-vision confidence is treated as input quality, not proof of a condition.",
            "No person identity, biometric template, raw image, or video URI is accepted.",
        ],
    )
    return raw, summary
