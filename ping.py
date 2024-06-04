import asyncio
import websockets

async def connect():
    uri = "wss://api.studio.thegraph.com/proxy/74187/p2pmainnet/version/latest"
    headers = {
        # Add any required headers here
        # 'Authorization': 'Bearer YOUR_TOKEN',
        # 'Some-Header': 'HeaderValue',
    }
    
    try:
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print("Connected to the WebSocket.")
            await websocket.send("Hello, WebSocket!")
            response = await websocket.recv()
            print(f"Received: {response}")
    except websockets.exceptions.InvalidHandshake as e:
        print(f"Invalid handshake: {e}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

asyncio.get_event_loop().run_until_complete(connect())
