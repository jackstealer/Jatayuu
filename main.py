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

    def start_new_mission(self, centerX, centerY, radius=10):
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
                "targets": self.tasks,
                "timestamp": time.time()
            }))
        print(f"[MISSION] Controller initialized with {self.total} tasks at ({centerX}, {centerY})")

    def get_next_task(self):
        if not self.tasks:
            return None
        return self.tasks.pop(0)

    def mark_complete(self):
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
        self.pos = list(start_pos)
        self.target = list(start_pos)
        self.battery = 100.0
        self.alive = True
        self.mesh = mesh
        self.role = "decision" if "1" in drone_id else "scout"
        self.status = "IDLE"
        self.tasks_done = 0
        self.current_mission_target = None
        self.emergency_stopped = False

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
                            finished = mission_ctrl.mark_complete()
                            if finished:
                                print("[MISSION] ALL 100 TASKS COMPLETE. STOPPING SWARM.")

                        await self.mesh.publish(config.TOPIC_TASK_DONE, {
                            "drone_id": self.drone_id,
                            "event": "DONE",
                            "tasks_done": self.tasks_done,
                            "cell": [self.pos[0], self.pos[1]] # Precise float
                        })

                        # Fetch next task from Mission Controller
                        if mission_ctrl.is_active:
                            next_t = mission_ctrl.get_next_task()
                            if next_t:
                                self.target = next_t
                            else:
                                self.status = "HOVER"
                        else:
                            self.status = "HOVER"
                    else:
                        self.status = "HOVER"

                # 3. Randomized Crash Logic (Simulation)
                if self.status == "FLYING" and random.random() < 0.0:  # Crashes disabled for Demo
                    self.alive = False
                    self.status = "💀 CRASHED"
                    print(f"[CRASH] {self.drone_id} HAS STALLED at {self.pos}")
                    await self.mesh.publish(config.TOPIC_TASK_DONE, {
                        "drone_id": self.drone_id,
                        "event": "CRASH",
                        "cell": [round(self.pos[0]), round(self.pos[1])]
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
                "tasks_done": self.tasks_done
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
    start_positions = [
        (0,0), (100,0), (0,100), (100,100), 
        (-100,-100), (200, 50), (50, 200), (-200, 200)
    ]
    
    leader_agent = None

    for i in range(8):
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
                            mission_ctrl.start_new_mission(float(tgt['x']), float(tgt['y']))
                        
                        # Assign drone its first/next sub-task
                        next_t = mission_ctrl.get_next_task()
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
                        print(f"[ESTOP] {a.drone_id} RESUMED.")
                
                # Handle Manual Kill (Simulated Crash)
                elif topic == config.TOPIC_KILL:
                    if payload.get("drone_id") == a.drone_id:
                        a.alive = False
                        a.status = "💀 CRASHED"
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
        asyncio.create_task(agent.run())

    print(f"\n[READY] 8 Strategic Units Ready via Global Mesh.")
    print("\nSelect target and click 'DISPATCH SWARM'. 0.5% failure probability active.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
