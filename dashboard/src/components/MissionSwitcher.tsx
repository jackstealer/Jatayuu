import { useCallback } from "react";

const MISSIONS = [
  { key: "SAR", label: "SEARCH & RESCUE", color: "from-blue-600 to-blue-800", accent: "#3b82f6" },
  { key: "Defense", label: "DEFENSE", color: "from-green-700 to-green-900", accent: "#22c55e" },
  { key: "Fire", label: "WILDFIRE", color: "from-orange-600 to-red-700", accent: "#f97316" },
  { key: "Pollution", label: "POLLUTION", color: "from-yellow-600 to-yellow-800", accent: "#eab308" },
  { key: "Ambulance", label: "MEDICAL", color: "from-slate-400 to-slate-600", accent: "#94a3b8" },
];

export function MissionSwitcher({
  current,
  onSendAction,
}: {
  current: string;
  onSendAction: (action: any) => void;
}) {
  const handleClick = useCallback(
    (mission: string) => {
      onSendAction({ action: "mission", mission });
    },
    [onSendAction]
  );

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="text-[9px] font-bold tracking-[0.2em] uppercase text-slate-500">Mission</div>
      <div className="flex gap-1.5 flex-wrap">
        {MISSIONS.map((m) => {
          const isActive = current === m.key;
          return (
            <button
              key={m.key}
              id={`mission-${m.key.toLowerCase()}`}
              onClick={() => handleClick(m.key)}
              className={`relative flex items-center gap-2 px-3 py-2 rounded-lg text-[10px] font-bold tracking-wider uppercase transition-all ${
                isActive
                  ? `bg-gradient-to-r ${m.color} border border-white/20 shadow-lg`
                  : "bg-white/[0.03] border border-white/[0.06] text-slate-500 hover:border-white/20 hover:text-white"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${isActive ? "bg-white animate-pulse" : "bg-slate-600"}`}
                style={isActive ? { boxShadow: `0 0 6px ${m.accent}` } : {}}
              />
              {m.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
