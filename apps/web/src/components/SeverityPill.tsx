import { clsx } from "clsx";
import type { Severity } from "../types/domain";

const LABELS: Record<Severity, string> = {
  nominal: "Nominal",
  watch: "Watch",
  elevated: "Elevated",
  critical: "Critical",
};

export function SeverityPill({
  severity,
  label,
  pulse = false,
}: {
  severity: Severity;
  label?: string;
  pulse?: boolean;
}) {
  return (
    <span className={clsx("severity-pill", `is-${severity}`, pulse && "is-pulsing")}>
      <span className="severity-pill__dot" aria-hidden="true" />
      {label ?? LABELS[severity]}
    </span>
  );
}

