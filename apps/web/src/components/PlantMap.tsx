import { motion } from "motion/react";
import { Crosshair, Layers3, MapPin, Navigation, Wind } from "lucide-react";
import { clsx } from "clsx";
import { useMemo, useState } from "react";
import { HOTSPOT, PLANT_ZONES } from "../data/plant";
import type { Severity, SimulationSnapshot } from "../types/domain";
import { SeverityPill } from "./SeverityPill";

const ZONE_COLORS: Record<Severity, string> = {
  nominal: "#78e9c2",
  watch: "#f1d06f",
  elevated: "#ff9b54",
  critical: "#ff625f",
};

function pipePath(fromX: number, fromY: number, toX: number, toY: number) {
  const midpoint = (fromX + toX) / 2;
  return `M ${fromX} ${fromY} H ${midpoint} V ${toY} H ${toX}`;
}

export function PlantMap({ snapshot }: { snapshot: SimulationSnapshot }) {
  const [selectedZone, setSelectedZone] = useState("gas-gallery");
  const [showRiskField, setShowRiskField] = useState(true);
  const selectedRisk = snapshot.zoneRisks.find((risk) => risk.zoneId === selectedZone);
  const zoneLookup = useMemo(
    () => new Map(snapshot.zoneRisks.map((risk) => [risk.zoneId, risk])),
    [snapshot.zoneRisks],
  );
  const plumeIntensity = Math.max(0, (snapshot.score - 20) / 80);
  const hotWorkStatus = snapshot.permits.find((permit) => permit.type === "HOT WORK")?.status;

  return (
    <section className="panel plant-panel">
      <header className="panel-header plant-panel__header">
        <div>
          <span className="eyebrow">SIMULATED SPATIAL LAYOUT</span>
          <h2>Illustrative risk field / West process block</h2>
        </div>
        <div className="plant-panel__tools">
          <div className="map-legend">
            <span><i className="legend-dot is-nominal" /> Nominal</span>
            <span><i className="legend-dot is-elevated" /> Compound risk</span>
            <span><i className="legend-worker" /> Worker</span>
          </div>
          <button className="icon-button subtle" type="button" aria-label="Toggle illustrative risk field" aria-pressed={showRiskField} onClick={() => setShowRiskField((value) => !value)}>
            <Layers3 size={16} />
          </button>
          <button className="icon-button subtle" type="button" aria-label="Recenter on West Gas Gallery" onClick={() => setSelectedZone("gas-gallery")}>
            <Crosshair size={16} />
          </button>
        </div>
      </header>

      <div className="plant-canvas">
        <svg viewBox="0 0 900 590" role="img" aria-label="Interactive plant safety map">
          <defs>
            <pattern id="minor-grid" width="18" height="18" patternUnits="userSpaceOnUse">
              <path d="M 18 0 L 0 0 0 18" fill="none" stroke="#b8c8c2" strokeOpacity="0.045" strokeWidth="1" />
            </pattern>
            <pattern id="major-grid" width="90" height="90" patternUnits="userSpaceOnUse">
              <rect width="90" height="90" fill="url(#minor-grid)" />
              <path d="M 90 0 L 0 0 0 90" fill="none" stroke="#b8c8c2" strokeOpacity="0.07" strokeWidth="1" />
            </pattern>
            <radialGradient id="risk-plume" cx="45%" cy="50%" r="60%">
              <stop offset="0%" stopColor="#ff625f" stopOpacity={0.44 * plumeIntensity} />
              <stop offset="42%" stopColor="#ff8b4c" stopOpacity={0.23 * plumeIntensity} />
              <stop offset="100%" stopColor="#ff8b4c" stopOpacity="0" />
            </radialGradient>
            <filter id="map-glow" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation="8" />
            </filter>
            <filter id="worker-shadow" x="-100%" y="-100%" width="300%" height="300%">
              <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#000" floodOpacity="0.45" />
            </filter>
          </defs>

          <rect width="900" height="590" fill="url(#major-grid)" />
          <g className="map-boundary">
            <path d="M40 54 H850 V565 H40 Z" />
            <path d="M41 455 H850" />
          </g>

          <g className="pipe-network" aria-hidden="true">
            <path d={pipePath(310, 164, 365, 166)} />
            <path d={pipePath(575, 166, 630, 166)} />
            <path d={pipePath(192, 234, 192, 278)} />
            <path d={pipePath(310, 340, 370, 340)} />
            <path d={pipePath(575, 358, 633, 358)} />
            <circle cx="338" cy="166" r="4" />
            <circle cx="602" cy="166" r="4" />
            <circle cx="340" cy="340" r="4" />
          </g>

          {showRiskField && <motion.ellipse
            cx={HOTSPOT.x + 48}
            cy={HOTSPOT.y + 10}
            rx={70 + snapshot.score * 1.15}
            ry={40 + snapshot.score * 0.54}
            fill="url(#risk-plume)"
            animate={{
              opacity: plumeIntensity,
              scale: 1 + Math.sin(snapshot.tick / 3) * 0.025,
            }}
            transition={{ duration: 0.55 }}
            style={{ transformOrigin: `${HOTSPOT.x + 48}px ${HOTSPOT.y + 10}px` }}
          />}
          {showRiskField && snapshot.score >= 52 && (
            <motion.ellipse
              cx={HOTSPOT.x + 36}
              cy={HOTSPOT.y + 8}
              rx="75"
              ry="38"
              fill="none"
              stroke={ZONE_COLORS[snapshot.severity]}
              strokeWidth="1.3"
              strokeDasharray="5 7"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: [0.2, 0.8, 0.2], scale: [0.92, 1.24, 1.38] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeOut" }}
              style={{ transformOrigin: `${HOTSPOT.x + 36}px ${HOTSPOT.y + 8}px` }}
            />
          )}

          {PLANT_ZONES.map((zone) => {
            const risk = zoneLookup.get(zone.id);
            const severity = risk?.severity ?? "nominal";
            const color = ZONE_COLORS[severity];
            const active = zone.id === selectedZone;
            return (
              <g
                key={zone.id}
                className={clsx("plant-zone", active && "is-selected")}
                onClick={() => setSelectedZone(zone.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") setSelectedZone(zone.id);
                }}
                aria-label={`${zone.name}, risk ${risk?.score ?? 0}`}
              >
                <motion.rect
                  x={zone.x}
                  y={zone.y}
                  width={zone.width}
                  height={zone.height}
                  rx="8"
                  animate={{
                    stroke: active ? color : `${color}7A`,
                    fill: severity === "nominal" ? "#101817" : `${color}12`,
                  }}
                />
                {active && (
                  <rect
                    x={zone.x - 5}
                    y={zone.y - 5}
                    width={zone.width + 10}
                    height={zone.height + 10}
                    rx="12"
                    className="plant-zone__selection"
                  />
                )}
                <text x={zone.x + 14} y={zone.y + 23} className="plant-zone__code">{zone.shortName}</text>
                <text x={zone.x + 14} y={zone.y + 45} className="plant-zone__name">{zone.name}</text>
                <g transform={`translate(${zone.x + 14} ${zone.y + zone.height - 25})`}>
                  <circle r="3.5" fill={color} />
                  <text x="10" y="4" className="plant-zone__risk">RISK {risk?.score ?? 0}</text>
                </g>
                {zone.sensorIds.slice(0, 4).map((sensorId, index) => (
                  <g
                    key={sensorId}
                    className="sensor-node"
                    transform={`translate(${zone.x + zone.width - 19 - index * 17} ${zone.y + zone.height - 20})`}
                  >
                    <circle r="5" />
                    <circle r="2" />
                  </g>
                ))}
              </g>
            );
          })}

          <g className="wind-indicator" transform="translate(724 63)">
            <Wind size={16} />
            <text x="24" y="7">SIM WIND · WNW · 2.4 m/s</text>
            <path d="M 24 20 H 94" />
            <path d="M 84 14 L 95 20 84 26" />
          </g>

          <g className={clsx("hot-work-marker", `is-${hotWorkStatus ?? "planned"}`)} transform={`translate(${HOTSPOT.x} ${HOTSPOT.y})`}>
            {hotWorkStatus === "active" && <motion.circle
              r="20"
              fill="none"
              stroke="#ff9b54"
              animate={{ r: [15, 24, 15], opacity: [0.8, 0.08, 0.8] }}
              transition={{ duration: 2.2, repeat: Infinity }}
            />}
            <circle r="11" />
            <path d="M-4 4 L0 -5 L4 4 M-6 6 H6" />
            <text x="18" y="4">HOT WORK · {hotWorkStatus === "active" ? "ACTIVE" : "PLANNED"}</text>
          </g>

          {snapshot.workers.map((worker) => (
            <motion.g
              key={worker.id}
              className={clsx("worker-marker", `is-${worker.status}`)}
              animate={{ x: worker.x, y: worker.y }}
              transition={{ type: "spring", stiffness: 68, damping: 18 }}
              filter="url(#worker-shadow)"
            >
              {worker.status === "exposed" && (
                <motion.circle
                  r="15"
                  fill="none"
                  stroke="#ff625f"
                  animate={{ r: [11, 19], opacity: [0.8, 0] }}
                  transition={{ duration: 1.6, repeat: Infinity }}
                />
              )}
              <circle r="10" />
              <text y="3.5" textAnchor="middle">{worker.label}</text>
            </motion.g>
          ))}
        </svg>

        <div className="map-coordinates">
          <Navigation size={13} /> LOCAL DEMO GRID · PLAN COORDINATES
        </div>
        <div className="map-selection-card">
          <div className="map-selection-card__pin"><MapPin size={15} /></div>
          <div>
            <span className="eyebrow">SELECTED ZONE</span>
            <strong>{PLANT_ZONES.find((zone) => zone.id === selectedZone)?.name}</strong>
          </div>
          {selectedRisk && <SeverityPill severity={selectedRisk.severity} label={`${selectedRisk.score} / 100`} />}
        </div>
        <div className="simulated-badge">SIMULATED REPLAY</div>
      </div>
    </section>
  );
}
