"""
nova_vertex.py — M1's file
========================
This is the Vertex node lifecycle manager.
It coordinates the mesh and the drone node.
"""

import asyncio
from typing import Optional, Dict

# Mesh internal imports - handle both package and direct execution
try:
    from mesh.nova_mesh import NovaMesh, DRONE_NETWORK_CONFIG
    from mesh.routing_table import RoutingTable
    from mesh.chaos_proxy import ChaosProxy
except ImportError:
    from nova_mesh import NovaMesh, DRONE_NETWORK_CONFIG
    from routing_table import RoutingTable
    from chaos_proxy import ChaosProxy

# Root import - assume root is in sys.path
try:
    import config
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config

class VertexNode:
    """
    Manages the lifecycle of a single drone's networking stack.
    """
    def __init__(self, drone_id: str, network_config: Dict = None, chaos_level: float = 0.0):
        self.drone_id = drone_id
        self.network_config = network_config or DRONE_NETWORK_CONFIG
        
        # Get broker for this drone
        broker_host, broker_port = self.network_config.get(drone_id, ("127.0.0.1", 1883))
        
        self.mesh = NovaMesh(drone_id, broker_host, broker_port)
        self.routing = RoutingTable(drone_id)
        self.chaos = ChaosProxy()
        self.chaos.set_chaos_level(chaos_level)
        
        # Inject dependencies
        self.mesh.routing = self.routing
        self.mesh.chaos = self.chaos

    async def start(self):
        """Start the vertex node."""
        await self.mesh.start()
        print(f"[VERTEX] {self.drone_id} mesh started.")
        
        # Self-discovery (listen for others)
        self.mesh.subscribe(config.TOPIC_DISCOVERY, self._on_discovery)
        self.mesh.subscribe(config.TOPIC_HEARTBEAT, self._on_heartbeat)
        self.mesh.subscribe(config.TOPIC_ESTOP, self._on_estop)

    async def stop(self):
        """Stop the vertex node."""
        await self.mesh.stop()

    async def discover(self) -> Dict:
        """Broadcast discovery and wait for responses."""
        await self.mesh.publish(config.TOPIC_DISCOVERY, {
            "type": "NOVA_HELLO",
            "drone_id": self.drone_id,
        })
        # Wait a bit for responses
        await asyncio.sleep(0.5)
        return self.routing.known_drones

    def subscribe(self, topic: str, callback):
        """Subscribe to a topic."""
        self.mesh.subscribe(topic, callback)

    async def publish(self, topic: str, payload: dict):
        """Higher level publish."""
        await self.mesh.publish(topic, payload)

    async def publish_task(self, task_token: dict):
        """Publish a task for bidding."""
        await self.mesh.publish(config.TOPIC_TASKS, task_token)

    async def publish_bid(self, bid: dict):
        """Publish a bid for a task."""
        await self.mesh.publish(config.TOPIC_BIDS, bid)

    async def publish_survivor(self, survivor: dict):
        """Publish a detected survivor signal."""
        await self.mesh.publish(config.TOPIC_SURVIVOR, survivor)

    async def send_estop(self, issued_by: str = "operator"):
        """Broadcast emergency stop."""
        await self.mesh.publish(config.TOPIC_ESTOP, {
            "type": "EMERGENCY_STOP",
            "issued_by": issued_by,
        })

    # Internal MQTT callbacks to update routing
    async def _on_discovery(self, topic, payload, sender):
        if sender != self.drone_id:
            # Update routing table
            self.routing.update_link(self.drone_id, sender, quality=0.9)
            self.routing.recalculate()
            
            # If they just said hello, we should say hello back (if not already done)
            if payload.get("type") == "NOVA_HELLO":
                await self.mesh.publish(config.TOPIC_DISCOVERY, {
                    "type": "NOVA_HELLO_ACK",
                    "drone_id": self.drone_id,
                })

    async def _on_heartbeat(self, topic, payload, sender):
        if sender != self.drone_id:
            # Use heartbeat to update link quality if simulated distance is in payload
            pass

    async def _on_estop(self, topic, payload, sender):
        # We don't do much here, DroneNode handles its own subscription
        pass

async def create_vertex_node(drone_id: str, network_config: Dict = None, chaos_level: float = 0.0) -> VertexNode:
    """Factory function for test suite."""
    node = VertexNode(drone_id, network_config, chaos_level)
    await node.start()
    return node
