import os
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