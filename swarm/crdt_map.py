# swarm/crdt_map.py
import time
from typing import Dict, Tuple, Optional, Any

# Cell states
CELL_UNKNOWN   = 0
CELL_SEARCHING = 1
CELL_SEARCHED  = 2
CELL_SURVIVOR  = 3

class CRDTMap:
    """
    Conflict-free Replicated Data Type (CRDT) for a SPARSE search grid.
    Uses Last-Writer-Wins (LWW) based on timestamps.
    Supports infinite coordinates without fixed bounds.
    """
    def __init__(self):
        # Sparse Grid: (row, col) -> (state, timestamp, drone_id)
        self.grid_data: Dict[Tuple[int, int], Tuple[int, int, str]] = {}

    def update_cell(self, row: int, col: int, state: int, drone_id: str, timestamp: Optional[int] = None) -> bool:
        """
        Update a cell using LWW logic. Returns True if the update was applied.
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000)
            
        key = (row, col)
        current_data = self.grid_data.get(key)
        
        if current_data is None:
            # New discovery
            self.grid_data[key] = (state, timestamp, drone_id)
            return True
            
        current_state, current_ts, current_drone = current_data
        
        # LWW Rule: higher timestamp wins
        if timestamp > current_ts:
            self.grid_data[key] = (state, timestamp, drone_id)
            return True
        elif timestamp == current_ts:
            # Deterministic tie-break using drone_id
            if drone_id > current_drone:
                self.grid_data[key] = (state, timestamp, drone_id)
                return True
                
        return False

    def merge(self, other_data: Dict[Tuple[int, int], Any]):
        """
        Merge with another sparse grid (e.g. from a full sync).
        """
        for key, data in other_data.items():
            r, c = key
            # data could be (state, ts, drone) or similar
            if isinstance(data, (list, tuple)) and len(data) >= 3:
                s, t, d = data[:3]
                self.update_cell(r, c, s, d, t)

    def get_sparse_state(self) -> Dict[Tuple[int, int], int]:
        """Returns only the state (int) for each occupied cell."""
        return {key: val[0] for key, val in self.grid_data.items()}

    def get_bounding_box(self) -> Tuple[int, int, int, int]:
        """Returns (min_row, min_col, max_row, max_col) of discovered area."""
        if not self.grid_data:
            return (0, 0, 0, 0)
        rows = [k[0] for k in self.grid_data.keys()]
        cols = [k[1] for k in self.grid_data.keys()]
        return (min(rows), min(cols), max(rows), max(cols))

    def serialize_cell(self, row: int, col: int) -> Optional[dict]:
        """Serialize a single cell for network transmission."""
        data = self.grid_data.get((row, col))
        if not data:
            return None
        s, t, d = data
        return {
            "cell": [col, row], # x=col, y=row as per INTERFACES.md
            "status": self.state_to_str(s),
            "drone_id": d,
            "timestamp": t
        }

    @staticmethod
    def state_to_str(state: int) -> str:
        mapping = {
            CELL_UNKNOWN: "unknown",
            CELL_SEARCHING: "searching",
            CELL_SEARCHED: "searched",
            CELL_SURVIVOR: "survivor_detected"
        }
        return mapping.get(state, "unknown")

    @staticmethod
    def str_to_state(status: str) -> int:
        mapping = {
            "unknown": CELL_UNKNOWN,
            "searching": CELL_SEARCHING,
            "searched": CELL_SEARCHED,
            "survivor_detected": CELL_SURVIVOR
        }
        return mapping.get(status, CELL_UNKNOWN)
