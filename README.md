# Personal Weather Assistant

Weather data combined with AI-powered personalized recommendations for clothing,
activities, and health. Built as a take-home task for Graia AI Solution Engineer position.

**Live demo:** _[Vercel URL after deployment]_  
**Backend API:** _[Railway URL after deployment]_

---

## What it does

- Fetches current weather and 5-day forecast for any city via OpenWeatherMap
- Sends weather data to Groq LLM (Llama 3.3 70B) for analysis
- Returns structured recommendations: clothing items, suggested/avoided activities, health tips
- Supports conversational follow-up questions with context from previous recommendation
- Caches weather data per city to minimize external API calls

---

## Stack

**Backend (Python 3.12)**
- FastAPI for async HTTP API
- Pydantic v2 for validated DTOs and structured LLM output
- httpx for async HTTP client
- Groq SDK for LLM inference
- structlog for structured JSON logging
- pytest + httpx ASGI transport for testing

**Frontend (TypeScript)**
- React 18 + Vite
- Tailwind CSS
- Axios for HTTP client

**Deployment**
- Backend: Railway (single container)
- Frontend: Vercel
- No database — request-scoped state only

---

## Architecture

### High-level flow

```
   User
    │
    ▼
┌─────────────┐    POST       ┌──────────────┐
│   React     │  ─────────▶   │  FastAPI     │
│  Frontend   │               │  Backend     │
└─────────────┘  ◀─────────   └──────────────┘
                  weather +          │
                  recommendation     │  parallel
                                     ├────────────┐
                                     ▼            ▼
                              ┌──────────┐  ┌──────────┐
                              │ Weather  │  │   LLM    │
                              │ Provider │  │ Provider │
                              │ (OWM)    │  │ (Groq)   │
                              └──────────┘  └──────────┘
```

### Module structure

```
backend/app/
├── core/                    # Cross-cutting concerns
│   ├── config.py            # Settings (validated at startup)
│   ├── dependencies.py      # DI setup, lifespan clients
│   ├── exceptions.py        # Domain exception hierarchy + handlers
│   └── logging.py           # structlog configuration
│
├── weather/                 # Weather domain
│   ├── protocols.py         # IWeatherProvider Protocol
│   ├── models.py            # WeatherSnapshot, CurrentConditions, ForecastDay
│   ├── openweather_client.py # OpenWeatherMap implementation
│   ├── cache.py             # Async TTL cache with single-flight semantics
│   ├── service.py           # Provider + cache orchestration
│   └── router.py            # GET /api/weather
│
├── recommendations/         # AI recommendation domain
│   ├── protocols.py         # IRecommendationGenerator Protocol
│   ├── models.py            # DailyRecommendation, ClothingAdvice, etc.
│   ├── prompts.py           # System prompt + builders
│   ├── parsing.py           # Robust JSON extraction
│   ├── groq_generator.py    # Groq LLM implementation
│   ├── service.py           # Weather + AI orchestration
│   └── router.py            # POST /api/recommendations, /followup
│
├── health/                  # Health checks
│   └── router.py
│
└── main.py                  # FastAPI app factory + lifespan
```

### Key design decisions

**Protocol-based dependency injection.** Both `IWeatherProvider` and
`IRecommendationGenerator` are Python Protocols, not abstract base classes.
Services depend on the Protocols. This lets us swap OpenWeatherMap for AccuWeather,
or Groq for OpenAI, without touching consumer code. Tests use `FakeWeatherProvider`
and `FakeRecommendationGenerator` — duck-typed implementations that satisfy the
Protocols without inheriting from anything. Tests run offline, no API keys needed.

**Long-lived async clients.** httpx and Groq clients are expensive to create
(connection pools, TLS handshakes). They're initialized once in the FastAPI
lifespan and reused across requests. Per-request services wrap these clients
but don't own them. Avoids socket exhaustion under load.

**Concurrency limiting via semaphores.** Two semaphores at the application
level cap concurrent calls to external providers (Groq, OpenWeatherMap). Without
this, a burst of incoming requests could trigger provider rate limits and cause
cascading failures. Default limits are 10 concurrent LLM calls and 20 concurrent
weather calls — tuned for free tier quotas.

**Single-flight cache.** `WeatherCache.get_or_set` uses per-key `asyncio.Lock`
to prevent thundering-herd on cache misses. If 5 requests for "Zagreb" arrive
simultaneously while the cache is empty, only one actually calls OpenWeatherMap;
the other 4 wait for the first to populate the cache.

**Structured JSON output from LLM.** Groq is called in JSON mode, response is
parsed with `json.JSONDecoder.raw_decode` (handles markdown fences, preamble,
postamble), then validated against Pydantic schema. Failure at any step raises
`LLMParseError` (502 to client). Users never get malformed data.

**Robust JSON parsing.** LLMs sometimes wrap JSON in markdown fences, prefix
with prose, or append explanations. Using `JSONDecoder.raw_decode` walks
character by character to find the first valid JSON object — more robust than
greedy regex matching, which fails on nested braces or strings containing braces.

**Typed exception hierarchy.** Domain errors (`CityNotFoundError`,
`LLMRateLimitError`, etc.) inherit from `AppError`, each with `status_code` and
`default_message`. A single global handler translates them to HTTP responses
and logs them with structured context. Routers stay clean — they raise meaningful
exceptions, framework handles HTTP semantics.

**Strict Pydantic DTOs.** Request models use `extra="forbid"` — unknown fields
are rejected. This catches typos in client requests early instead of silently
ignoring them. Response models use `frozen=True` for immutability.

**Async-first throughout.** Every I/O operation is awaitable. Weather and LLM
calls run concurrently when both are needed (via `asyncio.gather`). No sync
blocking calls inside async handlers — a common bug that silently destroys
event loop throughput.

---

## Setup (local development)

### Prerequisites

- Python 3.12+
- Node.js 20+
- API keys (free tier):
  - OpenWeatherMap: <https://openweathermap.org/api>
  - Groq: <https://console.groq.com>

### Backend

```bash
cd backend

# Create virtualenv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (production + dev tools)
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your OPENWEATHER_API_KEY and GROQ_API_KEY

# Run dev server with auto-reload
uvicorn app.main:app --reload --port 8000
```

API docs available at <http://localhost:8000/docs>.

### Frontend

```bash
cd frontend

npm install
cp .env.example .env  # set VITE_API_URL=http://localhost:8000
npm run dev
```

App available at <http://localhost:5173>.

### Running tests

```bash
cd backend
pytest                    # runs all tests with coverage report
pytest tests/test_cache.py  # specific test file
pytest -k "test_cache"    # tests matching pattern

# Or via the Makefile
make test                 # pytest with coverage (offline)
make lint                 # ruff check + format verification
make format               # auto-format and auto-fix
make typecheck            # mypy
make eval                 # live LLM output-quality eval (needs a real Groq key)
```

### LLM output-quality eval

`tests/eval/` defines golden weather scenarios (cold-and-rainy, hot-and-sunny,
mild-and-cloudy) and a keyword-based evaluator that scores whether a
recommendation surfaces the advice each scenario demands (rain → umbrella /
waterproof, heat → hydration / sunscreen, etc.). It runs in two layers:

- **Offline (in CI):** evaluator sanity checks plus prompt-regression tests that
  assert the prompt still carries each scenario's weather signals — deterministic,
  no API key.
- **Live (opt-in):** `pytest -m llm_eval` (or `make eval`) calls the real Groq
  model for each scenario and asserts the output passes the evaluator. Skipped
  automatically unless a real `GROQ_API_KEY` (`gsk_…`) is set, so it's suited to
  a nightly job rather than per-commit CI.

Frontend tests and build:

```bash
cd frontend
npm run lint
npm run test    # vitest
npm run build   # type-check + production build
```

### Continuous integration

`.github/workflows/ci.yml` runs on every push and PR to `main`:

- **Backend:** `ruff check` + `ruff format --check`, strict `mypy`, and `pytest`
  (95% coverage, including every external-provider error path via `respx` and a
  fake Groq client — no network or API keys needed).
- **Frontend:** `npm audit --audit-level=high`, ESLint, Vitest, and a production
  build (type-check included).
- **Docker:** the backend image is built to catch Dockerfile regressions.

A `.pre-commit-config.yaml` runs ruff locally before each commit
(`make precommit-install`).

### Reproducible dependencies

Both sides are lock-pinned so CI, Docker, and Vercel resolve identical trees:

- Backend: `requirements.txt` / `requirements-dev.txt`, compiled from
  `pyproject.toml` with `uv pip compile`. The Docker image installs from the
  pinned `requirements.txt`. Regenerate with
  `uv pip compile pyproject.toml -o requirements.txt` (and `--extra dev` for the
  dev lock).
- Frontend: `package-lock.json`, installed with `npm ci`.

### Operability

- **Liveness** at `GET /health`, **readiness** at `GET /health/ready` (reports
  whether the long-lived clients are initialized, without spending upstream API
  quota).
- Every request gets a correlation ID (generated or taken from an inbound
  `X-Request-ID`), bound to the structured logs and echoed in the response
  header, so a single request's weather + LLM calls can be traced together.
- **Per-IP rate limiting** on the two LLM endpoints (`20/minute` by default,
  configurable via `RATE_LIMIT`). The limiter reads the real client IP from
  `X-Forwarded-For` (correct behind Railway's proxy) and is in-memory — fine for
  a single instance; point slowapi at Redis for multiple instances.

---

## Deployment

This is a monorepo (`backend/` + `frontend/`). Each side deploys independently.

### Backend → Railway

1. **New Project → Deploy from GitHub repo**, then in the service settings set
   **Root Directory = `backend`**. This makes the Docker build context `backend/`,
   which is what the Dockerfile's relative `COPY` instructions (and
   `backend/railway.toml`) expect.
2. Railway auto-detects the Dockerfile and `railway.toml` (healthcheck `/health`,
   start command, restart policy). `PORT` is injected automatically.
3. Set environment variables:
   - `OPENWEATHER_API_KEY`, `GROQ_API_KEY` (required)
   - `ENVIRONMENT=production`
   - `ALLOWED_ORIGINS=https://<your-app>.vercel.app` (your Vercel URL — without
     this the browser will block the frontend's requests via CORS)
   - optionally `RATE_LIMIT`, `GROQ_MODEL`, etc.

### Frontend → Vercel

1. **Import the repo**, set **Root Directory = `frontend`**. Vercel detects Vite
   from `vercel.json` (build command, output dir, SPA rewrites).
2. Set the Node version to **22** (vite 8 requires Node ≥20.19; `engines` is
   pinned in `package.json`).
3. Set the build-time env var `VITE_API_URL=https://<your-app>.up.railway.app`
   (your Railway backend URL). Redeploy after the backend is up.

### Order

Deploy the backend first, copy its URL into the frontend's `VITE_API_URL`, then
deploy the frontend and copy its URL into the backend's `ALLOWED_ORIGINS`.

---

## API examples

### Get weather only

```bash
curl 'http://localhost:8000/api/weather?city=Zagreb'
```

### Get recommendation (weather + AI analysis)

```bash
# Today (target_date defaults to today)
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"city": "Zagreb"}'

# A specific date within the 5-day forecast window
curl -X POST http://localhost:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"city": "Zagreb", "target_date": "2026-06-15"}'
```

When `target_date` is a future day inside the forecast window, the AI bases its
advice on that day's forecast (today's live conditions are passed as reference
only). Dates in the past or beyond today + 5 days are rejected with `400`.

Response shape:

```json
{
  "target_date": "2026-06-09",
  "weather": {
    "city": "Zagreb",
    "country_code": "HR",
    "current": { "temperature_c": 18.5, "...": "..." },
    "forecast": [ {"date": "2026-06-09", "...": "..."} ]
  },
  "recommendation": {
    "summary": "Mild June day with scattered clouds...",
    "clothing": {
      "items": ["light jacket", "long-sleeve shirt", "jeans", "sneakers"],
      "reasoning": "Temperatures around 18°C feel pleasant..."
    },
    "activities": {
      "suggested": ["walk in Maksimir", "outdoor coffee"],
      "avoid": ["beach trip"],
      "reasoning": "Cloudy with mild temperatures..."
    },
    "health_tips": [
      {"tip": "UV is moderate even with clouds...", "priority": "medium"}
    ],
    "weekly_advice": "Tomorrow will be sunnier and warmer..."
  }
}
```

### Ask follow-up question

```bash
curl -X POST http://localhost:8000/api/recommendations/followup \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Zagreb",
    "target_date": "2026-06-09",
    "previous_recommendation": { ... from previous response ... },
    "user_question": "What about cycling along the Sava river?"
  }'
```

---

## Trade-offs and scope decisions

### What I built

- Full async backend with Protocol-based DI
- 5-day forecast aggregation from 3-hour OpenWeatherMap intervals
- Structured LLM output with strict Pydantic validation
- Single-flight cache to prevent thundering-herd
- Conversational follow-up endpoint (beyond the basic task — relevant to Graia's agentic AI domain)
- Multi-day "weekly advice" in recommendations (beyond the basic task)
- Comprehensive test suite using Fake Protocol implementations
- Production-grade logging, error handling, configuration

### What I deliberately cut

- **No persistence layer.** Request-scoped state — no recommendation history,
  no user accounts. Adding Postgres for a demo would be 30+ minutes of work
  with zero value to the evaluation. Would add Postgres in production for
  history, preferences, multi-tenant isolation.
- **No authentication.** Internal demo, not user-facing. Auth0 or similar
  would be the production pattern.
- **No real-time streaming.** SSE complexity for a request that completes in
  ~1-3 seconds wasn't worth it. For longer-running multi-agent workflows, SSE
  or WebSocket streaming would matter.
- **In-memory cache, not Redis.** Single-process cache works for demo scale.
  Production would use Redis for multi-instance deployments.

### What I'd add with more time

- **Richer eval metrics.** A lightweight eval harness ships today (golden
  scenarios + keyword evaluator + prompt-regression in CI, live model eval
  opt-in — see above). The next step is RAGAS-style faithfulness/relevance
  scoring and tracking the aggregate score over time.
- **Cost tracking** per request and per workflow — token spend monitoring is
  essential in production
- **OpenTelemetry tracing** for LLM-specific spans (prompt, response, tokens,
  cost) — building on the correlation IDs already emitted per request
- **Redis-backed rate limiting** so the per-IP limits hold across multiple
  instances (the in-memory limiter is per-process today)
- **Multi-language support** — recommendations in user's language

### Honest time spent

~14 hours over 4 days. Above the suggested 3-5 day budget but I went deliberately
deep on architecture (Protocol-based DI, lifespan management, single-flight caching)
because production-grade code is what I'd ship at Graia, not minimum-viable.

---

## Author

Alan Vogel  
[github.com/AlanVogel](https://github.com/AlanVogel)
