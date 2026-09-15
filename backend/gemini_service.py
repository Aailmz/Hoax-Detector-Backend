import os
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.6-flash"

SYSTEM_PROMPT = """Kamu adalah AI fact-checker untuk aplikasi anti-hoax di Indonesia.
Tugasmu: analisis klaim/berita yang diberikan user, gunakan Google Search untuk
mencari dan membandingkan sumber-sumber berita terpercaya (media nasional,
fact-checker resmi seperti Mafindo/Cek Fakta, lembaga resmi pemerintah, dsb).

Setelah menganalisis, WAJIB balas HANYA dalam format JSON murni seperti ini,
tanpa markdown code block, tanpa teks tambahan:

{
  "verdict": "HOAX" atau "MISLEADING" atau "VALID" atau "UNVERIFIED",
  "confidence": angka 0-100,
  "explanation": "penjelasan singkat dalam Bahasa Indonesia, 2-4 kalimat"
}

Gunakan "UNVERIFIED" kalau tidak cukup informasi kredibel yang ditemukan.
Jangan mengarang informasi. Jangan menambahkan teks di luar JSON.
"""

def _extract_sources(response):
    """
    Ambil daftar URL sumber dari grounding metadata Gemini, kalau ada.
    """
    sources = []
    try:
        candidates = response.candidates or []
        for candidate in candidates:
            grounding = getattr(candidate, "grounding_metadata", None)
            if not grounding:
                continue
            chunks = getattr(grounding, "grounding_chunks", None) or []
            for chunk in chunks:
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    sources.append({
                        "title": getattr(web, "title", "") or "",
                        "url": web.uri,
                    })
    except Exception:
        pass
    return sources

def _parse_json_response(text: str):
    """
    Bersihin output Gemini (kadang masih kebungkus ```json ... ```) lalu parse.
    """
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "explanation": "Gagal memproses hasil analisis AI. Coba lagi.",
        }

def analyze_content(content: str):
    """
    Kirim konten ke Gemini dengan Google Search grounding, dapetin verdict.
    """
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
    config = types.GenerateContentConfig(
        tools=[grounding_tool],
        system_instruction=SYSTEM_PROMPT,
    )
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"Analisis klaim/berita berikut: {content}",
        config=config,
    )
    parsed = _parse_json_response(response.text)
    sources = _extract_sources(response)
    return {
        "verdict": parsed.get("verdict", "UNVERIFIED"),
        "confidence": parsed.get("confidence", 0),
        "explanation": parsed.get("explanation", ""),
        "sources": sources,
    }