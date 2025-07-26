from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from src.ai.rewriter import rewrite_text
from src.utils.category_mapper import map_category
import logging

ZONACERO_BASE_URL = "https://zonacero.com"

CATEGORIAS_PERMITIDAS = [
    "colombia", "zona-caribe", "atlantico", "soledad", "barranquilla",
    "liga-colombiana", "luto", "cartagena", "tour-de-francia", "generales",
    "mundo", "podcast", "politica", "sociales", "eventos", "deportes",
    "tecnologia", "multimedia"
]

def scrape_zonacero():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(ZONACERO_BASE_URL, timeout=60000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    # Extraer las noticias destacadas del home
    destacados = soup.select("div.views-row > a[href^='/']")
    urls = set()

    for link in destacados:
        href = link.get("href")
        if not href:
            continue
        full_url = ZONACERO_BASE_URL + href
        urls.add(full_url)

    # Extraer las de "Lo más leído"
    mas_leido = soup.select("div.block-lo-mas-leido a[href^='/']")
    for link in mas_leido:
        href = link.get("href")
        full_url = ZONACERO_BASE_URL + href
        urls.add(full_url)

    noticias = []

    for url in urls:
        try:
            noticia = scrape_detalle(url)
            if noticia:
                noticias.append(noticia)
        except Exception as e:
            logging.warning(f"❌ Error al procesar {url}: {e}")

    return noticias


def scrape_detalle(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, 'html.parser')

    title_tag = soup.find("h1")
    content_div = soup.find("div", class_="field-item even")
    category_tag = soup.find("a", href=lambda x: x and '/categoria/' in x)
    image_tag = soup.select_one("meta[property='og:image']")

    if not title_tag or not content_div:
        return None

    raw_title = title_tag.get_text(strip=True)
    rewritten_title = rewrite_text(raw_title)

    paragraphs = content_div.find_all("p")
    content_text = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40])

    rewritten_content = rewrite_text(content_text)

    raw_category = category_tag.get_text(strip=True) if category_tag else "generales"
    mapped_category = map_category(raw_category)

    return {
        "title": rewritten_title,
        "original_title": raw_title,
        "content": rewritten_content,
        "original_content": content_text,
        "category": mapped_category,
        "source": "Zona Cero",
        "source_url": url,
        "image_url": image_tag["content"] if image_tag else None,
        "published_at": datetime.now().isoformat()
    }
