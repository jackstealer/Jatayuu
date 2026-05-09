# 🛰️ PROJECT NOVA — Advanced Drone Swarm Intelligence v2.0

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-010101?style=for-the-badge&logo=socket.io&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-OpenStreetMap-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A real-time autonomous drone swarm simulation and command platform built with Python + React.**  
*Tactical swarm coordination · Live telemetry · Mission control · Emergency management*

![Project NOVA Dashboard](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

</div>

---

## 🌟 Overview

**Project NOVA** is a full-stack autonomous drone swarm intelligence system that simulates and controls a fleet of 8 AI-driven drones operating over a real map (New Delhi, India). The system features a glassmorphic real-time command dashboard with live telemetry, P2P mesh networking visualization, mission dispatch, kill/revive controls, and emergency stop.

> Built as a demonstration of distributed systems, swarm AI, and real-time WebSocket-powered dashboards.

---

## ✨ Features

### 🚁 Swarm Intelligence
- **8-drone autonomous fleet** — one leader (decision) + 7 scouts
- **100-task mission controller** — auto-generates sub-tasks distributed uniformly within a target zone
- **Leader election** — the decision drone coordinates task redistribution on peer failure
- **Crash takeover** — leader auto-redispatches the swarm when a drone crashes
- **P2P mesh visualization** — shows live communication links between drones within signal range (250m)

### 🗺️ Live Map
- **OpenStreetMap** tiles via Leaflet — centered on New Delhi
- Real-time drone position markers (gold = leader, blue = scout, red = crashed)
- Animated dashed mesh links between active nodes
- Target acquisition circle (click anywhere on the map)
- Mission sub-task visualization (amber dots showing pending objectives)
- Grid cell coloring for searched/survivor-detected zones

### 📡 Real-Time Dashboard
- **WebSocket bridge** (`ws://localhost:8765`) — 5Hz broadcast rate
- Live NODE_TELEMETRY panel — battery, coordinates, task count, status per drone
- Mission progress bar with dynamic total (not hardcoded)
- Event log with color-coded entries (DAMAGE, MISSION, TASK, INFO, E-STOP)
- ACTIVE MESH node count overlay on map

### 🎯 Mission Modes
| Mode | Theme |
|------|-------|
| 🔵 **Search & Rescue** | Urban SAR operations |
| 🟢 **Defense** | Perimeter security sweep |
| 🟠 **Wildfire** | Fire mapping and monitoring |
| 🟡 **Pollution Sweep** | Environmental monitoring |
| ⚪ **Medical Evac** | Casualty extraction routing |

### ⚡ Operator Controls
- **DISPATCH SWARM** — click map → assign all drones to 100-task mission
- **KILL drone** — simulate hardware failure on any individual drone
- **EMERGENCY STOP** — halt entire swarm instantly with ACK latency display
- **RESET SYSTEM** — fully revive all drones (including killed ones) and resume operations

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     NOVA SYSTEM                              │
│                                                             │
│  ┌──────────────┐    WebSocket     ┌────────────────────┐  │
│  │   Dashboard   │◄────────────────►│   WS Bridge        │  │
│  │  (React/TS)  │   ws://8765      │   (ws_bridge.py)   │  │
│  └──────────────┘                  └─────────┬──────────┘  │
│                                              │              │
│                                    SHARED_MESH (in-memory)  │
│                                              │              │
│              ┌───────────────────────────────┤              │
│              │           │           │       │              │
│         ┌────▼── ┐  ┌─────▼──┐  ┌────▼──┐  ...             │
│         │Drone 1 │  │Drone 2 │  │Drone 3│  (×8)            │
│         │(Leader)│  │(Scout) │  │(Scout)│                   │
│         └───────┘  └────────┘  └───────┘                   │
│                                                             │
│         ┌─────────────────────────────────────────┐        │
│         │         MissionController               │        │
│         │   Generates & distributes 100 tasks     │        │
│         └─────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | File | Role |
|-----------|------|------|
| **WsBridge** | `ws_bridge.py` | WebSocket server; aggregates mesh events; handles operator commands |
| **DroneAgent** | `main.py` | Async drone simulation loop; flight, battery, kill/revive lifecycle |
| **MissionController** | `main.py` | 100-task mission generator; async task queue with lock |
| **NovaMesh** | `mesh/nova_mesh.py` | MOCK-mode in-process pub/sub mesh with range simulation |
| **InMemoryMesh** | `mesh/in_memory_mesh.py` | Global singleton message broker for all nodes |
| **GridMap** | `dashboard/src/components/GridMap.tsx` | Leaflet map with live drone markers, links, target circle |
| **DroneCard** | `dashboard/src/components/DroneCard.tsx` | Per-drone telemetry card with kill button |
| **useSwarm** | `dashboard/src/hooks/useSwarm.ts` | WebSocket hook with exponential backoff reconnect |

---

## 🚀 Getting Started

### Prerequisites
- Python **3.11+**
- Node.js **18+**

### 1. Clone the Repository
```bash
git clone https://github.com/jackstealer/Jatayuu.git
cd Jatayuu
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd dashboard
npm install
cd ..
```

### 4. Configure Environment (Optional)
```bash
cp .env.example .env
# Edit .env to customize ports, drone count, etc.
```

### 5. Run the Backend
```bash
python main.py
```

### 6. Run the Dashboard (in a new terminal)
```bash
cd dashboard
npm run dev
```

### 7. Open the Dashboard
Navigate to **http://localhost:5173** in your browser.

---

## 🎮 How to Use

### Basic Operation
1. **Wait** for all 8 drones to appear on the map and in the right panel (NODE_COUNT: 8/8)
2. **Click anywhere on the map** to set a target — a red circle appears
3. Click **🚁 DISPATCH SWARM** — all drones fly to the zone and start completing 100 sub-tasks
4. Watch the **Mission Progress** bar increment in real time

### Killing a Drone
- Click the **⚠ Kill** button on any drone card in the right panel
- The drone immediately shows as 💀 CRASHED (red card) and stops completing tasks
- NODE_COUNT decrements
- The **leader drone** auto-reassigns the fallen drone's pending tasks to survivors

### Emergency Stop & Reset
- Click **EMERGENCY STOP** (top-right, red button) — all drones halt instantly
- The ACK latency panel shows response time per drone
- Click **RESET SYSTEM** (green button) — all drones resume, including previously killed ones

### Switching Mission Modes
- Use the **Operation Mode** panel at the bottom center
- Click any mode (DEFENSE, WILDFIRE, etc.) — the swarm adapts its behavior

---

## 📁 Project Structure

```
Jatayuu/
├── main.py                    # Entry point — spawns drones, starts bridge
├── ws_bridge.py               # WebSocket server & state aggregator
├── config.py                  # Shared constants (topics, ports, positions)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
│
├── mesh/
│   ├── nova_mesh.py           # NovaMesh node (publish/subscribe)
│   ├── in_memory_mesh.py      # Shared in-process MQTT-like broker
│   ├── routing_table.py       # Signal range & routing logic
│   ├── chaos_proxy.py         # Network chaos simulation
│   └── ...
│
├── swarm/
│   ├── auction_engine.py      # Task auction/bidding system
│   ├── leader_election.py     # Distributed leader election
│   ├── crdt_map.py            # CRDT-based shared world state
│   └── mission_config.py      # Mission parameter definitions
│
└── dashboard/
    ├── src/
    │   ├── App.tsx            # Root component & layout
    │   ├── components/
    │   │   ├── GridMap.tsx    # Leaflet map (drones, links, targets)
    │   │   ├── DroneCard.tsx  # Per-drone telemetry card
    │   │   ├── EStopPanel.tsx # Emergency stop + ACK display
    │   │   ├── EventLog.tsx   # Mission log with color coding
    │   │   ├── MissionSwitcher.tsx # Operation mode buttons
    │   │   └── types.ts       # Shared TypeScript interfaces
    │   └── hooks/
    │       └── useSwarm.ts    # WebSocket hook with auto-reconnect
    ├── package.json
    └── vite.config.ts
```

---

## ⚙️ Configuration

All configuration is in `config.py` and `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `WS_PORT` | `8765` | WebSocket server port |
| `NUM_DRONES` | `8` | Number of drones to spawn |
| `METERS_PER_UNIT` | `10.0` | Grid unit to meters conversion |
| `MAX_SIGNAL_RANGE` | `250.0` | P2P mesh signal range (meters) |
| `VITE_WS_PORT` | `8765` | Frontend WebSocket port (must match WS_PORT) |

**Run with custom settings:**
```bash
NUM_DRONES=12 WS_PORT=9000 python main.py
VITE_WS_PORT=9000 npm run dev --prefix dashboard
```

---

## 🔌 WebSocket API

The bridge broadcasts JSON state at ~5Hz to all connected clients:

### Server → Client (state broadcast)
```json
{
  "type": "state",
  "drones": [
    {
      "id": "drone_1",
      "x": 45.2, "y": -32.1,
      "battery": 97.4,
      "role": "decision",
      "alive": true,
      "current_task": "FLYING",
      "tasks_done": 12,
      "offline_since": null,
      "last_seen": 1715234567.89
    }
  ],
  "mission": "SAR",
  "estop": false,
  "mission_done": 45,
  "mission_total": 100,
  "mission_pct": 45.0,
  "alive_count": 7,
  "events": [...],
  "grid": {"28_14": "searched", ...}
}
```

### Client → Server (actions)
```json
{ "action": "estop" }                            // Emergency stop
{ "action": "reset" }                            // System reset + revive killed drones
{ "action": "kill", "drone_id": "drone_3" }      // Kill specific drone
{ "action": "mission", "mission": "Defense" }    // Switch mission mode
{ "action": "goto_target", "target_grid": { "x": 45, "y": -30 } }  // Dispatch swarm
```

---

## 🛠️ Tech Stack

### Backend
- **Python 3.11+** — async/await with `asyncio`
- **websockets 16.0** — WebSocket server
- **In-Memory Mesh** — custom pub/sub broker simulating MQTT without a broker process

### Frontend
- **React 19** + **TypeScript 5.9** — component-based UI
- **Vite 8** — blazing-fast dev server and bundler
- **Tailwind CSS v4** — utility-first styling with glassmorphism effects
- **Leaflet** — interactive OpenStreetMap integration
- **WebSocket API** — native browser WebSocket with exponential backoff reconnect

---

## 🐛 Known Limitations

- The simulation runs in MOCK mode (in-process mesh, no real MQTT broker needed)
- Drone positions are simulated — no real hardware integration
- Map is centered on New Delhi; coordinates are simulated relative to that center
- Battery drain is slowed 10× for demo purposes

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ by **jackstealer**

*"The swarm is greater than the sum of its drones."*

</div>
