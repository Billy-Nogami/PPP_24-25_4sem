import redis.asyncio as redis
from fastapi import WebSocket
from typing import Dict
from app.core.config import settings

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = redis.Redis.from_url(settings.REDIS_URL)  # Инициализация Redis
        print("WebSocketManager initialized with Redis")

    async def connect(self, client_id: str, websocket: WebSocket):
        print(f"CONNECT: Client {client_id} connecting...")
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"CONNECT: Client {client_id} connected. Total: {len(self.active_connections)}")
        print(f"Active connections: {list(self.active_connections.keys())}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")

    async def send_message(self, client_id: str, message: str):
        print(f"SEND_MESSAGE: Attempting to send to {client_id}")
        print(f"Active connections: {list(self.active_connections.keys())}")
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_text(message)
                print(f"Message sent to {client_id}: {message}")
                return True
            except Exception as e:
                print(f"Error sending to {client_id}: {str(e)}")
                self.disconnect(client_id)
                return False
        else:
            print(f"No active connection for {client_id}. Active connections: {list(self.active_connections.keys())}")
            return False

    async def publish_message(self, client_id: str, message: str):
        """Публикует сообщение в Redis для доставки через WebSocket"""
        # Для Celery задач - публикуем в Redis
        channel = f"ws:{client_id}"
        await self.redis.publish(channel, message)
        print(f"Published to Redis channel {channel}: {message}")
        return True

manager = WebSocketManager()