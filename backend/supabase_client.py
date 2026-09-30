import os
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def find_cached_check(content: str):
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


def save_check(
    content: str,
    verdict: str,
    confidence: int,
    explanation: str,
    sources: list,
    user_id: str = None,
    counted: bool = False,
):
    result = (
        supabase.table("checks")
        .insert(
            {
                "content": content.strip(),
                "verdict": verdict,
                "confidence": confidence,
                "explanation": explanation,
                "sources": sources,
                "user_id": user_id,
                "counted": counted,
            }
        )
        .execute()
    )
    return result.data[0] if result.data else None


def count_checks_today(user_id: str) -> int:
    from datetime import datetime, timezone

    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    result = (
        supabase.table("checks")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("counted", True)
        .gte("created_at", start_of_day.isoformat())
        .execute()
    )
    return result.count or 0

def get_history(user_id: str, page: int = 1, page_size: int = 10):
    offset = (page - 1) * page_size
    result = (
        supabase.table("checks")
        .select("*", count="exact")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return result.data, (result.count or 0)

# ==========================
# User & Auth related queries
# ==========================

def create_user(email: str, password_hash: str):
    result = (
        supabase.table("users")
        .insert({"email": email.strip().lower(), "password_hash": password_hash})
        .execute()
    )
    return result.data[0] if result.data else None


def find_user_by_email(email: str):
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

def create_transaction(
    user_id: str,
    midtrans_order_id: str,
    amount: int,
    plan_type: str,
    duration_days: int,
):
    result = (
        supabase.table("transactions")
        .insert(
            {
                "user_id": user_id,
                "midtrans_order_id": midtrans_order_id,
                "amount": amount,
                "status": "pending",
                "plan_type": plan_type,
                "duration_days": duration_days,
            }
        )
        .execute()
    )
    return result.data[0] if result.data else None


def find_transaction_by_order_id(midtrans_order_id: str):
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
    result = (
        supabase.table("transactions")
        .update({"status": status})
        .eq("midtrans_order_id", midtrans_order_id)
        .execute()
    )
    return result.data[0] if result.data else None


def activate_subscription(user_id: str, api_key: str, expires_at: str, plan_type: str = None):
    result = (
        supabase.table("users")
        .update(
            {
                "subscription_status": "active",
                "api_key": api_key,
                "subscription_expires_at": expires_at,
                "plan_type": plan_type,
            }
        )
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None

def set_verification_token(user_id: str, token: str, expires_at):
    """Simpan token verifikasi baru untuk user (dipakai saat register & resend)."""
    supabase.table("users").update({
        "verification_token": token,
        "verification_token_expires_at": expires_at.isoformat(),
    }).eq("id", user_id).execute()


def verify_email_token(token: str):
    """
    Cari user berdasarkan token. Return dict user kalau valid & belum expired,
    None kalau token tidak ditemukan atau sudah expired.
    """
    result = supabase.table("users").select("*").eq("verification_token", token).execute()
    if not result.data:
        return None

    user = result.data[0]
    expires_at = datetime.fromisoformat(user["verification_token_expires_at"])
    if expires_at < datetime.now(timezone.utc):
        return None

    supabase.table("users").update({
        "email_verified": True,
        "verification_token": None,
        "verification_token_expires_at": None,
    }).eq("id", user["id"]).execute()

    return user


def find_user_by_email_for_resend(email: str):
    """Dipakai endpoint resend-verification. Return user dict atau None."""
    result = supabase.table("users").select("*").eq("email", email).execute()
    return result.data[0] if result.data else None