from transformers import pipeline

# Puedes cambiar los modelos si quieres versiones más pequeñas o específicas
rewrite_pipeline = pipeline("text2text-generation", model="t5-small", max_length=32)
content_pipeline = pipeline("text-generation", model="gpt2", max_length=512)
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

keywords = ["fútbol", "liga", "partido", "equipo", "jugador", "goles", "campeón"]

def rewrite_title(title):
    prompt = f"Reescribe este título de forma atractiva y concisa en español: {title}"
    output = rewrite_pipeline(prompt)[0]['generated_text']
    return output.strip()

def generate_content(title):
    prompt = f"Redacta una noticia profesional en español sobre: {title}. Al menos 300 palabras."
    result = content_pipeline(prompt)[0]['generated_text']
    return result.strip()

def summarize_text(content):
    if len(content) < 150:
        return content
    return summarizer(content[:1000])[0]['summary_text']

def extract_tags(content):
    return [k for k in keywords if k in content.lower()]
