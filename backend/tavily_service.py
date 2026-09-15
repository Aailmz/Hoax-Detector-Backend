import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(api_key=TAVILY_API_KEY)

def search_related_sources(query: str, max_results: int = 5):
    """
    Cari sumber-sumber terkait klaim/berita menggunakan Tavily.
    Return: (context_text, sources_list)
      - context_text: gabungan snippet/isi dari hasil search, buat dikirim ke AI
      - sources_list: daftar {title, url} buat ditampilkan ke user
    """
    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
        )
    except Exception as e:
        return "", []

    results = response.get("results", [])
    tavily_answer = response.get("answer", "")

    context_parts = []
    sources = []

    if tavily_answer:
        context_parts.append(f"Ringkasan awal dari pencarian: {tavily_answer}")

    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("content", "")
        if snippet:
            context_parts.append(f"Sumber: {title}\nURL: {url}\nIsi: {snippet}")
        if url:
            sources.append({"title": title, "url": url})

    context_text = "\n\n".join(context_parts)
    return context_text, sources