"""
nova_mesh.py — M1's file (Advanced Version)
========================
This is the FoxMQ/MQTT wrapper for NOVA.
Handles radio communication, distance-based simulation, and routing.
Uses InMemoryMeshDelegate for high-performance intra-process MOCK mode.
Special Case: The 'bridge' node has infinite range to simulate mission control.
"""

import json
import asyncio
import time
from typing import Callable, Optional, Dict, Any, List, Tuple

# Mesh internal imports
try:
    from mesh.chaos_proxy import ChaosProxy
    from mesh.routing_table import RoutingTable
    from mesh.in_memory_mesh import SHARED_MESH
except ImportError:
    try:
        from chaos_proxy import ChaosProxy
        from routing_table import RoutingTable
        from in_memory_mesh import SHARED_MESH
    except:
        ChaosProxy = None
        RoutingTable = None
        SHARED_MESH = None

import config

_GLOBAL_POSITIONS: Dict[str, Tuple[float, float]] = {}

class NovaMesh:
    """
    Advanced NovaMesh with high-performance MOCK mode support.
    """
    def __init__(self, drone_id: str, broker_host: str = "127.0.0.1", broker_port: int = 1883):
        self.drone_id = drone_id
        self.broker_host = broker_host
        self.is_mock = (broker_host == "MOCK")
        
        self.subscriptions: Dict[str, list[Callable]] = {}
        self.routing = RoutingTable(drone_id) if RoutingTable else None
        self.chaos = ChaosProxy() if ChaosProxy else None
        
        self._is_connected = False
        self._pos = (0.0, 0.0)

    def set_position(self, x: float, y: float):
        self._pos = (x, y)
        _GLOBAL_POSITIONS[self.drone_id] = (x, y)

    async def start(self):
        self._is_connected = True
        return True

    async def stop(self):
        self._is_connected = False

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(callback)
        
        if self.is_mock and SHARED_MESH:
            async def mock_handler(t, p, s):
                if s == self.drone_id: return
                
                # The 'bridge' node (Mission Control) has infinite reception and transmission range
                if self.drone_id == "bridge" or s == "bridge":
                    in_range = True
                else:
                    s_pos = _GLOBAL_POSITIONS.get(s, (0, 0))
                    dx = self._pos[0] - s_pos[0]
                    dy = self._pos[1] - s_pos[1]
                    dist = (dx**2 + dy**2)**0.5 * config.METERS_PER_UNIT
                    in_range = (dist <= config.MAX_SIGNAL_RANGE)
                
                if in_range:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(t, p, s)
                    else:
                        callback(t, p, s)
            
            SHARED_MESH.subscribe(topic, mock_handler)

    async def publish(self, topic: str, payload: dict):
        if not self._is_connected: return
        payload["drone_id"] = self.drone_id
        if self.is_mock and SHARED_MESH:
            SHARED_MESH.publish(topic, payload, self.drone_id)

    async def broadcast(self, payload: dict):
        msg_type = payload.get("type", payload.get("action", "UNKNOWN"))
        await self.publish(f"nova/{msg_type.lower()}", payload)
