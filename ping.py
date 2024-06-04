import asyncio
import websockets

async def ping_ws(ws_url):
    try:
        async with websockets.connect(ws_url) as ws:
            pass
        print(f"Successfully connected to {ws_url}")
    except Exception as e:
        print(f"Failed to connect to {ws_url}: {e}")

# Replace with your WebSocket URL
ws_url = "wss://api.studio.thegraph.com/proxy/74187/p2pmainnet/version/latest"

# Run the function
asyncio.run(ping_ws(ws_url))