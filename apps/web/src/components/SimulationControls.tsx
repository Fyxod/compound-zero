import { Pause, Play, RotateCcw, Sparkles } from "lucide-react";
import { clsx } from "clsx";
import type { CSSProperties } from "react";
import { PRIMARY_SCENARIO } from "../data/plant";
import type { SimulationController } from "../hooks/useSimulation";

export function SimulationControls({
  tick,
  running,
  speed,
  onToggle,
  onReset,
  onSpeed,
  onScrub,
  engine,
}: {
  tick: number;
  running: boolean;
  speed: 1 | 2 | 4;
  onToggle: () => void;
  onReset: () => void;
  onSpeed: (speed: 1 | 2 | 4) => void;
  onScrub: (tick: number) => void;
  engine: SimulationController["engine"];
}) {
  return (
    <section className="replay-control" aria-label="Incident replay controls">
      <div className="replay-control__scenario">
        <span className="replay-control__icon"><Sparkles size={16} /></span>
        <div>
          <span className="eyebrow">
            SIMULATED REPLAY · SEED 24001 · {engine.state === "model-api" ? "CALIBRATED MODEL API" : engine.state === "connecting" ? "CONNECTING" : "UX FALLBACK"}
          </span>
          <strong>{PRIMARY_SCENARIO.name}</strong>
        </div>
      </div>
      <div className="replay-control__transport">
        <button className="transport-button" type="button" onClick={onToggle}>
          {running ? <Pause size={16} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
          {running ? "Pause replay" : "Run incident"}
        </button>
        <button className="icon-button subtle" type="button" onClick={onReset} aria-label="Reset replay">
          <RotateCcw size={16} />
        </button>
      </div>
      <div className="replay-control__timeline">
        <span>T+{tick.toString().padStart(2, "0")}m</span>
        <input
          type="range"
          min="0"
          max={PRIMARY_SCENARIO.durationMinutes}
          value={tick}
          onChange={(event) => onScrub(Number(event.currentTarget.value))}
          aria-label="Replay minute"
          style={{ "--replay-progress": `${(tick / PRIMARY_SCENARIO.durationMinutes) * 100}%` } as CSSProperties}
        />
        <span>T+{PRIMARY_SCENARIO.durationMinutes}m</span>
      </div>
      <div className="speed-control" aria-label="Replay speed">
        {([1, 2, 4] as const).map((option) => (
          <button
            key={option}
            type="button"
            className={clsx(speed === option && "is-active")}
            onClick={() => onSpeed(option)}
          >
            {option}×
          </button>
        ))}
      </div>
    </section>
  );
}
