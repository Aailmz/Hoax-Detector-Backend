# Misinformation Detector

An AI-powered backend that checks whether a piece of text or a news URL is likely to be misinformation, using web search grounding and an LLM for analysis.

## How it works

1. A user submits a claim (plain text) or a news article URL.
2. The system checks a Supabase cache first. If the same input was checked before, the cached result is returned immediately.
3. If the input is a URL, the backend fetches and extracts the article's title and body text.
4. The backend searches the web (via Tavily) for related, up-to-date sources on the claim.
5. The claim, plus the search results, are sent to an LLM (Groq) which returns a verdict, a confidence score, and an explanation grounded in the search context.
6. The result is cached in Supabase and returned to the caller.

This design keeps repeated or previously-checked claims fast and cheap (served from cache), and only calls the search + AI pipeline when a claim hasn't been seen before.

## Tech stack

- **Backend framework:** FastAPI (Python)
- **Database / cache:** Supabase (Postgres)
- **LLM:** Groq API (`openai/gpt-oss-120b`)
- **Web search grounding:** Tavily API
- **Article extraction:** `requests` + `BeautifulSoup`

## Project structure

```
backend/
├── main.py              # FastAPI app and routes
├── models.py             # Pydantic request/response schemas
├── groq_service.py       # LLM analysis logic (Groq)
├── tavily_service.py     # Web search grounding logic (Tavily)
├── url_fetcher.py        # URL detection + article text extraction
├── supabase_client.py    # Supabase cache read/write
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

### 1. Clone and enter the backend folder

```bash
git clone <your-repo-url>
cd backend
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy the example file and fill in your own keys:

```bash
cp .env.example .env
```

Required values in `.env`:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | API key from [console.groq.com](https://console.groq.com) |
| `TAVILY_API_KEY` | API key from [app.tavily.com](https://app.tavily.com) |
| `SUPABASE_URL` | Your Supabase project URL (base URL only, no `/rest/v1/`) |
| `SUPABASE_KEY` | Your Supabase `anon` `public` API key |

### 5. Create the database table

In your Supabase project's SQL Editor, run:

```sql
create table checks (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  verdict text not null,
  confidence int not null,
  explanation text,
  sources jsonb,
  created_at timestamp with time zone default now()
);
```

### 6. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs (Swagger UI) are available at `http://localhost:8000/docs`.

## Notes and limitations

- The LLM's own knowledge has a training cutoff and is not reliable on its own for recent events. Search grounding via Tavily is used to reduce this, but result quality still depends on what the search turns up.
- If Tavily search fails or hits a rate limit, the system falls back to analysis without grounding rather than failing the request.
- This is a prototype. Source-credibility scoring and a curated local fact-check database (as outlined in the original project plan) are not yet implemented.

## License

Add your license here.
