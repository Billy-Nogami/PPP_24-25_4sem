import re
import httpx
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from collections import deque
from typing import Dict, List, Union, Callable

# Добавим тип для callback-функции прогресса
ProgressCallback = Callable[[str, int], None]

def extract_links(html: str) -> list[str]:
    return re.findall(r'href=[\'\"]?([^\'\" >]+)', html)

def parse_site(
    url: str, 
    build_graph: bool = False, 
    max_depth: int = 2,
    progress_callback: ProgressCallback = None
) -> Union[List[str], Dict[str, List[str]]]:
    """Парсинг сайта с callback для прогресса"""
    if not build_graph:
        try:
            # Отправляем событие о начале обработки
            if progress_callback:
                progress_callback(f"Обработка {url}", 0)
            
            response = httpx.get(url)
            status = response.status_code
            
            # Отправляем событие о результате
            if progress_callback:
                progress_callback(f"Результат {url}", status)
            
            if status == 200:
                links = extract_links(response.text)
                if progress_callback:
                    progress_callback(f"Найдено ссылок: {len(links)}", len(links))
                return links
            return []
        except Exception as e:
            if progress_callback:
                progress_callback(f"Ошибка: {str(e)}", 500)
            return []
    
    # Режим построения графа
    parsed_base = urlparse(url)
    base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
    graph = {}
    visited = set()
    queue = deque([(url, 0)])
    
    with httpx.Client() as client:
        while queue:
            current_url, depth = queue.popleft()
            
            if current_url in visited or depth > max_depth:
                continue
                
            visited.add(current_url)
            
            try:
                # Отправляем событие о начале обработки страницы
                if progress_callback:
                    progress_callback(f"Обработка {current_url}", depth)
                
                response = client.get(current_url, follow_redirects=True, timeout=5.0)
                status = response.status_code
                
                # Отправляем событие о результате запроса
                if progress_callback:
                    progress_callback(f"Результат {current_url}", status)
                
                if status != 200:
                    graph[current_url] = []
                    continue
                
                links = extract_links(response.text)
                absolute_links = []
                
                for link in links:
                    absolute_link = urljoin(current_url, link)
                    parsed = urlparse(absolute_link)
                    
                    if parsed.netloc == parsed_base.netloc:
                        absolute_link = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
                        absolute_links.append(absolute_link)
                        
                        if absolute_link not in visited:
                            queue.append((absolute_link, depth + 1))
                
                graph[current_url] = absolute_links
                
                # Отправляем событие о найденных ссылках
                if progress_callback:
                    progress_callback(f"Найдено ссылок: {len(absolute_links)}", len(absolute_links))
                
            except Exception as e:
                error_msg = f"Ошибка: {str(e)}"
                if progress_callback:
                    progress_callback(error_msg, 500)
                graph[current_url] = []
    
    return graph

# Функция graph_to_graphml без изменений
def graph_to_graphml(graph: Dict[str, List[str]]) -> str:
    """Конвертирует граф в формат GraphML"""
    root = ET.Element("graphml")
    root.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
    
    # Добавляем ключи
    ET.SubElement(root, "key", id="node_id", **{"for": "node", "attr.name": "label", "attr.type": "string"})
    ET.SubElement(root, "key", id="edge_id", **{"for": "edge", "attr.name": "label", "attr.type": "string"})
    
    # Создаем граф
    graph_elem = ET.SubElement(root, "graph", id="G", edgedefault="directed")
    
    # Создаем узлы
    node_ids = {}
    for i, node_url in enumerate(graph.keys()):
        node_id = f"n{i}"
        node_ids[node_url] = node_id
        node_elem = ET.SubElement(graph_elem, "node", id=node_id)
        data_elem = ET.SubElement(node_elem, "data", key="node_id")
        data_elem.text = node_url
    
    # Создаем ребра
    edge_counter = 0
    for source, targets in graph.items():
        if source not in node_ids:
            continue
            
        for target in targets:
            if target in node_ids:
                edge_id = f"e{edge_counter}"
                edge_counter += 1
                edge_elem = ET.SubElement(
                    graph_elem, 
                    "edge", 
                    id=edge_id, 
                    source=node_ids[source], 
                    target=node_ids[target]
                )
                data_elem = ET.SubElement(edge_elem, "data", key="edge_id")
                data_elem.text = f"{source} → {target}"
    
    # Форматируем XML
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="unicode")