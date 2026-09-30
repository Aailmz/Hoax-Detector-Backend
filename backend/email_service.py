import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")


def send_verification_email(to_email: str, token: str) -> bool:
    verify_link = f"{FRONTEND_URL}/verify.html?token={token}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verifikasi akun Fact.AI kamu"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email

    html = f"""
        <p>Terima kasih sudah mendaftar di Fact.AI.</p>
        <p>Klik link berikut untuk verifikasi akun kamu (berlaku 24 jam):</p>
        <p><a href="{verify_link}">{verify_link}</a></p>
    """
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[email_service] Gagal kirim email verifikasi: {e}")
        return False