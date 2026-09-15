from pydantic import BaseModel, Field
from typing import List, Optional

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