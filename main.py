import asyncio
import sys
import os
import time
import random
import math

# Root path alignment
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from mesh.nova_mesh import NovaMesh
from ws_bridge import WsBridge
from swarm.crdt_map import CRDTMap

# ── 100-Task Mission Controller ──
# Generates and tracks the status of 100 sub-problems in the target zone.
class MissionController:
    def __init__(self):
        self.tasks = []       # List of [x, y]
        self.completed = 0
        self.total = 100
        self.is_active = False
        self.mesh = None # To be set locally
        self._lock = asyncio.Lock()  # Thread safety for task assignment

    async def start_new_mission(self, centerX, centerY, radius=10):
        async with self._lock:
            self.tasks = []
            self.completed = 0
            self.is_active = True
            # Generate 100 problems in the red zone
            for _ in range(self.total):
                # Uniform distribution in a circle
                angle = random.uniform(0, 2 * math.pi)
                r = radius * math.sqrt(random.uniform(0, 1))
                tx = centerX + r * math.cos(angle)
                ty = centerY + r * math.sin(angle)
                self.tasks.append([tx, ty])
            
            # Publish targets to mesh so dashboard can visualize
            if self.mesh:
                asyncio.create_task(self.mesh.publish(config.TOPIC_MISSION + "/targets", {
                    "targets": self.tasks.copy(),  # Send copy to avoid mutation
                    "timestamp": time.time()
                }))
            print(f"[MISSION] Controller initialized with {self.total} tasks at ({centerX}, {centerY})")

    async def get_next_task(self):
        async with self._lock:
            if not self.tasks:
                return None
            return self.tasks.pop(0)

    async def mark_complete(self):
        async with self._lock:
            self.completed += 1
            if self.completed >= self.total:
                self.is_active = False
                return True # Mission Accomplished
            return False

# Global Mission instance
mission_ctrl = MissionController()

class DroneAgent:
    def __init__(self, drone_id, start_pos, mesh):
        self.drone_id = drone_id
        self.start_pos = list(start_pos)
        self.pos = list(start_pos)
        self.target = list(start_pos)
        self.battery = 100.0
        self.alive = True
        self.killed = False   # Manually killed by operator (separate from alive for resurrection)
        self.mesh = mesh
        self.role = "decision" if "1" in drone_id else "scout"
        self.status = "IDLE"
        self.tasks_done = 0
        self.current_mission_target = None
        self.emergency_stopped = False
        self._run_task = None  # asyncio task reference for restart

    def revive(self):
        """Revive this drone after a RESET. Restores state and restarts run loop."""
        self.killed = False
        self.alive = True
        self.emergency_stopped = False
        self.status = "HOVER"
        self.battery = max(self.battery, 20.0)  # Give at least 20% battery
        self._run_task = asyncio.create_task(self.run())
        print(f"[RESET] {self.drone_id} REVIVED.")

    async def run(self):
        print(f"[DRONE] {self.drone_id} started at {self.pos}")
        while self.alive:
            if self.emergency_stopped:
                self.status = "E-STOPPED"
            else:
                # 1. Update Position (Simulated Flight)
                dx = self.target[0] - self.pos[0]
                dy = self.target[1] - self.pos[1]
                dist = math.hypot(dx, dy)
                
                if dist > 0.5:
                    # 4 units per 0.5s = 8 units/s = 80m/s
                    speed = 4.0 
                    if dist < speed:
                        self.pos = list(self.target) # Exact arrival
                    else:
                        self.pos[0] += (dx / dist) * speed
                        self.pos[1] += (dy / dist) * speed
                    self.status = "FLYING"
                else:
                    # 2. Arrived at target? Task Completion Logic
                    if self.status == "FLYING":
                        self.tasks_done += 1
                        print(f"[TASK] {self.drone_id} cleared sub-task #{self.tasks_done}")
                        # Report to Mission Status
                        if mission_ctrl.is_active:
                            finished = await mission_ctrl.mark_complete()
                            if finished:
                                print("[MISSION] ALL 100 TASKS COMPLETE. STOPPING SWARM.")

                        await self.mesh.publish(config.TOPIC_TASK_DONE, {
                            "drone_id": self.drone_id,
                            "event": "DONE",
                            "tasks_done": self.tasks_done,
                            "cell": [self.pos[0], self.pos[1]], # Precise float
                            "timestamp": time.time()  # Add timestamp
                        })

                        # Fetch next task from Mission Controller
                        if mission_ctrl.is_active:
                            next_t = await mission_ctrl.get_next_task()
                            if next_t:
                                self.target = next_t
                            else:
                                self.status = "HOVER"
                        else:
                            self.status = "HOVER"
                    else:
                        self.status = "HOVER"

                # 3. Killed by operator — exit loop
                if self.killed:
                    self.alive = False
                    self.status = "\U0001f480 CRASHED"
                    await self.mesh.publish(config.TOPIC_TASK_DONE, {
                        "drone_id": self.drone_id,
                        "event": "CRASH",
                        "cell": [round(self.pos[0]), round(self.pos[1])],
                        "timestamp": time.time()
                    })
                    break

                # Battery Drain (10x longer life for Demo)
                self.battery -= (0.01 if self.status == "FLYING" else 0.005)
                if self.battery <= 0:
                    self.alive = False
                    self.status = "DEAD"

            # 4. Heartbeat (Report to Mission Control) - Moved outside the active check
            self.mesh.set_position(self.pos[0], self.pos[1])
            hb = {
                "drone_id": self.drone_id,
                "x": self.pos[0],
                "y": self.pos[1],
                "battery": round(self.battery, 1),
                "role": self.role,
                "current_task": self.status,
                "alive": self.alive,
                "tasks_done": self.tasks_done,
                "timestamp": time.time()  # Add timestamp for staleness detection
            }
            await self.mesh.publish(config.TOPIC_HEARTBEAT, hb)
            
            await asyncio.sleep(0.5)

async def main():
    print("=" * 60)
    print("   PROJECT NOVA — STRATEGIC SWARM CONTROLLER")
    print("=" * 60)

    # 1. Initialize Dashboard Bridge
    bridge = WsBridge()
    bridge_mesh = NovaMesh("bridge", "MOCK")
    
    async def bridge_handler(t, p, s):
        await bridge.subscribe(t, p, s)
    bridge_mesh.subscribe("nova/#", bridge_handler)
    
    bridge.target_handler = bridge_mesh.broadcast
    bridge._on_publish_estop = bridge_mesh.publish
    bridge._on_publish_mission = bridge_mesh.publish
    bridge._on_publish_kill = bridge_mesh.publish

    await bridge_mesh.start()
    await bridge.start_server()

    # 2. Spawning 8 Drones
    drones = []
    start_positions = config.DEFAULT_START_POSITIONS[:config.NUM_DRONES]
    
    leader_agent = None

    for i in range(config.NUM_DRONES):
        did = f"drone_{i+1}"
        d_mesh = NovaMesh(did, "MOCK")
        mission_ctrl.mesh = d_mesh # Shared mesh reference for mission controller
        await d_mesh.start()
        
        agent = DroneAgent(did, start_positions[i], d_mesh)
        drones.append(agent)
        if i == 0: leader_agent = agent
        
        # Tactical Command Handler
        def link_handler(a):
            async def on_msg(topic, payload, sender):
                # Handle target and mission commands from Mission Control or Leader
                if "goto_target" in topic or "dispatch_dots" in topic:
                    tgt = payload
                    if tgt and (tgt.get('x') is not None):
                        # 100 Task Mission Initiation (If not already active or if new target)
                        if not mission_ctrl.is_active:
                            await mission_ctrl.start_new_mission(float(tgt['x']), float(tgt['y']))
                        
                        # Assign drone its first/next sub-task
                        next_t = await mission_ctrl.get_next_task()
                        if next_t:
                            a.target = next_t
                            a.current_mission_target = tgt
                            print(f"[MISSION] {a.drone_id} assigned sub-task {a.target}")
                        else:
                            # Spread drones out in the red zone fallback
                            off_x = random.uniform(-6, 6)
                            off_y = random.uniform(-6, 6)
                            a.target = [float(tgt['x']) + off_x, float(tgt['y']) + off_y]
                            a.current_mission_target = tgt
                            print(f"[MISSION] {a.drone_id} heading to fallback target {a.target}")
                
                # Handle Emergency Stop / Reset
                if topic == config.TOPIC_ESTOP:
                    etype = payload.get("type")
                    if etype == "ESTOP":
                        a.emergency_stopped = True
                        print(f"[ESTOP] {a.drone_id} HALTED.")
                    elif etype == "RESET":
                        a.emergency_stopped = False
                        # If this drone was killed, revive it
                        if a.killed or not a.alive:
                            a.revive()
                        print(f"[RESET] {a.drone_id} RESUMED.")
                
                # Handle Manual Kill (Simulated Crash)
                elif topic == config.TOPIC_KILL:
                    target_id = payload.get("drone_id")
                    if target_id == a.drone_id:
                        a.killed = True
                        a.alive = False
                        a.status = "\U0001f480 CRASHED"
                        print(f"[CRASH] {a.drone_id} KILLED by operator.")
                
                # Takeover logic for LEADER
                if a.role == "decision" and topic.endswith("/task_done") and payload.get("event") == "CRASH":
                    crashed_id = payload.get("drone_id")
                    print(f"[TAKEOVER] Leader detected {crashed_id} crash! Re-dispatching swarm.")
                    if a.current_mission_target:
                        await a.mesh.broadcast({
                            "action": "goto_target",
                            "target_grid": a.current_mission_target
                        })
            return on_msg
            
        d_mesh.subscribe("nova/#", link_handler(agent))
        agent._run_task = asyncio.create_task(agent.run())

    print(f"\n[READY] 8 Strategic Units Ready via Global Mesh.")
    print("\nSelect target and click 'DISPATCH SWARM'. 0.5% failure probability active.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
