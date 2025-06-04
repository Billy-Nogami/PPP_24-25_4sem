import websockets
import asyncio
import uuid
import httpx
import json

async def main():
    client_id = str(uuid.uuid4())
    print(f"Ваш client_id: {client_id}")
    
    # Аутентификация пользователя
    username = input("Введите имя пользователя: ")
    password = input("Введите пароль: ")
    
    async with httpx.AsyncClient() as client:
        # Получаем токен аутентификации
        try:
            token_response = await client.post(
                "http://localhost:8000/token",
                data={
                    "username": username,
                    "password": password,
                    "grant_type": "password"
                }
            )
            
            if token_response.status_code != 200:
                print(f"Ошибка аутентификации: {token_response.status_code}")
                print(token_response.text)
                return
                
            token_data = token_response.json()
            access_token = token_data["access_token"]
            print("Успешная аутентификация!")
        except Exception as e:
            print(f"Ошибка при получении токена: {e}")
            return

    try:
        # Устанавливаем WebSocket соединение
        async with websockets.connect(f"ws://localhost:8000/ws/{client_id}") as websocket:
            print("Устанавливаем WebSocket соединение...")
            
            # Проверяем соединение
            await websocket.send("TEST_CONNECTION")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            if response == "CONNECTION_OK":
                print("Соединение проверено и работает корректно.")
            else:
                print(f"Неожиданный ответ от сервера: {response}")
                return

            # Запрос URL для парсинга
            url = input("Введите URL для парсинга: ")
            
            # Отправляем задачу на парсинг с авторизацией
            async with httpx.AsyncClient() as client:
                print("Отправляем задачу на парсинг...")
                try:
                    response = await client.post(
                        "http://localhost:8000/parse-url",
                        json={"url": url, "client_id": client_id},
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    if response.status_code != 200:
                        print(f"Ошибка при отправке задачи: {response.status_code}")
                        print(response.text)
                        return
                        
                    task_info = response.json()
                    print("Задача отправлена:", task_info)
                    print(f"ID задачи: {task_info['id']}")
                except Exception as e:
                    print(f"Ошибка при отправке задачи: {e}")
                    return

            # Ожидаем результат
            print("Ожидаем результат...")
            timeout_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    
                    # Обработка ping/pong
                    if message == "ping":
                        await websocket.send("pong")
                        print("Получен ping, отправлен pong")
                        continue
                    
                    # Проверяем, относится ли сообщение к нашей задаче
                    try:
                        message_data = json.loads(message)
                        if "task_id" in message_data and message_data["task_id"] == task_info["id"]:
                            print("\n" + "="*50)
                            print("Получен результат задачи:")
                            print(f"Статус: {message_data.get('status')}")
                            print(f"Сообщение: {message_data.get('message')}")
                            
                            if "result" in message_data:
                                print(f"Найдено ссылок: {len(message_data['result'])}")
                                print("Первые 5 ссылок:")
                                for link in message_data["result"][:5]:
                                    print(f"- {link}")
                            
                            print("="*50 + "\n")
                            break
                    except json.JSONDecodeError:
                        # Если сообщение не JSON, проверяем как текст
                        if "Task" in message and str(task_info['id']) in message:
                            print("Ответ от сервера:", message)
                            break
                        else:
                            print(f"Получено сообщение: {message}")
                    
                except asyncio.TimeoutError:
                    timeout_count += 1
                    if timeout_count > 4:  # 2 минуты ожидания (30 сек * 4)
                        print("Таймаут: результат не получен в течение 2 минут")
                        break
                    print("Ожидание результата...")
                except websockets.exceptions.ConnectionClosed:
                    print("Соединение закрыто сервером")
                    break
                except Exception as e:
                    print(f"Ошибка при получении сообщения: {e}")
                    break
                    
            # Проверяем статус задачи в базе
            try:
                async with httpx.AsyncClient() as client:
                    task_response = await client.get(
                        f"http://localhost:8000/tasks/{task_info['id']}",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    if task_response.status_code == 200:
                        task_data = task_response.json()
                        print(f"Финальный статус задачи: {task_data['status']}")
                        if task_data['result']:
                            try:
                                links = json.loads(task_data['result'])
                                print(f"Всего найдено ссылок: {len(links)}")
                            except:
                                print(f"Результат: {task_data['result'][:100]}...")
                    else:
                        print(f"Не удалось получить статус задачи: {task_response.status_code}")
            except Exception as e:
                print(f"Ошибка при проверке статуса задачи: {e}")
                
    except Exception as e:
        print(f"Ошибка при подключении к WebSocket: {e}")

if __name__ == "__main__":
    asyncio.run(main())