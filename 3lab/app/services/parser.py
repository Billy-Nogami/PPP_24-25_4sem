import re
import httpx

def extract_links(html: str) -> list[str]:
    return re.findall(r'href=[\'\"]?([^\'\" >]+)', html)

def parse_site(url: str) -> list[str]:
    try:
        response = httpx.get(url)
        if response.status_code == 200:
            return extract_links(response.text)
        return []
    except Exception:
        return []