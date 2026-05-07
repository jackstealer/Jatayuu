"""
test_mesh.py — M1's Integrated Test Suite
========================================
This test proves the entire M1 networking stack works.
Requires paho-mqtt and an MQTT broker (like Mosquitto) running on 1883.

Run it like this:
    python test_mesh.py

What it tests:
    1. Two drone nodes start up
    2. They discover each other via NOVA_HELLO
    3. Drone 1 publishes a heartbeat
    4. Drone 2 receives it
    5. Drone 1 publishes a task token
    6. Drone 2 receives it and sends a bid
    7. Chaos proxy drops packets based on distance/chaos level
    8. E-STOP broadcast → both drones freeze
    9. Routing table recalculates shortest paths

Expected output:
    NOVA M1 MESH TEST SUITE
    [PASS] drone_1 created
    [PASS] drone_2 created
    ...
    All tests passed!
"""

import asyncio
import time
import json

# Handle both package and direct execution
try:
    from mesh.drone_node import DroneNode, Role
    from mesh.nova_mesh import NovaMesh, DRONE_NETWORK_CONFIG
    from mesh.nova_vertex import VertexNode, create_vertex_node
    from mesh.chaos_proxy import ChaosProxy
except ImportError:
    from drone_node import DroneNode, Role
    from nova_mesh import NovaMesh, DRONE_NETWORK_CONFIG
    from nova_vertex import VertexNode, create_vertex_node
    from chaos_proxy import ChaosProxy


# ─────────────────────────────────────────────
# SIMPLE DRONE SUBCLASS FOR TESTING
# ─────────────────────────────────────────────
class TestDrone(DroneNode):
    """A minimal drone for testing M1's mesh."""

    def __init__(self, drone_id: str, role: str, x: float, y: float):
        super().__init__(drone_id, role, x, y)
        self.received_messages = []
        self.vertex: VertexNode = None

    async def on_start(self):
        """Subscribe to topics after starting."""
        if self.vertex:
            # Subscribe to all nova topics
            self.vertex.subscribe("nova/#", self._on_any_message)

    async def _on_any_message(self, topic: str, payload: dict, sender: str):
        self.received_messages.append({
            "topic": topic,
            "payload": payload,
            "sender": sender,
            "received_at": time.time(),
        })
        # Route through DroneNode handler for PEER/ESTOP processing
        await self.handle_message(payload)

    async def on_message(self, msg: dict):
        """Handle custom messages for the test drone if needed."""
        pass


# ─────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────
async def run_tests():
    print("\n" + "="*55)
    print("  NOVA M1 MESH TEST SUITE")
    print("="*55 + "\n")

    passed = 0
    failed = 0

    def check(condition: bool, test_name: str):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {test_name}")
            passed += 1
        else:
            print(f"  [FAIL] {test_name}")
            failed += 1

    # ── TEST 1: Create two drones ──────────────────
    print("Test 1: Creating drone nodes...")
    drone1 = TestDrone("drone_1", Role.SCOUT, x=50.0, y=50.0)
    drone2 = TestDrone("drone_2", Role.MAPPER, x=80.0, y=60.0)
    check(drone1.drone_id == "drone_1", "drone_1 created")
    check(drone2.drone_id == "drone_2", "drone_2 created")
    check(drone1.state.role == Role.SCOUT, "drone_1 role is scout")

    # ── TEST 2: Start mesh and vertex ─────────────
    print("\nTest 2: Starting mesh network...")

    # Create vertex nodes
    try:
        mock_config = {d: ("MOCK", 1883) for d in DRONE_NETWORK_CONFIG}
        vertex1 = await create_vertex_node("drone_1", network_config=mock_config, chaos_level=0.0)
        vertex2 = await create_vertex_node("drone_2", network_config=mock_config, chaos_level=0.0)
        
        drone1.mesh = vertex1.mesh
        drone2.mesh = vertex2.mesh
        drone1.vertex = vertex1
        drone2.vertex = vertex2

        # Start drones (heartbeat loop etc)
        await drone1.start()
        await drone2.start()

        check(drone1.mesh is not None, "drone_1 mesh started")
        check(drone2.mesh is not None, "drone_2 mesh started")
        
    except Exception as e:
        check(False, f"mesh started failed: {e}")
        return

    # ── TEST 3: Peer discovery ─────────────────────
    print("\nTest 3: Peer discovery...")
    for i in range(3):
        peers1 = await vertex1.discover()
        await asyncio.sleep(1.0)
        if len(vertex1.routing.known_drones) >= 2:
            break
        print(f"  [RETRY {i+1}] Discovery only found {len(vertex1.routing.known_drones)} nodes...")
    
    check(len(vertex1.routing.known_drones) >= 2, f"discovery found {len(vertex1.routing.known_drones)} nodes")

    # ── TEST 4: Heartbeat publishing ──────────────
    print("\nTest 4: Heartbeat...")
    # Manual trigger if loop didn't run yet
    await vertex1.publish("nova/heartbeat", drone1.get_status())
    await asyncio.sleep(1.0)

    # Check drone2 received something
    # Filter only hartbeats from drone_1
    heartbeat_received = any(
        m["topic"] == "nova/heartbeat" and m["sender"] == "drone_1"
        for m in drone2.received_messages
    )
    check(heartbeat_received, "drone_2 received heartbeat from drone_1")

    # ── TEST 5: Task publishing ───────────────────
    print("\nTest 5: Task auction...")
    task_token = {
        "type": "TASK_TOKEN",
        "task_id": "explore_zone_A",
        "priority": 8,
        "expires_ms": 200,
    }
    await vertex1.publish_task(task_token)
    await asyncio.sleep(1.0)
    
    task_received = any(
        m["topic"] == "nova/tasks" and m["payload"].get("task_id") == "explore_zone_A"
        for m in drone2.received_messages
    )
    check(task_received, "drone_2 received task from drone_1")

    # ── TEST 6: Bid response ──────────────────────
    print("\nTest 6: Bid response...")
    bid = {
        "type": "BID",
        "task_id": "explore_zone_A",
        "bidder": "drone_2",
        "score": 87,
    }
    await vertex2.publish_bid(bid)
    await asyncio.sleep(1.0)
    
    bid_received = any(
        m["topic"] == "nova/bids" and m["payload"].get("bidder") == "drone_2"
        for m in drone1.received_messages
    )
    check(bid_received, "drone_1 received bid from drone_2")

    # ── TEST 7: Survivor signal ───────────────────
    print("\nTest 7: Survivor detection signal...")
    survivor = {
        "type": "SURVIVOR",
        "cell_id": "45_120",
        "confidence": 0.82,
        "detected_by": "drone_1",
    }
    await vertex1.publish_survivor(survivor)
    await asyncio.sleep(1.0)
    
    survivor_received = any(
        m["topic"] == "nova/survivor" and m["payload"].get("cell_id") == "45_120"
        for m in drone2.received_messages
    )
    check(survivor_received, "drone_2 received survivor signal from drone_1")

    # ── TEST 8: Routing table ─────────────────────
    print("\nTest 8: Routing table...")
    # Add a mock relay hop: drone_1 -> drone_3 -> drone_2
    vertex1.routing.update_link("drone_1", "drone_3", quality=0.8)
    vertex1.routing.update_link("drone_3", "drone_2", quality=0.8)
    # Direct link is weaker
    vertex1.routing.update_link("drone_1", "drone_2", quality=0.2)
    vertex1.routing.recalculate()
    
    next_hop = vertex1.routing.get_next_hop("drone_2")
    check(next_hop == "drone_3", f"multi-hop routing picked {next_hop} (expected drone_3)")

    # ── TEST 9: Chaos proxy ───────────────────────
    print("\nTest 9: Chaos proxy...")
    chaos = vertex1.chaos
    chaos.set_chaos_level(0.4)   # 40% packet loss

    dropped = 0
    total = 100
    for _ in range(total):
        should_deliver, _ = chaos.check_delivery(
            "drone_1", "drone_2",
            sender_pos=(50, 50),
            receiver_pos=(80, 60)
        )
        if not should_deliver:
            dropped += 1

    # With 40% chaos we expect roughly 30-50% drops
    check(25 <= dropped <= 55, f"chaos proxy dropped {dropped}/{total} packets (~{dropped}% loss)")

    # ── TEST 10: Emergency stop ───────────────────
    print("\nTest 10: Emergency stop...")
    await vertex1.send_estop(issued_by="test_operator")
    await asyncio.sleep(0.5)
    
    check(drone1.emergency_stopped, "drone_1 processed E-STOP")
    check(drone2.emergency_stopped, "drone_2 processed E-STOP")

    # ── TEST 11: Blackout zone ────────────────────
    print("\nTest 11: Blackout zone...")
    chaos.add_blackout_zone(center_x=100, center_y=100, radius=30)
    should_deliver, reason = chaos.check_delivery(
        "drone_1", "drone_2",
        sender_pos=(50, 50),
        receiver_pos=(105, 105)   # inside blackout zone
    )
    check(not should_deliver and reason == "BLACKOUT_ZONE", "blackout zone blocks delivery")

    # ── TEST 12: Drone status ────────────────────
    print("\nTest 12: Drone status...")
    status = drone1.get_status()
    check("drone_id" in status, "status report contains drone_id")
    check(status["emergency_stopped"] == True, "status report shows E-STOP active")

    # ── RESULTS ────────────────────────────────────
    print("\n" + "="*55)
    print(f"  Results: {passed} passed, {failed} failed")
    print("="*55)

    if failed == 0:
        print("\n  All tests passed! M1's mesh stack is ready.")
    else:
        print(f"\n  {failed} test(s) failed. Check logs above.")

    # Clean up
    print("\nCleaning up...")
    await drone1.stop()
    await drone2.stop()
    await vertex1.stop()
    await vertex2.stop()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"FATAL ERROR: {e}")