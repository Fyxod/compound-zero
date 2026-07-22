import { useMemo } from "react";
import { EVIDENCE_EDGES, EVIDENCE_NODES } from "../data/plant";
import { clsx } from "clsx";

function pathBetween(
  from: (typeof EVIDENCE_NODES)[number],
  to: (typeof EVIDENCE_NODES)[number],
) {
  const control = (from.x + to.x) / 2;
  return `M ${from.x} ${from.y} C ${control} ${from.y}, ${control} ${to.y}, ${to.x} ${to.y}`;
}

export function EvidenceGraph() {
  const nodeMap = useMemo(() => new Map(EVIDENCE_NODES.map((node) => [node.id, node])), []);
  return (
    <div className="evidence-graph-wrap">
      <svg viewBox="0 0 910 308" role="img" aria-label="Compound risk evidence graph">
        <defs>
          <marker id="edge-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 z" fill="#64766f" />
          </marker>
          <filter id="node-glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="5" result="coloredBlur" />
            <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {EVIDENCE_EDGES.map((edge) => {
          const from = nodeMap.get(edge.from)!;
          const to = nodeMap.get(edge.to)!;
          const midpointX = (from.x + to.x) / 2;
          const midpointY = (from.y + to.y) / 2;
          return (
            <g key={`${edge.from}-${edge.to}`} className={clsx("evidence-edge", edge.active && "is-active")}>
              <path d={pathBetween(from, to)} markerEnd="url(#edge-arrow)" />
              <rect x={midpointX - 34} y={midpointY - 8} width="68" height="15" rx="7" />
              <text x={midpointX} y={midpointY + 3} textAnchor="middle">{edge.label}</text>
            </g>
          );
        })}
        {EVIDENCE_NODES.map((node) => {
          const lines = node.label.split("\n");
          return (
            <g key={node.id} className={clsx("evidence-node", `is-${node.type}`)} transform={`translate(${node.x} ${node.y})`}>
              {node.type === "risk" && <circle r="53" className="evidence-node__halo" filter="url(#node-glow)" />}
              <rect x="-63" y="-31" width="126" height="62" rx="10" />
              <circle cx="-48" cy="-16" r="4" />
              {lines.map((line, index) => (
                <text key={line} x="0" y={index * 15 - (lines.length - 1) * 7 + 4} textAnchor="middle">{line}</text>
              ))}
            </g>
          );
        })}
      </svg>
      <div className="graph-lane-labels" aria-hidden="true">
        <span>OBSERVE</span><span>CONTEXTUALIZE</span><span>INFER</span><span>CONTROL</span>
      </div>
    </div>
  );
}
