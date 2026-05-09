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
      
      {/* Enhanced Tactical Coordinates Overlay with Glassmorphism */}
      <div className="absolute top-4 left-4 z-[1000] font-mono text-[10px] text-cyan-400 bg-gradient-to-br from-black/80 to-cyan-950/40 p-3 border border-cyan-400/30 backdrop-blur-xl rounded-xl shadow-[0_0_30px_rgba(6,182,212,0.15)]">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_8px_#06b6d4]" />
          <span className="font-bold tracking-wider">TACTICAL OVERLAY</span>
        </div>
        {state.drones.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-slate-500">ACTIVE MESH:</span>
              <span className="text-white font-bold">{state.drones.filter(d => d.alive).length}</span>
              <span className="text-slate-500">NODES</span>
            </div>
        )}
        <div className="mt-1 text-slate-400">
          <span className="text-slate-500">GRID SCALE:</span> 1 UNIT = 10M
        </div>
      </div>

      {/* Enhanced Target Acquisition Panel with Animations */}
      {target && (
        <div className="absolute bottom-6 left-6 z-[1000] p-5 bg-gradient-to-br from-black/95 via-red-950/30 to-black/95 border border-red-500/40 rounded-2xl backdrop-blur-2xl shadow-[0_0_40px_rgba(239,68,68,0.25)] animate-[slideInLeft_0.3s_ease-out]">
           <div className="flex items-center gap-2 mb-3">
             <div className="w-3 h-3 bg-red-500 rounded-full animate-ping absolute" />
             <div className="w-3 h-3 bg-red-500 rounded-full shadow-[0_0_12px_#ef4444]" />
             <span className="text-red-400 font-bold text-xs uppercase tracking-widest ml-2">Target Acquired</span>
           </div>
           <div className="text-[11px] text-slate-300 font-mono mb-4 space-y-1 bg-black/30 p-3 rounded-lg border border-white/5">
             <div className="flex justify-between">
               <span className="text-slate-500">COORD:</span>
               <span className="text-cyan-400 font-bold">{target.gridX}, {target.gridY}</span>
             </div>
             <div className="flex justify-between">
               <span className="text-slate-500">RADIUS:</span>
               <span className="text-emerald-400 font-bold">10 UNITS</span>
             </div>
             <div className="flex justify-between">
               <span className="text-slate-500">AREA:</span>
               <span className="text-amber-400 font-bold">~3,140 m²</span>
             </div>
           </div>
           <button 
             onClick={() => onSendAction?.({ action: "goto_target", target_grid: { x: target.gridX, y: target.gridY }})}
             className="w-full py-3 bg-gradient-to-r from-red-600 via-red-500 to-red-600 text-xs font-black rounded-xl hover:from-red-500 hover:via-red-400 hover:to-red-500 transition-all duration-300 shadow-[0_0_20px_rgba(239,68,68,0.4)] hover:shadow-[0_0_30px_rgba(239,68,68,0.6)] uppercase tracking-widest border border-red-400/30 hover:scale-105 transform"
           >
             🚁 DISPATCH SWARM
           </button>
        </div>
      )}
    </div>
  );
}
