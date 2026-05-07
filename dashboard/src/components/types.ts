// NOVA Dashboard — shared types
export interface Drone {
  id: string;
  x: number;
  y: number;
  battery: number;
  role: string;
  alive: boolean;
  current_task?: string;
  tasks_done?: number;
  offline_since?: string | null;
  last_seen: number;
}

export interface DashboardEvent {
  ts: string;
  kind: string;
  msg: string;
}

export interface SwarmState {
  type: string;
  drones: Drone[];
  mission: string;
  mission_pct: number;
  mission_done?: number;
  mission_total?: number;
  mission_targets?: [number, number][];
  estop: boolean;
  coverage: number;
  dark_remaining: number;
  alive_count: number;
  events: DashboardEvent[];
  grid: Record<string, string>;
  connected: boolean;
}
