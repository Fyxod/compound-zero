import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { SimulationSnapshot } from "../types/domain";

export function RiskHistoryChart({ history }: { history: SimulationSnapshot[] }) {
  const latest = history[history.length - 1];
  const modelBacked = latest?.engineSource === "model-api";
  const firstPredictionMinute =
    history.find((snapshot) => snapshot.predictionActive)?.tick ?? (modelBacked ? 9 : 18);
  const eventMinute = latest?.eventMinute ?? 42;
  const interventionWindow = Math.max(0, eventMinute - firstPredictionMinute);
  const thresholdScore = Math.round((latest?.decisionThreshold ?? 0.52) * 100);
  const data = history.map((snapshot) => ({
    minute: snapshot.tick,
    risk: snapshot.score,
    legacy: snapshot.baselineAlarm ? 100 : 8,
    time: snapshot.timestamp.slice(0, 5),
  }));
  return (
    <section className="panel history-panel">
      <header className="panel-header">
        <div>
          <span className="eyebrow">FORECAST TRAJECTORY</span>
          <h2>Risk arrives before the alarm</h2>
        </div>
        <div className="history-legend">
          <span><i className="line-swatch is-fusion" /> Fusion risk</span>
          <span><i className="line-swatch is-threshold" /> Action threshold</span>
        </div>
      </header>
      <div className="history-chart">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 8, bottom: 2, left: -24 }}>
            <defs>
              <linearGradient id="risk-area" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ff8c52" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#ff8c52" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#b8c8c2" strokeOpacity={0.07} vertical={false} />
            <XAxis
              dataKey="minute"
              stroke="#60706b"
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `T+${value}`}
              tick={{ fill: "#73847e", fontSize: 10, fontFamily: "JetBrains Mono Variable" }}
            />
            <YAxis
              domain={[0, 100]}
              stroke="#60706b"
              tickLine={false}
              axisLine={false}
              ticks={[0, 25, 50, 75, 100]}
              tick={{ fill: "#73847e", fontSize: 10, fontFamily: "JetBrains Mono Variable" }}
            />
            <Tooltip
              contentStyle={{
                background: "#111817",
                border: "1px solid rgba(170,190,182,.15)",
                borderRadius: 10,
                boxShadow: "0 18px 50px rgba(0,0,0,.34)",
              }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.time ?? ""}
              formatter={(value) => [`${value ?? 0} / 100`, "Fusion risk"]}
            />
            <ReferenceLine y={thresholdScore} stroke="#f1d06f" strokeDasharray="5 6" strokeOpacity={0.65} />
            <ReferenceLine x={firstPredictionMinute} stroke="#78e9c2" strokeDasharray="3 5" strokeOpacity={0.4} />
            <Area
              type="monotone"
              dataKey="risk"
              stroke="#ff9b54"
              strokeWidth={2.2}
              fill="url(#risk-area)"
              animationDuration={260}
              isAnimationActive
              dot={false}
              activeDot={{ r: 4, fill: "#ff9b54", stroke: "#0b1110", strokeWidth: 3 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <footer className="history-panel__footer">
        <span className="history-marker"><i /> Fused warning · T+{firstPredictionMinute}m</span>
        <span>{modelBacked ? "Simulated harmful-state onset" : "Device threshold expected"} · T+{eventMinute}m</span>
        <strong>{interventionWindow} min intervention window</strong>
      </footer>
    </section>
  );
}
