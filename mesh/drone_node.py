"""
drone_node.py — M1's file
========================
This is the BASE CLASS for every drone in NOVA.
Think of it like a blueprint. Scout, Mapper, Relay, Decision drones
all inherit from this class and get these features for free.

What this file does:
- Gives every drone an ID, position, battery, role
- Starts the heartbeat (shouts "I am alive!" every 500ms)
- Tracks which other drones are alive or dead
- Handles the EMERGENCY STOP signal
"""

import asyncio
import json
import time
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Callable

# Root import - assume root is in sys.path
try:
    import config
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config


# ─────────────────────────────────────────────
# DRONE ROLES — what job can a drone have?
# ─────────────────────────────────────────────
class Role:
    SCOUT    = "scout"      # explores unknown areas, finds survivors
    MAPPER   = "mapper"     # builds the shared map
    RELAY    = "relay"      # bridges communication gaps in mesh
    DECISION = "decision"   # runs the auction, makes task assignments
    ANCHOR   = "anchor"     # stays still, gives GPS-free positioning


# ─────────────────────────────────────────────
# DRONE STATE — everything about one drone
# ─────────────────────────────────────────────
@dataclass
class DroneState:
    drone_id: str
    role: str
    x: float                          # position on the 200x200 grid
    y: float
    battery: float = 100.0            # percentage 0-100
    alive: bool = True
    current_task: Optional[str] = None
    last_seen: float = field(default_factory=time.time)
    capabilities: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def is_stale(self, timeout: float = 2.0) -> bool:
        """Returns True if drone hasn't sent heartbeat in 2 seconds — it's dead."""
        return (time.time() - self.last_seen) > timeout


# ─────────────────────────────────────────────
# BASE DRONE NODE
# ─────────────────────────────────────────────
class DroneNode:
    """
    Every drone in NOVA is a DroneNode.

    How to use:
        class ScoutDrone(DroneNode):
            async def on_start(self):
                await self.explore_frontier()

    What you get for free by inheriting this:
        - self.state          → your drone's current state
        - self.peers          → dictionary of all known drones
        - self.mesh           → the UDP mesh (set by NovaMesh)
        - self.send(msg)      → send a message to the mesh
        - self.heartbeat loop → automatically runs every 500ms
        - self.peer monitor   → detects when other drones die
    """

    def __init__(self, drone_id: str, role: str, x: float, y: float,
                 capabilities: list = None):
        self.state = DroneState(
            drone_id=drone_id,
            role=role,
            x=x,
            y=y,
            capabilities=capabilities or [],
        )
        self.drone_id = drone_id

        # All known drones — updated by heartbeats received
        # key = drone_id, value = DroneState
        self.peers: Dict[str, DroneState] = {}

        # Callbacks registered by higher layers
        # e.g. when a peer dies, swarm logic is notified
        self._on_peer_died_callbacks: list[Callable] = []
        self._on_peer_joined_callbacks: list[Callable] = []
        self._on_estop_callbacks: list[Callable] = []

        # Set to True when emergency stop is received
        self.emergency_stopped = False

        # Reference to the mesh — injected by NovaMesh after creation
        self.mesh = None

        # asyncio tasks running in background
        self._tasks = []

        print(f"[DRONE] {drone_id} created | role={role} | pos=({x},{y})")

    # ─────────────────────────────────────────
    # LIFECYCLE — start and stop
    # ─────────────────────────────────────────

    async def start(self):
        """Start the drone — begins heartbeat and peer monitoring."""
        print(f"[DRONE] {self.drone_id} starting...")

        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._peer_monitor_loop()),
            asyncio.create_task(self._battery_drain_loop()),
        ]

        # Let subclasses do their own startup
        await self.on_start()
        print(f"[DRONE] {self.drone_id} is online | role={self.state.role}")

    async def stop(self):
        """Stop the drone — cancel all background tasks."""
        for task in self._tasks:
            task.cancel()
        print(f"[DRONE] {self.drone_id} stopped.")

    async def on_start(self):
        """
        Override this in subclasses to add startup behaviour.
        Example: Scout drone starts exploring here.
        """
        pass

    # ─────────────────────────────────────────
    # HEARTBEAT — "I am alive!"
    # ─────────────────────────────────────────

    async def _heartbeat_loop(self):
        """
        Every 500ms, broadcast heartbeat.
        Keeps running even during emergency stop so dashboard sidebar stays live.
        """
        while self.state.alive:
            heartbeat = {
                "type": "HEARTBEAT",
                "drone_id": self.drone_id,
                "role": self.state.role,
                "x": self.state.x,
                "y": self.state.y,
                "battery": round(self.state.battery, 1),
                "current_task": self.state.current_task,
                "capabilities": self.state.capabilities,
                "timestamp": time.time(),
                "alive": not self.emergency_stopped,
            }
            if self.mesh:
                await self.mesh.publish(config.TOPIC_HEARTBEAT, heartbeat)

            await asyncio.sleep(0.5)   # every 500ms

    # ─────────────────────────────────────────
    # PEER MONITOR — detect dead drones
    # ─────────────────────────────────────────

    async def _peer_monitor_loop(self):
        """
        Every 1 second, check all known peers.
        If a peer hasn't sent a heartbeat in 2 seconds → it's dead.
        Notify the swarm logic layer so it can re-assign tasks.
        """
        while True:
            dead_peers = []
            for peer_id, peer_state in list(self.peers.items()):
                if peer_state.alive and peer_state.is_stale(timeout=2.0):
                    peer_state.alive = False
                    dead_peers.append(peer_id)
                    print(f"[DRONE] {self.drone_id} detected: {peer_id} is DEAD "
                          f"(silent for >2s)")

            # Notify swarm logic for each dead peer
            for peer_id in dead_peers:
                for cb in self._on_peer_died_callbacks:
                    await cb(peer_id, self.peers[peer_id])

            await asyncio.sleep(1.0)

    # ─────────────────────────────────────────
    # BATTERY DRAIN — realistic simulation
    # ─────────────────────────────────────────

    async def _battery_drain_loop(self):
        """
        Drain battery slowly over time.
        Relay drones drain faster (they transmit more).
        Anchor drones drain slowest (stationary).
        """
        drain_rates = {
            Role.SCOUT:    0.05,   # % per second
            Role.MAPPER:   0.04,
            Role.RELAY:    0.08,   # relays use most power
            Role.DECISION: 0.06,
            Role.ANCHOR:   0.01,   # stationary, minimal power
        }
        # Battery is managed externally by the mission dispatch logic.
        # Only the one assigned "damage drone" loses battery during a mission.
        # This loop just keeps the task alive without draining.
        while True:
            if self.state.battery <= 0 and self.state.alive:
                # Externally drained (damage event) — mark dead
                self.state.alive = False
                print(f"[DRONE] {self.drone_id} battery DEAD!")
                await self.stop()
                break
            await asyncio.sleep(1.0)

    # ─────────────────────────────────────────
    # INCOMING MESSAGE HANDLER
    # ─────────────────────────────────────────

    async def handle_message(self, msg: dict):
        """
        Called by NovaMesh whenever a message arrives for this drone.
        Routes message to the right handler based on type.
        """
        msg_type = msg.get("type")

        if msg_type == "HEARTBEAT":
            await self._handle_heartbeat(msg)

        elif msg_type == "NOVA_HELLO":
            await self._handle_hello(msg)

        elif msg_type == "EMERGENCY_STOP" or msg.get("type") == "ESTOP":
            await self._handle_estop(msg)

        else:
            # Pass to subclass for custom handling
            await self.on_message(msg)

    async def _handle_heartbeat(self, msg: dict):
        """Update our knowledge of a peer drone from its heartbeat."""
        sender_id = msg["drone_id"]

        if sender_id == self.drone_id:
            return   # ignore our own heartbeat

        if sender_id not in self.peers:
            # First time we hear from this drone
            new_peer = DroneState(
                drone_id=sender_id,
                role=msg["role"],
                x=msg["x"],
                y=msg["y"],
                battery=msg["battery"],
                capabilities=msg.get("capabilities", []),
                last_seen=time.time(),
            )
            self.peers[sender_id] = new_peer
            print(f"[DRONE] {self.drone_id} discovered peer: {sender_id} "
                  f"(role={msg['role']})")

            for cb in self._on_peer_joined_callbacks:
                await cb(sender_id, new_peer)
        else:
            # Update existing peer
            peer = self.peers[sender_id]
            peer.x = msg["x"]
            peer.y = msg["y"]
            peer.battery = msg["battery"]
            peer.role = msg["role"]
            peer.current_task = msg.get("current_task")
            peer.last_seen = time.time()
            peer.alive = True   # it was maybe dead, now it's back

    async def _handle_hello(self, msg: dict):
        """Respond to a NOVA_HELLO discovery packet."""
        sender_id = msg["drone_id"]
        if sender_id == self.drone_id:
            return

        # Reply with our own hello so they know about us too
        reply = {
            "type": "NOVA_HELLO",
            "drone_id": self.drone_id,
            "role": self.state.role,
            "x": self.state.x,
            "y": self.state.y,
            "battery": self.state.battery,
            "capabilities": self.state.capabilities,
        }
        if self.mesh:
            await self.mesh.broadcast(reply)

    async def _handle_estop(self, msg: dict):
        """EMERGENCY STOP or RESET received from dashboard."""
        msg_type = msg.get("type", "ESTOP")

        if msg_type == "RESET":
            print(f"[RESET] {self.drone_id} received SYSTEM RESET — resuming operations")
            self.emergency_stopped = False
            self.state.current_task = "IDLE"
            for cb in self._on_estop_callbacks:
                try:
                    await cb(msg)
                except Exception:
                    pass
            return

        # Handle ESTOP
        print(f"\n{'='*50}")
        print(f"[ESTOP] {self.drone_id} received EMERGENCY STOP!")
        print(f"[ESTOP] Issued by: {msg.get('issued_by', 'unknown')}")
        print(f"{'='*50}\n")

        self.emergency_stopped = True
        self.state.current_task = "STOPPED"

        # Send acknowledgement
        ack = {
            "type": "ESTOP_ACK",
            "drone_id": self.drone_id,
            "ack_timestamp": time.time(),
            "issued_by": msg.get("issued_by"),
        }
        if self.mesh:
            await self.mesh.publish(config.TOPIC_ESTOP_ACK, ack)

        # Notify swarm logic
        for cb in self._on_estop_callbacks:
            await cb(msg)

    async def publish(self, topic: str, payload: dict):
        """Helper to publish via the mesh."""
        if self.mesh:
            if "drone_id" not in payload:
                payload["drone_id"] = self.drone_id
            await self.mesh.publish(topic, payload)

    async def on_message(self, msg: dict):
        """
        Override in subclasses to handle custom message types.
        Example: Scout drone handles TASK_AWARD here.
        """
        pass

    # ─────────────────────────────────────────
    # MOVEMENT — update position on the grid
    # ─────────────────────────────────────────

    def move_to(self, x: float, y: float):
        """Move drone to new position on the 200x200 grid."""
        if self.emergency_stopped:
            print(f"[DRONE] {self.drone_id} cannot move — EMERGENCY STOP active")
            return
        self.state.x = max(0, min(200, x))   # clamp to grid
        self.state.y = max(0, min(200, y))

    def distance_to(self, other_x: float, other_y: float) -> float:
        """Calculate distance to a point on the grid."""
        return ((self.state.x - other_x) ** 2 +
                (self.state.y - other_y) ** 2) ** 0.5

    # ─────────────────────────────────────────
    # CALLBACK REGISTRATION — for swarm logic
    # ─────────────────────────────────────────

    def on_peer_died(self, callback: Callable):
        """Register callback: called when a peer drone dies."""
        self._on_peer_died_callbacks.append(callback)

    def on_peer_joined(self, callback: Callable):
        """Register callback: called when a new drone is discovered."""
        self._on_peer_joined_callbacks.append(callback)

    def on_estop(self, callback: Callable):
        """Register callback: called when emergency stop is received."""
        self._on_estop_callbacks.append(callback)

    # ─────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────

    def get_alive_peers(self) -> Dict[str, DroneState]:
        """Returns only the peers that are currently alive."""
        return {pid: ps for pid, ps in self.peers.items() if ps.alive}

    def get_status(self) -> dict:
        """Full status snapshot — used by dashboard WebSocket."""
        return {
            "drone_id": self.drone_id,
            "role": self.state.role,
            "x": round(self.state.x, 2),
            "y": round(self.state.y, 2),
            "battery": round(self.state.battery, 1),
            "alive": self.state.alive,
            "current_task": self.state.current_task,
            "emergency_stopped": self.emergency_stopped,
            "alive_peers": list(self.get_alive_peers().keys()),
            "total_peers": len(self.peers),
        }

    def __repr__(self):
        return (f"DroneNode(id={self.drone_id}, role={self.state.role}, "
                f"pos=({self.state.x:.1f},{self.state.y:.1f}), "
                f"battery={self.state.battery:.1f}%)")
