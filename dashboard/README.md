# 🏗️ NOVA Dashboard (v1)

### React-based Real-time Telemetry Visualizer

This dashboard component is the primary visual interface for the **Project NOVA (Jatayu)** swarm simulation. It connects to the simulation backend via a WebSocket bridge to provide real-time updates on drone status and world state.

---

## 🚦 Features

- **🌐 Live Grid Visualization**: Real-time position tracking for all 8 drones.
- **🔋 Battery & Status Monitor**: Visual health indicators for each agent in the mesh.
- **🛰 WebSocket Integration**: Seamless bi-directional comms with the `ws_bridge.py`.

---

## ⚙️ Setup & Run

1.  **Install**:
    ```bash
    npm install
    ```
2.  **Launch**:
    ```bash
    npm run dev
    ```
3.  **Port**: Defaults to `http://localhost:5173`.

---

*Part of the Project NOVA (Jatayu) Swarm Intelligence Suite.*
