import { useCallback } from "react";

export interface EstopACK {
  drone_id: string;
  received_at: number;
  latency_ms: number;
}

export function EStopPanel({
  estop_active,
  acks,
  onSendAction,
}: {
  estop_active: boolean;
  acks: EstopACK[];
  onSendAction: (action: any) => void;
}) {
  const handleAction = useCallback(() => {
    if (estop_active) {
      onSendAction({ action: "reset" });
    } else {
      onSendAction({
        action: "estop",
        issued_by: "dashboard",
        timestamp: Date.now(),
      });
    }
  }, [estop_active, onSendAction]);

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Button */}
      <button
        id="estop-button"
        onClick={handleAction}
        className={`w-full px-4 py-3 rounded-lg text-xs font-bold tracking-wider transition-all shadow-lg ${
          estop_active
            ? "bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500 shadow-emerald-500/20"
            : "bg-gradient-to-r from-red-600 to-red-800 border border-red-500 hover:from-red-500 hover:to-red-700 shadow-red-500/20 animate-pulse"
        }`}
      >
        {estop_active ? "RESET SYSTEM" : "EMERGENCY STOP"}
      </button>

      {/* ACK Latency Table */}
      {estop_active && acks.length > 0 && (
        <div className="bg-red-950/30 border border-red-500/20 rounded-lg overflow-hidden">
          <div className="px-3 py-1.5 text-[9px] font-bold tracking-[0.15em] uppercase text-red-400 border-b border-red-500/20">
            E-STOP ACKNOWLEDGMENTS
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-slate-500 uppercase tracking-wider border-b border-white/[0.03]">
                  <th className="px-3 py-1 text-left font-semibold">Drone</th>
                  <th className="px-3 py-1 text-right font-semibold">Latency</th>
                  <th className="px-3 py-1 text-center font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {acks.map((ack) => (
                  <tr key={ack.drone_id} className="border-b border-white/[0.02]">
                    <td className="px-3 py-1 font-mono text-slate-300">
                      {ack.drone_id.replace("drone_", "D")}
                    </td>
                    <td className="px-3 py-1 text-right font-mono tabular-nums">
                      {ack.latency_ms < 100
                        ? `${ack.latency_ms} ms`
                        : ack.latency_ms < 300
                        ? `${ack.latency_ms} ms`
                        : `${ack.latency_ms} ms`}
                    </td>
                    <td className="px-3 py-1 text-center">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${
                          ack.latency_ms < 200
                            ? "bg-emerald-400"
                            : ack.latency_ms < 500
                            ? "bg-amber-400"
                            : "bg-red-400"
                        }`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
