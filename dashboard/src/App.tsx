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

  return (
    <div className="h-screen w-screen bg-[#090a0f] text-white overflow-hidden flex flex-col font-mono selection:bg-cyan-500/30">
      {/* ── ADVANCED TOP BAR ── */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-cyan-500/10 bg-[#090a0f]/95 backdrop-blur-2xl z-20 shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-black shadow-[0_0_20px_rgba(6,182,212,0.15)]">
               N
            </div>
            <div>
              <div className="text-sm font-black tracking-[0.3em] text-white">PROJECT NOVA</div>
              <div className="text-[10px] text-cyan-400/60 tracking-[0.2em] uppercase font-bold">Advanced Swarm Dev v2.0</div>
            </div>
          </div>

          <div className="h-8 w-px bg-white/5 mx-2" />

          <div className={`flex items-center gap-3 px-4 py-2 rounded-xl border transition-all duration-500 ${
            connected
              ? "border-emerald-500/20 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.05)]"
              : "border-red-500/20 bg-red-500/5 shadow-[0_0_15px_rgba(239,68,68,0.05)]"
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              connected ? "bg-emerald-400 animate-pulse shadow-[0_0_10px_#34d399]" : "bg-red-500"
            }`} />
            <span className="text-[11px] font-bold tracking-widest uppercase">{
              connected ? "MESH ACTIVE" : "SIGNAL LOST"
            }</span>
          </div>
        </div>

        <div className="flex items-center gap-10">
           <Stat value={`${aliveCount}/8`} label="NODE_COUNT" accent={aliveCount === 8} />
           
           {/* Detailed Mission Progress */}
           <div className="flex flex-col gap-1 items-end min-w-[140px]">
              <div className="flex justify-between w-full">
                <div className="text-[9px] text-slate-500 font-bold uppercase tracking-widest leading-none">Mission Progress</div>
                <div className="text-[10px] text-cyan-400 font-bold leading-none">{state.mission_done ?? 0}/100</div>
              </div>
              <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden border border-white/5 shadow-inner">
                <div 
                  className="h-full bg-gradient-to-r from-cyan-600 to-emerald-500 rounded-full transition-all duration-1000 shadow-[0_0_8px_rgba(6,182,212,0.4)]"
                  style={{ width: `${Math.min((state.mission_done ?? 0), 100)}%` }}
                />
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
          
          {/* Mission Control Overlay */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[1000] min-w-[400px]">
             <div className="bg-[#0c0e14]/90 border border-white/5 backdrop-blur-2xl px-6 py-4 rounded-2xl shadow-2xl">
               <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-4 text-center">Operation Mode</div>
               <MissionSwitcher
                 current={state.mission}
                 onSendAction={handleMission}
               />
             </div>
          </div>
        </div>

        {/* SIDE PANEL: TELEMETRY & LOGS */}
        <aside className="w-85 border-l border-white/[0.06] bg-[#0c0e14]/50 backdrop-blur-xl flex flex-col shrink-0 overflow-hidden">
          <div className="p-6 flex-1 flex flex-col min-h-0">
            <div className="text-[11px] font-bold tracking-[0.25em] uppercase text-cyan-400/80 mb-5 flex items-center gap-2">
               <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full" />
               NODE_TELEMETRY
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

          <div className="h-px bg-white/5 mx-6" />

          <div className="p-6 h-[40%] flex flex-col min-h-0">
            <div className="text-[11px] font-bold tracking-[0.25em] uppercase text-slate-500 mb-5 flex items-center gap-2">
               <span className="w-1.5 h-1.5 bg-slate-500 rounded-full" />
               MISSION_LOGS
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
    <div className="flex flex-col items-center">
      <div className={`text-xl font-black tabular-nums transition-colors ${accent ? "text-cyan-400" : "text-white"}`}>
        {value}
      </div>
      <div className="text-[9px] text-slate-500 uppercase tracking-widest font-bold mt-1">
        {label}
      </div>
    </div>
  );
}

export default App;
