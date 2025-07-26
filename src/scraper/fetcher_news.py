import logging
# from src.scraper.sites.zonacero_scraper import scrape_zonacero
from src.scraper.scrape_colombia_news_with_ai import scrape_all
from src.utils.validator import is_valid_article
from src.utils.media import is_valid_image_url
from src.ai.rewriter import summarize_text
from src.db.supabase import save_article

def fetch_and_process_news():
    logging.info("🗞️ Iniciando fetch y procesamiento de noticias...")
    # articles = scrape_zonacero()
    articles = scrape_all()
    total_valid = 0

    for art in articles:
        try:
            if not is_valid_article(art):
                logging.info(f"⏩ Noticia descartada por validación: {art.get('title', '')[:60]}...")
                continue

            summary = summarize_text(art["original_content"])

            processed = {
                "title": art["title"],
                "content": summary,
                "image_url": art["image_url"] if is_valid_image_url(art["image_url"]) else None,
                "source_url": art["source_url"],
                "category": art["category"],
                "source": art["source"],
                "status": "draft"
            }

            save_article(processed)
            logging.info(f"✅ Guardado: {processed['title'][:60]}...")
            total_valid += 1

        except Exception as e:
            logging.error(f"❌ Error guardando noticia: {e}")

    logging.info(f"📦 Total noticias válidas obtenidas: {total_valid}")
