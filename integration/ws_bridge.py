# integration/ws_bridge.py
import asyncio
import json
import websockets
import paho.mqtt.client as mqtt
from typing import Set

# Root import - assume root is in sys.path
try:
    import config
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import config

class SwarmBridge:
    """
    M5 Integration Tool: Bridges FoxMQ (MQTT) to Dashboard (WebSocket).
    Subscribes to 'nova/#' and forwards to all connected dashboard clients.
    """
    def __init__(self, host=config.FOXMQ_HOST, port=config.FOXMQ_PORT, ws_port=config.WS_PORT):
        self.mqtt_host = host
        self.mqtt_port = port
        self.ws_port = ws_port
        
        self.clients: Set = set()
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[BRIDGE] Connected to FoxMQ @ {self.mqtt_host}:{self.mqtt_port}")
        client.subscribe("nova/#")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            data = {
                "topic": msg.topic,
                "payload": payload
            }
            # Forward to all connected WS clients
            if self.clients:
                message = json.dumps(data)
                asyncio.run_coroutine_threadsafe(self.broadcast_ws(message), self.loop)
        except Exception as e:
            print(f"[BRIDGE] Error processing MQTT: {e}")

    async def broadcast_ws(self, message: str):
        if self.clients:
            await asyncio.gather(*[client.send(message) for client in self.clients])

    async def ws_handler(self, websocket):
        print(f"[BRIDGE] New dashboard client connected.")
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # Handle incoming from Dashboard (e.g. ESTOP, MISSION SWITCH)
                try:
                    data = json.loads(message)
                    topic = data.get("topic")
                    payload = data.get("payload")
                    if topic and payload:
                        print(f"[BRIDGE] Dashboard -> MQTT: {topic}")
                        self.mqtt_client.publish(topic, json.dumps(payload))
                except Exception as e:
                    print(f"[BRIDGE] Error parsing dashboard msg: {e}")
        finally:
            self.clients.remove(websocket)
            print(f"[BRIDGE] Dashboard client disconnected.")

    async def run(self):
        self.loop = asyncio.get_running_loop()
        
        # Start MQTT Loop in background thread
        print(f"[BRIDGE] Starting MQTT client...")
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.mqtt_client.loop_start()
        
        # Start WebSocket Server
        print(f"[BRIDGE] Starting WebSocket server on port {self.ws_port}...")
        async with websockets.serve(self.ws_handler, "0.0.0.0", self.ws_port):
            await asyncio.Future()  # run forever

if __name__ == "__main__":
    bridge = SwarmBridge()
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        print("\n[BRIDGE] Stopping...")
