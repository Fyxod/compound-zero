import { AnimatePresence, motion } from "motion/react";
import { lazy, Suspense, useEffect, useState } from "react";
import { AppShell } from "./components/AppShell";
import { useSimulation } from "./hooks/useSimulation";
import type { AppView } from "./types/domain";

const CommandCenter = lazy(() => import("./pages/CommandCenter").then((module) => ({ default: module.CommandCenter })));
const EvidenceView = lazy(() => import("./pages/EvidenceView").then((module) => ({ default: module.EvidenceView })));
const IntelligenceView = lazy(() => import("./pages/IntelligenceView").then((module) => ({ default: module.IntelligenceView })));
const ValidationView = lazy(() => import("./pages/ValidationView").then((module) => ({ default: module.ValidationView })));
const SafetyCaseView = lazy(() => import("./pages/SafetyCaseView").then((module) => ({ default: module.SafetyCaseView })));

const VIEW_ORDER: AppView[] = ["command", "evidence", "intelligence", "validation", "safety-case"];

export default function App() {
  const [view, setView] = useState<AppView>("command");
  const simulation = useSimulation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [view]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest("button, a, input, textarea, select, [role='button'], [contenteditable='true']")) return;
      if (event.key === " ") {
        event.preventDefault();
        simulation.toggle();
      }
      const numeric = Number(event.key);
      if (numeric >= 1 && numeric <= VIEW_ORDER.length) setView(VIEW_ORDER[numeric - 1]);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [simulation.toggle]);

  return (
    <AppShell view={view} onViewChange={setView} engine={simulation.engine}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={view}
          className="view-transition"
          initial={{ opacity: 0, y: 7 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
        >
          <Suspense fallback={<div className="route-loading"><span /><strong>Opening workspace</strong></div>}>
            {view === "command" && (
              <CommandCenter simulation={simulation} onOpenEvidence={() => setView("evidence")} />
            )}
            {view === "evidence" && <EvidenceView simulation={simulation} />}
            {view === "intelligence" && <IntelligenceView />}
            {view === "validation" && <ValidationView />}
            {view === "safety-case" && <SafetyCaseView simulation={simulation} />}
          </Suspense>
        </motion.div>
      </AnimatePresence>
    </AppShell>
  );
}
