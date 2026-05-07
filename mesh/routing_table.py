"""
routing_table.py — M1's file
=============================
This is the MESH ROUTING TABLE for NOVA.

The problem it solves:
    Drone 1 wants to send a message to Drone 6.
    But Drone 1 and Drone 6 are too far apart for direct radio.
    Who should Drone 1 pass the message to so it eventually reaches Drone 6?

This file answers that question using Bellman-Ford algorithm.
Every drone runs this and updates it every 500ms.

Simple analogy:
    Like Google Maps for the drone mesh.
    "To reach Drone 6, go via Drone 3 first."
"""

import time
from typing import Dict, Optional, Tuple


# ─────────────────────────────────────────────
# LINK — one connection between two drones
# ─────────────────────────────────────────────
class MeshLink:
    """
    Represents a radio link between two drones.

    quality: 0.0 (terrible) to 1.0 (perfect)
    A link with quality below 0.2 is considered broken.
    """
    def __init__(self, source: str, target: str, quality: float = 1.0):
        self.source = source
        self.target = target
        self.quality = quality          # signal quality 0.0 - 1.0
        self.last_updated = time.time()
        self.packet_loss = 0.0          # 0.0 = no loss, 1.0 = all lost

    @property
    def cost(self) -> float:
        """
        Cost of using this link.
        Lower quality = higher cost = less preferred.
        Bellman-Ford picks the path with lowest total cost.
        """
        if self.quality < 0.1:
            return float('inf')   # broken link — never use
        return 1.0 / max(self.quality, 0.01)

    @property
    def is_alive(self) -> bool:
        return self.quality >= 0.2

    def __repr__(self):
        return (f"Link({self.source}→{self.target}, "
                f"quality={self.quality:.2f}, cost={self.cost:.2f})")


# ─────────────────────────────────────────────
# ROUTING TABLE — Bellman-Ford implementation
# ─────────────────────────────────────────────
class RoutingTable:
    """
    Bellman-Ford routing for the drone mesh.

    Every drone keeps one of these.
    It tells the drone: "To reach drone X, send via drone Y."

    Updates automatically every time:
    - A new drone is discovered
    - A drone dies
    - Link quality changes

    Usage:
        table = RoutingTable("drone_1")
        table.update_link("drone_1", "drone_3", quality=0.9)
        table.update_link("drone_3", "drone_6", quality=0.7)
        table.recalculate()

        next_hop = table.get_next_hop("drone_6")
        # Returns "drone_3" — send via drone_3 to reach drone_6
    """

    def __init__(self, my_id: str):
        self.my_id = my_id

        # All known links in the mesh
        # key = (source_id, target_id), value = MeshLink
        self.links: Dict[Tuple[str, str], MeshLink] = {}

        # Routing table result
        # key = destination drone_id
        # value = (next_hop drone_id, total_cost, hop_count)
        self.routes: Dict[str, Tuple[str, float, int]] = {}

        # All known drones in the mesh
        self.known_drones: set = {my_id}

        self._last_calculated = 0.0

    # ─────────────────────────────────────────
    # LINK MANAGEMENT
    # ─────────────────────────────────────────

    def update_link(self, source: str, target: str, quality: float,
                    packet_loss: float = 0.0):
        """
        Add or update a link between two drones.
        Called when we receive signal quality info from the mesh.

        quality: 0.0 to 1.0 (1.0 = perfect signal)
        packet_loss: 0.0 to 1.0 (fraction of packets dropped)
        """
        # Add both directions (radio works both ways)
        for s, t in [(source, target), (target, source)]:
            key = (s, t)
            if key not in self.links:
                self.links[key] = MeshLink(s, t, quality)
            else:
                self.links[key].quality = quality
                self.links[key].packet_loss = packet_loss
                self.links[key].last_updated = time.time()

        self.known_drones.add(source)
        self.known_drones.add(target)

    def remove_link(self, source: str, target: str):
        """Remove a link — called when a drone dies."""
        self.links.pop((source, target), None)
        self.links.pop((target, source), None)

    def mark_drone_dead(self, drone_id: str):
        """
        Remove all links involving a dead drone.
        Then recalculate routes so mesh heals automatically.
        """
        dead_links = [k for k in self.links if drone_id in k]
        for key in dead_links:
            del self.links[key]
        self.known_drones.discard(drone_id)
        self.routes.pop(drone_id, None)
        print(f"[ROUTING] Removed {len(dead_links)} links for dead drone {drone_id}")
        self.recalculate()

    # ─────────────────────────────────────────
    # BELLMAN-FORD ALGORITHM
    # ─────────────────────────────────────────

    def recalculate(self):
        """
        Run Bellman-Ford from our own position to all other drones.

        How Bellman-Ford works (simple explanation):
        1. Start: distance to myself = 0, distance to everyone else = infinity
        2. Repeat N-1 times:
           For every link in the mesh:
               If (cost to reach source + link cost) < current cost to target:
                   Update: new best path to target goes via source
        3. Result: shortest path from me to every other drone

        Time complexity: O(V * E) where V = drones, E = links
        For 8 drones this runs in microseconds.
        """
        drones = list(self.known_drones)
        n = len(drones)

        # Initialize distances — infinity to everywhere except myself
        dist = {d: float('inf') for d in drones}
        dist[self.my_id] = 0.0

        # next_hop[d] = which drone to send to first when going to d
        next_hop = {d: None for d in drones}
        hop_count = {d: 0 for d in drones}

        # Bellman-Ford relaxation — repeat n-1 times
        for iteration in range(n - 1):
            updated = False
            for (source, target), link in self.links.items():
                if not link.is_alive:
                    continue

                new_cost = dist[source] + link.cost
                if new_cost < dist.get(target, float('inf')):
                    dist[target] = new_cost
                    hop_count[target] = hop_count.get(source, 0) + 1

                    # Track next hop — if source is me, next hop is target
                    # Otherwise inherit source's next hop
                    if source == self.my_id:
                        next_hop[target] = target
                    else:
                        next_hop[target] = next_hop.get(source)

                    updated = True

            # Early exit if no updates in this iteration
            if not updated:
                break

        # Store results — only reachable drones
        self.routes = {}
        for drone_id in drones:
            if drone_id != self.my_id and dist[drone_id] < float('inf'):
                self.routes[drone_id] = (
                    next_hop[drone_id],
                    dist[drone_id],
                    hop_count[drone_id]
                )

        self._last_calculated = time.time()
        # Removed debug print to avoid noise in logs
        # self._print_routes()

    # ─────────────────────────────────────────
    # ROUTE LOOKUP
    # ─────────────────────────────────────────

    def get_next_hop(self, destination: str) -> Optional[str]:
        """
        Who should I send to first to reach destination?

        Returns None if destination is unreachable.

        Example:
            get_next_hop("drone_6") → "drone_3"
            Meaning: send to drone_3 first, it will forward to drone_6
        """
        if destination == self.my_id:
            return self.my_id   # it's me!

        route = self.routes.get(destination)
        if route:
            return route[0]   # next hop
        return None   # unreachable

    def get_hop_count(self, destination: str) -> int:
        """How many hops to reach destination? 1 = direct, 2 = via one relay, etc."""
        route = self.routes.get(destination)
        return route[2] if route else -1   # -1 = unreachable

    def get_path_cost(self, destination: str) -> float:
        """Total cost of path to destination."""
        route = self.routes.get(destination)
        return route[1] if route else float('inf')

    def is_reachable(self, destination: str) -> bool:
        """Can we reach this drone at all?"""
        return destination in self.routes

    def get_unreachable_drones(self) -> list:
        """List of drones we cannot currently reach."""
        return [d for d in self.known_drones
                if d != self.my_id and not self.is_reachable(d)]

    def get_direct_neighbors(self) -> list:
        """Drones we can reach in exactly 1 hop (direct radio)."""
        return [d for d, (_, _, hops) in self.routes.items() if hops == 1]

    # ─────────────────────────────────────────
    # LINK QUALITY UPDATE (from signal strength)
    # ─────────────────────────────────────────

    def update_quality_from_distance(self, source: str, target: str,
                                     distance: float,
                                     wifi_range: float = 200.0):
        """
        Calculate link quality based on simulated distance.
        Further = weaker signal = lower quality.

        This simulates real radio signal degradation.
        """
        if distance > wifi_range:
            quality = 0.0   # out of range
        else:
            # Linear degradation: at 0m = 1.0, at wifi_range = 0.1
            quality = max(0.1, 1.0 - (distance / wifi_range) * 0.9)

        self.update_link(source, target, quality)

    # ─────────────────────────────────────────
    # DEBUG OUTPUT
    # ─────────────────────────────────────────

    def _print_routes(self):
        """Print current routing table — useful for debugging."""
        if not self.routes:
            print(f"[ROUTING] {self.my_id}: no routes yet")
            return
        print(f"[ROUTING] {self.my_id} routing table:")
        for dest, (hop, cost, hops) in sorted(self.routes.items()):
            print(f"  → {dest}: via {hop} | cost={cost:.2f} | {hops} hop(s)")

    def get_summary(self) -> dict:
        """Return routing table as dict — for dashboard display."""
        return {
            "my_id": self.my_id,
            "known_drones": list(self.known_drones),
            "reachable": list(self.routes.keys()),
            "unreachable": self.get_unreachable_drones(),
            "routes": {
                dest: {
                    "next_hop": hop,
                    "cost": round(cost, 2),
                    "hops": hops
                }
                for dest, (hop, cost, hops) in self.routes.items()
            },
            "last_calculated": self._last_calculated,
        }
