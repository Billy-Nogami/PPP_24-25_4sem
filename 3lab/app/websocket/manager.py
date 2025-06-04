import redis.asyncio as redis
from fastapi import WebSocket
from typing import Dict
from app.core.config import settings

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = redis.Redis.from_url(settings.REDIS_URL)
        print("WebSocketManager initialized with Redis")

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, client_id: str, message: str):
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_text(message)
                return True
            except Exception:
                self.disconnect(client_id)
                return False
        return False

    async def publish_message(self, client_id: str, message: str):
        channel = f"ws:{client_id}"
        await self.redis.publish(channel, message)
        return True

manager = WebSocketManager()