"""
chaos_proxy.py — M1's file
========================
This is the chaos simulator for the drone mesh.
It simulates real-world radio interference and distance-based packet loss.
"""

import random
import time
from typing import Dict, List, Tuple, Optional

class ChaosProxy:
    """
    Simulates packet loss, delay, and blackout zones in the drone mesh.
    """
    def __init__(self):
        # Global chaos level (0.0 = perfect, 1.0 = total blackout)
        self.chaos_level = 0.0
        self.blackout_zones: List[Dict] = []
        
        # Statistics
        self.stats = {
            "delivered": 0,
            "dropped": 0,
            "delayed": 0
        }

    def set_chaos_level(self, level: float):
        """Set the global packet loss percentage (0.0 to 1.0)."""
        self.chaos_level = max(0.0, min(1.0, level))
        print(f"[CHAOS] Level set to {self.chaos_level*100:.0f}% loss")

    def add_blackout_zone(self, center_x: float, center_y: float, radius: float):
        """Add a geographic zone where radio communication fails."""
        zone = {
            "center": (center_x, center_y),
            "radius": radius
        }
        self.blackout_zones.append(zone)
        print(f"[CHAOS] Blackout zone added at ({center_x}, {center_y}) radius={radius}")

    def check_delivery(self, sender_id: str, receiver_id: str, 
                        sender_pos: Tuple[float, float], 
                        receiver_pos: Tuple[float, float]) -> Tuple[bool, str]:
        """
        Determines if a packet should be delivered based on:
        1. Distance between drones (beyond 200m = loss)
        2. Global chaos level (random drop)
        3. Blackout zones (geographic drop)
        
        Returns (should_deliver, reason).
        """
        # Calculate Euclidean distance
        dx = sender_pos[0] - receiver_pos[0]
        dy = sender_pos[1] - receiver_pos[1]
        dist = (dx**2 + dy**2)**0.5
        
        # 1. Distance check (WiFi range limit)
        if dist > 200.0:
            self.stats["dropped"] += 1
            return False, "OUT_OF_RANGE"

        # 2. Blackout zone check
        for zone in self.blackout_zones:
            zx, zy = zone["center"]
            r = zone["radius"]
            # Check if sender or receiver is in blackout zone
            d_sender = ((sender_pos[0] - zx)**2 + (sender_pos[1] - zy)**2)**0.5
            d_receiver = ((receiver_pos[0] - zx)**2 + (receiver_pos[1] - zy)**2)**0.5
            
            if d_sender < r or d_receiver < r:
                self.stats["dropped"] += 1
                return False, "BLACKOUT_ZONE"

        # 3. Random packet loss (Chaos level)
        if random.random() < self.chaos_level:
            self.stats["dropped"] += 1
            return False, "RANDOM_DROP"

        # 4. Success!
        self.stats["delivered"] += 1
        return True, "SUCCESS"

    def print_stats(self):
        """Print statistics for debugging."""
        total = self.stats["delivered"] + self.stats["dropped"]
        if total == 0:
            print("[CHAOS] No packets processed yet.")
            return
            
        drop_pct = (self.stats["dropped"] / total) * 100
        print(f"[CHAOS] Stats: {total} packets | {self.stats['delivered']} delivered | {self.stats['dropped']} dropped ({drop_pct:.1f}% loss)")
