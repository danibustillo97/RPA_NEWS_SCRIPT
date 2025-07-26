def is_valid_article(article: dict) -> bool:
    title = article.get("title", "").strip()
    content = article.get("original_content", "").strip()
    if title and content and len(content) > 30:  # En lugar de 10 o 100
        return True
    return False
