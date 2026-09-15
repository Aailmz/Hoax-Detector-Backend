import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def find_cached_check(content: str):
    """
    Cek apakah konten yang mirip sudah pernah di-check sebelumnya.
    Pakai exact match dulu (simpel). Bisa diupgrade ke similarity search nanti.
    """
    result = (
        supabase.table("checks")
        .select("*")
        .ilike("content", content.strip())
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None

def save_check(content: str, verdict: str, confidence: int, explanation: str, sources: list):
    """
    Simpan hasil check baru ke Supabase.
    """
    result = (
        supabase.table("checks")
        .insert(
            {
                "content": content.strip(),
                "verdict": verdict,
                "confidence": confidence,
                "explanation": explanation,
                "sources": sources,
            }
        )
        .execute()
    )
    return result.data[0] if result.data else None

def get_history(limit: int = 20):
    """
    Ambil riwayat check terbaru.
    """
    result = (
        supabase.table("checks")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data