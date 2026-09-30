from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
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
    plan_type: Optional[str] = None
    is_subscribed: bool = False
    checks_used_today: int = 0
    daily_limit: Optional[int] = None

class CheckoutRequest(BaseModel):
    plan_type: Literal["monthly", "five_months", "yearly"]

class CheckoutResponse(BaseModel):
    order_id: str
    snap_token: str
    redirect_url: str

class CheckHistoryItem(BaseModel):
    id: str
    content: str
    verdict: str
    confidence: int
    explanation: str
    sources: List[Source] = []
    created_at: datetime

class CheckHistoryResponse(BaseModel):
    items: List[CheckHistoryItem]
    total: int
    page: int
    page_size: int
    has_more: bool

class VerifyEmailResponse(BaseModel):
    message: str

class ResendVerificationRequest(BaseModel):
    email: str

class ResendVerificationResponse(BaseModel):
    message: str

class UserProfile(BaseModel):
    id: str
    email: str
    subscription_status: str

class UserProfile(BaseModel):
    id: str
    email: str
    email_verified: bool = False
    subscription_status: str