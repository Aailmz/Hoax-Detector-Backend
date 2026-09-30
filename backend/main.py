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
    CheckoutRequest,
    CheckoutResponse,
    CheckHistoryResponse,
    VerifyEmailResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
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
    count_checks_today,
    set_verification_token,
    verify_email_token,
    find_user_by_email_for_resend,
    set_reset_token,
    find_user_by_reset_token,
    update_password,
)

from groq_service import analyze_content
from url_fetcher import is_url, fetch_article_text
from tavily_service import search_related_sources
from auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    generate_verification_token,
    verification_token_expiry,
    generate_reset_token,
    reset_token_expiry,
)
from email_service import send_verification_email, send_reset_password_email
from dependencies import get_current_user
from midtrans_service import create_subscription_checkout, PLANS, verify_notification_signature

app = FastAPI(title="Misinformation Detector API")

FREE_DAILY_LIMIT = 3

DEFAULT_ANALYSIS_DETAILS = {
    "credibility": {"score": 50, "description": "Belum dianalisis (data lama sebelum fitur ini aktif)."},
    "language": {"score": 50, "description": "Belum dianalisis (data lama sebelum fitur ini aktif)."},
    "fact_match": {"score": 50, "description": "Belum dianalisis (data lama sebelum fitur ini aktif)."},
    "context": {"score": 50, "description": "Belum dianalisis (data lama sebelum fitur ini aktif)."},
}

def is_subscription_active(user: dict) -> bool:
    """
    Subscription dianggap aktif kalau status 'active' DAN belum lewat expiry.
    Dicek saat request (tanpa cron job), jadi user yang expired otomatis jadi gratis.
    """
    if user.get("subscription_status") != "active":
        return False

    expires_at = user.get("subscription_expires_at")
    if not expires_at:
        return False

    expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    return expiry > datetime.now(timezone.utc)

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
async def check_misinformation(
    payload: CheckRequest,
    current_user: dict = Depends(get_current_user),
):
    raw_content = payload.content.strip()

    if not current_user.get("email_verified"):
        raise HTTPException(
            status_code=403,
            detail="Verifikasi email kamu dulu sebelum melakukan pemeriksaan. Cek inbox atau minta kirim ulang.",
        )

    cached = find_cached_check(raw_content)
    if cached:
        return CheckResponse(
            verdict=cached["verdict"],
            confidence=cached["confidence"],
            explanation=cached["explanation"],
            sources=cached.get("sources") or [],
            analysis_details=cached.get("analysis_details") or DEFAULT_ANALYSIS_DETAILS,
            from_cache=True,
        )

    
    # 0b. Cache miss: cek jatah harian (kecuali subscription aktif)
    if not is_subscription_active(current_user):
        used_today = count_checks_today(current_user["id"])
        if used_today >= FREE_DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Batas harian akun gratis ({FREE_DAILY_LIMIT} pemeriksaan) sudah habis. "
                    "Berlangganan untuk pemeriksaan tanpa batas."
                ),
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

    save_check(
        content=raw_content,
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        sources=result["sources"],
        user_id=current_user["id"],
        counted=True,
        analysis_details=result["analysis"],
    )

    return CheckResponse(
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        sources=result["sources"],
        analysis_details=result["analysis"],
        from_cache=False,
    )


@app.get("/api/checks/history", response_model=CheckHistoryResponse)
async def check_history(
    page: int = 1,
    page_size: int = 10,
    current_user: dict = Depends(get_current_user),
):
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 10

    items, total = get_history(current_user["id"], page=page, page_size=page_size)

    return CheckHistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


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

    verification_token = generate_verification_token()
    expires_at = verification_token_expiry()
    set_verification_token(new_user["id"], verification_token, expires_at)
    send_verification_email(new_user["email"], verification_token)

    return UserProfile(
        id=new_user["id"],
        email=new_user["email"],
        subscription_status=new_user["subscription_status"],
        subscription_expires_at=new_user.get("subscription_expires_at"),
        api_key=new_user.get("api_key"),
        email_verified=new_user.get("email_verified", False),
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
    subscribed = is_subscription_active(current_user)

    return UserProfile(
        id=current_user["id"],
        email=current_user["email"],
        email_verified=current_user.get("email_verified", False),
        subscription_status=current_user["subscription_status"],
        subscription_expires_at=current_user.get("subscription_expires_at"),
        # API key hanya ditampilkan selama subscription masih berlaku
        api_key=current_user.get("api_key") if subscribed else None,
        plan_type=current_user.get("plan_type") if subscribed else None,
        is_subscribed=subscribed,
        checks_used_today=count_checks_today(current_user["id"]),
        daily_limit=None if subscribed else FREE_DAILY_LIMIT,
    )

@app.get("/api/auth/verify", response_model=VerifyEmailResponse)
def verify_email(token: str):
    user = verify_email_token(token)
    if not user:
        raise HTTPException(status_code=400, detail="Token verifikasi tidak valid atau sudah kedaluwarsa")
    return {"message": "Email berhasil diverifikasi"}

@app.post("/api/auth/resend-verification", response_model=ResendVerificationResponse)
def resend_verification(payload: ResendVerificationRequest):
    user = find_user_by_email_for_resend(payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="Email tidak ditemukan")
    if user["email_verified"]:
        raise HTTPException(status_code=400, detail="Akun sudah terverifikasi")

    token = generate_verification_token()
    expires_at = verification_token_expiry()
    set_verification_token(user["id"], token, expires_at)
    send_verification_email(user["email"], token)
    return {"message": "Email verifikasi telah dikirim ulang"}


@app.post("/api/auth/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest):
    """
    Selalu balas pesan yang sama baik email ditemukan atau tidak,
    supaya orang lain tidak bisa pakai endpoint ini buat cek email mana yang terdaftar.
    """
    user = find_user_by_email(payload.email)
    if user:
        token = generate_reset_token()
        expires_at = reset_token_expiry()
        set_reset_token(user["id"], token, expires_at)
        send_reset_password_email(user["email"], token)

    return {"message": "Kalau email terdaftar, kami sudah mengirim link reset password ke email tersebut"}


@app.post("/api/auth/reset-password", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest):
    user = find_user_by_reset_token(payload.token)
    if not user:
        raise HTTPException(status_code=400, detail="Token reset password tidak valid atau sudah kedaluwarsa")

    hashed = hash_password(payload.new_password)
    update_password(user["id"], hashed)

    return {"message": "Password berhasil diubah, silakan masuk dengan password baru"}

# ==========================
# Subscription / payment endpoints
# ==========================

@app.post("/api/subscription/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    current_user: dict = Depends(get_current_user),
):
    plan = PLANS[payload.plan_type]

    checkout = create_subscription_checkout(
        user_id=current_user["id"],
        email=current_user["email"],
        plan_type=payload.plan_type,
    )

    transaction = create_transaction(
        user_id=current_user["id"],
        midtrans_order_id=checkout["order_id"],
        amount=plan["price"],
        plan_type=payload.plan_type,
        duration_days=plan["duration_days"],
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

    # 3. Ambil status lama dulu sebelum di-update, buat cegah aktivasi ganda
    #    (Midtrans bisa kirim notifikasi yang sama lebih dari sekali)
    already_settled = transaction["status"] in ("settlement", "capture")

    # 4. Update status transaksi sesuai notifikasi
    update_transaction_status(order_id, transaction_status)

    # 5. Kalau pembayaran sukses (dan belum pernah diproses), aktifkan subscription user
    if transaction_status in ("settlement", "capture") and not already_settled:
        user_id = transaction["user_id"]
        user = find_user_by_id(user_id)

        # Generate api_key baru cuma kalau user belum punya, biar key lama tetap valid
        # kalau ini perpanjangan subscription, bukan pembelian pertama
        api_key = user.get("api_key") if user and user.get("api_key") else secrets.token_urlsafe(32)

        # Durasi dari transaksi; fallback ke 30 hari untuk transaksi lama yang belum punya kolom ini
        duration_days = transaction.get("duration_days") or 30
        plan_type = transaction.get("plan_type") or "monthly"

        # Perpanjangan: kalau masih aktif, tambah dari sisa masa aktif. Kalau tidak, mulai dari sekarang.
        start_from = datetime.now(timezone.utc)
        if user and is_subscription_active(user):
            current_expiry = datetime.fromisoformat(str(user["subscription_expires_at"]).replace("Z", "+00:00"))
            if current_expiry.tzinfo is None:
                current_expiry = current_expiry.replace(tzinfo=timezone.utc)
            start_from = current_expiry

        expires_at = (start_from + timedelta(days=duration_days)).isoformat()

        activate_subscription(
            user_id=user_id,
            api_key=api_key,
            expires_at=expires_at,
            plan_type=plan_type,
        )

    return {"message": "Notifikasi diterima"}