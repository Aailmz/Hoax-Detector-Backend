from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime


class CheckRequest(BaseModel):
    content: str = Field(..., min_length=3, description="Teks/klaim/berita yang mau dicek")

class Source(BaseModel):
    title: str
    url: str

class AnalysisAspect(BaseModel):
    score: int
    description: str

class AnalysisDetails(BaseModel):
    credibility: AnalysisAspect
    language: AnalysisAspect
    fact_match: AnalysisAspect
    context: AnalysisAspect

class CheckResponse(BaseModel):
    verdict: str
    confidence: int
    explanation: str
    sources: List[Source] = []
    analysis_details: AnalysisDetails
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
    analysis_details: Optional[AnalysisDetails] = None
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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=72, description="8-72 karakter")

class ResetPasswordResponse(BaseModel):
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