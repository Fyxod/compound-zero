import { ArrowDown, ArrowUp, CircleGauge, Radio } from "lucide-react";
import { clsx } from "clsx";
import type { SensorReading } from "../types/domain";

function progress(sensor: SensorReading) {
  return sensor.direction === "above"
    ? Math.min(100, (sensor.value / sensor.alarmAt) * 100)
    : Math.min(100, (sensor.alarmAt / sensor.value) * 100);
}

export function TelemetryPanel({ sensors }: { sensors: SensorReading[] }) {
  return (
    <section className="panel telemetry-panel">
      <header className="panel-header">
        <div>
          <span className="eyebrow">SCADA / 1 HZ</span>
          <h2>Signals remain below alarm</h2>
        </div>
        <span className="live-label"><Radio size={13} /> LIVE</span>
      </header>
      <div className="telemetry-list">
        {sensors.slice(0, 4).map((sensor) => {
          const rising = sensor.trend > 0;
          return (
            <div className="telemetry-row" key={sensor.id}>
              <div className="telemetry-row__icon"><CircleGauge size={16} /></div>
              <div className="telemetry-row__copy">
                <div>
                  <strong>{sensor.label}</strong>
                  <span>{sensor.id.toUpperCase()}</span>
                </div>
                <div className="telemetry-row__bar">
                  <span
                    className={clsx(`is-${sensor.status}`)}
                    style={{ width: `${progress(sensor)}%` }}
                  />
                  <i style={{ left: "100%" }} />
                </div>
              </div>
              <div className="telemetry-row__value">
                <strong>{sensor.value}<small>{sensor.unit}</small></strong>
                <span className={clsx(rising ? "is-rising" : "is-falling")}>
                  {rising ? <ArrowUp size={11} /> : <ArrowDown size={11} />}
                  {Math.abs(sensor.trend).toFixed(2)} / min
                </span>
              </div>
              <div className="telemetry-row__limit">
                <span>ALARM</span>
                <strong>{sensor.direction === "below" ? "<" : ">"}{sensor.alarmAt}</strong>
              </div>
            </div>
          );
        })}
      </div>
      <footer className="telemetry-panel__footer">
        <span><i className="status-led is-online" /> Quality checks passed</span>
        <span>Last packet 0.8s ago</span>
      </footer>
    </section>
  );
}

