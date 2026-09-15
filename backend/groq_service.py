import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MODEL_NAME = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """Kamu adalah AI fact-checker untuk aplikasi anti-hoax di Indonesia.
Tugasmu: analisis klaim/berita yang diberikan user.

Kamu akan diberi juga "KONTEKS PENCARIAN" yang berisi hasil pencarian web terbaru
terkait klaim tersebut. WAJIB utamakan informasi dari konteks pencarian itu
dibanding pengetahuan internalmu, karena konteks itu lebih baru dan lebih relevan.

Aturan:
- Kalau konteks pencarian jelas mendukung atau membantah klaim, gunakan itu sebagai dasar verdict.
- Kalau konteks pencarian kosong atau tidak relevan, gunakan pengetahuan internalmu,
  tapi turunkan confidence dan verdict-nya jadi "UNVERIFIED" kalau kamu tidak yakin.
- Jangan mengarang informasi/fakta yang tidak ada di konteks maupun pengetahuanmu.

WAJIB balas HANYA dalam format JSON murni seperti ini, tanpa markdown code block,
tanpa teks tambahan apapun di luar JSON:

{
  "verdict": "HOAX" atau "MISLEADING" atau "VALID" atau "UNVERIFIED",
  "confidence": angka 0-100,
  "explanation": "penjelasan singkat dalam Bahasa Indonesia, 2-4 kalimat, sebutkan alasan berdasarkan konteks pencarian kalau ada"
}
"""

def _parse_json_response(text: str):
    """
    Bersihin output model (kadang masih kebungkus ```json ... ```) lalu parse.
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

def analyze_content(content: str, search_context: str = "", sources: list = None):
    """
    Kirim konten + konteks hasil search (Tavily) ke Groq, dapetin verdict.
    """
    sources = sources or []
    if search_context:
        user_message = (
            f"Klaim/berita yang mau dicek: {content}\n\n"
            f"=== KONTEKS PENCARIAN ===\n{search_context}\n=== AKHIR KONTEKS ==="
        )
    else:
        user_message = (
            f"Klaim/berita yang mau dicek: {content}\n\n"
            f"(Tidak ada konteks pencarian tersedia, gunakan pengetahuan internal "
            f"dan tandai UNVERIFIED kalau tidak yakin.)"
        )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    raw_text = response.choices[0].message.content
    parsed = _parse_json_response(raw_text)
    return {
        "verdict": parsed.get("verdict", "UNVERIFIED"),
        "confidence": parsed.get("confidence", 0),
        "explanation": parsed.get("explanation", ""),
        "sources": sources,
    }