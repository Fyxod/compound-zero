from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.geospatial_bench import (
    DATA_CLASSIFICATION,
    DEFAULT_LAYOUT,
    GeospatialBenchmarkConfig,
    assess_exposure,
    build_geospatial_metrics,
    distance_to_polygon,
    generate_geospatial_benchmark,
    nearest_hazard_distance,
    point_in_polygon,
    point_to_segment_distance,
    uncertainty_relation_to_polygon,
    write_geospatial_metrics,
)


SQUARE = ((0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0))
CONCAVE_L = ((0.0, 0.0), (6.0, 0.0), (6.0, 2.0), (2.0, 2.0), (2.0, 6.0), (0.0, 6.0))


def test_point_in_polygon_handles_inside_outside_edges_vertices_and_concavity() -> None:
    assert point_in_polygon((10.0, 10.0), SQUARE)
    assert not point_in_polygon((21.0, 10.0), SQUARE)
    assert point_in_polygon((0.0, 10.0), SQUARE)
    assert point_in_polygon((0.0, 0.0), SQUARE)
    assert not point_in_polygon((0.0, 10.0), SQUARE, include_boundary=False)
    assert point_in_polygon((1.0, 5.0), CONCAVE_L)
    assert not point_in_polygon((4.0, 4.0), CONCAVE_L)
    assert point_in_polygon((1.0, 5.0), tuple(reversed(CONCAVE_L)))


def test_invalid_polygons_fail_closed() -> None:
    with pytest.raises(ValueError):
        point_in_polygon((0.0, 0.0), ((0.0, 0.0), (1.0, 1.0)))
    with pytest.raises(ValueError):
        point_in_polygon(
            (0.0, 0.0),
            ((0.0, 0.0), (2.0, 0.0), (2.0, 0.0), (0.0, 2.0)),
        )
    with pytest.raises(ValueError):
        point_in_polygon(
            (1.0, 1.0),
            ((0.0, 0.0), (4.0, 4.0), (0.0, 4.0), (4.0, 0.0), (2.0, 5.0)),
        )
    with pytest.raises(ValueError):
        point_in_polygon((float("nan"), 0.0), SQUARE)


def test_polygon_and_hazard_distances_are_euclidean_and_deterministic() -> None:
    assert point_to_segment_distance((3.0, 4.0), (0.0, 0.0), (0.0, 10.0)) == 3.0
    assert distance_to_polygon((10.0, 10.0), SQUARE) == 0.0
    assert distance_to_polygon((23.0, 10.0), SQUARE) == 3.0
    hazard, distance = nearest_hazard_distance((28.0, 22.0), DEFAULT_LAYOUT.hazards)
    assert hazard.hazard_id == "HZ-C7-PROCESS"
    assert distance == 5.0


def test_uncertainty_envelope_distinguishes_certain_possible_and_clear() -> None:
    certain = assess_exposure((25.0, 18.0), 1.0)
    possible_distance = assess_exposure((39.5, 18.0), 1.0)
    possible_zone = assess_exposure((68.5, 18.0), 1.0)
    clear = assess_exposure((-10.0, -10.0), 1.0)

    assert certain.classification == "EXPOSED"
    assert possible_distance.classification == "POSSIBLE"
    assert possible_zone.classification == "POSSIBLE"
    assert clear.classification == "CLEAR"
    assert certain.data_classification == DATA_CLASSIFICATION
    assert "not plume physics" in certain.boundary
    assert not clear.review_required


def test_increasing_uncertainty_routes_boundary_cases_to_review() -> None:
    point = (39.5, 18.0)
    assert assess_exposure(point, 0.0).classification == "CLEAR"
    assert assess_exposure(point, 1.0).classification == "POSSIBLE"
    assert assess_exposure(point, 20.0).classification == "POSSIBLE"
    assert uncertainty_relation_to_polygon((-0.5, 20.0), 0.1, SQUARE) == "OUTSIDE"
    assert uncertainty_relation_to_polygon((-0.5, 20.0), 0.5, SQUARE) == "OVERLAP"
    with pytest.raises(ValueError):
        assess_exposure(point, -0.1)


def test_benchmark_is_reproducible_and_improves_missed_exposure_rate() -> None:
    config = GeospatialBenchmarkConfig()
    first_cases = generate_geospatial_benchmark(config)
    second_cases = generate_geospatial_benchmark(config)
    assert first_cases == second_cases

    metrics = build_geospatial_metrics(config)
    point_method = metrics["methods"]["point_estimate_baseline"]
    bounded_method = metrics["methods"]["uncertainty_aware_review"]
    assert metrics["data_classification"] == "SIMULATED"
    assert metrics["cases"]["total"] == 337
    assert point_method["false_negative_rate"] > 0
    assert bounded_method["false_negative_rate"] == 0
    assert bounded_method["recall"] == 1
    assert metrics["evidence_quality"]["certain_exposure_precision"] == 1
    assert metrics["scope"]["plume_physics_used"] is False
    assert metrics["scope"]["surveyed_coordinates_used"] is False


def test_checked_in_artifact_matches_generator_byte_for_byte(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    write_geospatial_metrics(first_path)
    write_geospatial_metrics(second_path)
    assert first_path.read_bytes() == second_path.read_bytes()

    checked_in = Path(__file__).resolve().parents[2] / "artifacts" / "geospatial_metrics.json"
    assert checked_in.read_bytes() == first_path.read_bytes()
    payload = json.loads(checked_in.read_text(encoding="utf-8"))
    assert "not field geospatial accuracy" in payload["metric_scope"]
    assert len(payload["configuration"]["case_manifest_sha256"]) == 64
    assert len(payload["scope"]["layout_manifest_sha256"]) == 64
