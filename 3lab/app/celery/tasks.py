from app.celery.celery_app import celery_app
from app.services.parser import parse_site, graph_to_graphml
from app.db.session import SessionLocal
from app.cruds.task import update_task_result
from app.websocket.manager import manager
import json
import asyncio

@celery_app.task
def parse_url_task(task_id: int, url: str, client_id: str, build_graph: bool = False, max_depth: int = 2):
    print(f"Начата задача {task_id} для клиента {client_id}")
    
    # Создаем event loop для асинхронных операций
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def send_progress(message: str, count: int = 0):
        """Отправляет прогресс через WebSocket"""
        try:
            await manager.publish_message(client_id, json.dumps({
                "type": "progress",
                "task_id": task_id,
                "message": message,
                "count": count
            }))
        except Exception as e:
            print(f"Ошибка отправки прогресса: {e}")
    
    try:
        # Отправляем начальное событие
        loop.run_until_complete(send_progress(f"Начата обработка {url}"))
        
        if build_graph:
            # Запускаем парсинг с callback
            graph = parse_site(
                url, 
                build_graph=True, 
                max_depth=max_depth,
                progress_callback=lambda msg, cnt: loop.run_until_complete(
                    send_progress(msg, cnt)
                )
            )
            
            # Конвертируем в GraphML
            loop.run_until_complete(send_progress("Генерация GraphML..."))
            graphml = graph_to_graphml(graph)
            
            result = json.dumps({
                "graph": graph,
                "graphml": graphml,
                "message": f"Построен граф из {len(graph)} страниц"
            })
            
            # Отправляем финальный результат
            loop.run_until_complete(send_progress("Задача завершена", len(graph)))
        else:
            # Простой режим парсинга
            links = parse_site(
                url,
                progress_callback=lambda msg, cnt: loop.run_until_complete(
                    send_progress(msg, cnt)
                )
            )
            result = json.dumps({
                "links": links,
                "message": f"Найдено {len(links)} ссылок"
            })
            loop.run_until_complete(send_progress("Задача завершена", len(links)))
        
        # Обновляем задачу в базе
        db = SessionLocal()
        update_task_result(db, task_id, result)
        
        # Отправляем финальный результат
        loop.run_until_complete(
            manager.publish_message(client_id, json.dumps({
                "type": "result",
                "task_id": task_id,
                "data": json.loads(result)
            }))
        )
        
        return True
    except Exception as e:
        error_msg = f"Ошибка выполнения: {str(e)}"
        loop.run_until_complete(send_progress(error_msg))
        raise
    finally:
        loop.close()