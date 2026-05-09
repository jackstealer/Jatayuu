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
    <div className="flex flex-col gap-3 w-full">
      <div className="flex gap-2 flex-wrap justify-center">
        {MISSIONS.map((m) => {
          const isActive = current === m.key;
          return (
            <button
              key={m.key}
              id={`mission-${m.key.toLowerCase()}`}
              onClick={() => handleClick(m.key)}
              className={`group relative flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-[10px] font-bold tracking-wider uppercase transition-all duration-300 ${
                isActive
                  ? `bg-gradient-to-r ${m.color} border border-white/30 shadow-[0_0_25px_${m.accent}40] scale-105`
                  : "bg-white/[0.04] border border-white/[0.08] text-slate-400 hover:border-white/25 hover:text-white hover:bg-white/[0.08] hover:scale-102"
              }`}
            >
              <div className="relative">
                <span
                  className={`w-2.5 h-2.5 rounded-full transition-all ${
                    isActive ? "bg-white" : "bg-slate-600 group-hover:bg-slate-400"
                  }`}
                  style={isActive ? { boxShadow: `0 0 10px ${m.accent}` } : {}}
                />
                {isActive && (
                  <span 
                    className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-white animate-ping"
                    style={{ animationDuration: '2s' }}
                  />
                )}
              </div>
              <span className={isActive ? "text-white" : ""}>{m.label}</span>
              {isActive && (
                <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_2s_infinite]" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
