import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

EMAIL_FROM = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")


def send_verification_email(to_email: str, token: str) -> bool:
    verify_link = f"{FRONTEND_URL}/verify.html?token={token}"
    try:
        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": to_email,
            "subject": "Verifikasi akun Fact.AI kamu",
            "html": f"""
                <p>Terima kasih sudah mendaftar di Fact.AI.</p>
                <p>Klik link berikut untuk verifikasi akun kamu (berlaku 24 jam):</p>
                <p><a href="{verify_link}">{verify_link}</a></p>
            """,
        })
        return True
    except Exception as e:
        print(f"[email_service] Gagal kirim email verifikasi: {e}")
        return False