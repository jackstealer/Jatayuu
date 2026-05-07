# nova_m3/swarm/mission_config.py
"""
Mission configurations for Project NOVA.
Contains themes, roles, and search patterns for different mission types.
"""

MISSIONS = {
    "SAR": {
        "name": "Search & Rescue",
        "primary": (30, 80, 200),
        "accent": (220, 40, 40),
        "bg": (20, 20, 35),
        "drone_roles": ["decision", "scout", "scout", "scout", "scout", "scout", "scout", "scout"],
        "search_pattern": "frontier_exploration"
    },
    "Defense": {
        "name": "Defense Perimeter",
        "primary": (30, 100, 30),
        "accent": (200, 200, 0),
        "bg": (10, 25, 10),
        "drone_roles": ["decision", "sentinel", "sentinel", "sentinel", "sentinel", "sentinel", "sentinel", "sentinel"],
        "search_pattern": "circular_patrol"
    },
    "Fire": {
        "name": "Wildfire Containment",
        "primary": (200, 80, 0),
        "accent": (255, 200, 0),
        "bg": (30, 15, 5),
        "drone_roles": ["decision", "thermal_scout", "thermal_scout", "water_dropper", "water_dropper", "scout", "scout", "scout"],
        "search_pattern": "grid_sweep"
    },
    "Pollution": {
        "name": "Pollution Sweep",
        "primary": (160, 140, 0),
        "accent": (100, 180, 50),
        "bg": (20, 20, 10),
        "drone_roles": ["decision", "sensor_node", "sensor_node", "sensor_node", "sensor_node", "sensor_node", "scout", "scout"],
        "search_pattern": "gradient_ascent"
    },
    "Ambulance": {
        "name": "Medical Evac",
        "primary": (180, 180, 180),
        "accent": (220, 40, 40),
        "bg": (10, 10, 30),
        "drone_roles": ["decision", "medic", "medic", "evac", "evac", "scout", "scout", "scout"],
        "search_pattern": "point_to_point"
    }
}

# Default mission
DEFAULT_MISSION = "SAR"
