import asyncio
import json
import socket

class MockBrokerServer:
    """
    A simple TCP-based Mock Broker for Project NOVA.
    Allows multiple processes (drones, bridge, dashboard) to share the mesh
    without requiring a real MQTT broker like Mosquitto.
    """
    def __init__(self, host="127.0.0.1", port=18833):
        self.host = host
        self.port = port
        self.clients = set() # Set of (reader, writer)

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[BROKER] Connection from {addr}")
        self.clients.add((reader, writer))
        
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                
                # Broadcast message to all OTHER clients
                for r, w in self.clients:
                    if w != writer:
                        try:
                            w.write(data)
                            await w.drain()
                        except:
                            pass
        except Exception as e:
            print(f"[BROKER] Error: {e}")
        finally:
            print(f"[BROKER] Disconnecting {addr}")
            self.clients.remove((reader, writer))
            writer.close()
            await writer.wait_closed()

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"[BROKER] Mock Broker listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    broker = MockBrokerServer()
    asyncio.run(broker.start())
