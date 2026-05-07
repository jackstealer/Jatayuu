import asyncio
import time
import random
from typing import Dict, List, Optional, Callable

# Root import - assume root is in sys.path
try:
    import config
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config

class AuctionEngine:
    """
    Distributed task allocation mechanism between drones.
    - Decision drone posts to 'nova/tasks'
    - Scout drones calculate scores and reply to 'nova/bids'
    - Decision drone picks winner and posts to 'nova/task_assigned'
    """
    def __init__(self, drone_id: str, is_leader: bool = False):
        self.drone_id = drone_id
        self.is_leader = is_leader
        
        # Internal state
        self.active_tasks: Dict[str, dict] = {} # task_id -> {details, bids}
        self.my_bids: Dict[str, float] = {}    # task_id -> my_score
        
        # Network callbacks (to be set by mesh integrator)
        self.on_publish = None # func(topic, payload)

    async def post_task(self, task_id: str, task_type: str, priority: int = 1):
        """Leader function: Start a new auction."""
        if not self.is_leader:
            return
            
        task_payload = {
            "task_id": task_id,
            "type": task_type,
            "priority": priority,
            "expires_ms": 500, # Bidding window
            "drone_id": self.drone_id
        }
        
        self.active_tasks[task_id] = {
            "payload": task_payload,
            "bids": {},
            "start_time": time.time()
        }
        
        if self.on_publish:
            await self.on_publish(config.TOPIC_TASKS, task_payload)
            
        # Wait for bids, then resolve
        asyncio.create_task(self._resolve_auction(task_id))

    async def _resolve_auction(self, task_id: str):
        """Leader function: Pick winner after timeout."""
        await asyncio.sleep(0.6) # Slightly longer than expires_ms
        
        if task_id not in self.active_tasks:
            return
            
        bids = self.active_tasks[task_id]["bids"]
        if not bids:
            # Re-auction later if no bids
            return
            
        # Pick winner (highest score)
        winner = max(bids, key=bids.get)
        
        assignment_payload = {
            "task_id": task_id,
            "assigned_to": winner,
            "drone_id": self.drone_id
        }
        
        if self.on_publish:
            await self.on_publish(config.TOPIC_TASK_ASSIGNED, assignment_payload)
            
        # Clean up
        del self.active_tasks[task_id]

    async def receive_task(self, task_payload: dict, my_battery: float, my_pos: tuple):
        """Scout function: Bid on a task."""
        if self.is_leader:
            return # Leader doesn't bid

        task_id = task_payload["task_id"]
        # Read target zone from task payload
        tx = task_payload.get("zone_x", 25)
        ty = task_payload.get("zone_y", 25)

        # Heuristic: score = battery_weight - distance_penalty
        dist = ((my_pos[0]-tx)**2 + (my_pos[1]-ty)**2)**0.5
        score = (my_battery * 0.4) + (100.0 / max(1, dist) * 0.6)

        bid_payload = {
            "task_id": task_id,
            "bidder": self.drone_id,
            "score": round(score, 2),
            "drone_id": self.drone_id
        }

        if self.on_publish:
            await self.on_publish(config.TOPIC_BIDS, bid_payload)

    def receive_bid(self, bid_payload: dict):
        """Leader function: Collect a bid from a scout."""
        if not self.is_leader:
            return
            
        task_id = bid_payload["task_id"]
        if task_id in self.active_tasks:
            bidder = bid_payload["bidder"]
            score = bid_payload["score"]
            self.active_tasks[task_id]["bids"][bidder] = score
