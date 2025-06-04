from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.api import parse, auth
from app.websocket.manager import manager
import asyncio
import redis.asyncio as redis
from app.core.config import settings
import json

app = FastAPI()
app.include_router(auth.router)
app.include_router(parse.router)


# Keep-alive function to send periodic pings
async def keep_alive(websocket: WebSocket, client_id: str):
    while True:
        try:
            await asyncio.sleep(10)  # Send ping every 10 seconds
            await websocket.send_text("ping")
            print(f"Sent ping to client {client_id}")
        except Exception as e:
            print(f"Error sending ping to client {client_id}: {e}")
            break

@app.on_event("startup")
async def startup_event():
    r = redis.Redis.from_url(settings.REDIS_URL)
    try:
        await r.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        return

    pubsub = r.pubsub()
    await pubsub.psubscribe("ws:*")
    print("Subscribed to ws:* channels")

    async def redis_listener():
        print("Redis listener started")
        while True:
            message = await pubsub.get_message()
            if message and message["type"] == "pmessage":
                channel = message["channel"].decode()
                client_id = channel.split(":")[1]
                data = message["data"].decode()
                print(f"Received Redis message for {client_id}: {data}")
                success = await manager.send_message(client_id, data)
                if success:
                    print(f"Message sent to client {client_id}")
                else:
                    print(f"Failed to send message to client {client_id}")
            await asyncio.sleep(0.1)  # Prevent tight loop
    
    asyncio.create_task(redis_listener())
    print("Redis listener task started")

# main.py
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    print(f"Client {client_id} connected")
    keep_alive_task = asyncio.create_task(keep_alive(websocket, client_id))
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from client {client_id}: {data}")
            if data == "TEST_CONNECTION":
                await websocket.send_text("CONNECTION_OK")
                print(f"Sent CONNECTION_OK to client {client_id}")
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        manager.disconnect(client_id)
        keep_alive_task.cancel()
    except Exception as e:
        print(f"Unexpected error in WebSocket for client {client_id}: {e}")
        manager.disconnect(client_id)
        keep_alive_task.cancel()

@app.get("/check-connection/{client_id}")
async def check_connection(client_id: str):
    if client_id in manager.active_connections:
        return {"status": "connected"}
    return {"status": "disconnected"}


@app.get("/active-connections")
async def get_active_connections():
    return {
        "count": len(manager.active_connections),
        "connections": list(manager.active_connections.keys()),
    }
