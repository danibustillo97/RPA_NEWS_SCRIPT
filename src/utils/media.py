def is_valid_image_url(url: str | None) -> bool:
    if not url:
        return False
    return any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"])
