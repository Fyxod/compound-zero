import { useCallback, useEffect, useMemo, useState } from "react";
import { PRIMARY_SCENARIO } from "../data/plant";
import { fetchModelReplay } from "../lib/api";
import { buildSnapshot } from "../lib/simulation";
import type { EngineState, ModelReplayResponse } from "../types/api";
import type { InterventionId, SimulationSnapshot } from "../types/domain";

const START_TICK = 8;

export interface SimulationController {
  snapshot: SimulationSnapshot;
  history: SimulationSnapshot[];
  running: boolean;
  speed: 1 | 2 | 4;
  completedControls: Set<InterventionId>;
  engine: {
    state: EngineState;
    modelVersion: string;
    detail: string;
  };
  toggle: () => void;
  reset: () => void;
  setSpeed: (speed: 1 | 2 | 4) => void;
  scrub: (tick: number) => void;
  execute: (id: InterventionId) => void;
}

export function useSimulation(): SimulationController {
  const [tick, setTick] = useState(START_TICK);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState<1 | 2 | 4>(2);
  const [completedControls, setCompletedControls] = useState<Set<InterventionId>>(
    new Set(),
  );
  const [modelReplay, setModelReplay] = useState<ModelReplayResponse | null>(null);
  const [engineState, setEngineState] = useState<EngineState>("connecting");

  useEffect(() => {
    const controller = new AbortController();
    fetchModelReplay(controller.signal)
      .then((replay) => {
        setModelReplay(replay);
        setEngineState("model-api");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setEngineState("ux-fallback");
      });
    return () => controller.abort();
  }, []);

  const snapshot = useMemo(
    () =>
      buildSnapshot(
        tick,
        completedControls,
        modelReplay?.snapshots[tick],
        modelReplay?.model_version,
        modelReplay?.decision_threshold,
      ),
    [tick, completedControls, modelReplay],
  );
  const history = useMemo(
    () =>
      Array.from({ length: tick + 1 }, (_, index) =>
        buildSnapshot(
          index,
          index === tick ? completedControls : [],
          modelReplay?.snapshots[index],
          modelReplay?.model_version,
          modelReplay?.decision_threshold,
        ),
      ),
    [tick, completedControls, modelReplay],
  );

  useEffect(() => {
    if (!running) return undefined;
    const timer = window.setInterval(() => {
      setTick((current) => {
        if (current >= PRIMARY_SCENARIO.durationMinutes) {
          setRunning(false);
          return current;
        }
        return current + 1;
      });
    }, 1000 / speed);
    return () => window.clearInterval(timer);
  }, [running, speed]);

  const toggle = useCallback(() => setRunning((value) => !value), []);
  const reset = useCallback(() => {
    setRunning(false);
    setTick(START_TICK);
    setCompletedControls(new Set());
  }, []);
  const scrub = useCallback((value: number) => {
    setRunning(false);
    setTick(Math.round(value));
  }, []);
  const execute = useCallback((id: InterventionId) => {
    setCompletedControls((current) => new Set([...current, id]));
  }, []);

  return {
    snapshot,
    history,
    running,
    speed,
    completedControls,
    engine: {
      state: engineState,
      modelVersion: modelReplay?.model_version ?? "ux-fixture-v1",
      detail:
        engineState === "model-api"
          ? "Calibrated ScenarioBench replay from FastAPI"
          : engineState === "connecting"
            ? "Connecting to the local risk service"
            : "Explicit UX fallback; start FastAPI for model inference",
    },
    toggle,
    reset,
    setSpeed,
    scrub,
    execute,
  };
}
