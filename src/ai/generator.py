from transformers import pipeline

# Más estable que Vamsi/T5_Paraphrase_Paws y compatible con tu setup
rewriter = pipeline("text2text-generation", model="t5-base")

def rewrite_text(text: str) -> str:
    prompt = f"Paraphrase: {text}"
    result = rewriter(prompt, max_length=256, do_sample=True, top_k=50)[0]['generated_text']
    return result

def summarize_text(text: str) -> str:
    prompt = f"summarize: {text}"
    result = rewriter(prompt, max_length=100, do_sample=False)[0]['generated_text']
    return result
