# integration/verify_integration.py
import asyncio
import threading
import sys
import os
import time

# Headless mode for Pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'

# Add root of Swarm to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from mesh.nova_vertex import VertexNode, create_vertex_node
from simulation.world_sim import WorldSim
from swarm.crdt_map import CELL_SURVIVOR

async def run_test():
    print("\n" + "="*50)
    print("  NOVA INTEGRATION VERIFIER")
    print("="*50)

    # 1. Setup Mesh (Mock)
    DRONE_ID = "test_verifier"
    from mesh.nova_mesh import DRONE_NETWORK_CONFIG
    network_config = {d: ("MOCK", 1883) for d in DRONE_NETWORK_CONFIG}
    network_config[DRONE_ID] = ("MOCK", 1883)
    
    print("[TEST] Starting Vertex Node...")
    vertex = await create_vertex_node(DRONE_ID, network_config=network_config)
    
    # 2. Setup Simulation
    print("[TEST] Starting World Sim...")
    sim = WorldSim()
    sim.connect_mesh(vertex)
    
    # Run sim in a background thread
    def sim_worker():
        try:
            sim.run()
        except SystemExit:
            pass
    
    sim_thread = threading.Thread(target=sim_worker, daemon=True)
    sim_thread.start()
    
    await asyncio.sleep(2.0) # Wait for sim to initialize
    
    # 3. Test Injection: Send a survivor signal
    print("[TEST] Injecting survivor signal into mesh...")
    test_x, test_y = 10, 20
    # M1 format uses x, y (0-200). M3 expects cell [x,y] or x/y from heartbeat.
    # In world_sim.py, _on_worldstate expects "cell": [x, y] where x=col, y=row.
    survivor_msg = {
        "cell": [test_x, test_y],
        "status": "survivor_detected",
        "drone_id": "discovery_drone"
    }
    await vertex.publish("nova/worldstate", survivor_msg)
    
    # 4. Verification: Check sim grid
    print("[TEST] Waiting for processing...")
    await asyncio.sleep(3.0)
    
    state = sim.grid[test_y][test_x]
    if state == CELL_SURVIVOR:
        print(f"[PASS] Simulation grid updated correctly at ({test_x}, {test_y})")
    else:
        print(f"[FAIL] Simulation grid state is {state}, expected {CELL_SURVIVOR}")
        sys.exit(1)

    # 5. Test Injection 2: Mission change
    print("[TEST] Injecting mission change...")
    await vertex.publish("nova/mission", {"mission": "Fire", "drone_id": "other_operator"})
    await asyncio.sleep(2.0)
    if sim.mission == "Fire":
        print("[PASS] Simulation mission changed to Fire")
    else:
        print(f"[FAIL] Simulation mission is {sim.mission}, expected Fire")
        sys.exit(1)

    print("\n" + "="*50)
    print("  ALL INTEGRATION TESTS PASSED!")
    print("="*50)
    
    # Cleanup
    sim.running = False
    await vertex.stop()
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_test())
