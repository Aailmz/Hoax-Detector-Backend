import os
import uuid
import hashlib
import midtransclient
from dotenv import load_dotenv

load_dotenv()

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")
MIDTRANS_CLIENT_KEY = os.getenv("MIDTRANS_CLIENT_KEY")

# Tabel paket: sumber tunggal harga (Rupiah) dan durasi (hari).
# Mau ubah harga/durasi, cukup edit di sini.
PLANS = {
    "monthly": {"name": "1 Bulan", "price": 49000, "duration_days": 30},
    "five_months": {"name": "5 Bulan", "price": 239000, "duration_days": 150},
    "yearly": {"name": "1 Tahun", "price": 559000, "duration_days": 365},
}

snap = midtransclient.Snap(
    is_production=False,  # sandbox mode
    server_key=MIDTRANS_SERVER_KEY,
    client_key=MIDTRANS_CLIENT_KEY,
)


def create_subscription_checkout(user_id: str, email: str, plan_type: str):
    """
    Bikin Snap transaction buat paket subscription yang dipilih.
    Return: dict berisi order_id, token, redirect_url
    """
    plan = PLANS[plan_type]
    order_id = f"SUB-{user_id[:8]}-{uuid.uuid4().hex[:8]}"

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": plan["price"],
        },
        "customer_details": {
            "email": email,
        },
        "item_details": [
            {
                "id": f"subscription-{plan_type}",
                "price": plan["price"],
                "quantity": 1,
                "name": f"Misinformation Detector API - {plan['name']}",
            }
        ],
    }

    transaction = snap.create_transaction(param)

    return {
        "order_id": order_id,
        "token": transaction["token"],
        "redirect_url": transaction["redirect_url"],
    }


def verify_notification_signature(order_id: str, status_code: str, gross_amount: str, signature_key: str) -> bool:
    """
    Verifikasi signature dari notifikasi webhook Midtrans, biar tidak bisa dipalsukan.
    Formula resmi Midtrans: SHA512(order_id + status_code + gross_amount + server_key)
    """
    raw_string = f"{order_id}{status_code}{gross_amount}{MIDTRANS_SERVER_KEY}"
    computed_signature = hashlib.sha512(raw_string.encode("utf-8")).hexdigest()
    return computed_signature == signature_key