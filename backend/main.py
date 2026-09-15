from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import CheckRequest, CheckResponse
from supabase_client import find_cached_check, save_check, get_history
from groq_service import analyze_content
from url_fetcher import is_url, fetch_article_text
from tavily_service import search_related_sources

app = FastAPI(title="Misinformation Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Misinformation Detector API is running"}

@app.post("/api/check", response_model=CheckResponse)
async def check_misinformation(payload: CheckRequest):
    raw_content = payload.content.strip()

    cached = find_cached_check(raw_content)
    if cached:
        return CheckResponse(
            verdict=cached["verdict"],
            confidence=cached["confidence"],
            explanation=cached["explanation"],
            sources=cached.get("sources") or [],
            from_cache=True,
        )

    if is_url(raw_content):
        try:
            content_to_analyze = fetch_article_text(raw_content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        content_to_analyze = raw_content

    search_query = raw_content if not is_url(raw_content) else content_to_analyze[:200]
    search_context, sources = search_related_sources(search_query)
    try:
        result = analyze_content(content_to_analyze, search_context=search_context, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menganalisis konten: {str(e)}")
    save_check(
        content=raw_content,
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        sources=result["sources"],
    )

    return CheckResponse(
        verdict=result["verdict"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        sources=result["sources"],
        from_cache=False,
    )

@app.get("/api/checks/history")
async def check_history(limit: int = 20):
    return get_history(limit=limit)