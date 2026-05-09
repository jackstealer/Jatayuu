import type { Drone } from "./types";

interface Props {
  drone: Drone;
  onKill: (id: string) => void;
}

export function DroneCard({ drone, onKill }: Props) {
  const isAlive = drone.alive;
  const isDec = drone.role === "decision";
  const color = isDec ? "#eab308" : "#3b82f6";
  const barColor =
    drone.battery < 25
      ? "#ef4444"
      : drone.battery < 55
      ? "#eab308"
      : "#22c55e";
  const barW = `${Math.min(drone.battery, 100)}%`;
  const isCrashed = drone.current_task === "💀 CRASHED";
  const isStopped = drone.current_task === "E-STOPPED" || drone.current_task === "STOPPED";
  const taskColor =
    isCrashed
      ? "text-red-500 font-black animate-pulse"
      : isStopped
      ? "text-red-400 font-bold"
      : drone.current_task === "IDLE"
      ? "text-slate-600"
      : drone.current_task === "HOVER"
      ? "text-amber-400"
      : drone.current_task?.startsWith("⚠")
      ? "text-yellow-400"
      : "text-cyan-400";

  return (
    <div
      className={`group relative px-4 py-3.5 rounded-xl border transition-all duration-300 hover:scale-[1.02] ${
        isCrashed
          ? "border-red-600/70 bg-gradient-to-br from-red-950/50 to-red-900/30 shadow-[0_0_20px_rgba(220,38,38,0.25)] animate-pulse"
          : isAlive
          ? "border-white/10 bg-gradient-to-br from-white/[0.04] to-white/[0.02] hover:bg-white/[0.08] hover:border-cyan-500/30 hover:shadow-[0_0_20px_rgba(6,182,212,0.1)]"
          : "border-red-900/40 bg-gradient-to-br from-red-950/20 to-slate-950/20 opacity-70"
      }`}
    >
      {/* Enhanced Task Badge with Glow */}
      <div className="absolute -top-2.5 -right-2 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gradient-to-r from-emerald-500 to-green-500 shadow-[0_0_15px_rgba(16,185,129,0.5)] border border-white/30 z-10 animate-[fadeIn_0.5s_ease-out]">
        <span className="text-[11px] font-black text-white leading-none tabular-nums">
          {drone.tasks_done ?? 0}
        </span>
        <span className="text-[8px] font-bold text-white/90 uppercase tracking-tight leading-none">
          Tasks
        </span>
      </div>

      {/* Row 1: status dot + name + kill btn */}
      <div className="flex items-center gap-2.5">
        <div className="relative">
          <span
            className={`w-2.5 h-2.5 rounded-full shrink-0 transition-all ${
              isAlive ? "bg-emerald-400 shadow-[0_0_12px_#4ade80]" : "bg-red-500 shadow-[0_0_12px_#ef4444]"
            }`}
          />
          {isAlive && <span className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />}
        </div>
        <div className="flex-1 min-w-0 flex items-center gap-2">
            <span
              className="text-xs font-black font-mono tracking-tight transition-colors"
              style={{ color: isAlive ? color : "#991b1b" }}
            >
              {drone.id.replace("drone_", "DRONE ").toUpperCase()}
            </span>
            {isDec && (
              <span className="text-[11px] opacity-80 animate-bounce" title="Squad Leader" style={{ animationDuration: '2s' }}>
                👑
              </span>
            )}
            
            {/* Enhanced Kill/Demo Button */}
            {isAlive && !isCrashed && (
                <button 
                  onClick={(e) => { e.stopPropagation(); onKill(drone.id); }}
                  className="ml-auto px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-[8px] font-bold text-slate-400 hover:bg-gradient-to-r hover:from-red-600 hover:to-red-700 hover:text-white hover:border-red-400/50 transition-all duration-300 uppercase tracking-tight hover:shadow-[0_0_15px_rgba(239,68,68,0.4)] hover:scale-105 transform"
                  title="Simulate Hardware Failure"
                >
                    ⚠ Kill
                </button>
            )}
        </div>
      </div>

      {/* Enhanced Battery bar with gradient */}
      <div className="mt-3 space-y-1.5">
        <div className="flex justify-between items-center px-0.5">
             <div className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">
                {isCrashed ? "⚠ SIGNAL LOST" : "BATTERY"}
             </div>
             <div className={`text-[10px] font-mono font-bold tabular-nums ${
               drone.battery < 25 ? "text-red-400" : drone.battery < 55 ? "text-amber-400" : "text-emerald-400"
             }`}>
                {Math.round(drone.battery)}%
             </div>
        </div>
        <div className="h-1.5 rounded-full bg-gradient-to-r from-slate-900/50 to-slate-800/50 overflow-hidden border border-white/10 shadow-inner relative">
            <div
              className={`h-full rounded-full transition-all duration-1000 relative ${isCrashed ? "bg-red-900" : ""}`}
              style={{ 
                width: isCrashed ? "0%" : barW, 
                backgroundColor: isCrashed ? undefined : barColor,
                boxShadow: isCrashed ? "none" : `0 0 8px ${barColor}80`
              }}
            >
              {!isCrashed && (
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_infinite]" />
              )}
            </div>
        </div>
      </div>

      {/* Row 2: current task with enhanced styling */}
      <div className={`flex items-center gap-2 text-[10px] font-black font-mono mt-3.5 uppercase tracking-tight ${taskColor}`}>
        {isCrashed && <span className="animate-bounce text-sm">⚠</span>}
        <span className="relative">
          {drone.current_task || "READY"}
          {drone.current_task === "FLYING" && (
            <span className="absolute -right-4 top-0 text-[8px]">✈️</span>
          )}
        </span>
      </div>

      {/* Row 3: Enhanced Coords with icon */}
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/5">
        <span className="text-[9px] text-slate-500 font-mono font-bold tracking-tight flex items-center gap-1.5">
          <span className="text-cyan-400/60">📍</span>
          <span className="text-cyan-400/80">{Math.round(drone.x)}</span>
          <span className="text-slate-600">/</span>
          <span className="text-cyan-400/80">{Math.round(drone.y)}</span>
        </span>
        <span className="text-[8px] text-slate-600 uppercase tracking-wider">GPS</span>
      </div>
    </div>
  );
}
