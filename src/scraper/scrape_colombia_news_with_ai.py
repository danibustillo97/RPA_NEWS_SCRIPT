import logging
from src.scrapers.utils import is_valid_article, clean_text
from src.scrapers.sources import get_colombia_sources
from src.supabase_client import save_articles_to_supabase
from src.ai.rewriter import rewrite_text, summarize_text, extract_tags

logger = logging.getLogger(__name__)

def fetch_colombia_news():
    logger.info("🗞️ Iniciando fetch y procesamiento de noticias...")
    sources = get_colombia_sources()
    all_articles = []

    for source in sources:
        try:
            logger.info(f"🌐 Scraping {source['url']}")
            articles = source["scraper_func"]()

            for art in articles:
                if not is_valid_article(art):
                    continue

                # ✍️ Reescribir título
                art["title"] = rewrite_text(art["title"]) or art["title"]

                # 🧠 Generar contenido resumido (como reemplazo de artículo completo)
                content_input = art.get("original_content", "") or art["title"]
                art["content"] = summarize_text(content_input) or clean_text(content_input)

                # 🏷️ Extraer etiquetas
                art["tags"] = extract_tags(art["content"])

                all_articles.append(art)

        except Exception as e:
            logger.error(f"❌ Error al procesar {source['url']}: {e}")

    valid_articles = [a for a in all_articles if is_valid_article(a)]
    logger.info(f"📦 Total noticias válidas obtenidas: {len(valid_articles)}")

    if valid_articles:
        save_articles_to_supabase(valid_articles)
