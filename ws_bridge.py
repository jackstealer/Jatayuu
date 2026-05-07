"""
ws_bridge.py — WebSocket bridge between NOVA mesh and web dashboard.
Subscribes to mesh events and broadcasts JSON snapshots to all connected WebSocket clients.
"""

import asyncio
import json
import time
import websockets
from typing import Set

try:
    import config
except ImportError:
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config


class WsBridge:
    """WebSocket server that pushes swarm state to dashboard clients."""

    def __init__(self, port: int = config.WS_PORT):
        self.port = port
        self.clients: Set = set()
        self.drones: dict = {}           # drone_id -> latest heartbeat dict
        self.drone_stats: dict = {}      # drone_id -> {tasks_done, offline_since}
        self.events: list = []           # recent event log
        self.grid_snapshot: dict = {}    # cell_key -> state
        self.current_mission: str = "SAR"
        self.estop_active: bool = False
        self.grid_snapshot: dict = {}    # cell_key -> state
        self.searched_cells: int = 0
        self.dark_zone_total: int = 0    # cells marked dark at dispatch time
        self.mission_active: bool = False
        self.mission_tasks_total: int = 100
        self.mission_tasks_done: int = 0
        self.mission_targets: list = [] # To be drawn on map
        self.server = None
        self._last_broadcast = 0

    async def subscribe(self, topic, payload, sender):
        """Called by mesh when any MQTT topic arrives."""

        if topic.endswith("/heartbeat"):
            did = payload.get("drone_id", sender)
            was_alive = self.drones.get(did, {}).get("alive", True)
            is_alive = payload.get("alive", True)

            # Init stats for new drone
            if did not in self.drone_stats:
                self.drone_stats[did] = {"tasks_done": 0, "offline_since": None}
                ts = time.strftime("%H:%M:%S")
                self.events.append({"ts": ts, "kind": "DRONE",
                                    "msg": f"{did} joined swarm"})
                self._trim_events()

            self.drones[did] = {
                "id": did,
                "x": payload.get("x", 0),
                "y": payload.get("y", 0),
                "battery": payload.get("battery", 100),
                "role": payload.get("role", "scout"),
                "alive": is_alive,
                "current_task": payload.get("current_task", "IDLE"),
                "tasks_done": self.drone_stats[did]["tasks_done"],
                "offline_since": self.drone_stats[did]["offline_since"],
                "last_seen": time.time(),
            }

            # Log state transitions
            ts = time.strftime("%H:%M:%S")
            if was_alive and not is_alive:
                self.drone_stats[did]["offline_since"] = ts
                self.drones[did]["offline_since"] = ts
                self.events.append({"ts": ts, "kind": "DRONE",
                                    "msg": f"{did} STOPPED (ESTOP)"})
                self._trim_events()
            elif not was_alive and is_alive:
                self.drone_stats[did]["offline_since"] = None
                self.drones[did]["offline_since"] = None
                self.events.append({"ts": ts, "kind": "DRONE",
                                    "msg": f"{did} RESUMED"})
                self._trim_events()

        elif topic.endswith("/task_done"):
            did = payload.get("drone_id", sender)
            event_type = payload.get("event", "DONE")
            if did not in self.drone_stats:
                self.drone_stats[did] = {"tasks_done": 0, "offline_since": None}
            ts = time.strftime("%H:%M:%S")

            if event_type == "CRASH":
                # Drone crashed — mark it offline
                self.drone_stats[did]["offline_since"] = ts
                if did in self.drones:
                    self.drones[did]["alive"] = False
                    self.drones[did]["offline_since"] = ts
                    self.drones[did]["current_task"] = "💀 CRASHED"
                cell = payload.get("cell", ["?", "?"])
                tasks = self.drone_stats[did]["tasks_done"]
                self.events.append({"ts": ts, "kind": "DAMAGE",
                                    "msg": f"💥 {did} CRASHED at ({cell[0]},{cell[1]}) after {tasks} tasks!"})
                self._trim_events()
            else:
                # Normal task completion
                self.drone_stats[did]["tasks_done"] += 1
                if did in self.drones:
                    self.drones[did]["tasks_done"] = self.drone_stats[did]["tasks_done"]
                count = self.drone_stats[did]["tasks_done"]
                
                # Global Mission Progress
                if self.mission_active:
                    self.mission_tasks_done += 1
                    
                    # Remove the nearest target from the visualization list
                    if self.mission_targets:
                        # Payloads from main.py cell format is [x, y]
                        p_cell = payload.get("cell", [0, 0])
                        dx = p_cell[0] # x
                        dy = p_cell[1] # y
                        best_idx = -1
                        min_dist = 9999
                        for i, (tx, ty) in enumerate(self.mission_targets):
                            d = ((tx - dx)**2 + (ty - dy)**2)**0.5
                            if d < min_dist:
                                min_dist = d
                                best_idx = i
                        # Distance check for task removal (in simulation units)
                        if best_idx >= 0 and min_dist < 10.0: 
                            self.mission_targets.pop(best_idx)

                    if self.mission_tasks_done >= self.mission_tasks_total:
                        self.mission_active = False
                        ts_m = time.strftime("%H:%M:%S")
                        self.events.append({"ts": ts_m, "kind": "MISSION", "msg": "🏆 100-TASK MISSION COMPLETE! Swarm holding position."})

                self.events.append({"ts": ts, "kind": "TASK",
                                    "msg": f"{did} cleared zone #{count}"})
                self._trim_events()

        elif topic.endswith("/worldstate"):
            cell = payload.get("cell")
            if cell:
                # Format: {"cell": [col, row], "status": "searched"}
                key = f"{cell[1]}_{cell[0]}"
                status = payload.get("status", "unknown")
                self.grid_snapshot[key] = status
            else:
                # Format: {"row_col": "dark_zone"} or {"row_col": "searched"}
                for key, status in payload.items():
                    if isinstance(status, str) and "_" in key:
                        self.grid_snapshot[key] = status

            # Recalculate mission progress based on discovered/mission cells
            self.searched_cells = sum(1 for v in self.grid_snapshot.values()
                                      if v in ("searched", "survivor_detected"))
            dark_remaining = sum(1 for v in self.grid_snapshot.values() if v == "dark_zone")

            # Mission completed: all dark zones cleared
            if self.mission_active and dark_remaining == 0 and self.dark_zone_total > 0:
                self.mission_active = False
                alive_count = sum(1 for d in self.drones.values() if d.get("alive"))
                total_done = sum(s["tasks_done"] for s in self.drone_stats.values())
                ts = time.strftime("%H:%M:%S")
                self.events.append({"ts": ts, "kind": "MISSION",
                                    "msg": f"✅ MISSION COMPLETE! {self.dark_zone_total} zones cleared by {alive_count} drones ({total_done} tasks)"})
                self._trim_events()

        elif topic.endswith("/mission"):
            mission = payload.get("mission")
            if mission:
                self.current_mission = mission
                ts = time.strftime("%H:%M:%S")
                self.events.append({"ts": ts, "kind": "MISSION",
                                    "msg": f"Mission set to: {mission}"})
                self._trim_events()
        
        elif topic.endswith("/mission/targets"):
            targets = payload.get("targets", [])
            self.mission_targets = targets
            self.mission_tasks_total = len(targets)
            self.mission_tasks_done = 0
            self.mission_active = True
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "INFO", 
                                "msg": f"NEW MISSION: {self.mission_tasks_total} sub-tasks generated"})
            self._trim_events()

        elif topic.endswith("/estop"):
            self.estop_active = True
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "E-STOP",
                                "msg": f"EMERGENCY STOP — {len(self.drones)} drones halted"})
            self._trim_events()

        elif topic.endswith("/survivor"):
            cell = payload.get("cell")
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "SURVIVOR",
                                "msg": f"Survivor at ({cell}) — {sender}"})
            self._trim_events()

        await self._broadcast()

    def _trim_events(self):
        if len(self.events) > 50:
            self.events = self.events[-50:]

    async def _broadcast(self, force=False):
        """Broadcast state to all clients, with throttling to prevent congestion."""
        if not self.clients: return
        
        now = time.time()
        # Cap broadcast at ~5Hz unless forced
        if not force and (now - self._last_broadcast < 0.2):
            return
        
        self._last_broadcast = now
        
        alive_count = sum(1 for d in self.drones.values() if d.get("alive"))
        dark_remaining = sum(1 for v in self.grid_snapshot.values() if v == "dark_zone")
        mission_pct = 0.0
        if self.dark_zone_total > 0:
            mission_pct = round((self.dark_zone_total - dark_remaining) / self.dark_zone_total * 100, 1)

        msg = json.dumps({
            "type": "state",
            "drones": list(self.drones.values()),
            "drone_stats": self.drone_stats,
            "mission": self.current_mission,
            "estop": self.estop_active,
            "coverage": round(self.searched_cells, 1),
            "mission_pct": mission_pct if not self.mission_active else round((self.mission_tasks_done / self.mission_tasks_total * 100), 1),
            "mission_done": self.mission_tasks_done,
            "mission_total": self.mission_tasks_total,
            "mission_targets": self.mission_targets,
            "dark_remaining": dark_remaining,
            "alive_count": alive_count,
            "events": self.events[-15:],
            "grid": self.grid_snapshot,
        })

        dead = set()
        for ws in list(self.clients):
            try:
                await ws.send(msg)
            except websockets.exceptions.ConnectionClosed:
                dead.add(ws)
            except Exception as e:
                # print(f"[WS_BRIDGE] send error: {e}")
                dead.add(ws)
        self.clients -= dead
        if dead:
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "INFO",
                                "msg": f"{len(dead)} dashboard client(s) disconnected"})

    async def start_server(self):
        self.server = await websockets.serve(
            self._handle_client, "0.0.0.0", self.port
        )
        ts = time.strftime("%H:%M:%S")
        self.events.append({"ts": ts, "kind": "INFO",
                            "msg": f"WebSocket server on port {self.port}"})
        print(f"[WS_BRIDGE] Listening on ws://0.0.0.0:{self.port}")

    async def _handle_client(self, websocket):
        self.clients.add(websocket)
        ts = time.strftime("%H:%M:%S")
        alive = sum(1 for d in self.drones.values() if d.get("alive"))
        self.events.append({"ts": ts, "kind": "INFO",
                            "msg": f"Dashboard connected ({alive}/{len(self.drones)} drones live)"})
        print(f"[WS_BRIDGE] Client connected ({len(self.clients)} total, {len(self.drones)} drones)")
        await self._broadcast()
        try:
            async for msg in websocket:
                try:
                    data = json.loads(msg)
                    await self._handle_inbound(data)
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "INFO", "msg": "Dashboard disconnected"})
            await self._broadcast()

    async def _handle_inbound(self, data: dict):
        """Handle messages from dashboard (estop, mission change, etc.)"""
        print(f"[WS_BRIDGE] inbound: {data}")
        action = data.get("action")
        if action == "estop":
            self.estop_active = True
            if hasattr(self, '_on_publish_estop') and self._on_publish_estop:
                await self._on_publish_estop(config.TOPIC_ESTOP, {
                    "type": "ESTOP", "issued_by": "dashboard",
                    "timestamp": time.time(),
                })
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "E-STOP", "msg": f"EMERGENCY STOP issued by operator"})
        elif action == "mission":
            mission = data.get("mission")
            if isinstance(mission, dict):
                mission = mission.get("mission")
            if mission and isinstance(mission, str):
                self.current_mission = mission
                if hasattr(self, '_on_publish_mission') and self._on_publish_mission:
                    await self._on_publish_mission(config.TOPIC_MISSION, {
                        "mission": mission,
                    })
                ts = time.strftime("%H:%M:%S")
                self.events.append({"ts": ts, "kind": "MISSION", "msg": f"Mission set to: {mission}"})
        elif action == "reset":
            self.estop_active = False
            ts = time.strftime("%H:%M:%S")
            self.events.append({"ts": ts, "kind": "INFO", "msg": "System RESET — drones resuming"})
            # Broadcast RESET to all drones so they clear emergency_stopped
            if hasattr(self, '_on_publish_estop') and self._on_publish_estop:
                await self._on_publish_estop(config.TOPIC_ESTOP, {
                    "type": "RESET",
                    "issued_by": "dashboard",
                    "timestamp": time.time(),
                })
        elif action in ("goto_target", "dispatch_dots"):
            target_grid = data.get("target_grid")
            if target_grid and self.target_handler:
                target_grid["action"] = action
                await self.target_handler(target_grid)
            ts = time.strftime("%H:%M:%S")
            radius = target_grid.get("radius", 10) if target_grid else 10
            self.events.append({"ts": ts, "kind": "TARGET",
                                "msg": f"Target: ({target_grid.get('x','?')}, {target_grid.get('y','?')}) r={radius}"})
        elif action == "kill":
            drone_id = data.get("drone_id")
            if drone_id and hasattr(self, '_on_publish_kill') and self._on_publish_kill:
                await self._on_publish_kill(config.TOPIC_KILL, {"drone_id": drone_id})
                ts = time.strftime("%H:%M:%S")
                self.events.append({"ts": ts, "kind": "DAMAGE", "msg": f"Manual KILL signal sent to {drone_id}"})

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

if __name__ == "__main__":
    from mesh.nova_mesh import NovaMesh
    
    async def run_bridge():
        bridge = WsBridge()
        
        # Connect bridge to simulated mesh (MOCK mode)
        mesh = NovaMesh("bridge", "MOCK")
        
        # Wire bridge to receive all mesh traffic
        mesh.subscribe("nova/#", bridge.subscribe)
        
        # Provide bridge a way to send actions back to mesh
        bridge._on_publish_estop = mesh.publish
        bridge._on_publish_mission = mesh.publish
        bridge.target_handler = mesh.broadcast
        
        await mesh.start()
        await bridge.start_server()
        
        print("[WS_BRIDGE] Bridge and Mesh connected. Ready for dashboard.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await bridge.stop()
            await mesh.stop()

    asyncio.run(run_bridge())
