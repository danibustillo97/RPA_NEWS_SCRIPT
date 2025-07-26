from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL or SUPABASE_KEY not set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_article(article):
    response = supabase.table("news").insert(article).execute()
    return response
