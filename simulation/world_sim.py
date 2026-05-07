import sys
import os
import time
import random
import pygame
import math

# Root import
try:
    import config
except ImportError:
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config

from .sim_drone import SimDrone
from swarm.crdt_map import CRDTMap, CELL_UNKNOWN, CELL_SEARCHED, CELL_SURVIVOR, CELL_SEARCHING

class WorldSim:
    """
    Advanced WorldSim with Panning Camera, Sparse Grid & Infinite Coordinates.
    """
    def __init__(self):
        pygame.init()
        pygame.font.init()

        # Window size (Fixed UI area + Dynamic Map area)
        self.sidebar_w = 240
        self.screen = pygame.display.set_mode((config.WINDOW_W + self.sidebar_w, config.WINDOW_H))
        pygame.display.set_caption("Project NOVA — Advanced Swarm Command Hub")

        self.font_sm = pygame.font.SysFont("Fira Code", 11)
        self.font_md = pygame.font.SysFont("Fira Code", 14, bold=True)
        self.font_lg = pygame.font.SysFont("Fira Code", 18, bold=True)
        self.clock = pygame.time.Clock()

        # Camera & Viewport (Grid units)
        self.cam_pos = [0.0, 0.0]
        self.zoom = config.INITIAL_ZOOM
        self.dragging = False
        self.last_mouse_pos = (0, 0)

        # CRDT Sparse Map
        self.crdt_map = CRDTMap()
        self.drones = self._init_drones()

        # State
        self.mission = config.DEFAULT_MISSION
        self.theme = config.MISSIONS[self.mission]
        self.event_log = []
        self.mesh = None
        self.running = True
        self.estop_active = False

        self.log_event("INFO", "Advanced Sim Initialized (Infinite Coords)")

    def _init_drones(self):
        # Initial positions across a larger space
        positions = [(0,0), (50,0), (0,50), (50,50), (25,-25), (-25,25), (75,25), (25,75)]
        drones = {}
        for i in range(config.NUM_DRONES):
            did = f"drone_{i+1}"
            col, row = positions[i]
            role = SimDrone.ROLE_DECISION if i == 0 else SimDrone.ROLE_SCOUT
            drones[did] = SimDrone(did, col, row, role)
        return drones

    def connect_mesh(self, mesh):
        self.mesh = mesh
        mesh.subscribe(config.TOPIC_WORLDSTATE, self._on_worldstate)
        mesh.subscribe(config.TOPIC_HEARTBEAT, self._on_heartbeat)
        mesh.subscribe(config.TOPIC_ESTOP, self._on_estop)
        mesh.subscribe(config.TOPIC_MISSION, self._on_mission)
        self.log_event("MESH", "P2P Network Active")

    # ── Handlers ──────────────────────────────────────────────────────────

    async def _on_worldstate(self, topic, payload, sender):
        try:
            x, y = payload["cell"]
            status = payload["status"]
            s = CRDTMap.str_to_state(status)
            updated = self.crdt_map.update_cell(y, x, s, sender, payload.get("timestamp"))
            if updated and status == "survivor_detected":
                self.log_event("SURVIVOR", f"Found at ({x},{y})")
        except: pass

    async def _on_heartbeat(self, topic, payload, sender):
        try:
            did = payload["drone_id"]
            if did in self.drones:
                d = self.drones[did]
                d.battery = float(payload.get("battery", d.battery))
                if "x" in payload and "y" in payload:
                    d.assign_target(payload["x"], payload["y"])
        except: pass

    async def _on_estop(self, topic, payload, sender):
        self.estop_active = (payload.get("type") == "ESTOP")
        for d in self.drones.values(): d.kill() if self.estop_active else d.revive(d.col, d.row)

    async def _on_mission(self, topic, payload, sender):
        m = payload.get("mission")
        if m in config.MISSIONS:
            self.mission = m
            self.theme = config.MISSIONS[m]

    def log_event(self, kind, msg):
        ts = time.strftime("%H:%M:%S")
        self.event_log.append({"ts": ts, "kind": kind, "msg": msg})
        if len(self.event_log) > 50: self.event_log.pop(0)

    # ── Core Logic ───────────────────────────────────────────────────────

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: self.running = False
            
            # 1. Panning (Middle Click or Alt+Left)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (2, 3): 
                    self.dragging = True
                    self.last_mouse_pos = event.pos
                elif event.button == 4: # Zoom In
                    self.zoom = min(64, self.zoom + 2)
                elif event.button == 5: # Zoom Out
                    self.zoom = max(4, self.zoom - 2)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3): self.dragging = False
                
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.cam_pos[0] -= dx / self.zoom
                    self.cam_pos[1] -= dy / self.zoom
                    self.last_mouse_pos = event.pos

    def _update_mesh_state(self):
        """Sync positions to Mesh for P2P simulation."""
        if self.mesh:
            for d in self.drones.values():
                self.mesh.set_position(d.col, d.row)

    # ── Drawing ──────────────────────────────────────────────────────────

    def _draw_grid(self):
        # Iterate over sparse cells
        for (r, c), (state, _, _) in self.crdt_map.grid_data.items():
            # Screen pos
            sx = int((c - self.cam_pos[0]) * self.zoom + config.WINDOW_W // 2)
            sy = int((r - self.cam_pos[1]) * self.zoom + config.WINDOW_H // 2)
            
            # Culling
            if sx < -self.zoom or sx > config.WINDOW_W or sy < -self.zoom or sy > config.WINDOW_H:
                continue
                
            color = (20, 140, 80) if state == 2 else (255, 60, 60) if state == 3 else self.theme["primary"]
            pygame.draw.rect(self.screen, color, (sx, sy, self.zoom - 1, self.zoom - 1))

    def _draw_mesh_links(self):
        """Advanced Visual: Draw P2P links between drones."""
        alive = [d for d in self.drones.values() if d.status == "alive"]
        for i, d1 in enumerate(alive):
            for d2 in alive[i+1:]:
                dist = math.sqrt((d1.col-d2.col)**2 + (d1.row-d2.row)**2) * config.METERS_PER_UNIT
                if dist < config.MAX_SIGNAL_RANGE:
                    # Draw link
                    p1 = ((d1.col - self.cam_pos[0]) * self.zoom + config.WINDOW_W // 2, 
                          (d1.row - self.cam_pos[1]) * self.zoom + config.WINDOW_H // 2)
                    p2 = ((d2.col - self.cam_pos[0]) * self.zoom + config.WINDOW_W // 2, 
                          (d2.row - self.cam_pos[1]) * self.zoom + config.WINDOW_H // 2)
                    alpha = int(255 * (1.0 - dist / config.MAX_SIGNAL_RANGE))
                    pygame.draw.line(self.screen, (0, 255, 200, alpha), p1, p2, 1)

    def _draw_sidebar(self):
        sx = config.WINDOW_W
        pygame.draw.rect(self.screen, (15, 15, 20), (sx, 0, self.sidebar_w, config.WINDOW_H))
        pygame.draw.line(self.screen, (40, 40, 50), (sx, 0), (sx, config.WINDOW_H), 1)
        
        y = 15
        title = self.font_lg.render("SWARM OVERVIEW", True, (0, 255, 200))
        self.screen.blit(title, (sx + 15, y))
        y += 40
        
        for d in self.drones.values():
            status_col = (0, 255, 100) if d.status == "alive" else (255, 50, 50)
            pygame.draw.circle(self.screen, status_col, (sx + 25, y + 8), 6)
            txt = self.font_md.render(f"{d.drone_id}: {int(d.battery)}%", True, (200, 200, 210))
            self.screen.blit(txt, (sx + 40, y))
            y += 25
            
        y += 20
        self.screen.blit(self.font_md.render("EVENT LOG", True, (100, 100, 120)), (sx + 15, y))
        y += 25
        for ev in self.event_log[-12:]:
            color = (255, 100, 100) if ev["kind"] == "SURVIVOR" else (150, 150, 160)
            msg = self.font_sm.render(f"[{ev['ts']}] {ev['msg'][:22]}", True, color)
            self.screen.blit(msg, (sx + 15, y))
            y += 18

    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            self._handle_events()
            self._update_mesh_state()
            
            for d in self.drones.values(): d.update(dt)
            
            self.screen.fill((10, 10, 15))
            self._draw_grid()
            self._draw_mesh_links()
            for d in self.drones.values(): d.draw(self.screen, self.font_sm, self.cam_pos, self.zoom)
            self._draw_sidebar()
            
            pygame.display.flip()
        pygame.quit()

if __name__ == "__main__":
    WorldSim().run()