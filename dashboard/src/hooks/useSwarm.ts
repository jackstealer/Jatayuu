import { useEffect, useRef, useState, useCallback } from "react";
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
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    const pageHost = window.location.hostname || "localhost";
    const url = `ws://${pageHost}:${port}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] Connected to backend");
      setConnected(true);
      setState((prev) => ({ ...prev, connected: true }));
      reconnectAttemptsRef.current = 0; // Reset reconnect attempts
    };
    
    ws.onclose = () => {
      console.log("[WS] Disconnected from backend");
      setConnected(false);
      setState((prev) => ({ ...prev, connected: false }));
      
      // Attempt reconnection with exponential backoff
      const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
      console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);
      
      reconnectTimeoutRef.current = window.setTimeout(() => {
        reconnectAttemptsRef.current += 1;
        connect();
      }, delay);
    };
    
    ws.onerror = (error) => {
      console.error("[WS] Error:", error);
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
      } catch (error) {
        console.error("[WS] Failed to parse message:", error);
      }
    };
  }, [port]);

  useEffect(() => {
    connect();

    const intervalId = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "ping" }));
      }
    }, 5000);

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      clearInterval(intervalId);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendAction = (action: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(action));
    }
  };

  return { state, connected, sendAction };
}
