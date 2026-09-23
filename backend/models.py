from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

class CheckRequest(BaseModel):
    content: str = Field(..., min_length=3, description="Teks/klaim/berita yang mau dicek")

class Source(BaseModel):
    title: str
    url: str

class CheckResponse(BaseModel):
    verdict: str
    confidence: int
    explanation: str
    sources: List[Source] = []
    from_cache: bool = False

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72, description="8-72 karakter")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserProfile(BaseModel):
    id: str
    email: str
    subscription_status: str
    subscription_expires_at: Optional[datetime] = None
    api_key: Optional[str] = None

class CheckoutResponse(BaseModel):
    order_id: str
    snap_token: str
    redirect_url: str