# config.py — shared constants for Project NOVA (Advanced Version)

# ── NETWORK (FoxMQ / MQTT) ────────────────────────────────────────────────
FOXMQ_HOST  = "127.0.0.1"   # change to M1's IP when available
FOXMQ_PORT  = 1883
WS_PORT     = 8765

# FoxMQ Topics (standardized)
TOPIC_DISCOVERY     = "nova/discovery"
TOPIC_HEARTBEAT     = "nova/heartbeat"
TOPIC_WORLDSTATE    = "nova/worldstate"
TOPIC_TASKS         = "nova/tasks"
TOPIC_BIDS          = "nova/bids"
TOPIC_TASK_ASSIGNED = "nova/task_assigned"
TOPIC_ELECTION      = "nova/election"
TOPIC_ELECTION_VOTE = "nova/election_vote"
TOPIC_SURVIVOR      = "nova/survivor"
TOPIC_ESTOP         = "nova/estop"
TOPIC_ESTOP_ACK     = "nova/estop_ack"
TOPIC_MISSION       = "nova/mission"
TOPIC_TASK_DONE     = "nova/task_done"
TOPIC_KILL          = "nova/kill"

# ── GLOBAL MESH & COORDINATES ─────────────────────────────────────────────
METERS_PER_UNIT = 10.0      # 1 grid unit = 10 meters
MAX_SIGNAL_RANGE = 250.0    # meters (approx WiFi range)
SIGNAL_DECAY    = 0.5       # signal drop-off factor

NUM_DRONES  = 8
FPS         = 30

# Advanced Viewport Defaults (Initial View)
WINDOW_W    = 800
WINDOW_H    = 800
INITIAL_VIEW_X = 0
INITIAL_VIEW_Y = 0
INITIAL_ZOOM   = 16         # pixels per unit (cell size)

# ── MISSION THEMES ────────────────────────────────────────────────────────
MISSIONS = {
    "SAR":       {"name": "Search & Rescue", "primary": ( 30, 80, 200), "accent": (220, 40,  40), "bg": (20, 20, 35)},
    "Defense":   {"name": "Defense",         "primary": ( 30,100,  30), "accent": (200,200,   0), "bg": (10, 25, 10)},
    "Fire":      {"name": "Wildfire",        "primary": (200, 80,   0), "accent": (255,200,   0), "bg": (30, 15,  5)},
    "Pollution": {"name": "Pollution Sweep", "primary": (160,140,   0), "accent": (100,180,  50), "bg": (20, 20, 10)},
    "Ambulance": {"name": "Medical Evac",    "primary": (180,180, 180), "accent": (220, 40,  40), "bg": (10, 10, 30)},
}

DEFAULT_MISSION = "SAR"