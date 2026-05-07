import asyncio
import sys
import os
import time

# Add root of Swarm to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
from mesh.nova_vertex import create_vertex_node
from swarm.auction_engine import AuctionEngine
from swarm.leader_election import LeaderElection

async def run_drone(drone_id, num_peers):
    """Lifecycle of a single virtual drone in the mock mesh."""
    # 1. Start Mesh Node (MOCK)
    from mesh.nova_mesh import DRONE_NETWORK_CONFIG
    network_config = {d: ("MOCK", 1883) for d in DRONE_NETWORK_CONFIG}
    vertex = await create_vertex_node(drone_id, network_config=network_config)
    
    # 2. Initialize Swarm Logic (M2)
    auction = AuctionEngine(drone_id)
    election = LeaderElection(drone_id)
    
    auction.on_publish = vertex.publish
    election.on_publish = vertex.publish
    
    # 3. Setup Subscriptions
    def on_task(p): 
        print(f"[AUCTION] {drone_id} received task {p['task_id']}")
        asyncio.create_task(auction.receive_task(p, 90, (25,25)))
    def on_bid(p): 
        print(f"[AUCTION] {drone_id} (Leader) received bid from {p['bidder']} (Score: {p['score']})")
        auction.receive_bid(p)
    def on_assign(p):
        print(f"[AUCTION] {p['task_id']} assigned to {p['assigned_to']}")
    def on_elect(p): asyncio.create_task(election.handle_vote_request(p))
    def on_vote(p): election.handle_vote(p, num_peers)
    def on_heartbeat(p): 
        # print(f"[DEBUG] {drone_id} received heartbeat from {p['drone_id']} (is_leader={p.get('is_leader')})")
        election.record_heartbeat(p['drone_id'], p.get('is_leader', False))
    
    vertex.subscribe(config.TOPIC_TASKS, lambda t, p, s: on_task(p))
    vertex.subscribe(config.TOPIC_BIDS, lambda t, p, s: on_bid(p))
    vertex.subscribe(config.TOPIC_TASK_ASSIGNED, lambda t, p, s: on_assign(p))
    vertex.subscribe(config.TOPIC_ELECTION, lambda t, p, s: on_elect(p))
    vertex.subscribe(config.TOPIC_ELECTION_VOTE, lambda t, p, s: on_vote(p))
    vertex.subscribe(config.TOPIC_HEARTBEAT, lambda t, p, s: on_heartbeat(p))
    
    # 4. Start Election Monitor
    asyncio.create_task(election.run())
    
    async def heartbeat_loop():
        while True:
            await vertex.publish(config.TOPIC_HEARTBEAT, {
                "drone_id": drone_id,
                "is_leader": election.is_leader
            })
            await asyncio.sleep(1.5)
    
    asyncio.create_task(heartbeat_loop())
    
    # 5. Main Loop (Auctions)
    while True:
        await asyncio.sleep(1.0)
        
        # If I am leader, post a task
        if election.is_leader:
            auction.is_leader = True
            task_id = f"task_{int(time.time())}"
            await auction.post_task(task_id, "exploration")
            await asyncio.sleep(8.0) # Long wait before next auction

async def main():
    print("="*60)
    print("  NOVA SWARM LOGIC DEMO (Multi-Node Election & Auction)")
    print("="*60)
    
    num_drones = 3
    drones = ["drone_1", "drone_2", "drone_3"]
    
    print(f"[CONF] Starting {num_drones} drones. Majority required: 2")
    
    tasks = [run_drone(did, num_drones) for did in drones]
    print("[SYSTEM] Swarm initialization launched...")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYSTEM] Demo stopped.")
