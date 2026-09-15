import re
import requests
from bs4 import BeautifulSoup

URL_PATTERN = re.compile(r"^https?://\S+$")

def is_url(text: str) -> bool:
    """
    Cek apakah teks yang dikirim user itu URL tunggal.
    """
    return bool(URL_PATTERN.match(text.strip()))

def fetch_article_text(url: str, max_chars: int = 5000) -> str:
    """
    Ambil isi artikel dari URL berita.
    Ambil <title> + paragraf <p> utama, buang script/style/nav/footer.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Gagal mengakses URL: {str(e)}")
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
        tag.decompose()
        
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    paragraphs = soup.find_all("p")
    body_text = " ".join(p.get_text(strip=True) for p in paragraphs)
    full_text = f"{title}. {body_text}".strip()
    if not body_text or len(body_text) < 50:
        raise ValueError(
            "Tidak bisa mengambil isi artikel dari URL ini "
            "(mungkin butuh login, JavaScript-heavy, atau diblokir situs)."
        )

    return full_text[:max_chars]

def resolve_content(content: str) -> str:
    """
    Kalau content berupa URL, fetch isinya dulu.
    Kalau bukan URL, kembalikan teks aslinya.
    """
    content = content.strip()
    if is_url(content):
        return fetch_article_text(content)
    return content