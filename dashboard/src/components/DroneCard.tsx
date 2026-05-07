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
  const taskColor =
    isCrashed
      ? "text-red-500 font-black animate-pulse"
      : drone.current_task === "STOPPED"
      ? "text-red-400"
      : drone.current_task === "IDLE"
      ? "text-slate-600"
      : drone.current_task?.startsWith("⚠")
      ? "text-yellow-400"
      : "text-cyan-400";

  return (
    <div
      className={`relative px-3 py-3 rounded-xl border transition-all duration-300 ${
        isCrashed
          ? "border-red-600/60 bg-red-950/40 shadow-[0_0_15px_rgba(220,38,38,0.2)]"
          : isAlive
          ? "border-white/10 bg-white/[0.03] hover:bg-white/[0.07] hover:border-white/20"
          : "border-red-900/40 bg-red-950/20 opacity-70"
      }`}
    >
      {/* Task Badge (Pill) */}
      <div className="absolute -top-2 -right-1 flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.4)] border border-white/20 z-10">
        <span className="text-[10px] font-black text-white leading-none">
          {drone.tasks_done ?? 0}
        </span>
        <span className="text-[7px] font-bold text-white/80 uppercase tracking-tighter leading-none">
          Zones
        </span>
      </div>

      {/* Row 1: status dot + name + kill btn */}
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${
            isAlive ? "bg-emerald-400 shadow-[0_0_8px_#4ade80]" : "bg-red-500 animate-pulse"
          }`}
        />
        <div className="flex-1 min-w-0 flex items-center gap-2">
            <span
              className="text-xs font-black font-mono tracking-tight"
              style={{ color: isAlive ? color : "#991b1b" }}
            >
              {drone.id.replace("drone_", "DRONE ").toUpperCase()}
            </span>
            {isDec && <span className="text-[10px] opacity-70" title="Squad Leader">👑</span>}
            
            {/* Kill/Demo Button */}
            {isAlive && !isCrashed && (
                <button 
                  onClick={(e) => { e.stopPropagation(); onKill(drone.id); }}
                  className="ml-auto px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[8px] font-bold text-slate-500 hover:bg-red-600 hover:text-white hover:border-red-400 transition-all uppercase tracking-tighter"
                  title="Simulate Hardware Failure"
                >
                    Kill
                </button>
            )}
        </div>
      </div>

      {/* Battery bar */}
      <div className="mt-2.5 space-y-1">
        <div className="flex justify-between items-center px-0.5">
             <div className="text-[8px] text-slate-500 font-bold uppercase tracking-widest">
                {isCrashed ? "SIGNAL LOST" : "BATTERY"}
             </div>
             <div className="text-[9px] text-slate-400 font-mono">
                {Math.round(drone.battery)}%
             </div>
        </div>
        <div className="h-1 rounded-full bg-white/5 overflow-hidden border border-white/5">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${isCrashed ? "bg-red-900" : ""}`}
              style={{ 
                width: isCrashed ? "0%" : barW, 
                backgroundColor: isCrashed ? undefined : barColor,
                boxShadow: isCrashed ? "none" : `0 0 4px ${barColor}80`
              }}
            />
        </div>
      </div>

      {/* Row 2: current task */}
      <div className={`flex items-center gap-1.5 text-[10px] font-black font-mono mt-3 uppercase tracking-tighter ${taskColor}`}>
        {isCrashed && <span className="animate-bounce">⚠</span>}
        {drone.current_task || "READY"}
      </div>

      {/* Row 3: Coords */}
      <div className="flex items-center justify-between mt-1">
        <span className="text-[9px] text-slate-500 font-mono font-bold tracking-tight">
          COORD_GPS: {Math.round(drone.x)}N / {Math.round(drone.y)}E
        </span>
      </div>
    </div>
  );
}
