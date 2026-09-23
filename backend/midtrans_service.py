import os
import uuid
import hashlib
import midtransclient
from dotenv import load_dotenv

load_dotenv()

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")
MIDTRANS_CLIENT_KEY = os.getenv("MIDTRANS_CLIENT_KEY")

# Harga subscription bulanan (dalam Rupiah), sesuaikan sesuai kebutuhan
SUBSCRIPTION_PRICE = 49000

snap = midtransclient.Snap(
    is_production=False,  # sandbox mode
    server_key=MIDTRANS_SERVER_KEY,
    client_key=MIDTRANS_CLIENT_KEY,
)

def create_subscription_checkout(user_id: str, email: str):
    """
    Bikin Snap transaction buat subscription bulanan.
    Return: (order_id, snap_token, redirect_url)
    """
    order_id = f"SUB-{user_id[:8]}-{uuid.uuid4().hex[:8]}"

    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": SUBSCRIPTION_PRICE,
        },
        "customer_details": {
            "email": email,
        },
        "item_details": [
            {
                "id": "subscription-monthly",
                "price": SUBSCRIPTION_PRICE,
                "quantity": 1,
                "name": "Misinformation Detector API - Monthly Subscription",
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