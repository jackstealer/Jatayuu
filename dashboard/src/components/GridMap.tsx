import { useRef, useEffect, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { SwarmState } from "./types";

// PRO-MAX ADVANCED CONSTANTS
const METERS_PER_UNIT = 10.0;
const DEG_PER_METER = 0.0000089; // Approx at equator/mid-latitudes
const SCALE = DEG_PER_METER * METERS_PER_UNIT; // Grid units to Lat/Lng degrees

const DRONE_COLORS: Record<string, string> = {
  decision: "#facc15", // Gold
  scout: "#3b82f6",    // Blue
};

function gridToLatLng(x: number, y: number) {
  const BASE_LNG = 77.209;  // Delhi center
  const BASE_LAT = 28.6139;
  return {
    lat: BASE_LAT - y * SCALE,
    lng: BASE_LNG + x * SCALE,
  };
}

function latLngToGrid(lat: number, lng: number) {
  const BASE_LNG = 77.209;
  const BASE_LAT = 28.6139;
  return {
    x: Math.round((lng - BASE_LNG) / SCALE),
    y: Math.round((BASE_LAT - lat) / SCALE),
  };
}

export function GridMap({
  state,
  connected,
  onSendAction,
}: {
  state: SwarmState;
  connected: boolean;
  onSendAction?: (action: any) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Map<string, L.CircleMarker>>(new Map());
  const linkLayerRef = useRef<L.LayerGroup | null>(null);
  const gridLayerRef = useRef<L.LayerGroup | null>(null);
  const targetLayerRef = useRef<L.LayerGroup | null>(null);
  const problemLayerRef = useRef<L.LayerGroup | null>(null);

  const [is3D, setIs3D] = useState(false);
  const [target, setTarget] = useState<{
    lat: number;
    lng: number;
    gridX: number;
    gridY: number;
    radius: number;
  } | null>(null);

  // ── Init map ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OSM",
      maxZoom: 19,
    });

    const sat = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      attribution: "© Esri",
      maxZoom: 19,
    });

    const map = L.map(containerRef.current, {
      center: [28.6139, 77.209],
      zoom: 17, // Start closer for detail
      layers: [osm],
      zoomControl: false,
    });

    map.on("click", (e) => {
      const { lat, lng } = e.latlng;
      const grid = latLngToGrid(lat, lng);
      setTarget({ lat, lng, gridX: grid.x, gridY: grid.y, radius: 10 });
    });

    gridLayerRef.current = L.layerGroup().addTo(map);
    linkLayerRef.current = L.layerGroup().addTo(map);
    targetLayerRef.current = L.layerGroup().addTo(map);
    problemLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Mesh Links & Drones ──────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    const ll = linkLayerRef.current;
    if (!map || !ll) return;

    ll.clearLayers();
    // Update Drones (Show all drones, handle crashes visually)
    const allDrones = state.drones;
    const droneIds = new Set(allDrones.map((d) => d.id));
    
    // Cleanup old markers
    for (const [id, marker] of markersRef.current) {
        if (!droneIds.has(id)) {
            marker.remove();
            markersRef.current.delete(id);
        }
    }

    // Draw Links (P2P Mesh Simulation) - Only for active nodes
    const live = allDrones.filter(d => d.alive);
    for (let i = 0; i < live.length; i++) {
        for (let j = i + 1; j < live.length; j++) {
            const d1 = live[i];
            const d2 = live[j];
            const dist = Math.sqrt((d1.x - d2.x)**2 + (d1.y - d2.y)**2) * 10;
            if (dist < 250) {
                const p1 = gridToLatLng(d1.x, d1.y);
                const p2 = gridToLatLng(d2.x, d2.y);
                L.polyline([[p1.lat, p1.lng], [p2.lat, p2.lng]], {
                    color: "#06b6d4",
                    weight: 2,
                    opacity: 0.3,
                    dashArray: "5, 5"
                }).addTo(ll);
            }
        }
    }

    for (const drone of allDrones) {
      const pos = gridToLatLng(drone.x, drone.y);
      const isAlive = drone.alive;
      const color = isAlive 
        ? (drone.role === "decision" ? DRONE_COLORS.decision : DRONE_COLORS.scout)
        : "#ef4444"; // Red for crash
      
      if (markersRef.current.has(drone.id)) {
        const marker = markersRef.current.get(drone.id)!;
        marker.setLatLng([pos.lat, pos.lng]);
        
        // Update styling if status changed
        if (!isAlive) {
           marker.setStyle({ fillColor: "#ef4444", color: "#fff", weight: 3 });
           if (!marker.getPopup()) {
             marker.bindPopup(`💥 ${drone.id} CRASHED`).openPopup();
           }
        }
      } else {
        const marker = L.circleMarker([pos.lat, pos.lng], {
          radius: drone.role === "decision" ? 12 : 8,
          color: isAlive ? "#090a0f" : "#fff",
          weight: 2,
          fillColor: color,
          fillOpacity: 1,
        }).addTo(map);
        
        if (!isAlive) {
            marker.bindPopup(`💥 ${drone.id} CRASHED`).openPopup();
        }
        
        markersRef.current.set(drone.id, marker);
      }
    }
  }, [state.drones]);

  // ── Sparse Grid Rendering ────────────────────────────────────────────────
  useEffect(() => {
    const gl = gridLayerRef.current;
    if (!gl) return;
    gl.clearLayers();

    for (const [key, cellState] of Object.entries(state.grid)) {
      const parts = key.split("_");
      if (parts.length !== 2) continue;
      const r = Number(parts[0]);
      const c = Number(parts[1]);

      const a = gridToLatLng(c, r);
      const b = gridToLatLng(c + 1, r + 1);

      let color = "#06b6d422";
      if (cellState === "searched") color = "#22c55e44";
      if (cellState === "survivor_detected") color = "#f97316";

      L.rectangle([[a.lat, a.lng], [b.lat, b.lng]], {
        color: "transparent",
        fillColor: color,
        fillOpacity: 0.5,
        interactive: false,
      }).addTo(gl);
    }
  }, [state.grid]);

  // ── Target Marker (Red Zone) ─────────────────────────────────────────────
  useEffect(() => {
    const tl = targetLayerRef.current;
    if (!tl) return;
    tl.clearLayers();
    
    if (target) {
      L.circle([target.lat, target.lng], {
        radius: target.radius * METERS_PER_UNIT, // Scale units to meters
        color: "#ef4444",
        fillColor: "#ef4444",
        fillOpacity: 0.2,
        weight: 2,
        dashArray: "5, 5"
      }).addTo(tl);

      // Also add a small center marker
      L.circleMarker([target.lat, target.lng], {
        radius: 4,
        color: "#ef4444",
        fillColor: "#ef4444",
        fillOpacity: 1
      }).addTo(tl);
    }
  }, [target]);

  // ── Mission Sub-Targets (Problems) ──
  useEffect(() => {
    const pl = problemLayerRef.current;
    if (!pl) return;
    pl.clearLayers();

    if (state.mission_targets) {
      state.mission_targets.forEach(([tx, ty]: [number, number]) => {
        const pos = gridToLatLng(tx, ty);
        L.circleMarker([pos.lat, pos.lng], {
          radius: 3,
          color: "#f59e0b", // Amber
          fillColor: "#f59e0b",
          fillOpacity: 1,
          weight: 1
        }).addTo(pl);
      });
    }
  }, [state.mission_targets]);

  return (
    <div className="w-full h-full relative">
      <div ref={containerRef} className="w-full h-full bg-[#090a0f]" />
      
      {/* Tactical Coordinates Overlay */}
      <div className="absolute top-4 left-4 z-[1000] font-mono text-[10px] text-cyan-400 bg-black/60 p-2 border border-cyan-400/20 backdrop-blur-md rounded">
        {state.drones.length > 0 && (
            <div>ACTIVE MESH: {state.drones.filter(d => d.alive).length} NODES</div>
        )}
        <div className="mt-1">GRID SCALE: 1 UNIT = 10M</div>
      </div>

      {target && (
        <div className="absolute bottom-6 left-6 z-[1000] p-4 bg-black/90 border border-red-500/30 rounded-xl backdrop-blur-xl">
           <div className="text-red-400 font-bold text-xs mb-2 uppercase tracking-widest">Target Acquired</div>
           <div className="text-[10px] text-slate-400 font-mono mb-4">
             COORD: {target.gridX}, {target.gridY}<br/>
             RADIUS: 10 UNITS
           </div>
           <button 
             onClick={() => onSendAction?.({ action: "goto_target", target_grid: { x: target.gridX, y: target.gridY }})}
             className="w-full py-2 bg-red-600 text-xs font-bold rounded-lg hover:bg-red-500 transition-colors"
           >
             DISPATCH SWARM
           </button>
        </div>
      )}
    </div>
  );
}
