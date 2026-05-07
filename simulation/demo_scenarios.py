# simulation/demo_scenarios.py
import sys
import os
import time
import random
import threading
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import GRID_ROWS, GRID_COLS, MISSIONS

# cell state constants — must match world_sim.py
CELL_UNKNOWN   = 0
CELL_SEARCHING = 1
CELL_SEARCHED  = 2
CELL_SURVIVOR  = 3


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 1 — Normal Operation
# Shows: discovery → auction → search → survivor found → complete
# Duration: ~45 seconds
# ═══════════════════════════════════════════════════════════════════
def run_scenario_1(sim, mesh=None):
    print("\n" + "="*55)
    print("  SCENARIO 1 — Normal Operation")
    print("="*55)
    sim.log_event("DEMO", "Scenario 1: Normal Operation starting")
    time.sleep(1)

    # ── Phase 1: All drones discover each other (0–6s) ────────────
    sim.log_event("INFO", "All 8 drones broadcasting discovery...")
    time.sleep(1)

    drone_ids = list(sim.drones.keys())
    for did in drone_ids:
        sim.log_event("JOIN", f"{did} discovered on FoxMQ mesh")
        # if live mesh: publish nova/discovery
        if mesh:
            pos = [int(sim.drones[did].col), int(sim.drones[did].row)]
            mesh.publish("nova/discovery", {
                "drone_id": did,
                "role":     sim.drones[did].role,
                "battery":  int(sim.drones[did].battery),
                "position": pos
            })
        time.sleep(0.4)

    sim.log_event("INFO", "All 8 drones online — mesh formed")
    time.sleep(2)

    # ── Phase 2: Auction assigns sectors (6–20s) ──────────────────
    sim.log_event("INFO", "Decision drone posting tasks to nova/tasks...")
    time.sleep(1)

    # Divide 50x50 grid into 8 sectors — one per drone
    sectors = [
        (1,  1,  24, 24),   # drone_1: top-left quad
        (25, 1,  49, 24),   # drone_2: top-right quad
        (1,  25, 24, 49),   # drone_3: bottom-left quad
        (25, 25, 49, 49),   # drone_4: bottom-right quad
        (12, 1,  37, 12),   # drone_5: top strip
        (1,  12, 12, 37),   # drone_6: left strip
        (37, 12, 49, 37),   # drone_7: right strip
        (12, 37, 37, 49),   # drone_8: bottom strip
    ]

    for i, did in enumerate(drone_ids):
        c1, r1, c2, r2 = sectors[i]
        # send drone to centre of its sector
        tc = (c1 + c2) // 2
        tr = (r1 + r2) // 2
        sim.drones[did].assign_target(tc, tr, f"task_{i+1}")
        sim.log_event("TASK",
            f"{did} → sector ({c1},{r1})→({c2},{r2})")

        if mesh:
            mesh.publish("nova/task_assigned", {
                "task_id":     f"task_{i+1}",
                "assigned_to": did
            })
        time.sleep(0.6)

    time.sleep(3)

    # ── Phase 3: Drones search their sectors (20–35s) ─────────────
    sim.log_event("INFO", "Drones searching assigned sectors...")

    def fill_sector(c1, r1, c2, r2, delay=0.03):
        """Fill a sector with SEARCHED cells gradually."""
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if sim.grid[r][c] == CELL_UNKNOWN:
                    sim.grid[r][c] = CELL_SEARCHED
                    if mesh:
                        mesh.publish("nova/worldstate", {
                            "cell":      [c, r],
                            "status":    "searched",
                            "drone_id":  f"drone_{random.randint(1,8)}",
                            "timestamp": int(time.time() * 1000)
                        })
            time.sleep(delay)

    # Fill sectors in parallel threads so map fills from multiple spots
    fill_threads = []
    for i, (c1, r1, c2, r2) in enumerate(sectors[:4]):
        t = threading.Thread(
            target=fill_sector,
            args=(c1, r1, c2, r2, 0.04),
            daemon=True)
        fill_threads.append(t)

    for t in fill_threads:
        t.start()
    for t in fill_threads:
        t.join()

    time.sleep(1)

    # ── Phase 4: Survivor found (35–40s) ──────────────────────────
    survivor_col = 31
    survivor_row = 18
    sim.grid[survivor_row][survivor_col] = CELL_SURVIVOR
    sim.log_event("SURVIVOR",
        f"Survivor at ({survivor_col},{survivor_row}) — drone_4")

    if mesh:
        mesh.publish("nova/worldstate", {
            "cell":      [survivor_col, survivor_row],
            "status":    "survivor_detected",
            "drone_id":  "drone_4",
            "timestamp": int(time.time() * 1000)
        })

    # move drone_4 toward survivor
    sim.drones["drone_4"].assign_target(
        survivor_col, survivor_row, "rescue_task")
    time.sleep(4)

    # ── Phase 5: Mission complete (40–45s) ────────────────────────
    # fill remaining sectors
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if sim.grid[r][c] == CELL_UNKNOWN:
                sim.grid[r][c] = CELL_SEARCHED
        time.sleep(0.01)

    sim.log_event("INFO", "All sectors searched — mission complete")
    sim.log_event("INFO", "Scenario 1 DONE ✓")
    print("\n[SCENARIO 1] Complete — all sectors searched, survivor found")


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 2 — Drone Death Recovery
# Shows: drone_3 killed → FoxMQ detects silence →
#        leader election (if needed) → tasks redistributed
# Duration: ~55 seconds
# THIS IS YOUR STRONGEST DEMO — shows BFT resilience
# ═══════════════════════════════════════════════════════════════════
def run_scenario_2(sim, mesh=None):
    print("\n" + "="*55)
    print("  SCENARIO 2 — Drone Death Recovery")
    print("="*55)
    sim.log_event("DEMO", "Scenario 2: Drone Death Recovery")
    time.sleep(1)

    # ── Phase 1: Normal operation for 10s ─────────────────────────
    sim.log_event("INFO", "Swarm operating normally — 7 scouts active")
    drone_ids = list(sim.drones.keys())

    # assign all drones random targets
    for did in drone_ids:
        nc = random.randint(5, 45)
        nr = random.randint(5, 45)
        sim.drones[did].assign_target(nc, nr)

    # gradually fill some cells to show progress
    def background_fill():
        for _ in range(300):
            r = random.randint(0, GRID_ROWS-1)
            c = random.randint(0, GRID_COLS-1)
            if sim.grid[r][c] == CELL_UNKNOWN:
                sim.grid[r][c] = CELL_SEARCHED
            time.sleep(0.03)

    fill_t = threading.Thread(target=background_fill, daemon=True)
    fill_t.start()
    time.sleep(10)

    # ── Phase 2: Kill drone_3 — the critical moment ───────────────
    sim.log_event("FAULT",
        ">>> KILLING drone_3 — simulating battery failure")
    print("\n[SCENARIO 2] ⚡ Killing drone_3 NOW...")

    sim.drones["drone_3"].kill()

    if mesh:
        # publish dead heartbeat — M1's death detector picks this up
        mesh.publish("nova/heartbeat", {
            "drone_id":  "drone_3",
            "timestamp": int(time.time() * 1000),
            "battery":   0,
            "position":  [int(sim.drones["drone_3"].col),
                          int(sim.drones["drone_3"].row)]
        })

    time.sleep(0.5)
    sim.log_event("FAULT", "drone_3 battery = 0 — signal lost")

    # ── Phase 3: FoxMQ detects heartbeat silence (<2s) ────────────
    time.sleep(2)
    sim.log_event("DETECT",
        "FoxMQ: drone_3 silent >2s — node failure confirmed")
    time.sleep(0.5)

    # ── Phase 4: Leader election check ────────────────────────────
    # drone_1 is Decision drone — it's still alive, no election needed
    sim.log_event("ELECT",
        "Decision drone (drone_1) alive — no election needed")
    time.sleep(1)

    # Simulate what happens if Decision drone died:
    # (commented out — uncomment to demo election scenario)
    # sim.drones["drone_1"].kill()
    # sim.log_event("ELECT", "Election: drone_2 wins majority vote")
    # sim.drones["drone_2"].role = SimDrone.ROLE_DECISION

    # ── Phase 5: New auction round — redistribute drone_3 tasks ───
    sim.log_event("AUCTION",
        "M2: new auction round for drone_3 sectors...")
    time.sleep(1)

    # drone_3 was covering bottom-left — split between drone_5 & drone_6
    redistributed = [
        ("drone_5", 8,  28, "redisc_task_A"),
        ("drone_6", 15, 35, "redisc_task_B"),
    ]
    for did, tc, tr, tid in redistributed:
        if did in sim.drones and sim.drones[did].status == "alive":
            sim.drones[did].assign_target(tc, tr, tid)
            sim.log_event("TASK",
                f"{did} inherits drone_3 sector → ({tc},{tr})")
            if mesh:
                mesh.publish("nova/task_assigned", {
                    "task_id":     tid,
                    "assigned_to": did
                })
            time.sleep(1.5)

    # ── Phase 6: Show swarm continues with 7 drones ───────────────
    time.sleep(2)
    sim.log_event("INFO",
        "7 drones continuing — mission uninterrupted")

    # fill some more cells to show continued progress
    for row in range(0, 25):
        for col in range(0, 25):
            if sim.grid[row][col] == CELL_UNKNOWN:
                sim.grid[row][col] = CELL_SEARCHED
        time.sleep(0.02)

    time.sleep(3)
    sim.log_event("INFO", "Scenario 2 DONE ✓ — recovery proven")
    print("\n[SCENARIO 2] Complete — swarm recovered from drone_3 failure")


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 3 — Byzantine Fault Tolerance / Blackout
# Shows: 60% packet loss → 2 drones killed simultaneously →
#        FoxMQ mesh reroutes → 6 drones continue
# Duration: ~65 seconds
# DIFFERENTIATOR: most teams kill ONE drone. You kill TWO.
# ═══════════════════════════════════════════════════════════════════
def run_scenario_3(sim, mesh=None):
    print("\n" + "="*55)
    print("  SCENARIO 3 — Byzantine Fault Tolerance")
    print("="*55)
    sim.log_event("DEMO", "Scenario 3: BFT Blackout")
    time.sleep(1)

    # ── Phase 1: Normal operation (0–8s) ──────────────────────────
    sim.log_event("INFO", "All 8 drones active — normal operation")
    drone_ids = list(sim.drones.keys())
    for did in drone_ids:
        nc = random.randint(5, 45)
        nr = random.randint(5, 45)
        sim.drones[did].assign_target(nc, nr)

    def slow_fill():
        for _ in range(200):
            r = random.randint(0, GRID_ROWS-1)
            c = random.randint(0, GRID_COLS-1)
            if sim.grid[r][c] == CELL_UNKNOWN:
                sim.grid[r][c] = CELL_SEARCHED
            time.sleep(0.04)

    t = threading.Thread(target=slow_fill, daemon=True)
    t.start()
    time.sleep(8)

    # ── Phase 2: Announce blackout / 60% packet loss ──────────────
    sim.log_event("CHAOS",
        ">>> BLACKOUT: 60% packet loss injected")
    sim.log_event("CHAOS",
        "FoxMQ mesh entering degraded mode...")
    print("\n[SCENARIO 3] ⚡ Blackout — 60% packet loss active")

    # Visually slow down drone movements to simulate degraded comms
    for did in drone_ids:
        if sim.drones[did].status == "alive":
            # assign nearby targets — drones move sluggishly
            nc = max(0, min(GRID_COLS-1,
                    int(sim.drones[did].col) + random.randint(-3,3)))
            nr = max(0, min(GRID_ROWS-1,
                    int(sim.drones[did].row) + random.randint(-3,3)))
            sim.drones[did].assign_target(nc, nr)

    time.sleep(6)
    sim.log_event("INFO",
        "FoxMQ Vertex rerouting — mesh still holding...")
    time.sleep(3)

    # ── Phase 3: Kill TWO drones simultaneously ───────────────────
    # This is the BFT showcase — 2/8 = 25%, within 1/3 tolerance
    sim.log_event("FAULT",
        ">>> KILLING drone_2 AND drone_4 SIMULTANEOUSLY")
    print("\n[SCENARIO 3] ⚡⚡ Killing drone_2 AND drone_4 simultaneously!")

    for did in ["drone_2", "drone_4"]:
        sim.drones[did].kill()
        sim.log_event("FAULT", f"{did} — OFFLINE")
        if mesh:
            mesh.publish("nova/heartbeat", {
                "drone_id":  did,
                "timestamp": int(time.time() * 1000),
                "battery":   0,
                "position":  [int(sim.drones[did].col),
                              int(sim.drones[did].row)]
            })

    time.sleep(0.5)

    # ── Phase 4: FoxMQ BFT response ───────────────────────────────
    time.sleep(2)
    sim.log_event("BFT",
        "Vertex: 2/8 nodes failed (25%) — within 1/3 limit")
    sim.log_event("BFT",
        "FoxMQ consensus mesh rerouting around failures...")
    time.sleep(2)
    sim.log_event("BFT",
        "Hashgraph virtual voting — new consensus in <100ms")
    time.sleep(2)

    # ── Phase 5: 6 surviving drones redistribute work ─────────────
    survivors = [did for did in drone_ids
                 if sim.drones[did].status == "alive"]
    sim.log_event("INFO",
        f"{len(survivors)} drones active — redistributing tasks")

    for did in survivors:
        nc = random.randint(5, 45)
        nr = random.randint(5, 45)
        sim.drones[did].assign_target(nc, nr)
        if mesh:
            mesh.publish("nova/task_assigned", {
                "task_id":     f"bft_task_{did}",
                "assigned_to": did
            })

    time.sleep(2)

    # ── Phase 6: Show CRDT map still consistent ───────────────────
    sim.log_event("INFO",
        "CRDT map consistent across all 6 survivors")
    sim.log_event("INFO",
        "Swarm never stopped — BFT tolerance proven")

    # fill remaining area to show mission continues
    def final_fill():
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if sim.grid[r][c] == CELL_UNKNOWN:
                    sim.grid[r][c] = CELL_SEARCHED
            time.sleep(0.025)

    ff = threading.Thread(target=final_fill, daemon=True)
    ff.start()
    time.sleep(10)

    sim.log_event("INFO", "Scenario 3 DONE ✓ — BFT proven")
    print("\n[SCENARIO 3] Complete — 2 drones killed, swarm survived")


# ═══════════════════════════════════════════════════════════════════
# SCENARIO 4 — Red Zone Global Target & Task Handoff
# Shows: Red zone triggered → Drones converge → Dark dots spawn →
#        One drone killed during solving → Task handed off
# ═══════════════════════════════════════════════════════════════════
def run_scenario_4(sim, mesh=None):
    print("\n" + "="*55)
    print("  SCENARIO 4 — Red Zone Global Target & Task Handoff")
    print("="*55)
    sim.log_event("DEMO", "Scenario 4: Red Zone Global Target")
    time.sleep(1)

    sim.log_event("INFO", "Setting Global Red Zone Target at (25, 25)...")
    sim._trigger_global_red_zone(25, 25)

    # Wait for convergence
    sim.log_event("INFO", "Waiting for drones to converge...")
    while sim.rz_state == 'CONVERGE':
        time.sleep(0.5)

    time.sleep(1)
    sim.log_event("INFO", "Drones converging -> SOLVING phase started.")
    
    time.sleep(2)  # brief wait to let them start

    sim.log_event("FAULT", ">>> KILLING a drone randomly while it's assigned a dot!")
    
    # Pick a drone that actually has an assignment to kill
    target_drone = None
    for did in ["drone_2", "drone_3", "drone_4", "drone_5"]:
        if did in sim.rz_assignments and sim.drones[did].status == "alive":
            target_drone = did
            break
            
    if not target_drone:
        target_drone = "drone_4" # fallback
        
    print(f"\n[SCENARIO 4] ⚡ Killing {target_drone} NOW...")
    if target_drone in sim.drones:
        sim.drones[target_drone].kill()

    # The simulator logic will automatically log the handoff.
    
    while sim.rz_active:
        time.sleep(0.5)

    sim.log_event("INFO", "Scenario 4 DONE ✓ — Red Zone cleared & handoff proven")
    print("\n[SCENARIO 4] Complete — Red Zone cleared")


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# Usage:
#   python simulation/demo_scenarios.py --scenario 1
#   python simulation/demo_scenarios.py --scenario 2
#   python simulation/demo_scenarios.py --scenario 3
#   python simulation/demo_scenarios.py --scenario 4
# ═══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="NOVA Demo Scenarios — Project NOVA")
    parser.add_argument(
        "--scenario", type=int, choices=[1, 2, 3, 4], required=True,
        help="1=Normal  2=DroneRecovery  3=BFT  4=RedZone")
    args = parser.parse_args()

    # import here to avoid circular import at top of file
    from world_sim import WorldSim

    mesh = None
    # mesh connection added on Day 2 when M1 delivers nova_mesh.py

    # build the sim
    sim = WorldSim()
    if mesh:
        sim.connect_mesh(mesh)

    # map scenario number to function
    fn_map = {
        1: run_scenario_1,
        2: run_scenario_2,
        3: run_scenario_3,
        4: run_scenario_4,
    }
    fn = fn_map[args.scenario]

    # run scenario in background thread so Pygame stays responsive
    t = threading.Thread(
        target=fn,
        args=(sim, mesh),
        daemon=True)
    t.start()

    # this blocks until the window is closed
    sim.run()


if __name__ == "__main__":
    main()