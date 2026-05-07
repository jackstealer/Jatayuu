import { useEffect, useRef, useState } from "react";
import type { SwarmState } from "../components/types";

const initialState: SwarmState = {
  type: "state",
  drones: [],
  mission: "SAR",
  estop: false,
  coverage: 0,
  mission_pct: 0,
  dark_remaining: 0,
  alive_count: 0,
  events: [],
  grid: {},
  connected: false,
};

export function useSwarm(port: number = 8765) {
  const [state, setState] = useState<SwarmState>(initialState);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const pageHost = window.location.hostname || "localhost";
    const url = `ws://${pageHost}:${port}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setState((prev) => ({ ...prev, connected: true }));
    };
    ws.onclose = () => {
      setConnected(false);
      setState((prev) => ({ ...prev, connected: false }));
    };
    ws.onerror = () => {
      setConnected(false);
      setState((prev) => ({ ...prev, connected: false }));
    };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "state") {
          setState((prev) => ({
            ...msg,
            drones: (msg.drones || []).map((d: any) => ({
              ...d,
              x: d.x,
              y: d.y,
            })),
            connected: prev.connected,
          }));
        }
      } catch {
        // ignore malformed
      }
    };

    const intervalId = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "ping" }));
      }
    }, 5000);

    return () => {
      ws.close();
      clearInterval(intervalId);
    };
  }, [port]);

  const sendAction = (action: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(action));
    }
  };

  return { state, connected, sendAction };
}
