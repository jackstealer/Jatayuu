import { useCallback, useState, useEffect, useRef } from "react";
import { useSwarm } from "./hooks/useSwarm";
import { GridMap } from "./components/GridMap";
import { DroneCard } from "./components/DroneCard";
import { EventLog } from "./components/EventLog";
import { MissionSwitcher } from "./components/MissionSwitcher";
import { EStopPanel } from "./components/EStopPanel";
import type { EstopACK } from "./components/EStopPanel";

function App() {
  const { state, connected, sendAction } = useSwarm(
    Number(import.meta.env.VITE_WS_PORT) || 8765
  );
  const [estopAcks, setEstopAcks] = useState<EstopACK[]>([]);
  const estopStartRef = useRef<number | null>(null);

  // When estop becomes active, record start time
  useEffect(() => {
    if (state.estop && estopStartRef.current === null) {
      estopStartRef.current = Date.now();
      setEstopAcks([]);
    } else if (!state.estop) {
      estopStartRef.current = null;
      setEstopAcks([]);
    }

    if (state.estop && estopStartRef.current !== null) {
      const newAcks: EstopACK[] = state.drones
        .filter((d) => !d.alive)
        .map((d) => ({
          drone_id: d.id,
          received_at: d.last_seen || Date.now(),
          latency_ms: Date.now() - estopStartRef.current!,
        }));
      if (newAcks.length > estopAcks.length) {
        setEstopAcks(newAcks);
      }
    }
  }, [state.estop, state.drones]);

  const handleEstopAction = useCallback(() => {
    if (state.estop) {
      estopStartRef.current = null;
      setEstopAcks([]);
      sendAction({ action: "reset" });
    } else {
      estopStartRef.current = Date.now();
      setEstopAcks([]);
      sendAction({ action: "estop" });
    }
  }, [state.estop, sendAction]);

  const handleMission = useCallback(
    (mission: string) => {
      sendAction({ action: "mission", mission });
    },
    [sendAction]
  );

  const aliveCount = state.alive_count || 0;
  const totalDrones = state.drones.length || 0;
  const missionTotal = state.mission_total ?? 100;

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-[#0a0b10] via-[#090a0f] to-[#0c0d14] text-white overflow-hidden flex flex-col font-mono selection:bg-cyan-500/30 relative">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none" style={{
        backgroundImage: 'linear-gradient(rgba(6, 182, 212, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 0.3) 1px, transparent 1px)',
        backgroundSize: '50px 50px'
      }} />
      
      {/* ── ENHANCED TOP BAR WITH GLASSMORPHISM ── */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/20 bg-gradient-to-r from-[#090a0f]/95 via-[#0a0e1a]/95 to-[#090a0f]/95 backdrop-blur-2xl z-20 shrink-0 shadow-[0_4px_30px_rgba(0,0,0,0.3)]">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4 animate-[fadeIn_0.6s_ease-out]">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-600/30 to-blue-600/30 border border-cyan-400/40 flex items-center justify-center text-cyan-400 font-black shadow-[0_0_30px_rgba(6,182,212,0.3)] hover:shadow-[0_0_40px_rgba(6,182,212,0.5)] transition-all duration-300 hover:scale-110 transform">
               <span className="text-xl">N</span>
            </div>
            <div>
              <div className="text-sm font-black tracking-[0.3em] text-transparent bg-clip-text bg-gradient-to-r from-white via-cyan-200 to-white">PROJECT NOVA</div>
              <div className="text-[10px] text-cyan-400/70 tracking-[0.2em] uppercase font-bold flex items-center gap-2">
                <span className="w-1 h-1 bg-cyan-400 rounded-full animate-pulse" />
                Advanced Swarm Intelligence v2.0
              </div>
            </div>
          </div>

          <div className="h-8 w-px bg-white/5 mx-2" />

          <div className={`flex items-center gap-3 px-5 py-2.5 rounded-xl border transition-all duration-500 ${
            connected
              ? "border-emerald-500/30 bg-gradient-to-r from-emerald-500/10 to-green-500/10 shadow-[0_0_25px_rgba(16,185,129,0.15)]"
              : "border-red-500/30 bg-gradient-to-r from-red-500/10 to-orange-500/10 shadow-[0_0_25px_rgba(239,68,68,0.15)] animate-pulse"
          }`}>
            <div className="relative">
              <span className={`w-2.5 h-2.5 rounded-full ${
                connected ? "bg-emerald-400 shadow-[0_0_15px_#34d399]" : "bg-red-500 shadow-[0_0_15px_#ef4444]"
              }`} />
              {connected && <span className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />}
            </div>
            <span className="text-[11px] font-bold tracking-widest uppercase">{
              connected ? "MESH ACTIVE" : "SIGNAL LOST"
            }</span>
          </div>
        </div>

        <div className="flex items-center gap-10">
           <Stat value={`${aliveCount}/${totalDrones}`} label="NODE_COUNT" accent={aliveCount === totalDrones && totalDrones > 0} />
           
           {/* Enhanced Mission Progress with Glow Effect */}
           <div className="flex flex-col gap-1.5 items-end min-w-[160px]">
              <div className="flex justify-between w-full items-center">
                <div className="text-[9px] text-slate-400 font-bold uppercase tracking-widest leading-none">Mission Progress</div>
                <div className="text-[11px] text-cyan-400 font-black leading-none tabular-nums">{state.mission_done ?? 0}/{missionTotal}</div>
              </div>
              <div className="w-full h-2 bg-gradient-to-r from-slate-900/50 to-slate-800/50 rounded-full overflow-hidden border border-cyan-500/20 shadow-inner relative">
                <div 
                  className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-emerald-500 rounded-full transition-all duration-1000 shadow-[0_0_15px_rgba(6,182,212,0.6)] relative"
                  style={{ width: `${missionTotal > 0 ? Math.min(((state.mission_done ?? 0) / missionTotal) * 100, 100) : 0}%` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_infinite]" />
                </div>
              </div>
           </div>

           <Stat value={state.mission_pct > 0 ? `${state.mission_pct}%` : "READY"} label="MISSION_STATUS" accent={state.mission_pct >= 100} />
        </div>

        <div className="flex items-center gap-4">
          <EStopPanel
            estop_active={state.estop}
            acks={estopAcks}
            onSendAction={handleEstopAction}
          />
        </div>
      </header>

      {/* ── TACTICAL MAIN VIEW ── */}
      <main className="flex-1 flex overflow-hidden">
        {/* CENTER: MAP AREA */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <div className="flex-1">
            <GridMap
              state={state}
              connected={connected}
              onSendAction={sendAction}
            />
          </div>
          
          {/* Enhanced Mission Control Overlay with Glassmorphism */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1000] min-w-[450px] animate-[slideInRight_0.4s_ease-out]">
             <div className="bg-gradient-to-br from-[#0c0e14]/95 via-[#0a0d16]/95 to-[#0c0e14]/95 border border-cyan-500/20 backdrop-blur-2xl px-7 py-5 rounded-2xl shadow-[0_8px_50px_rgba(0,0,0,0.5),0_0_30px_rgba(6,182,212,0.1)]">
               <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mb-4 text-center flex items-center justify-center gap-2">
                 <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
                 Operation Mode
                 <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-pulse" />
               </div>
               <MissionSwitcher
                 current={state.mission}
                 onSendAction={sendAction}
               />
             </div>
          </div>
        </div>

        {/* ENHANCED SIDE PANEL: TELEMETRY & LOGS */}
        <aside className="w-85 border-l border-cyan-500/10 bg-gradient-to-b from-[#0c0e14]/60 via-[#0a0d16]/60 to-[#0c0e14]/60 backdrop-blur-xl flex flex-col shrink-0 overflow-hidden shadow-[-10px_0_50px_rgba(0,0,0,0.3)]">
          <div className="p-6 flex-1 flex flex-col min-h-0">
            <div className="text-[11px] font-bold tracking-[0.25em] uppercase text-cyan-400/90 mb-5 flex items-center gap-2 pb-3 border-b border-cyan-500/10">
               <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-[0_0_8px_#06b6d4] animate-pulse" />
               NODE_TELEMETRY
               <span className="ml-auto text-[9px] text-slate-500 font-mono">{state.drones.filter(d => d.alive).length} ACTIVE</span>
            </div>
            <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
              {state.drones.map((d) => (
                <DroneCard 
                  key={d.id} 
                  drone={d} 
                  onKill={(id) => sendAction({ action: "kill", drone_id: id })} 
                />
              ))}
            </div>
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent mx-6" />

          <div className="p-6 h-[40%] flex flex-col min-h-0">
            <div className="text-[11px] font-bold tracking-[0.25em] uppercase text-slate-400 mb-5 flex items-center gap-2 pb-3 border-b border-slate-500/10">
               <span className="w-1.5 h-1.5 bg-slate-400 rounded-full shadow-[0_0_6px_#94a3b8]" />
               MISSION_LOGS
               <span className="ml-auto text-[9px] text-slate-600 font-mono">{state.events.length} EVENTS</span>
            </div>
            <div className="flex-1 min-h-0">
              <EventLog events={state.events} />
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

function Stat({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div className="flex flex-col items-center group">
      <div className={`text-2xl font-black tabular-nums transition-all duration-300 ${
        accent 
          ? "text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-cyan-400 animate-gradient" 
          : "text-white group-hover:text-cyan-300"
      }`}>
        {value}
      </div>
      <div className="text-[9px] text-slate-500 uppercase tracking-widest font-bold mt-1.5 group-hover:text-slate-400 transition-colors">
        {label}
      </div>
    </div>
  );
}

export default App;
