import type { ReactNode } from "react";
import { clsx } from "clsx";

export function MetricCard({
  label,
  value,
  suffix,
  meta,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  suffix?: string;
  meta: ReactNode;
  icon: ReactNode;
  tone?: "neutral" | "safe" | "warning" | "critical";
}) {
  return (
    <article className={clsx("metric-card", `tone-${tone}`)}>
      <div className="metric-card__topline">
        <span>{label}</span>
        <span className="metric-card__icon">{icon}</span>
      </div>
      <div className="metric-card__value">
        <strong>{value}</strong>
        {suffix && <span>{suffix}</span>}
      </div>
      <div className="metric-card__meta">{meta}</div>
    </article>
  );
}

