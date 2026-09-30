# Fact.AI Backend

An AI-powered backend that checks whether a piece of text or a news URL is likely to be misinformation, using web search grounding and an LLM for analysis. Includes user accounts, email verification, password reset, daily free-tier limits, paid subscriptions via Midtrans, and per-user check history.

## How it works

1. A user registers and verifies their email before they can run any checks.
2. A user submits a claim (plain text) or a news article URL.
3. The system checks a Supabase cache first. If the same input was checked before, the cached result is returned immediately without using up the daily quota.
4. If the input is a URL, the backend fetches and extracts the article's title and body text.
5. The backend searches the web (via Tavily) for related, up-to-date sources on the claim.
6. The claim, plus the search results, are sent to an LLM (Groq) which returns a verdict, a confidence score, and an explanation grounded in the search context.
7. The result is cached in Supabase, saved to the user's history, and returned to the caller.

Free accounts get 3 checks per day; subscribers (via Midtrans) get unlimited checks and an API key.

## Tech stack

- **Backend framework:** FastAPI (Python)
- **Database:** Supabase (Postgres)
- **LLM:** Groq API (`openai/gpt-oss-120b`)
- **Web search grounding:** Tavily API
- **Article extraction:** `requests` + `BeautifulSoup`
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **Payment:** Midtrans Snap
- **Transactional email:** Brevo API (verification, password reset)
- **Hosting:** Railway

## Setup

### 1. Clone and enter the backend folder

```bash
git clone <your-repo-url>
cd backend
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Fill in your own keys for Groq, Tavily, Supabase, JWT secret, Midtrans, and Brevo (see `.env.example` for the full list).

### 4. Set up the database

Create the `users`, `checks`, and `transactions` tables in your Supabase project (see project docs for the full schema), including the email verification and password reset columns on `users`.

### 5. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs (Swagger UI) are available at `http://localhost:8000/docs`.

## Notes and limitations

- The LLM's own knowledge has a training cutoff and is not reliable on its own for recent events. Search grounding via Tavily reduces this, but result quality still depends on what the search turns up.
- If Tavily search fails or hits a rate limit, the system falls back to analysis without grounding rather than failing the request.
- This is a prototype built for a competition. CORS is currently open to all origins and should be narrowed before real production use.
