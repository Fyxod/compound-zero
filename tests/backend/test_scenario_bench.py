from __future__ import annotations

import pandas as pd

from ml.scenario_bench import DATA_CLASSIFICATION, generate_scenario


def test_scenario_generation_is_seed_deterministic() -> None:
    first = generate_scenario(24001, "compound_hot_work")
    second = generate_scenario(24001, "compound_hot_work")
    pd.testing.assert_frame_equal(first, second, check_exact=True)

    different = generate_scenario(24002, "compound_hot_work")
    assert not first.equals(different)


def test_compound_event_precedes_any_individual_device_alarm() -> None:
    frame = generate_scenario(24001, "compound_hot_work")
    assert frame["data_classification"].eq(DATA_CLASSIFICATION).all()
    assert int(frame["event_minute"].iloc[0]) >= 0
    assert not frame["single_sensor_alarm"].any()
    assert frame["risk_within_horizon"].any()


def test_isolated_device_spike_is_not_authored_as_compound_harm() -> None:
    frame = generate_scenario(24001, "isolated_sensor_spike")
    assert frame["single_sensor_alarm"].any()
    assert int(frame["event_minute"].iloc[0]) == -1
    assert not frame["risk_within_horizon"].any()

