# ScenarioBench

ScenarioBench is deterministic **simulated data** created for the Compound Zero
prototype. It is not plant telemetry, field validation, or proof of production
safety performance.

Each scenario is a 48-minute grouped replay. The group key is the scenario type
plus random seed. Training, probability calibration, and final evaluation use
disjoint whole seeds, so no time window from one seed appears in multiple
partitions.

Regenerate the CSV, metadata, model, and evaluation artifacts from the repository
root:

```powershell
python -m ml.train
```

The target, `risk_within_horizon`, indicates whether the authored physical-risk
state becomes hazardous within the configured 12-minute forecast horizon.

