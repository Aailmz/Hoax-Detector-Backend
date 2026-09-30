from fastapi import Header, HTTPException

from auth_service import decode_access_token
from supabase_client import find_user_by_id, find_user_by_api_key

async def get_current_user(authorization: str = Header(None)):
    """
    Dependency buat endpoint yang butuh login.
    Ambil token dari header 'Authorization: Bearer <token>', validasi, lalu
    return data user yang sedang login. Raise 401 kalau token tidak ada/invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token tidak ditemukan, silakan login")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token tidak valid atau sudah kedaluwarsa")

    user_id = payload.get("sub")
    user = find_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")

    return 

async def get_current_user_by_api_key(x_api_key: str = Header(None)):
    """
    Dependency buat endpoint publik /api/v1/*.
    Ambil user dari header 'X-API-Key', wajib subscription aktif.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Header X-API-Key tidak ditemukan")

    user = find_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="API key tidak valid")

    return user