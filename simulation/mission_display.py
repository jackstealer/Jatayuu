# simulation/mission_display.py
# M3 owns this file
# Mission switching is handled directly inside world_sim.py
# This file exists as a module placeholder for M5 integration
# The full mission bar rendering is in WorldSim._draw_mission_bar()
# and WorldSim._handle_mission_click()

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import MISSIONS, WINDOW_W

MISSION_LIST = ["SAR", "Defense", "Fire", "Pollution", "Ambulance"]

def get_mission_names():
    """Returns list of all available mission names."""
    return MISSION_LIST

def get_mission_theme(mission_name):
    """Returns colour theme dict for a given mission name."""
    return MISSIONS.get(mission_name, MISSIONS["SAR"])

def get_all_themes():
    """Returns full missions dict — used by M4 dashboard for theming."""
    return MISSIONS