#!/usr/bin/env python3
"""
Test script to dispatch a mission via WebSocket
Run this to automatically send a dispatch command
"""

import asyncio
import websockets
import json

async def dispatch_mission():
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to NOVA backend")
            
            # Send dispatch command
            command = {
                "action": "goto_target",
                "target_grid": {
                    "x": 50,
                    "y": 50,
                    "radius": 10
                }
            }
            
            await websocket.send(json.dumps(command))
            print(f"🚁 Dispatched mission to coordinates (50, 50)")
            print("✅ Mission sent! Check your dashboard.")
            
            # Wait a moment to receive confirmation
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the backend is running on port 8765")

if __name__ == "__main__":
    print("=" * 60)
    print("  NOVA Mission Dispatch Test")
    print("=" * 60)
    asyncio.run(dispatch_mission())
