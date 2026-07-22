import { AlertTriangle, ArrowRight, CalendarClock, MapPinned } from "lucide-react";
import { clsx } from "clsx";
import type { Permit, Severity } from "../types/domain";
import { PLANT_ZONES } from "../data/plant";

export function PermitMatrix({ permits, severity }: { permits: Permit[]; severity: Severity }) {
  return (
    <section className="panel permit-panel">
      <header className="panel-header">
        <div>
          <span className="eyebrow">SIMULTANEOUS OPERATIONS</span>
          <h2>Permit / barrier conflicts</h2>
        </div>
        <button type="button" className="text-button">Open SIMOPS matrix <ArrowRight size={14} /></button>
      </header>
      <div className="permit-grid">
        {permits.map((permit) => {
          const zone = PLANT_ZONES.find((item) => item.id === permit.zoneId);
          const conflict = permit.id === "PTW-2841" && severity !== "nominal" && permit.status !== "held";
          return (
            <article key={permit.id} className={clsx("permit-card", conflict && "has-conflict", permit.status === "held" && "is-held")}>
              <div className="permit-card__status">
                <span className="permit-card__type">{permit.type}</span>
                <span className={clsx("permit-state", `is-${permit.status}`)}>{permit.status}</span>
              </div>
              <strong>{permit.work}</strong>
              <div className="permit-card__meta">
                <span><MapPinned size={13} /> {zone?.shortName}</span>
                <span><CalendarClock size={13} /> {permit.startsAt}–{permit.expiresAt}</span>
                <span>{permit.workers} people</span>
              </div>
              {conflict && (
                <div className="permit-card__conflict">
                  <AlertTriangle size={15} />
                  Overlaps rising flammable-gas confidence contour
                </div>
              )}
              {permit.status === "held" && (
                <div className="permit-card__held">Held by operator · audit receipt written</div>
              )}
            </article>
          );
        })}
        <article className="barrier-card">
          <div className="barrier-card__topline">
            <span className="eyebrow">SAFETY BARRIER</span>
            <span className="barrier-health is-impaired">IMPAIRED</span>
          </div>
          <strong>Extraction fan EF-04</strong>
          <p>Mechanical isolation is valid, but its protection role was not visible to the permit system.</p>
          <div className="barrier-card__foot">
            <span>CMMS WO-44812</span>
            <span>Since 13:40</span>
          </div>
        </article>
      </div>
    </section>
  );
}

