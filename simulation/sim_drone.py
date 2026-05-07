import pygame
import math
import sys
import os

# Root import
import config

class SimDrone:
    """
    Drones in the simulation. 
    Handles movement, battery, and drawing relative to a camera.
    """
    ROLE_DECISION = "decision"
    ROLE_SCOUT    = "scout"
    STATUS_ALIVE  = "alive"
    STATUS_DEAD   = "dead"

    def __init__(self, drone_id, start_col, start_row, role=None):
        if role is None:
            role = self.ROLE_SCOUT
        self.drone_id   = drone_id
        # Coordinates are in 'Grid Units'
        self.col        = float(start_col)
        self.row        = float(start_row)
        self.role       = role
        self.battery    = 100.0
        self.status     = self.STATUS_ALIVE
        self.target_col = float(start_col)
        self.target_row = float(start_row)
        self.task_id    = None
        self.trail      = [] # List of (col, row)
        self._pulse     = 0.0

    def assign_target(self, col, row, task_id=None):
        self.target_col = float(col)
        self.target_row = float(row)
        self.task_id    = task_id

    def update(self, dt):
        if self.status == self.STATUS_DEAD:
            return
            
        SPEED = 6.0 # Grid units per second
        dc    = self.target_col - self.col
        dr    = self.target_row - self.row
        dist  = math.sqrt(dc * dc + dr * dr)
        
        if dist > 0.05:
            step = SPEED * dt
            if step >= dist:
                self.col = self.target_col
                self.row = self.target_row
            else:
                self.col += (dc / dist) * step
                self.row += (dr / dist) * step
            
            # Update trail occasionally
            int_pos = (round(self.col, 1), round(self.row, 1))
            if not self.trail or self.trail[-1] != int_pos:
                self.trail.append(int_pos)
                if len(self.trail) > 12:
                    self.trail.pop(0)
                    
        self.battery = max(0.0, self.battery - 0.2 * dt)
        if self.battery <= 0:
            self.status = self.STATUS_DEAD
        self._pulse = (self._pulse + dt * 2.5) % (2 * math.pi)

    def kill(self):
        self.status  = self.STATUS_DEAD
        self.battery = 0.0
        self.task_id = None

    def revive(self, col, row):
        self.col     = float(col)
        self.row     = float(row)
        self.status  = self.STATUS_ALIVE
        self.battery = 80.0
        self.trail   = []

    def draw(self, surface, font_small, camera_offset, zoom):
        """
        Draw drone relative to camera.
        camera_offset: (ox, oy) in grid units
        zoom: pixels per grid unit
        """
        # Screen position
        px = int((self.col - camera_offset[0]) * zoom + config.WINDOW_W // 2)
        py = int((self.row - camera_offset[1]) * zoom + config.WINDOW_H // 2)
        
        radius = max(6, int(zoom * 0.45))

        # 1. Trail
        for i, (tc, tr) in enumerate(self.trail):
            tpx = int((tc - camera_offset[0]) * zoom + config.WINDOW_W // 2)
            tpy = int((tr - camera_offset[1]) * zoom + config.WINDOW_H // 2)
            alph = int(120 * (i / max(1, len(self.trail))))
            base = (255, 215, 0) if self.role == self.ROLE_DECISION else (60, 150, 255)
            
            trail_dot = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(trail_dot, (*base, alph), (2, 2), 2)
            surface.blit(trail_dot, (tpx - 2, tpy - 2))

        # 2. Body
        if self.status == self.STATUS_DEAD:
            pygame.draw.circle(surface, (150, 50, 50), (px, py), radius, 2)
            o = radius - 2
            pygame.draw.line(surface, (150, 50, 50), (px-o, py-o), (px+o, py+o), 2)
            pygame.draw.line(surface, (150, 50, 50), (px+o, py-o), (px-o, py+o), 2)
        else:
            color = (255, 215, 0) if self.role == self.ROLE_DECISION else (60, 150, 255)
            # Outer glow
            glow = pygame.Surface((radius*4, radius*4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, 40), (radius*2, radius*2), radius*1.5)
            surface.blit(glow, (px - radius*2, py - radius*2))
            
            pygame.draw.circle(surface, color, (px, py), radius)
            
            # Leader pulse
            if self.role == self.ROLE_DECISION:
                pr = int(radius + 4 + 3 * math.sin(self._pulse))
                pygame.draw.circle(surface, (255, 255, 255, 100), (px, py), pr, 1)

        # 3. Stats (Battery)
        if self.status != self.STATUS_DEAD:
            bc = (60, 200, 80) if self.battery > 60 else (220, 180, 0) if self.battery > 30 else (220, 60, 60)
            bw = int(radius * 2 * (self.battery / 100.0))
            pygame.draw.rect(surface, (30, 30, 30), (px - radius, py + radius + 4, radius * 2, 4))
            pygame.draw.rect(surface, bc, (px - radius, py + radius + 4, bw, 4))

        # 4. Label
        label = font_small.render(self.drone_id.replace("drone_", "D"), True, (255, 255, 255))
        surface.blit(label, (px - label.get_width() // 2, py - radius - label.get_height() - 4))