import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CheckRequest,
    CheckResponse,
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfile,
    CheckoutResponse,
)
from supabase_client import (
    find_cached_check,
    save_check,
    get_history,
    create_user,
    find_user_by_email,
    find_user_by_id,
    create_transaction,
    find_transaction_by_order_id,
    update_transaction_status,
    activate_subscription,
)
from groq_service import analyze_content
from url_fetcher import is_url, fetch_article_text
from tavily_service import search_related_sources
from auth_service import hash_password, verify_password, create_access_token
from dependencies import get_current_user
from midtrans_service import create_subscription_checkout, SUBSCRIPTION_PRICE, verify_notification_signature

app = FastAPI(title="Misinformation Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # nanti dipersempit ke domain frontend pas production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Misinformation Detector API is running"}


@app.post("/api/check", response_model=CheckResponse)
async def check_misinformation(payload: CheckRequest):
    raw_content = payload.content.strip()

    # 0. Cek cache dulu pakai input asli (URL atau teks) sebagai key,
    #    biar cache tetap kena walau fetch artikel beda-beda tiap kali
    cached = find_cached_check(raw_content)
    if cached:
        return CheckResponse(
            verdict=cached["verdict"],
            confidence=cached["confidence"],
            explanation=cached["explanation"],
            sources=cached.get("sources") or [],
            from_cache=True,
        )

    # 1. Kalau input berupa URL, fetch isi artikelnya dulu
    if is_url(raw_content):
        try:
            content_to_analyze = fetch_article_text(raw_content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        content_to_analyze = raw_content

    # 2. Search web pakai Tavily buat dapetin konteks terbaru (grounding)
    #    Query pakai raw_content (klaim asli), bukan hasil fetch yang bisa panjang
    search_query = raw_content if not is_url(raw_content) else content_to_analyze[:200]
    search_context, sources = search_related_sources(search_query)

    # 3. Panggil Groq, dikasih konteks hasil search buat grounding
    try:
        result = analyze_content(content_to_analyze, search_context=search_context, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menganalisis konten: {str(e)}")

    # 4. Simpan hasil ke Supabase, key-nya tetap input asli (raw_content)
    save_check(
        content=raw_content,
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        sources=result["sources"],
    )

    return CheckResponse(
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        sources=result["sources"],
        from_cache=False,
    )


@app.get("/api/checks/history")
async def check_history(limit: int = 20):
    return get_history(limit=limit)


# ==========================
# Auth endpoints
# ==========================

@app.post("/api/auth/register", response_model=UserProfile)
async def register(payload: RegisterRequest):
    existing = find_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    hashed = hash_password(payload.password)
    new_user = create_user(email=payload.email, password_hash=hashed)

    if not new_user:
        raise HTTPException(status_code=500, detail="Gagal membuat akun, coba lagi")

    return UserProfile(
        id=new_user["id"],
        email=new_user["email"],
        subscription_status=new_user["subscription_status"],
        subscription_expires_at=new_user.get("subscription_expires_at"),
        api_key=new_user.get("api_key"),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    user = find_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Email atau password salah")

    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    token = create_access_token(user_id=user["id"], email=user["email"])
    return TokenResponse(access_token=token)


@app.get("/api/account/me", response_model=UserProfile)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        subscription_status=current_user["subscription_status"],
        subscription_expires_at=current_user.get("subscription_expires_at"),
        api_key=current_user.get("api_key"),
    )


# ==========================
# Subscription / payment endpoints
# ==========================

@app.post("/api/subscription/checkout", response_model=CheckoutResponse)
async def create_checkout(current_user: dict = Depends(get_current_user)):
    checkout = create_subscription_checkout(
        user_id=current_user["id"],
        email=current_user["email"],
    )

    transaction = create_transaction(
        user_id=current_user["id"],
        midtrans_order_id=checkout["order_id"],
        amount=SUBSCRIPTION_PRICE,
    )

    if not transaction:
        raise HTTPException(status_code=500, detail="Gagal membuat transaksi, coba lagi")

    return CheckoutResponse(
        order_id=checkout["order_id"],
        snap_token=checkout["token"],
        redirect_url=checkout["redirect_url"],
    )


@app.post("/api/subscription/webhook")
async def midtrans_webhook(payload: dict):
    """
    Endpoint yang didengerin Midtrans buat notifikasi status pembayaran.
    Tidak butuh login (dipanggil server-to-server oleh Midtrans), tapi signature
    tetap diverifikasi supaya tidak bisa dipalsukan.
    """
    order_id = payload.get("order_id")
    status_code = payload.get("status_code")
    gross_amount = payload.get("gross_amount")
    signature_key = payload.get("signature_key")
    transaction_status = payload.get("transaction_status")

    if not all([order_id, status_code, gross_amount, signature_key, transaction_status]):
        raise HTTPException(status_code=400, detail="Payload notifikasi tidak lengkap")

    # 1. Verifikasi signature, tolak kalau tidak valid
    is_valid = verify_notification_signature(order_id, status_code, gross_amount, signature_key)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Signature tidak valid")

    # 2. Pastikan transaksi ini memang ada di database kita
    transaction = find_transaction_by_order_id(order_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")

    # 3. Update status transaksi sesuai notifikasi
    update_transaction_status(order_id, transaction_status)

    # 4. Kalau pembayaran sukses, aktifkan subscription user
    if transaction_status in ("settlement", "capture"):
        user_id = transaction["user_id"]
        user = find_user_by_id(user_id)

        # Generate api_key baru cuma kalau user belum punya, biar key lama tetap valid
        # kalau ini perpanjangan subscription, bukan pembelian pertama
        api_key = user.get("api_key") if user and user.get("api_key") else secrets.token_urlsafe(32)

        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        activate_subscription(user_id=user_id, api_key=api_key, expires_at=expires_at)

    return {"message": "Notifikasi diterima"}