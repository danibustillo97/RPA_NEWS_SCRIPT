import os
import re
import time
import unicodedata
import requests
from urllib.parse import urlparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
import dateparser

# Configuración de entorno
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
NEWS_SOURCES = [
    "https://www.espn.com.co/", "https://www.tycsports.com/", "https://as.com/", "https://www.marca.com/",
    "https://www.futbolred.com/", "https://www.elgrafico.com.ar/", "https://www.rpctv.com/deportes",
    "https://www.ovacion.pe/", "https://www.eluniverso.com/deportes/", "https://mexico.as.com/",
    "https://espndeportes.espn.com/", "https://us.as.com/", "https://www.elnacional.com/deportes/",
    "https://www.elcolombiano.com/deportes/", "https://www.eltiempo.com/deportes", "https://www.depor.com/", "https://www.tudn.com/futbol",
    "https://www.larepublica.pe/deportes/"
]
LEAGUE_KEYWORDS = {
    "premier": "Premier League", "laliga": "La Liga", "liga española": "La Liga", "bundesliga": "Bundesliga",
    "serie a": "Serie A", "champions": "Champions League", "libertadores": "Copa Libertadores",
    "sudamericana": "Copa Sudamericana", "mls": "MLS", "colombia": "Liga BetPlay",
    "argentina": "Liga Profesional Argentina", "brasil": "Brasileirão", "liga mx": "Liga MX",
    "ecuador": "LigaPro", "perú": "Liga 1", "uruguay": "Primera División Uruguay",
    "paraguay": "Primera División Paraguay", "chile": "Primera División Chile"
}
COUNTRIES = [
    "colombia", "españa", "argentina", "brasil", "méxico", "alemania", "inglaterra", "italia", "francia",
    "ecuador", "perú", "uruguay", "chile", "paraguay", "venezuela", "estados unidos"
]
TEAMS = [
    "barcelona", "real madrid", "manchester", "liverpool", "juventus", "bayern", "inter", "milan",
    "river", "boca", "nacional", "junior", "américa", "santa fe", "medellín", "atlético nacional",
    "flamengo", "palmeiras", "pumas", "chivas", "cruz azul"
]
OPENROUTER_MODEL = "meta-llama/llama-3-70b-instruct"

def generate_slug(title):
    slug = title.lower()
    slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode("utf-8")
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug

def is_duplicate(slug, source_url):
    r = supabase.table("news").select("slug", "source_url").or_(f"slug.eq.{slug},source_url.eq.{source_url}").execute()
    return len(r.data) > 0

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

def extract_domain(url):
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except:
        return None

def clean_text(t):
    return re.sub(r'\s+', ' ', t).strip()

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
            {"role": "system", "content": "Responde solo con el título reescrito. No agregues comillas, símbolos ni ninguna explicación. Manténlo corto, atractivo, en español neutro, sin adornos. Máximo 12 palabras."},
            {"role": "user", "content": title}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            new_title = r.json()["choices"][0]["message"]["content"].strip()
            if len(new_title.split()) < 5:
                return title
            return new_title
        return title
    except:
        return title

def generate_content(title, source_url):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Redacta una noticia profesional clara, fluida, en español neutro y sin adornos, basada en este título: {title}. "
        f"Debe ser un texto limpio, directo, sin frases decorativas, sin repetir el título, ni explicaciones ni encabezados. "
        f"Solo el contenido. Cierra con esta fuente: {source_url}"
    )
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Responde solo con el contenido de la noticia. No incluyas instrucciones ni encabezados."},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return ""
    except:
        return ""

def generate_summary(content):
    if len(content) < 100:
        return None
    return content[:150] + "..."

def extract_tags(content):
    keywords = ["fútbol", "liga", "partido", "equipo", "jugador", "goles", "campeón"]
    return [k for k in keywords if k in content.lower()]

def estimate_seo_score(content):
    score = 0
    if len(content) > 300:
        score += 50
    keywords = ["fútbol", "liga", "partido", "equipo", "jugador", "goles"]
    score += sum(1 for k in keywords if k in content.lower()) * 10
    return min(score, 100)

def fetch_news():
    articles = []
    for src in NEWS_SOURCES:
        print("🌐 Revisando fuente:", src)
        try:
            r = requests.get(src, timeout=10)
            s = BeautifulSoup(r.text, "html.parser")
            for a in s.find_all("a", href=True):
                href, t = a["href"], clean_text(a.get_text())
                if len(t) > 40 and any(p in href for p in ["noticia", "news", "/202"]):
                    full = href if href.startswith("http") else src.rstrip("/") + "/" + href.lstrip("/")
                    # Intentar extraer la fecha de publicación
                    published_at = None
                    try:
                        date_tag = a.find_previous('time') or a.find_next('time')
                        if date_tag:
                            published_at_str = date_tag.get_text()
                            published_at = dateparser.parse(published_at_str)
                        else:
                            date_meta = s.find("meta", attrs={"property": "article:published_time"})
                            if date_meta and date_meta.get("content"):
                                published_at_str = date_meta.get("content")
                                published_at = dateparser.parse(published_at_str)
                        if published_at and published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    except Exception as e:
                        print("⚠️ Error al extraer fecha:", e)
                    articles.append({"title": t, "url": full, "published_at": published_at})
        except Exception as e:
            print("⚠️ Error fuente:", e)
    return articles

def save_article(article):
    slug = generate_slug(article["title"])
    now = datetime.now(timezone.utc).isoformat()
    content = article["content"]
    data = {
        "title": article["title"],
        "slug": slug,
        "content": content,
        "image_url": article["image_url"],
        "source_url": article["url"],
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
    print("💾 Guardando artículo:", data["title"])
    supabase.table("news").insert(data).execute()

def main():
    articles = fetch_news()
    print("🔍 Total artículos encontrados:", len(articles))
    default_date = datetime.min.replace(tzinfo=timezone.utc)
    articles_sorted = sorted(articles, key=lambda x: x['published_at'] if x['published_at'] else default_date, reverse=True)

    saved = 0
    for art in articles_sorted:
        if not art['published_at']:
            continue

        art["title"] = rewrite_title(art["title"])
        slug = generate_slug(art["title"])
        print("Slug generado:", slug)  # Depuración
        if is_duplicate(slug, art["url"]):  # Verifica duplicados usando slug y la URL
            print("⛔ Noticia duplicada:", slug)
            continue

        art["content"] = generate_content(art["title"], art["url"])
        if not art["content"] or len(art["content"]) < 200:
            print("⛔ Contenido muy corto, saltando.")
            continue
        img = extract_image_url(art["url"])
        if not img or "placeholder.com" in img:
            print("⛔ Imagen no válida, saltando.")
            continue
        art["image_url"] = img
        save_article(art)
        saved += 1
        time.sleep(2)
        if saved >= 5:
            break
    print("✅ Proceso completado. Noticias guardadas:", saved)

if __name__ == "__main__":
    main()
