import os
import re
import time
import unicodedata
import requests
import logging
from urllib.parse import urlparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
import dateparser

HISTORIAL_FILE = "visited_urls.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

def load_visited_urls():
    if not os.path.exists(HISTORIAL_FILE):
        return set()
    with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_visited_url(url):
    with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

visited_urls = load_visited_urls()

CATEGORIES = {
    "deporte": ["fútbol", "liga", "gol", "equipo", "partido", "copa", "jugador", "deporte", "champions", "final", "junior", "barranquilla"],
    "economía": ["economía", "bolsa", "dólar", "finanzas", "impuestos", "negocios", "banco", "comercio"],
    "política": ["política", "elección", "congreso", "senado", "presidente", "ministro", "gobierno", "alcalde"],
    "salud": ["salud", "virus", "covid", "enfermedad", "hospital", "vacuna", "medicina"],
    "tecnología": ["tecnología", "software", "hardware", "internet", "redes sociales", "ciencia", "robot", "inteligencia artificial"],
    "internacional": ["eeuu", "china", "rusia", "venezuela", "ucrania", "naciones unidas", "acuerdo", "conflicto", "europa"],
    "cultura": ["cultura", "cine", "música", "arte", "literatura", "concierto", "exposición"],
    "entretenimiento": ["farandula", "celebridad", "espectáculo", "show", "televisión", "reality"],
    "judicial": ["corte", "justicia", "denuncia", "proceso", "fiscalía", "juez", "sentencia"],
    "colombia": ["colombia", "bogotá", "medellín", "cali", "barranquilla", "cartagena", "manizales", "pereira", "bucaramanga"],
    "junior": ["junior", "junior de barranquilla", "tiburón", "barranquilla", "rojiblanco", "banderazo"]
}

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
    "junior", "junior de barranquilla", "barcelona", "real madrid", "manchester", "liverpool", "juventus", "bayern", "inter", "milan",
    "river", "boca", "nacional", "junior", "américa", "santa fe", "medellín", "atlético nacional",
    "flamengo", "palmeiras", "pumas", "chivas", "cruz azul"
]

NEWS_SOURCES = [
    "https://www.eltiempo.com/", "https://www.elcolombiano.com/", "https://www.semana.com/", "https://caracol.com.co/", "https://www.rcnradio.com/",
    "https://www.larepublica.co/", "https://www.bluradio.com/", "https://www.elespectador.com/", "https://noticias.canal1.com.co/", "https://www.vanguardia.com/",
    "https://www.elheraldo.co/", "https://zonacero.com/", "https://www.adnradio.com.co/", "https://www.elpais.com.co/",
    "https://www.antena2.com/", "https://www.futbolred.com/", "https://deportes.canalrcn.com/",
    "https://www.infobae.com/", "https://www.tycsports.com/", "https://www.ole.com.ar/", "https://www.clarin.com/", "https://www.lanacion.com.ar/",
    "https://www.marca.com/", "https://as.com/", "https://www.mundodeportivo.com/", "https://www.elmundo.es/", "https://elpais.com/",
    "https://cnnespanol.cnn.com/", "https://www.bbc.com/mundo", "https://elpais.com/", "https://www.eluniverso.com/",
    "https://www.abc.es/", "https://www.20minutos.es/", "https://www.expansion.com/",
    "https://www.xataka.com/", "https://hipertextual.com/", "https://www.fayerwayer.com/", "https://techcetera.co/", "https://www.dw.com/es/",
    "https://www.nytimes.com/es/", "https://www.nationalgeographic.com.es/", "https://www.noticiasrcn.com/tecnologia",
    "https://www.portafolio.co/", "https://www.dinero.com/", "https://forbes.co/",
    "https://www.sopitas.com/", "https://www.latercera.com/", "https://www.bolavip.com/", "https://www.goal.com/es",
    "https://www.elcomercio.pe/", "https://www.elbocon.pe/", "https://www.larepublica.pe/",
    "https://www.mediotiempo.com/", "https://www.debate.com.mx/deportes/", "https://www.univision.com/noticias/",
    "https://www.culturagenial.com/es/", "https://www.elcultural.com/", "https://www.elconfidencial.com/cultura/"
]

# ENV y conexión supabase
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def rewrite_title(title: str) -> str:
    return title.strip().capitalize()

def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def clean_ai_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def summarize_text(text: str) -> str:
    return text[:160] + "..." if len(text) > 160 else text

def extract_tags(text: str) -> list:
    return list(set(re.findall(r'\b\w{4,}\b', text.lower())))[:5]

def generate_slug(title: str) -> str:
    slug = unicodedata.normalize("NFKD", title.lower()).encode("ascii", "ignore").decode("utf-8")
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug

def is_duplicate(slug: str, source_url: str) -> bool:
    res = supabase.table("news").select("slug", "source_url").or_(f"slug.eq.{slug},source_url.eq.{source_url}").execute()
    return bool(res.data)

def detect_category(title: str, content: str) -> str:
    text = (title + " " + content).lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                if cat == "junior":
                    return "banderazo rojo"
                return cat
    return "actualidad"

def detect_league(text: str) -> str:
    text = text.lower()
    for k, v in LEAGUE_KEYWORDS.items():
        if k in text:
            return v
    return "General"

def detect_country(text: str):
    text = text.lower()
    for c in COUNTRIES:
        if c in text:
            return c.capitalize()
    return None

def detect_team(text: str):
    text = text.lower()
    for t in TEAMS:
        if t in text:
            return t.capitalize()
    return None

def extract_domain(url: str):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return None

def estimate_seo_score(content: str) -> int:
    score = 50 if len(content) > 300 else 0
    keywords = ["fútbol", "liga", "partido", "equipo", "jugador", "goles", "junior", "colombia", "noticia", "presidente"]
    score += sum(10 for k in keywords if k in content.lower())
    return min(score, 100)

def extract_body(url: str) -> str:
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        desc = soup.find("meta", attrs={"name": "description"})
        ps = soup.find_all("p")
        ps_text = " ".join([p.get_text(strip=True) for p in ps if len(p.get_text(strip=True)) > 40])
        if desc and desc.get("content"):
            text = desc["content"].strip() + " " + ps_text
        else:
            text = ps_text if ps_text else soup.get_text(" ", strip=True)
        text = re.sub(r'\s+', ' ', text)
        text = ". ".join(dict.fromkeys(text.split(". ")))  # Eliminar frases duplicadas
        return text[:3500]
    except Exception as e:
        logging.warning(f"[extract_body] Error: {e}")
        return ""

def extract_image_url(url: str) -> str:
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for selector in ["meta[property='og:image']", "img"]:
            tag = soup.select_one(selector)
            if tag:
                src = tag.get("content") if selector.startswith("meta") else tag.get("src")
                if src and not src.startswith("data:"):
                    return src
    except Exception as e:
        logging.warning(f"[extract_image_url] {e}")
    return "https://via.placeholder.com/1200x675.png?text=Noticia+destacada"

def generate_content(title: str, url: str) -> str:
    body = extract_body(url)
    if not body or len(body) < 100:
        logging.info(f"[generate_content] Contenido insuficiente para {title}")
        return rewrite_title(title)
    texto = rewrite_title(title)
    if texto.lower() not in body.lower():
        texto += ". "
    texto += body
    texto = clean_text(texto)
    if len(texto) < 400:
        texto += (
            " Información en desarrollo y análisis de expertos serán añadidos a medida que surjan nuevos datos relevantes."
        )
    return texto

def fetch_news() -> list:
    articles = []
    for src in NEWS_SOURCES:
        logging.info(f"Revisando fuente: {src}")
        try:
            res = requests.get(src, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href, text = a["href"], clean_text(a.get_text())
                if len(text) > 40 and any(p in href for p in ["noticia", "news", "/202", "junior", "colombia", "politica", "deporte", "economia", "cultura", "salud"]):
                    full_url = href if href.startswith("http") else src.rstrip("/") + "/" + href.lstrip("/")
                    if full_url in visited_urls:
                        continue
                    time_tag = a.find_previous('time') or a.find_next('time')
                    published_at = dateparser.parse(time_tag.get_text()) if time_tag else None
                    if not published_at:
                        meta = soup.find("meta", attrs={"property": "article:published_time"})
                        published_at = dateparser.parse(meta["content"]) if meta and meta.get("content") else None
                    if published_at and not published_at.tzinfo:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                    articles.append({"title": text, "url": full_url, "published_at": published_at})
        except Exception as e:
            logging.warning(f"[fetch_news] Error fuente {src}: {e}")
            continue
    return articles

def save_article(article: dict):
    slug = generate_slug(article["title"])
    now = datetime.now(timezone.utc).isoformat()
    content = clean_ai_text(article["content"])
    category = detect_category(article["title"], content)
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
        "category": category,
        "source": extract_domain(article["url"]),
        "league": detect_league(article["title"]),
        "country": detect_country(content),
        "team": detect_team(content),
        "tags": extract_tags(content),
        "summary": summarize_text(content),
        "relevance_score": estimate_seo_score(content),
        "language": "es",
        "seo_score": estimate_seo_score(content)
    }
    supabase.table("news").insert(data).execute()
    save_visited_url(article["url"])
    logging.info(f"Artículo guardado: {data['title']} | Categoría: {category}")

def main():
    articles = fetch_news()
    logging.info(f"Total artículos encontrados: {len(articles)}")
    articles = sorted(
        [a for a in articles if a["published_at"]],
        key=lambda x: x["published_at"],
        reverse=True
    )
    saved = 0
    for article in articles:
        article["title"] = rewrite_title(article["title"])
        slug = generate_slug(article["title"])
        if is_duplicate(slug, article["url"]):
            logging.info(f"Noticia duplicada ignorada: {slug}")
            continue
        article["content"] = generate_content(article["title"], article["url"])
        if not article["content"] or len(article["content"]) < 200:
            logging.info(f"Contenido demasiado corto: {article['title']}")
            continue
        image = extract_image_url(article["url"])
        if not image or "placeholder.com" in image:
            logging.info(f"Imagen no válida o genérica: {article['title']}")
            continue
        article["image_url"] = image
        save_article(article)
        saved += 1
        if saved >= 30:
            break
        time.sleep(1)
    logging.info(f"✅ Proceso finalizado. Noticias guardadas: {saved}")

if __name__ == "__main__":
    main()
