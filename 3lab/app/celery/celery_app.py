from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    include=["app.celery.tasks"]  # Убедитесь, что это есть
)

# Явно импортируем задачи
from app.celery import tasks  # Добавьте эту строку