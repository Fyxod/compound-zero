"""Deterministic simulated geospatial evidence and evaluation.

This module intentionally implements bounded geometry only: site-local polygon
membership, Euclidean point distances, and a caller-supplied localization
uncertainty radius.  It is not a GIS connector, surveyed plant model,
dispersion calculation, plume model, or field-validation result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Sequence


DATA_CLASSIFICATION = "SIMULATED"
GEOSPATIAL_METHOD = "POLYGON_AND_DISTANCE_BOUNDS"
DEFAULT_BENCHMARK_SEED = 20_260_722
EPSILON = 1e-9

Point = tuple[float, float]
PolygonRelation = Literal["INSIDE", "OVERLAP", "OUTSIDE"]
ExposureClassification = Literal["EXPOSED", "POSSIBLE", "CLEAR"]


@dataclass(frozen=True, slots=True)
class PlantZone:
    """A fictional site-local polygon expressed in metres."""

    zone_id: str
    label: str
    polygon: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class HazardSource:
    """An authored review point and radius, not a physical dispersion model."""

    hazard_id: str
    zone_id: str
    label: str
    location: Point
    review_radius_m: float


@dataclass(frozen=True, slots=True)
class PlantLayout:
    """Validated fictional zones and their authored hazard review points."""

    layout_id: str
    zones: tuple[PlantZone, ...]
    hazards: tuple[HazardSource, ...]
    data_classification: str = DATA_CLASSIFICATION
    coordinate_system: str = "FICTIONAL_SITE_LOCAL_CARTESIAN_METRES"

    def __post_init__(self) -> None:
        if self.data_classification != DATA_CLASSIFICATION:
            raise ValueError("geospatial fixtures must be classified SIMULATED")
        zone_ids = [zone.zone_id for zone in self.zones]
        hazard_ids = [hazard.hazard_id for hazard in self.hazards]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("zone identifiers must be unique")
        if len(hazard_ids) != len(set(hazard_ids)):
            raise ValueError("hazard identifiers must be unique")
        if not self.zones or not self.hazards:
            raise ValueError("layout requires at least one zone and one hazard")
        for zone in self.zones:
            _validate_polygon(zone.polygon)
        zone_lookup = {zone.zone_id: zone for zone in self.zones}
        for hazard in self.hazards:
            if hazard.zone_id not in zone_lookup:
                raise ValueError(f"hazard {hazard.hazard_id} references an unknown zone")
            if not math.isfinite(hazard.review_radius_m) or hazard.review_radius_m <= 0:
                raise ValueError("hazard review radii must be positive and finite")
            if not point_in_polygon(hazard.location, zone_lookup[hazard.zone_id].polygon):
                raise ValueError(f"hazard {hazard.hazard_id} must lie inside its zone")


@dataclass(frozen=True, slots=True)
class HazardDistanceEvidence:
    hazard_id: str
    zone_id: str
    zone_relation: PolygonRelation
    nominal_distance_m: float
    distance_lower_bound_m: float
    distance_upper_bound_m: float
    review_radius_m: float
    classification: ExposureClassification


@dataclass(frozen=True, slots=True)
class ExposureAssessment:
    """Conservative assessment of one uncertain, anonymous position."""

    data_classification: str
    method: str
    classification: ExposureClassification
    review_required: bool
    observed_position: Point
    localization_uncertainty_m: float
    nominal_zone_ids: tuple[str, ...]
    possible_zone_ids: tuple[str, ...]
    certain_zone_ids: tuple[str, ...]
    nearest_hazard_id: str
    nearest_hazard_distance_m: float
    evidence: tuple[HazardDistanceEvidence, ...]
    boundary: str


@dataclass(frozen=True, slots=True)
class GeospatialBenchmarkCase:
    case_id: str
    actual_position: Point
    observed_position: Point
    localization_uncertainty_m: float
    source_kind: Literal["HAZARD_RING", "BACKGROUND_GRID"]


@dataclass(frozen=True, slots=True)
class GeospatialBenchmarkConfig:
    seed: int = DEFAULT_BENCHMARK_SEED
    angles_per_hazard: int = 12
    radial_offsets_m: tuple[float, ...] = (-3.0, -1.0, -0.25, 0.25, 1.0, 3.0)

    def __post_init__(self) -> None:
        if self.angles_per_hazard < 4:
            raise ValueError("angles_per_hazard must be at least four")
        if not self.radial_offsets_m:
            raise ValueError("radial_offsets_m cannot be empty")


def _validate_point(point: Point) -> None:
    if len(point) != 2 or not all(math.isfinite(value) for value in point):
        raise ValueError("points must contain two finite coordinates")


def _validate_polygon(polygon: Sequence[Point]) -> None:
    if len(polygon) < 3:
        raise ValueError("polygons require at least three vertices")
    for point in polygon:
        _validate_point(point)
    if len(set(polygon)) < 3:
        raise ValueError("polygons require at least three unique vertices")
    for index, point in enumerate(polygon):
        if point == polygon[(index + 1) % len(polygon)]:
            raise ValueError("polygons cannot contain repeated adjacent vertices")
    if abs(_signed_area(polygon)) <= EPSILON:
        raise ValueError("polygon area must be non-zero")
    edge_count = len(polygon)
    for first_index in range(edge_count):
        first_start = polygon[first_index]
        first_end = polygon[(first_index + 1) % edge_count]
        for second_index in range(first_index + 1, edge_count):
            if second_index in {first_index, (first_index + 1) % edge_count}:
                continue
            if first_index == 0 and second_index == edge_count - 1:
                continue
            second_start = polygon[second_index]
            second_end = polygon[(second_index + 1) % edge_count]
            if _segments_intersect(first_start, first_end, second_start, second_end):
                raise ValueError("self-intersecting polygons are unsupported")


def _signed_area(polygon: Sequence[Point]) -> float:
    area = 0.0
    for index, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(index + 1) % len(polygon)]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _orientation(first: Point, second: Point, third: Point) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def _segments_intersect(first_start: Point, first_end: Point, second_start: Point, second_end: Point) -> bool:
    first_left = _orientation(first_start, first_end, second_start)
    first_right = _orientation(first_start, first_end, second_end)
    second_left = _orientation(second_start, second_end, first_start)
    second_right = _orientation(second_start, second_end, first_end)
    if (first_left > EPSILON and first_right < -EPSILON) or (
        first_left < -EPSILON and first_right > EPSILON
    ):
        if (second_left > EPSILON and second_right < -EPSILON) or (
            second_left < -EPSILON and second_right > EPSILON
        ):
            return True
    return any(
        abs(orientation) <= EPSILON and _point_on_segment(point, start, end)
        for orientation, point, start, end in (
            (first_left, second_start, first_start, first_end),
            (first_right, second_end, first_start, first_end),
            (second_left, first_start, second_start, second_end),
            (second_right, first_end, second_start, second_end),
        )
    )


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    scale = max(1.0, abs(x2 - x1), abs(y2 - y1))
    if abs(cross) > EPSILON * scale:
        return False
    dot = (px - x1) * (px - x2) + (py - y1) * (py - y2)
    return dot <= EPSILON


def point_in_polygon(
    point: Point,
    polygon: Sequence[Point],
    *,
    include_boundary: bool = True,
) -> bool:
    """Return whether a point lies in a simple polygon using ray casting."""

    _validate_point(point)
    _validate_polygon(polygon)
    x, y = point
    inside = False
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(point, start, end):
            return include_boundary
        x1, y1 = start
        x2, y2 = end
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
    return inside


def point_distance(first: Point, second: Point) -> float:
    _validate_point(first)
    _validate_point(second)
    return math.hypot(first[0] - second[0], first[1] - second[1])


def point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    _validate_point(point)
    _validate_point(start)
    _validate_point(end)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= EPSILON:
        return point_distance(point, start)
    projection = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator
    projection = min(1.0, max(0.0, projection))
    closest = (start[0] + projection * dx, start[1] + projection * dy)
    return point_distance(point, closest)


def distance_to_polygon_boundary(point: Point, polygon: Sequence[Point]) -> float:
    _validate_point(point)
    _validate_polygon(polygon)
    return min(
        point_to_segment_distance(point, start, polygon[(index + 1) % len(polygon)])
        for index, start in enumerate(polygon)
    )


def distance_to_polygon(point: Point, polygon: Sequence[Point]) -> float:
    """Return zero inside/on the polygon, otherwise the nearest-edge distance."""

    if point_in_polygon(point, polygon):
        return 0.0
    return distance_to_polygon_boundary(point, polygon)


def uncertainty_relation_to_polygon(
    point: Point,
    localization_uncertainty_m: float,
    polygon: Sequence[Point],
) -> PolygonRelation:
    """Relate a circular bounded-error envelope to a polygon."""

    if not math.isfinite(localization_uncertainty_m) or localization_uncertainty_m < 0:
        raise ValueError("localization uncertainty must be finite and non-negative")
    boundary_distance = distance_to_polygon_boundary(point, polygon)
    if point_in_polygon(point, polygon):
        if localization_uncertainty_m <= boundary_distance + EPSILON:
            return "INSIDE"
        return "OVERLAP"
    if boundary_distance <= localization_uncertainty_m + EPSILON:
        return "OVERLAP"
    return "OUTSIDE"


def nearest_hazard_distance(
    point: Point,
    hazards: Sequence[HazardSource],
) -> tuple[HazardSource, float]:
    """Return the nearest authored hazard point and Euclidean distance."""

    if not hazards:
        raise ValueError("at least one hazard is required")
    ranked = sorted(
        ((point_distance(point, hazard.location), hazard.hazard_id, hazard) for hazard in hazards),
        key=lambda item: (item[0], item[1]),
    )
    distance, _, hazard = ranked[0]
    return hazard, distance


DEFAULT_LAYOUT = PlantLayout(
    layout_id="fictional-kalinga-west-block-v1",
    zones=(
        PlantZone(
            zone_id="ZONE-C7",
            label="West Gas Gallery",
            polygon=((0.0, 0.0), (68.0, 0.0), (68.0, 18.0), (60.0, 42.0), (0.0, 42.0)),
        ),
        PlantZone(
            zone_id="ZONE-C4",
            label="Coke Oven Battery 4",
            polygon=((75.0, 0.0), (116.0, 0.0), (116.0, 38.0), (75.0, 38.0)),
        ),
        PlantZone(
            zone_id="ZONE-M1",
            label="Maintenance Bay",
            polygon=((18.0, 50.0), (68.0, 50.0), (68.0, 78.0), (50.0, 88.0), (18.0, 80.0)),
        ),
        PlantZone(
            zone_id="ZONE-MUSTER-A",
            label="Muster Point Alpha",
            polygon=((80.0, 52.0), (116.0, 52.0), (116.0, 86.0), (80.0, 86.0)),
        ),
    ),
    hazards=(
        HazardSource(
            hazard_id="HZ-C7-PROCESS",
            zone_id="ZONE-C7",
            label="Authored process review point",
            location=(25.0, 18.0),
            review_radius_m=14.0,
        ),
        HazardSource(
            hazard_id="HZ-C7-EGRESS",
            zone_id="ZONE-C7",
            label="Authored egress review point",
            location=(61.0, 18.0),
            review_radius_m=9.0,
        ),
        HazardSource(
            hazard_id="HZ-C4-HOTWORK",
            zone_id="ZONE-C4",
            label="Authored hot-work review point",
            location=(94.0, 18.0),
            review_radius_m=11.0,
        ),
        HazardSource(
            hazard_id="HZ-M1-LIFT",
            zone_id="ZONE-M1",
            label="Authored lifting review point",
            location=(44.0, 67.0),
            review_radius_m=12.0,
        ),
    ),
)


def assess_exposure(
    observed_position: Point,
    localization_uncertainty_m: float,
    layout: PlantLayout = DEFAULT_LAYOUT,
) -> ExposureAssessment:
    """Classify exposure using bounded geometry and conservative review logic.

    ``EXPOSED`` means the entire declared uncertainty envelope remains within a
    hazard's zone and authored review radius. ``POSSIBLE`` means the envelope
    intersects both. ``CLEAR`` means no such intersection exists.
    """

    _validate_point(observed_position)
    if not math.isfinite(localization_uncertainty_m) or localization_uncertainty_m < 0:
        raise ValueError("localization uncertainty must be finite and non-negative")
    zone_lookup = {zone.zone_id: zone for zone in layout.zones}
    zone_relations = {
        zone.zone_id: uncertainty_relation_to_polygon(
            observed_position, localization_uncertainty_m, zone.polygon
        )
        for zone in layout.zones
    }
    nominal_zone_ids = tuple(
        zone.zone_id for zone in layout.zones if point_in_polygon(observed_position, zone.polygon)
    )
    possible_zone_ids = tuple(
        zone.zone_id for zone in layout.zones if zone_relations[zone.zone_id] != "OUTSIDE"
    )
    certain_zone_ids = tuple(
        zone.zone_id for zone in layout.zones if zone_relations[zone.zone_id] == "INSIDE"
    )

    evidence: list[HazardDistanceEvidence] = []
    for hazard in layout.hazards:
        nominal_distance = point_distance(observed_position, hazard.location)
        lower_bound = max(0.0, nominal_distance - localization_uncertainty_m)
        upper_bound = nominal_distance + localization_uncertainty_m
        relation = zone_relations[hazard.zone_id]
        if relation == "INSIDE" and upper_bound <= hazard.review_radius_m + EPSILON:
            classification: ExposureClassification = "EXPOSED"
        elif relation != "OUTSIDE" and lower_bound <= hazard.review_radius_m + EPSILON:
            classification = "POSSIBLE"
        else:
            classification = "CLEAR"
        evidence.append(
            HazardDistanceEvidence(
                hazard_id=hazard.hazard_id,
                zone_id=hazard.zone_id,
                zone_relation=relation,
                nominal_distance_m=round(nominal_distance, 6),
                distance_lower_bound_m=round(lower_bound, 6),
                distance_upper_bound_m=round(upper_bound, 6),
                review_radius_m=hazard.review_radius_m,
                classification=classification,
            )
        )

    rank = {"CLEAR": 0, "POSSIBLE": 1, "EXPOSED": 2}
    evidence.sort(
        key=lambda item: (
            -rank[item.classification],
            item.distance_lower_bound_m - item.review_radius_m,
            item.hazard_id,
        )
    )
    classification = evidence[0].classification
    nearest_hazard, nearest_distance = nearest_hazard_distance(observed_position, layout.hazards)
    return ExposureAssessment(
        data_classification=DATA_CLASSIFICATION,
        method=GEOSPATIAL_METHOD,
        classification=classification,
        review_required=classification != "CLEAR",
        observed_position=observed_position,
        localization_uncertainty_m=localization_uncertainty_m,
        nominal_zone_ids=nominal_zone_ids,
        possible_zone_ids=possible_zone_ids,
        certain_zone_ids=certain_zone_ids,
        nearest_hazard_id=nearest_hazard.hazard_id,
        nearest_hazard_distance_m=round(nearest_distance, 6),
        evidence=tuple(evidence),
        boundary=(
            "SIMULATED bounded-geometry evidence only. Review radii are authored analytic thresholds, "
            "not plume physics, surveyed safety boundaries, or field-validated localization confidence."
        ),
    )


def exact_exposure(position: Point, layout: PlantLayout = DEFAULT_LAYOUT) -> bool:
    """Ground-truth rule used only inside the deterministic benchmark."""

    zone_lookup = {zone.zone_id: zone for zone in layout.zones}
    return any(
        point_in_polygon(position, zone_lookup[hazard.zone_id].polygon)
        and point_distance(position, hazard.location) <= hazard.review_radius_m + EPSILON
        for hazard in layout.hazards
    )


def _hash_unit(seed: int, case_id: str, channel: str) -> float:
    digest = hashlib.sha256(f"{seed}:{case_id}:{channel}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def _observed_case(
    *,
    case_id: str,
    actual_position: Point,
    source_kind: Literal["HAZARD_RING", "BACKGROUND_GRID"],
    seed: int,
) -> GeospatialBenchmarkCase:
    error_magnitude = 0.15 + 2.65 * _hash_unit(seed, case_id, "magnitude")
    error_angle = 2.0 * math.pi * _hash_unit(seed, case_id, "angle")
    margin = 0.20 + 0.80 * _hash_unit(seed, case_id, "margin")
    observed = (
        round(actual_position[0] + error_magnitude * math.cos(error_angle), 6),
        round(actual_position[1] + error_magnitude * math.sin(error_angle), 6),
    )
    return GeospatialBenchmarkCase(
        case_id=case_id,
        actual_position=(round(actual_position[0], 6), round(actual_position[1], 6)),
        observed_position=observed,
        localization_uncertainty_m=round(error_magnitude + margin, 6),
        source_kind=source_kind,
    )


def generate_geospatial_benchmark(
    config: GeospatialBenchmarkConfig = GeospatialBenchmarkConfig(),
    layout: PlantLayout = DEFAULT_LAYOUT,
) -> tuple[GeospatialBenchmarkCase, ...]:
    """Generate deterministic boundary-heavy simulated position observations."""

    cases: list[GeospatialBenchmarkCase] = []
    for hazard in layout.hazards:
        for angle_index in range(config.angles_per_hazard):
            angle = 2.0 * math.pi * angle_index / config.angles_per_hazard
            for offset_index, offset in enumerate(config.radial_offsets_m):
                radius = hazard.review_radius_m + offset
                case_id = f"ring-{hazard.hazard_id}-{angle_index:02d}-{offset_index:02d}"
                actual = (
                    hazard.location[0] + radius * math.cos(angle),
                    hazard.location[1] + radius * math.sin(angle),
                )
                cases.append(
                    _observed_case(
                        case_id=case_id,
                        actual_position=actual,
                        source_kind="HAZARD_RING",
                        seed=config.seed,
                    )
                )

    background_points = tuple(
        (float(x), float(y))
        for y in (-6, 10, 30, 46, 58, 74, 92)
        for x in (-6, 10, 35, 70, 84, 108, 124)
    )
    for index, actual in enumerate(background_points):
        cases.append(
            _observed_case(
                case_id=f"grid-{index:03d}",
                actual_position=actual,
                source_kind="BACKGROUND_GRID",
                seed=config.seed,
            )
        )
    return tuple(cases)


def _confusion_metrics(truth: Sequence[bool], prediction: Sequence[bool]) -> dict[str, object]:
    tp = sum(actual and predicted for actual, predicted in zip(truth, prediction, strict=True))
    tn = sum(not actual and not predicted for actual, predicted in zip(truth, prediction, strict=True))
    fp = sum(not actual and predicted for actual, predicted in zip(truth, prediction, strict=True))
    fn = sum(actual and not predicted for actual, predicted in zip(truth, prediction, strict=True))
    positives = tp + fn
    negatives = tn + fp
    return {
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "recall": round(tp / positives, 6) if positives else 0.0,
        "false_negative_rate": round(fn / positives, 6) if positives else 0.0,
        "specificity": round(tn / negatives, 6) if negatives else 0.0,
        "false_positive_rate": round(fp / negatives, 6) if negatives else 0.0,
        "precision": round(tp / (tp + fp), 6) if tp + fp else 0.0,
        "accuracy": round((tp + tn) / len(truth), 6) if truth else 0.0,
    }


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _case_manifest_sha256(cases: Sequence[GeospatialBenchmarkCase]) -> str:
    canonical = json.dumps(
        [asdict(case) for case in cases],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _layout_manifest_sha256(layout: PlantLayout) -> str:
    canonical = json.dumps(
        asdict(layout),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def evaluate_geospatial_benchmark(
    cases: Sequence[GeospatialBenchmarkCase],
    *,
    config: GeospatialBenchmarkConfig = GeospatialBenchmarkConfig(),
    layout: PlantLayout = DEFAULT_LAYOUT,
) -> dict[str, object]:
    """Evaluate point-only and uncertainty-aware exposure classification."""

    truth: list[bool] = []
    point_predictions: list[bool] = []
    bounded_predictions: list[bool] = []
    assessments: list[ExposureAssessment] = []
    uncertainty_contains_truth: list[bool] = []
    distance_bounds_contain_truth: list[bool] = []
    nearest_distance_errors: list[float] = []

    hazard_lookup = {hazard.hazard_id: hazard for hazard in layout.hazards}
    for case in cases:
        actual = exact_exposure(case.actual_position, layout)
        point_assessment = assess_exposure(case.observed_position, 0.0, layout)
        bounded_assessment = assess_exposure(
            case.observed_position, case.localization_uncertainty_m, layout
        )
        truth.append(actual)
        point_predictions.append(point_assessment.classification == "EXPOSED")
        bounded_predictions.append(bounded_assessment.review_required)
        assessments.append(bounded_assessment)
        error = point_distance(case.actual_position, case.observed_position)
        uncertainty_contains_truth.append(error <= case.localization_uncertainty_m + 1e-6)

        nearest_hazard = hazard_lookup[bounded_assessment.nearest_hazard_id]
        true_distance = point_distance(case.actual_position, nearest_hazard.location)
        observed_distance = bounded_assessment.nearest_hazard_distance_m
        nearest_distance_errors.append(abs(true_distance - observed_distance))
        lower = max(0.0, observed_distance - case.localization_uncertainty_m)
        upper = observed_distance + case.localization_uncertainty_m
        distance_bounds_contain_truth.append(lower - 1e-6 <= true_distance <= upper + 1e-6)

    point_metrics = _confusion_metrics(truth, point_predictions)
    bounded_metrics = _confusion_metrics(truth, bounded_predictions)
    classifications = {
        label: sum(assessment.classification == label for assessment in assessments)
        for label in ("EXPOSED", "POSSIBLE", "CLEAR")
    }
    certain_indices = [
        index for index, assessment in enumerate(assessments) if assessment.classification == "EXPOSED"
    ]
    certain_true = sum(truth[index] for index in certain_indices)
    positive_count = sum(truth)
    negative_count = len(truth) - positive_count

    return {
        "schema_version": "compound-zero.geospatial-benchmark.v1",
        "benchmark_name": "GeoEvidenceBench",
        "benchmark_version": "1.0.0",
        "data_classification": DATA_CLASSIFICATION,
        "description": (
            "Deterministic simulated evaluation of polygon membership, nearest authored hazard distance, "
            "and bounded localization uncertainty for conservative exposure review."
        ),
        "metric_scope": (
            "Boundary-heavy authored software-conformance fixtures; case prevalence is not representative "
            "of a plant and metrics are not field geospatial accuracy."
        ),
        "configuration": {
            "seed": config.seed,
            "angles_per_hazard": config.angles_per_hazard,
            "radial_offsets_m": list(config.radial_offsets_m),
            "case_manifest_sha256": _case_manifest_sha256(cases),
        },
        "scope": {
            "method": GEOSPATIAL_METHOD,
            "coordinate_system": layout.coordinate_system,
            "layout_id": layout.layout_id,
            "layout_manifest_sha256": _layout_manifest_sha256(layout),
            "zone_count": len(layout.zones),
            "zone_ids": [zone.zone_id for zone in layout.zones],
            "hazard_count": len(layout.hazards),
            "hazard_ids": [hazard.hazard_id for hazard in layout.hazards],
            "uncertainty_semantics": "DECLARED_ISOTROPIC_ERROR_BOUND_METRES",
            "plume_physics_used": False,
            "surveyed_coordinates_used": False,
            "probabilistic_confidence_claimed": False,
        },
        "cases": {
            "total": len(cases),
            "positive": positive_count,
            "negative": negative_count,
            "hazard_ring": sum(case.source_kind == "HAZARD_RING" for case in cases),
            "background_grid": sum(case.source_kind == "BACKGROUND_GRID" for case in cases),
        },
        "methods": {
            "point_estimate_baseline": point_metrics,
            "uncertainty_aware_review": bounded_metrics,
        },
        "comparison": {
            "false_negative_rate_absolute_reduction": round(
                float(point_metrics["false_negative_rate"])
                - float(bounded_metrics["false_negative_rate"]),
                6,
            ),
            "recall_absolute_gain": round(
                float(bounded_metrics["recall"]) - float(point_metrics["recall"]),
                6,
            ),
            "false_positive_rate_absolute_increase": round(
                float(bounded_metrics["false_positive_rate"])
                - float(point_metrics["false_positive_rate"]),
                6,
            ),
            "interpretation": (
                "The bounded method routes uncertain boundary cases to human review: it removes misses in this "
                "authored stress set while increasing review load."
            ),
        },
        "classification_counts": classifications,
        "evidence_quality": {
            "declared_uncertainty_contains_true_position_rate": round(
                sum(uncertainty_contains_truth) / len(cases), 6
            ),
            "true_distance_within_reported_bounds_rate": round(
                sum(distance_bounds_contain_truth) / len(cases), 6
            ),
            "nearest_hazard_distance_mae_m": round(
                sum(nearest_distance_errors) / len(nearest_distance_errors), 6
            ),
            "nearest_hazard_distance_p95_absolute_error_m": round(
                _percentile(nearest_distance_errors, 0.95), 6
            ),
            "certain_exposure_precision": round(
                certain_true / len(certain_indices), 6
            )
            if certain_indices
            else 0.0,
            "possible_review_rate": round(classifications["POSSIBLE"] / len(cases), 6),
        },
        "limitations": [
            "All zones, hazard points, positions, errors, and labels are SIMULATED and fictional.",
            "Review radii are authored analytic thresholds, not gas dispersion, plume, fire, or blast models.",
            "The uncertainty radius is assumed to bound localization error; field systems require calibration and coverage testing.",
            "Results measure this deterministic geometry contract only and are not evidence of real-plant safety performance.",
        ],
    }


def build_geospatial_metrics(
    config: GeospatialBenchmarkConfig = GeospatialBenchmarkConfig(),
    layout: PlantLayout = DEFAULT_LAYOUT,
) -> dict[str, object]:
    cases = generate_geospatial_benchmark(config, layout)
    return evaluate_geospatial_benchmark(cases, config=config, layout=layout)


def write_geospatial_metrics(
    output_path: Path,
    config: GeospatialBenchmarkConfig = GeospatialBenchmarkConfig(),
    layout: PlantLayout = DEFAULT_LAYOUT,
) -> dict[str, object]:
    metrics = build_geospatial_metrics(config, layout)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/geospatial_metrics.json"),
        help="Path for the deterministic JSON metrics artifact.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_BENCHMARK_SEED)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    metrics = write_geospatial_metrics(
        args.output,
        GeospatialBenchmarkConfig(seed=args.seed),
    )
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
