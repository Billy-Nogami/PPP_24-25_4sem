import websockets
import asyncio
import uuid
import httpx
import json

async def main():
    client_id = str(uuid.uuid4())
    print(f"Ваш client_id: {client_id}")
    
    # Аутентификация
    username = input("Введите имя пользователя: ")
    password = input("Введите пароль: ")
    
    async with httpx.AsyncClient() as client:
        # Получение токена
        try:
            token_response = await client.post(
                "http://localhost:8000/token",
                data={"username": username, "password": password, "grant_type": "password"}
            )
            
            if token_response.status_code != 200:
                print(f"Ошибка аутентификации: {token_response.status_code}")
                return
                
            token_data = token_response.json()
            access_token = token_data["access_token"]
            print("✅ Аутентификация успешна!")
            
        except Exception as e:
            print(f"❌ Ошибка при получении токена: {e}")
            return

    try:
        # Устанавливаем WebSocket соединение
        async with websockets.connect(
            f"ws://localhost:8000/ws/{client_id}",
            ping_interval=30,
            ping_timeout=120
        ) as websocket:
            # Проверка соединения
            await websocket.send("TEST_CONNECTION")
            response = await websocket.recv()
            if response != "CONNECTION_OK":
                print("Ошибка подключения к WebSocket")
                return

            # Отправка задачи
            url = input("Введите URL для парсинга: ")
            build_graph = input("Построить граф сайта? (y/n): ").lower() == 'y'
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/parse-url",
                    json={
                        "url": url,
                        "client_id": client_id,
                        "build_graph": build_graph
                    },
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                task_info = response.json()
                print(f"\nЗадача создана. ID: {task_info['id']}")

            # Ожидание результата с отображением прогресса
            print("\nПрогресс выполнения:")
            print("=" * 50)
            
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    
                    # Обработка ping/pong
                    if message == "ping":
                        await websocket.send("pong")
                        continue
                    
                    try:
                        data = json.loads(message)
                        
                        # Отображение прогресса
                        if data.get("type") == "progress":
                            msg = data["message"]
                            count = data.get("count", 0)
                            
                            # Форматированный вывод
                            if "Обработка" in msg:
                                print(f"\n {msg}")
                            elif "Результат" in msg:
                                status = count
                                status_str = f"Статус: {status}"
                                if status == 200:
                                    print(f" {status_str}")
                                elif status >= 400:
                                    print(f" {status_str}")
                                else:
                                    print(f"ℹ️ {status_str}")
                            elif "Найдено ссылок" in msg:
                                print(f" {msg}")
                            else:
                                print(f"ℹ️ {msg}")
                        
                        # Отображение результата
                        elif data.get("type") == "result":
                            result_data = data.get("data", {})
                            print("\n" + "=" * 50)
                            print("🎉 ЗАДАЧА ЗАВЕРШЕНА")
                            
                            if build_graph:
                                graph = result_data.get("graph", {})
                                print(f"Узлов графа: {len(graph)}")
                                print(f"Связей: {sum(len(links) for links in graph.values())}")
                                print(f"Сообщение: {result_data.get('message', '')}")
                            else:
                                links = result_data.get("links", [])
                                print(f"Найдено ссылок: {len(links)}")
                                print("Первые 5 ссылок:")
                                for link in links[:5]:
                                    print(f"  • {link}")
                            
                            print("=" * 50)
                            break
                    
                    except json.JSONDecodeError:
                        print(f"📨 {message}")
                
                except asyncio.TimeoutError:
                    # Отправляем ping для поддержания соединения
                    try:
                        await websocket.send("ping")
                        print("⚡ Отправлен ping для поддержания соединения")
                    except:
                        break
                    
                except Exception as e:
                    print(f"⚠️ Ошибка: {e}")
                    break
                    
    except Exception as e:
        print(f"⛔ Критическая ошибка: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("🌐 РЕАЛЬНЫЙ МОНИТОРИНГ ПАРСИНГА САЙТОВ")
    print("=" * 50)
    asyncio.run(main())