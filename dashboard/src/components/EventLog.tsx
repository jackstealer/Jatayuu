import type { DashboardEvent } from "./types";

interface Props {
  events: DashboardEvent[];
}

const EVENT_STYLES: Record<string, { color: string; bg: string }> = {
  TASK:    { color: "#22c55e", bg: "rgba(34,197,94,0.06)" },
  DRONE:   { color: "#38bdf8", bg: "rgba(56,189,248,0.06)" },
  SURVIVOR:{ color: "#f97316", bg: "rgba(249,115,22,0.08)" },
  "E-STOP":{ color: "#ef4444", bg: "rgba(239,68,68,0.10)" },
  DAMAGE:  { color: "#ff4500", bg: "rgba(255,69,0,0.15)" },
  INFO:    { color: "#475569", bg: "transparent" },
  MISSION: { color: "#a78bfa", bg: "rgba(167,139,250,0.08)" },
  TARGET:  { color: "#fb923c", bg: "rgba(251,146,60,0.06)" },
};

export function EventLog({ events }: Props) {
  const reversed = [...events].reverse(); // newest first

  return (
    <div className="flex-1 min-h-0 overflow-y-auto rounded-lg border border-white/[0.06] bg-white/[0.01]">
      {reversed.length === 0 ? (
        <div className="flex items-center justify-center h-16 text-[11px] text-slate-600">
          No events yet
        </div>
      ) : (
        <div className="divide-y divide-white/[0.03]">
          {reversed.map((ev, i) => {
            const style = EVENT_STYLES[ev.kind] ?? EVENT_STYLES.INFO;
            return (
              <div
                key={i}
                className="flex items-start gap-2 px-3 py-1.5 hover:bg-white/[0.02] text-[11px] transition-colors"
                style={{ backgroundColor: style.bg }}
              >
                <span className="text-slate-600 font-mono text-[9px] shrink-0 tabular-nums pt-px">
                  {ev.ts}
                </span>
                <span
                  className="font-bold text-[9px] shrink-0 tracking-wider uppercase pt-px"
                  style={{ color: style.color }}
                >
                  [{ev.kind}]
                </span>
                <span className="text-slate-300 leading-tight text-[10px] break-words min-w-0">
                  {ev.msg}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
