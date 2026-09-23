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


# ==========================
# User & Auth related queries
# ==========================

def create_user(email: str, password_hash: str):
    """
    Bikin user baru. subscription_status default 'inactive' (sesuai default di tabel).
    """
    result = (
        supabase.table("users")
        .insert({"email": email.strip().lower(), "password_hash": password_hash})
        .execute()
    )
    return result.data[0] if result.data else None


def find_user_by_email(email: str):
    """
    Cari user berdasarkan email. Return None kalau tidak ketemu.
    """
    result = (
        supabase.table("users")
        .select("*")
        .eq("email", email.strip().lower())
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def find_user_by_id(user_id: str):
    """
    Cari user berdasarkan id. Return None kalau tidak ketemu.
    """
    result = (
        supabase.table("users")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def find_user_by_api_key(api_key: str):
    """
    Cari user berdasarkan API key. Dipakai buat validasi endpoint developer API.
    Return None kalau tidak ketemu.
    """
    result = (
        supabase.table("users")
        .select("*")
        .eq("api_key", api_key)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


# ==========================
# Transaction related queries
# ==========================

def create_transaction(user_id: str, midtrans_order_id: str, amount: int):
    """
    Simpan record transaksi baru dengan status 'pending'.
    """
    result = (
        supabase.table("transactions")
        .insert(
            {
                "user_id": user_id,
                "midtrans_order_id": midtrans_order_id,
                "amount": amount,
                "status": "pending",
            }
        )
        .execute()
    )
    return result.data[0] if result.data else None


def find_transaction_by_order_id(midtrans_order_id: str):
    """
    Cari transaksi berdasarkan order_id dari Midtrans.
    """
    result = (
        supabase.table("transactions")
        .select("*")
        .eq("midtrans_order_id", midtrans_order_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def update_transaction_status(midtrans_order_id: str, status: str):
    """
    Update status transaksi (settlement/failed/expired) berdasarkan notifikasi Midtrans.
    """
    result = (
        supabase.table("transactions")
        .update({"status": status})
        .eq("midtrans_order_id", midtrans_order_id)
        .execute()
    )
    return result.data[0] if result.data else None


def activate_subscription(user_id: str, api_key: str, expires_at: str):
    """
    Aktifkan subscription user: set status 'active', generate api_key (kalau belum ada),
    dan set tanggal kedaluwarsa.
    """
    result = (
        supabase.table("users")
        .update(
            {
                "subscription_status": "active",
                "api_key": api_key,
                "subscription_expires_at": expires_at,
            }
        )
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None