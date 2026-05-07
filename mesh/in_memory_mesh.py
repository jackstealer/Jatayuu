"""
in_memory_mesh.py — High-performance in-process mesh simulator.
Used when all drones and the bridge are in the same script.
"""

import asyncio
from typing import Dict, List, Callable

class InMemoryMeshDelegate:
    """
    A singleton/shared delegate that replaces a real MQTT broker.
    Handles message routing between NovaMesh instances in the same process.
    """
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    def publish(self, topic: str, payload: dict, sender_id: str):
        # Determine matches (exact or wildcard)
        matches = []
        if topic in self.subscribers:
            matches.extend(self.subscribers[topic])
        
        # Simple wildcard support for '#'
        for sub_topic, callbacks in self.subscribers.items():
            if sub_topic.endswith("/#"):
                base = sub_topic[:-2]
                if topic.startswith(base):
                    matches.extend(callbacks)

        # Dispatch
        for cb in matches:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(topic, payload, sender_id))
                else:
                    cb(topic, payload, sender_id)
            except:
                pass

# Global Singleton for the Process
SHARED_MESH = InMemoryMeshDelegate()
