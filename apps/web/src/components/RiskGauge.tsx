import { motion } from "motion/react";
import type { Severity } from "../types/domain";

const COLOR: Record<Severity, string> = {
  nominal: "#78e9c2",
  watch: "#f1d06f",
  elevated: "#ff9b54",
  critical: "#ff625f",
};

export function RiskGauge({
  score,
  severity,
  confidence,
  confidenceLabel = "model probability",
  size = 174,
}: {
  score: number;
  severity: Severity;
  confidence: number;
  confidenceLabel?: string;
  size?: number;
}) {
  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  return (
    <div className="risk-gauge" style={{ width: size, height: size }}>
      <svg viewBox="0 0 176 176" role="img" aria-label={`Risk score ${score} out of 100`}>
        <defs>
          <filter id="gauge-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <circle className="risk-gauge__track" cx="88" cy="88" r={radius} />
        <motion.circle
          className="risk-gauge__value"
          cx="88"
          cy="88"
          r={radius}
          initial={false}
          animate={{ strokeDashoffset: circumference - progress, stroke: COLOR[severity] }}
          transition={{ type: "spring", stiffness: 75, damping: 18 }}
          style={{ strokeDasharray: circumference, filter: "url(#gauge-glow)" }}
        />
        <circle className="risk-gauge__inner" cx="88" cy="88" r="53" />
      </svg>
      <div className="risk-gauge__copy">
        <motion.strong
          key={score}
          initial={{ opacity: 0.4, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {score}
        </motion.strong>
        <span>RISK INDEX</span>
        <small>{confidence.toFixed(0)}% {confidenceLabel}</small>
      </div>
    </div>
  );
}
