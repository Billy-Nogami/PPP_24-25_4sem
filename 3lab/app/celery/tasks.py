from app.celery.celery_app import celery_app
from app.services.parser import parse_site
from app.db.session import SessionLocal
from app.cruds.task import update_task_result
from app.websocket.manager import manager  # Импортируем менеджер
import json
import asyncio

@celery_app.task
def parse_url_task(task_id: int, url: str, client_id: str):
    print(f"Starting task {task_id} for client {client_id}")
    
    try:
        links = parse_site(url)
        print(f"Found {len(links)} links")
        
        db = SessionLocal()
        result = json.dumps(links)
        update_task_result(db, task_id, result)
        print(f"Task {task_id} updated in database")
        
        # Создаем новое событийное окружение для асинхронного кода
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Отправка сообщения через Redis
        message = f"Task {task_id} completed. Found {len(links)} links."
        loop.run_until_complete(manager.publish_message(client_id, message))
        print(f"Message published for client {client_id}")
        
        return True
    except Exception as e:
        print(f"Error in task {task_id}: {str(e)}")
        raise
    finally:
        loop.close()