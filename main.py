import os
import re
import time
import hashlib
import requests
from urllib.parse import urlparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv

# 🔐 Configuración de entorno
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 📰 Fuentes mejoradas
NEWS_SOURCES = [
    "https://www.espn.com.co/", "https://www.tycsports.com/", "https://www.goal.com/es",
    "https://as.com/", "https://www.marca.com/", "https://www.futbolred.com/",
    "https://www.elgrafico.com.ar/", "https://www.rpctv.com/deportes", "https://www.ovacion.pe/",
    "https://www.eluniverso.com/deportes/", "https://mexico.as.com/", "https://espndeportes.espn.com/",
    "https://us.as.com/", "https://www.elnacional.com/deportes/", "https://www.elcolombiano.com/deportes/",
    "https://www.eltiempo.com/deportes", "https://www.elheraldo.co/deportes",
    "https://www.depor.com/", "https://www.tudn.com/futbol", "https://www.larepublica.pe/deportes/"
]

# Categorías
LEAGUE_KEYWORDS = {
    "premier": "Premier League", "laliga": "La Liga", "liga española": "La Liga", "bundesliga": "Bundesliga",
    "serie a": "Serie A", "champions": "Champions League", "libertadores": "Copa Libertadores",
    "sudamericana": "Copa Sudamericana", "mls": "MLS", "colombia": "Liga BetPlay",
    "argentina": "Liga Profesional Argentina", "brasil": "Brasileirão", "liga mx": "Liga MX",
    "ecuador": "LigaPro", "perú": "Liga 1", "uruguay": "Primera División Uruguay",
    "paraguay": "Primera División Paraguay", "chile": "Primera División Chile"
}

COUNTRIES = [
    "colombia", "españa", "argentina", "brasil", "méxico", "alemania", "inglaterra", "italia",
    "francia", "ecuador", "perú", "uruguay", "chile", "paraguay", "venezuela", "estados unidos"
]

TEAMS = [
    "barcelona", "real madrid", "manchester", "liverpool", "juventus", "bayern", "inter", "milan",
    "river", "boca", "nacional", "junior", "américa", "santa fe", "medellín", "atlético nacional",
    "flamengo", "palmeiras", "pumas", "chivas", "cruz azul"
]

OPENROUTER_MODEL = "meta-llama/llama-3-70b-instruct"

def clean_text(t):
    return re.sub(r'\s+', ' ', t).strip()

def normalize_url(url):
    return re.sub(r'\?.*$', '', url).rstrip("/")

def extract_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return None

def is_duplicate(title, url):
    slug = hashlib.md5(title.encode()).hexdigest()
    norm_url = normalize_url(url)
    r = supabase.table("news").select("slug, source_url").or_(
        f"slug.eq.{slug},source_url.eq.{norm_url}"
    ).execute()
    return len(r.data) > 0

def is_valid_article_link(href, text):
    href = href.lower()
    return (
        any(p in href for p in ["/202", "/deportes", "/noticia", "/futbol", "news"]) and
        len(text) > 40 and not href.endswith(".pdf")
    )

def extract_image_url(url):
    try:
        r = requests.get(url, timeout=10)
        s = BeautifulSoup(r.text, "html.parser")
        m = s.find("meta", property="og:image")
        if m and m.get("content"):
            return m["content"]
        img = s.find("img")
        if img and img.get("src") and not img["src"].startswith("data:"):
            return img["src"]
    except Exception as e:
        print("⚠️ Img error:", e)
    return "https://via.placeholder.com/1200x675.png?text=Noticia+deportiva"

def rewrite_title(title):
    print(f"✍️ Reescribiendo título: {title}")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Responde solo con el título reescrito. No agregues comillas ni explicaciones. Máximo 12 palabras."},
            {"role": "user", "content": f"{title}"}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            new_title = r.json()["choices"][0]["message"]["content"].strip()
            return new_title if len(new_title.split()) >= 5 else title
    except Exception as e:
        print("⚠️ Error conexión OpenRouter:", e)
    return title

def generate_content(title, source_url):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Redacta una noticia profesional clara, sin adornos, basada en este título: {title}. "
        f"Solo contenido puro, sin repetir el título ni añadir instrucciones. Cierra con esta fuente: {source_url}"
    )
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Responde solo con el contenido. No incluyas instrucciones."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("⚠️ Error OpenRouter:", e)
    return ""

def detect_league(t): 
    for k, v in LEAGUE_KEYWORDS.items():
        if k in t.lower():
            return v
    return "General"

def detect_country(text):
    for c in COUNTRIES:
        if c in text.lower():
            return c.capitalize()
    return None

def detect_team(text):
    for t in TEAMS:
        if t in text.lower():
            return t.capitalize()
    return None

def extract_tags(content):
    keywords = ["fútbol", "liga", "partido", "equipo", "jugador", "goles", "campeón"]
    return [k for k in keywords if k in content.lower()]

def generate_summary(content):
    return content[:150] + "..." if len(content) > 100 else None

def estimate_seo_score(content):
    score = 0
    if len(content) > 300:
        score += 50
    keywords = ["fútbol", "liga", "partido", "equipo", "jugador", "goles"]
    score += sum(1 for k in keywords if k in content.lower()) * 10
    return min(score, 100)

def save_article(article):
    slug = hashlib.md5(article['title'].encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    content = article["content"]
    data = {
        "title": article["title"],
        "slug": slug,
        "content": content,
        "image_url": article["image_url"],
        "source_url": normalize_url(article["url"]),
        "author": "Noirs Virals",
        "status": "draft",
        "published_at": now,
        "created_at": now,
        "category": detect_league(article["title"]),
        "source": extract_domain(article["url"]),
        "league": detect_league(article["title"]),
        "country": detect_country(content),
        "team": detect_team(content),
        "tags": extract_tags(content),
        "summary": generate_summary(content),
        "relevance_score": estimate_seo_score(content),
        "language": "es",
        "seo_score": estimate_seo_score(content)
    }
    print("💾 Guardando:", data["title"])
    supabase.table("news").insert(data).execute()

def fetch_news():
    articles = []
    seen_urls = set()
    for src in NEWS_SOURCES:
        print("🌍 Revisando fuente:", src)
        try:
            r = requests.get(src, timeout=10)
            s = BeautifulSoup(r.text, "html.parser")
            for a in s.find_all("a", href=True):
                href, t = a["href"], clean_text(a.get_text())
                if not href.startswith("http"):
                    href = src.rstrip("/") + "/" + href.lstrip("/")
                href = normalize_url(href)
                if is_valid_article_link(href, t) and href not in seen_urls:
                    seen_urls.add(href)
                    articles.append({"title": t, "url": href})
        except Exception as e:
            print("⚠️ Error fuente:", e)
    return articles

def main():
    articles = fetch_news()
    print("🔍 Total artículos encontrados:", len(articles))
    saved = 0
    for art in articles:
        print("📌 Procesando:", art["title"][:60])
        if is_duplicate(art["title"], art["url"]):
            print("⛔ Duplicado.")
            continue
        art["title"] = rewrite_title(art["title"])
        art["content"] = generate_content(art["title"], art["url"])
        if not art["content"] or len(art["content"]) < 200:
            print("⛔ Contenido inválido.")
            continue
        img = extract_image_url(art["url"])
        if not img or "placeholder" in img:
            print("⛔ Imagen inválida.")
            continue
        art["image_url"] = img
        save_article(art)
        saved += 1
        time.sleep(1)
        if saved >= 5:
            break
    print("✅ Noticias guardadas:", saved)

if __name__ == "__main__":
    main()
