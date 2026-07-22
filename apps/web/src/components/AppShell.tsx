import {
  Activity,
  Bell,
  Boxes,
  ChevronDown,
  ClipboardCheck,
  GitBranch,
  LayoutDashboard,
  Menu,
  Radar,
  Search,
  ShieldCheck,
  TestTubeDiagonal,
  Wifi,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { useState, type ReactNode } from "react";
import { BrandMark } from "./BrandMark";
import type { SimulationController } from "../hooks/useSimulation";
import type { AppView } from "../types/domain";

const NAV_ITEMS: Array<{
  id: AppView;
  label: string;
  eyebrow: string;
  icon: typeof LayoutDashboard;
}> = [
  { id: "command", label: "Replay twin", eyebrow: "Operate", icon: LayoutDashboard },
  { id: "evidence", label: "Why now?", eyebrow: "Explain", icon: GitBranch },
  { id: "intelligence", label: "Intelligence", eyebrow: "Correlate", icon: Radar },
  { id: "validation", label: "Model evidence", eyebrow: "Prove", icon: TestTubeDiagonal },
  { id: "safety-case", label: "Safety case", eyebrow: "Audit", icon: ClipboardCheck },
];

export function AppShell({
  view,
  onViewChange,
  engine,
  children,
}: {
  view: AppView;
  onViewChange: (view: AppView) => void;
  engine: SimulationController["engine"];
  children: ReactNode;
}) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const navigate = (nextView: AppView) => {
    onViewChange(nextView);
    setMobileNavOpen(false);
  };

  return (
    <div className="app-shell">
      {mobileNavOpen && <button type="button" className="mobile-nav-backdrop" aria-label="Close menu" onClick={() => setMobileNavOpen(false)} />}
      <aside className={clsx("sidebar", mobileNavOpen && "is-mobile-open")}>
        <div className="sidebar__brand">
          <BrandMark />
          <button type="button" className="icon-button mobile-nav-close" aria-label="Close menu" onClick={() => setMobileNavOpen(false)}><X size={17} /></button>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                className={clsx("nav-item", view === item.id && "is-active")}
                onClick={() => navigate(item.id)}
                aria-current={view === item.id ? "page" : undefined}
              >
                <span className="nav-item__icon"><Icon size={18} strokeWidth={1.8} /></span>
                <span className="nav-item__copy">
                  <span className="nav-item__eyebrow">{item.eyebrow}</span>
                  <span className="nav-item__label">{item.label}</span>
                </span>
                <span className="nav-item__rail" />
              </button>
            );
          })}
        </nav>

        <div className="sidebar__spacer" />

        <div className="edge-status">
          <div className="edge-status__topline">
            <span className="eyebrow">EDGE RUNTIME</span>
            <span className={`status-led ${engine.state === "model-api" ? "is-online" : "is-watch"}`} />
          </div>
          <div className="edge-status__title"><Boxes size={16} /> CZ-EDGE-04</div>
          <div className="edge-status__meta">
            <span>SB v1.0</span>
            <span>{engine.state === "model-api" ? "API" : engine.state === "connecting" ? "CONNECT" : "FALLBACK"}</span>
          </div>
          <div className="edge-status__bar"><span style={{ width: "71%" }} /></div>
          <div className="edge-status__caption">{engine.detail}</div>
        </div>

        <button type="button" className="operator-card" disabled title="Simulated operator profile">
          <div className="operator-card__avatar">AS</div>
          <div className="operator-card__copy">
            <strong>Arjun Sen</strong>
            <span>Shift safety officer</span>
          </div>
          <ChevronDown size={15} />
        </button>
      </aside>

      <div className="app-stage">
        <header className="topbar">
          <div className="topbar__left">
            <button className="icon-button mobile-menu" type="button" aria-label="Open menu" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen(true)}>
              <Menu size={18} />
            </button>
            <button type="button" className="plant-selector" disabled title="Single simulated site">
              <span className="plant-selector__glyph"><Activity size={17} /></span>
              <span className="plant-selector__copy">
                <span>Kalinga Works</span>
                <strong>Coke &amp; by-product unit</strong>
              </span>
              <ChevronDown size={15} />
            </button>
            <div className="stream-health">
              <Wifi size={14} />
              <span>23 simulated streams healthy</span>
              <span className="stream-health__latency">0.8s lag</span>
            </div>
          </div>
          <div className="topbar__right">
            <button className="search-box" type="button" disabled title="Search adapter not connected in this prototype">
              <Search size={16} />
              <span>Search asset, permit or person</span>
              <kbd>⌘ K</kbd>
            </button>
            <button className="icon-button has-badge" type="button" aria-label="Notifications unavailable in simulated replay" disabled>
              <Bell size={18} />
              <span className="notification-badge">1</span>
            </button>
            <div className="trust-chip">
              <ShieldCheck size={15} />
              <span>Shadow mode</span>
            </div>
          </div>
        </header>
        <main className="main-stage">{children}</main>
      </div>
    </div>
  );
}
