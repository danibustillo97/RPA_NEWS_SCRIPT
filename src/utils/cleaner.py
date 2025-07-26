import re

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text


### src/utils/media.py
import requests

def is_valid_image_url(url: str) -> bool:
    try:
        r = requests.head(url, timeout=5)
        return r.status_code == 200 and 'image' in r.headers['Content-Type']
    except:
        return False
