import os
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = BREVO_API_KEY


def send_verification_email(to_email: str, token: str) -> bool:
    """
    Kirim email verifikasi akun lewat Brevo API. Return True kalau berhasil,
    False kalau gagal (tidak melempar exception supaya register tidak ikut gagal).
    """
    verify_link = f"{FRONTEND_URL}/verify.html?token={token}"

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    email_payload = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": EMAIL_FROM, "name": "Fact.AI"},
        subject="Verifikasi akun Fact.AI kamu",
        html_content=f"""
            <p>Terima kasih sudah mendaftar di Fact.AI.</p>
            <p>Klik link berikut untuk verifikasi akun kamu (berlaku 24 jam):</p>
            <p><a href="{verify_link}">{verify_link}</a></p>
        """,
    )

    try:
        api_instance.send_transac_email(email_payload)
        return True
    except ApiException as e:
        print(f"[email_service] Gagal kirim email verifikasi: {e}")
        return False

def send_reset_password_email(to_email: str, token: str) -> bool:
    reset_link = f"{FRONTEND_URL}/reset-password.html?token={token}"

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    email_payload = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": EMAIL_FROM, "name": "Fact.AI"},
        subject="Reset password akun Fact.AI kamu",
        html_content=f"""
            <p>Kami menerima permintaan reset password untuk akun kamu.</p>
            <p>Klik link berikut untuk membuat password baru (berlaku 1 jam):</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
            <p>Kalau kamu tidak meminta ini, abaikan saja email ini.</p>
        """,
    )

    try:
        api_instance.send_transac_email(email_payload)
        return True
    except ApiException as e:
        print(f"[email_service] Gagal kirim email reset password: {e}")
        return False

PLAN_LABELS = {
    "monthly": "1 Bulan",
    "five_months": "5 Bulan",
    "yearly": "1 Tahun",
}


def send_subscription_active_email(to_email: str, plan_type: str, expires_at: str) -> bool:
    """
    Kirim email konfirmasi setelah subscription aktif/diperpanjang.
    Return True kalau berhasil, False kalau gagal (tidak melempar exception).
    """
    plan_label = PLAN_LABELS.get(plan_type, plan_type)

    try:
        expiry_display = datetime.fromisoformat(expires_at).strftime("%d %B %Y")
    except Exception:
        expiry_display = expires_at

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    email_payload = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"email": EMAIL_FROM, "name": "Fact.AI"},
        subject="Langganan Fact.AI kamu sudah aktif",
        html_content=f"""
            <p>Terima kasih! Langganan Fact.AI paket <strong>{plan_label}</strong> kamu sudah aktif.</p>
            <p>Langganan kamu berlaku hingga <strong>{expiry_display}</strong>.</p>
            <p>Kamu sekarang bisa melakukan pemeriksaan tanpa batas dan memakai API key di halaman akun.</p>
        """,
    )

    try:
        api_instance.send_transac_email(email_payload)
        return True
    except ApiException as e:
        print(f"[email_service] Gagal kirim email subscription aktif: {e}")
        return False