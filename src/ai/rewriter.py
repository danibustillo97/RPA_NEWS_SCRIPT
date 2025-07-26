# src/ai/rewriter.py

from transformers import pipeline, Pipeline
from typing import List, Optional
import logging
import re

logging.basicConfig(level=logging.INFO)

class TextAIProcessor:
    def __init__(self):
        try:
            self.rewriter: Pipeline = pipeline("text2text-generation", model="t5-base")
        except Exception as e:
            logging.error(f"❌ Error cargando el modelo de reescritura: {e}")
            raise

    def rewrite_text(self, text: str, max_length: int = 256) -> Optional[str]:
        if not text or len(text) < 20:
            return None
        prompt = f"Paraphrase: {text.strip()}"
        try:
            result = self.rewriter(prompt, max_length=max_length, do_sample=True, top_k=50)
            output = result[0]['generated_text'].strip()
            return output if output.lower() != text.lower() else None
        except Exception as e:
            logging.error(f"❌ Error al reescribir: {e}")
            return None

    def summarize_text(self, text: str, max_length: int = 100) -> Optional[str]:
        if not text or len(text.split()) < 20:
            return None
        prompt = f"summarize: {text.strip()}"
        try:
            result = self.rewriter(prompt, max_length=max_length, do_sample=False)
            return result[0]['generated_text'].strip()
        except Exception as e:
            logging.error(f"❌ Error al resumir: {e}")
            return None

    def extract_tags(self, text: str, top_n: int = 5) -> List[str]:
        if not text:
            return []
        words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{4,}\b', text.lower())
        stopwords = set([
            "esta", "haber", "para", "desde", "luego", "tiene", "pero", "entre",
            "sobre", "cuando", "donde", "porque", "como", "solo", "todo", "cada", "más"
        ])
        filtered = [w for w in words if w not in stopwords]
        freq = {}
        for word in filtered:
            freq[word] = freq.get(word, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]

processor = TextAIProcessor()

def rewrite_text(text: str, max_length: int = 256):
    return processor.rewrite_text(text, max_length)

def summarize_text(text: str, max_length: int = 100):
    return processor.summarize_text(text, max_length)

def extract_tags(text: str, top_n: int = 5):
    return processor.extract_tags(text, top_n)
