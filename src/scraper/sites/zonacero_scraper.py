import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import logging

logging.basicConfig(level=logging.INFO)

def scrape_zonacero():
    BASE_URL = "https://zonacero.com"
    SECTION_SELECTOR = "#block-views-block-ultimas-noticas-home-block-2 a"
    logging.info("🌐 Zona Cero...")

    try:
        res = requests.get(BASE_URL, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"❌ Zona Cero: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select(SECTION_SELECTOR)
    articles = []

    for a in links:
        href = a.get("href")
        if not href:
            continue
        full_url = urljoin(BASE_URL, href)

        try:
            article_res = requests.get(full_url, timeout=10)
            article_res.raise_for_status()
        except:
            continue

        article_soup = BeautifulSoup(article_res.text, "html.parser")
        title = article_soup.find("h1", class_="titulo-principal")
        content_blocks = article_soup.select("div.field--name-body p")

        content = "\n".join(p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True))
        if not title or not content or len(content) < 100:
            continue

        image = article_soup.select_one("meta[property='og:image']")
        image_url = image["content"] if image else None

        articles.append({
            "title": title.get_text(strip=True),
            "url": full_url,
            "source": "Zona Cero",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": image_url,
            "content": content
        })

    return articles

def scrape_elheraldo():
    BASE_URL = "https://www.elheraldo.co"
    logging.info("🌐 El Heraldo...")
    try:
        res = requests.get(BASE_URL, timeout=10)
        res.raise_for_status()
    except:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    article_links = soup.select("div.views-field-title a[href]")
    articles = []

    for a in article_links[:10]:
        href = a.get("href")
        full_url = urljoin(BASE_URL, href)
        try:
            article_res = requests.get(full_url, timeout=10)
            article_res.raise_for_status()
        except:
            continue

        article_soup = BeautifulSoup(article_res.text, "html.parser")
        title_tag = article_soup.find("h1")
        paragraphs = article_soup.select("div.field--name-body p")

        content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        if not title_tag or not content or len(content) < 100:
            continue

        image = article_soup.select_one("meta[property='og:image']")
        image_url = image["content"] if image else None

        articles.append({
            "title": title_tag.get_text(strip=True),
            "url": full_url,
            "source": "El Heraldo",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": image_url,
            "content": content
        })

    return articles

def scrape_semana():
    BASE_URL = "https://www.semana.com"
    logging.info("🌐 Semana...")
    try:
        res = requests.get(BASE_URL, timeout=10)
        res.raise_for_status()
    except:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    article_links = soup.select("article a[href^='/nacion/']")
    articles = []

    seen = set()
    for a in article_links[:10]:
        href = a.get("href")
        if href in seen:
            continue
        seen.add(href)

        full_url = urljoin(BASE_URL, href)
        try:
            article_res = requests.get(full_url, timeout=10)
            article_res.raise_for_status()
        except:
            continue

        article_soup = BeautifulSoup(article_res.text, "html.parser")
        title_tag = article_soup.find("h1")
        content_blocks = article_soup.select("div.article-body p")

        content = "\n".join(p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True))
        if not title_tag or not content or len(content) < 100:
            continue

        image = article_soup.select_one("meta[property='og:image']")
        image_url = image["content"] if image else None

        articles.append({
            "title": title_tag.get_text(strip=True),
            "url": full_url,
            "source": "Semana",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": image_url,
            "content": content
        })

    return articles

def scrape_caracol():
    BASE_URL = "https://noticias.caracoltv.com"
    logging.info("🌐 Noticias Caracol...")
    try:
        res = requests.get(BASE_URL, timeout=10)
        res.raise_for_status()
    except:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("a.card-title")
    articles = []

    for a in links[:10]:
        href = a.get("href")
        full_url = urljoin(BASE_URL, href)
        try:
            article_res = requests.get(full_url, timeout=10)
            article_res.raise_for_status()
        except:
            continue

        article_soup = BeautifulSoup(article_res.text, "html.parser")
        title_tag = article_soup.find("h1")
        content_blocks = article_soup.select("div.article-body p")

        content = "\n".join(p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True))
        if not title_tag or not content or len(content) < 100:
            continue

        image = article_soup.select_one("meta[property='og:image']")
        image_url = image["content"] if image else None

        articles.append({
            "title": title_tag.get_text(strip=True),
            "url": full_url,
            "source": "Noticias Caracol",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": image_url,
            "content": content
        })

    return articles

def scrape_rcn():
    BASE_URL = "https://www.noticiasrcn.com"
    logging.info("🌐 Noticias RCN...")
    try:
        res = requests.get(BASE_URL, timeout=10)
        res.raise_for_status()
    except:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("div.views-field-title a[href]")
    articles = []

    for a in links[:10]:
        href = a.get("href")
        full_url = urljoin(BASE_URL, href)
        try:
            article_res = requests.get(full_url, timeout=10)
            article_res.raise_for_status()
        except:
            continue

        article_soup = BeautifulSoup(article_res.text, "html.parser")
        title_tag = article_soup.find("h1")
        content_blocks = article_soup.select("div.article-content p")

        content = "\n".join(p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True))
        if not title_tag or not content or len(content) < 100:
            continue

        image = article_soup.select_one("meta[property='og:image']")
        image_url = image["content"] if image else None

        articles.append({
            "title": title_tag.get_text(strip=True),
            "url": full_url,
            "source": "Noticias RCN",
            "published_at": datetime.utcnow().isoformat(),
            "image_url": image_url,
            "content": content
        })

    return articles

# 🧠 Ejecutar todo junto
if __name__ == "__main__":
    logging.info("🚀 Iniciando scraping de noticias colombianas...")

    all_articles = (
        scrape_zonacero() +
        scrape_elheraldo() +
        scrape_semana() +
        scrape_caracol() +
        scrape_rcn()
    )

    logging.info(f"📦 Total general de noticias recolectadas: {len(all_articles)}")
    for article in all_articles[:5]:  # Mostrar solo las primeras 5
        logging.info(f"- {article['source']}: {article['title']}")

