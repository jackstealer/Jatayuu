import asyncio
import time
import random
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

class LeaderElection:
    """
    Raft-lite leader election implementation for a drone swarm.
    - Monitors heartbeats to trigger elections.
    - Drones vote for a candidate.
    - First drone to get N/2+1 votes declares itself new Decision drone.
    """
    def __init__(self, drone_id: str):
        self.drone_id = drone_id
        self.is_leader = False
        self.current_term = 0
        self.votes_received = set()
        
        # Track last heartbeat of the current leader
        self.leader_id = None
        self.last_leader_heartbeat = time.time()
        self.election_timeout = random.uniform(2.5, 4.5) # Random to prevent collisions
        self.election_in_progress = False

        # Callback for publishing
        self.on_publish = None # func(topic, payload)

    async def run(self):
        """Main loop that monitors leader health."""
        while True:
            await asyncio.sleep(0.5)

            # Check if leader is dead
            if self.leader_id != self.drone_id:
                if time.time() - self.last_leader_heartbeat > self.election_timeout and not self.election_in_progress:
                    print(f"[ELECT] {self.drone_id}: Leader {self.leader_id} timeout — starting election term {self.current_term + 1}")
                    await self._start_election()

    async def _start_election(self):
        """Transition to candidate state and request votes."""
        self.current_term += 1
        self.votes_received = {self.drone_id} # Vote for self
        self.last_leader_heartbeat = time.time() # Reset to avoid immediate re-election
        
        payload = {
            "candidate": self.drone_id,
            "term": self.current_term,
            "drone_id": self.drone_id
        }
        
        if self.on_publish:
            await self.on_publish(config.TOPIC_ELECTION, payload)

    async def handle_vote_request(self, payload: dict):
        """Respond to another drone's election request."""
        candidate = payload["candidate"]
        term = payload["term"]
        
        if term > self.current_term:
            self.current_term = term
            self.is_leader = False
            self.leader_id = None
            print(f"[ELECT] {self.drone_id}: Voting for {candidate} (Term {term})")
            
            vote_back = {
                "voter": self.drone_id,
                "target": candidate,
                "term": term,
                "drone_id": self.drone_id
            }
            if self.on_publish:
                await self.on_publish(config.TOPIC_ELECTION_VOTE, vote_back)
                
    def handle_vote(self, payload: dict, num_peers: int):
        """Collect votes and declare victory if majority is reached."""
        target = payload["target"]
        term = payload["term"]
        voter = payload["drone_id"]
        
        if target == self.drone_id and term == self.current_term:
            self.votes_received.add(voter)
            print(f"[ELECT] {self.drone_id}: Received vote from {voter} ({len(self.votes_received)}/{num_peers})")
            
            # Majority check (n/2 + 1)
            if len(self.votes_received) >= (num_peers // 2) + 1:
                if not self.is_leader:
                    print(f"[PASS] {self.drone_id} elected as LEADER for term {self.current_term}!")
                    self.is_leader = True
                    self.leader_id = self.drone_id

    def record_heartbeat(self, drone_id: str, is_leader: bool):
        """Track leader heartbeats to keep simulation alive."""
        if is_leader:
            # print(f"[DEBUG] {self.drone_id} received heartbeat from leader {drone_id}")
            self.leader_id = drone_id
            self.last_leader_heartbeat = time.time()
            if drone_id != self.drone_id:
                self.is_leader = False
        elif drone_id == self.leader_id:
            # If the known leader says they are no longer leader
            self.leader_id = None
