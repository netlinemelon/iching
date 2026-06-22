# Development Setup 开发指南

> Guide for setting up a local development environment for the I Ching Divination server.

---

## Quick Start 快速开始

### Prerequisites

- Python 3.10+
- Git
- (Optional) Redis — for cache and multi-worker testing

### Setup

```bash
# Clone the repository (server branch)
git clone https://github.com/netlinemelon/iching.git -b server
cd iching

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: add your AI API key, set DEBUG=true
```

### Run

```bash
python run.py
```

The app starts at `http://localhost:8088` by default.

### Verify

```bash
# Health check
curl http://localhost:8088/api/health
# → {"status":"ok","app":"八卦 - I Ching Divination"}

# Coin divination
curl -X POST http://localhost:8088/api/divine/coin
# → Full JSON divination result

# List hexagrams
curl http://localhost:8088/api/hexagrams
# → All 64 hexagrams
```

---

## Debug Mode 调试模式

Set `DEBUG=true` in your `.env` file to enable:

| Feature | Behavior |
|---------|----------|
| **Auto-reload** | Uvicorn hot-reloads on file changes (no manual restart) |
| **SQL echo** | All SQLAlchemy queries printed to terminal |
| **Debug logging** | Full `[Dxxx]` numbered debug messages |
| **Cookie secure flag** | Disabled (`secure=False`) for local HTTP dev |

**Note**: Set `DEBUG=false` in production. Debug mode exposes SQL queries and disables cookie security.

---

## Project Structure 项目结构

```
iching/
│
├── app/                              # Python application package
│   ├── __init__.py
│   │
│   ├── main.py                       # FastAPI app creation, middleware, lifespan
│   ├── config.py                     # Pydantic Settings (all .env vars)
│   ├── database.py                   # SQLAlchemy async engine + session
│   ├── cache.py                      # Redis cache wrapper (optional, graceful degradation)
│   ├── debug.py                      # [Dxxx] numbered logging system
│   ├── limits.py                     # IP rate limiter + circuit breaker (in-memory)
│   ├── ai_interpreter.py             # LLM integration (DeepSeek/Anthropic)
│   │
│   ├── engine/                       # PURE — divination algorithms, no side effects
│   │   ├── core.py                   #     LineType, TrigramBagua, Line, Hexagram types
│   │   ├── coin.py                   #     Three-coin method
│   │   ├── yarrow.py                 #     Yarrow stalk method (大衍筮法)
│   │   ├── time.py                   #     Time-based divination
│   │   ├── number.py                 #     Number-based divination
│   │   ├── plum_blossom.py           #     Plum blossom (梅花易数)
│   │   ├── transform.py              #     Changed/mutual/opposite/reverse hexagrams
│   │   ├── interpretation.py         #     Zhu Xi rules for 0-6 changing lines
│   │   └── result_builder.py         #     Assembles full divination result dict
│   │
│   ├── models/                       # ORM models + Pydantic schemas
│   │   ├── divination_record.py      #     SQLAlchemy: DivinationRecord, SyncCode
│   │   ├── hexagram_data.py          #     64 hexagrams JSON loader + search
│   │   └── schemas.py                #     Pydantic request/response models
│   │
│   ├── routes/                       # FastAPI route handlers
│   │   ├── home.py                   #     GET / — landing page
│   │   ├── divine.py                 #     HTML form-based divination
│   │   ├── hexagram.py               #     Hexagram study pages
│   │   ├── study.py                  #     Learning resources
│   │   ├── history.py                #     History pages + share + delete
│   │   └── api.py                    #     REST JSON API (all /api/* endpoints)
│   │
│   ├── templates/                    # Jinja2 HTML templates
│   │   ├── base.html                 #     Base layout + navigation
│   │   ├── components/               #     Reusable components (donate, etc.)
│   │   ├── result/                   #     Divination result pages
│   │   └── history/                  #     History listing + detail pages
│   │
│   └── static/                       # Static assets (CSS, JS, images)
│       ├── css/                      #     Stylesheets (main.css, donate.css, etc.)
│       ├── js/                       #     JavaScript (storage.js, sync.js, etc.)
│       └── img/                      #     Images (QR codes, favicon)
│
├── data/                             # Runtime data
│   ├── hexagrams.json                #     64 hexagrams reference data (read-only)
│   ├── trigrams.json                 #     8 trigrams reference data (read-only)
│   └── iching.db                     #     SQLite database (auto-created)
│
├── deploy/                           # Production deployment configs
│   ├── iching.service                #     systemd unit file
│   ├── iching-nginx.conf             #     nginx site config
│   └── setup.sh                      #     One-click deployment script
│
├── docs/                             # Documentation
│   ├── ARCHITECTURE.md               #     System architecture
│   ├── API.md                        #     API reference
│   ├── SECURITY.md                   #     Security design
│   ├── DEVELOPMENT.md                #     This file
│   └── screenshots/                  #     Screenshots for README
│
├── run.py                            # Uvicorn launcher (python run.py)
├── start.bat                         # Windows double-click startup
├── start.sh                          # Linux/Mac startup script
├── .env.example                      # Configuration template
├── requirements.txt                  # Python dependencies
└── README.md                         # Project overview (English + Chinese)
```

---

## Key Files 关键文件说明

### app/main.py — Application Entry Point

The FastAPI application is constructed here. Key responsibilities:

```python
# Middleware registration (order matters!)
app.middleware("http")(client_id_middleware)   # Runs first
app.middleware("http")(circuit_breaker_middleware)  # Runs second
app.mount("/static", StaticFiles(...))          # Static file serving
app.include_router(api.router, prefix="/api")   # All API routes
```

The `lifespan` context manager handles:
1. Database table creation and migration
2. Expired sync code cleanup
3. Redis connection initialization (graceful degradation)

### app/limits.py — Rate Limiting

In-memory rate limiter with three layers:
1. **Periodic cleanup**: 60-second sliding window per IP
2. **Burst detection**: >10 requests in 1 second → 300s ban
3. **Per-minute cap**: 120 requests per minute per IP

The AI limiter (`can_use_ai` / `record_ai_use`) is a separate global daily counter.

### app/engine/core.py — Core Types

The type system at the heart of all divination:

```
LineType enum: OLD_YIN=6, YOUNG_YANG=7, YOUNG_YIN=8, OLD_YANG=9
TrigramBagua enum: 8 trigrams with binary, name, element, unicode
Line dataclass: position + line_type + text + xiang
Hexagram dataclass: 6 Line objects → binary, changed_binary, transforms
```

All engine modules import from `core.py` and produce/consume `Hexagram` objects.

### app/routes/api.py — JSON API

The largest route file (~714 lines). Contains:
- 5 divination endpoints (coin, yarrow, time, number, plum-blossom)
- Hexagram list/detail/search endpoints
- History CRUD endpoints
- AI interpretation endpoint
- Sync create/download endpoints
- Health check

### app/models/divination_record.py — ORM

Two SQLAlchemy models:
- `DivinationRecord`: Full divination result persistence
- `SyncCode`: Cross-device sync storage (SQLite-backed)

---

## Testing 测试指南

### Manual Testing with curl

```bash
# Health check (no cookie needed)
curl http://localhost:8088/api/health

# Coin divination (gets auto-assigned client_id)
curl -v -X POST http://localhost:8088/api/divine/coin

# With seed for reproducible results
curl -X POST "http://localhost:8088/api/divine/coin?seed=42"

# With custom values (simulate client-side toss)
curl -X POST "http://localhost:8088/api/divine/coin?values=7,8,6,9,7,8"

# Get all hexagrams
curl http://localhost:8088/api/hexagrams

# Search hexagrams
curl "http://localhost:8088/api/hexagrams/search?q=乾"

# Get a specific hexagram
curl http://localhost:8088/api/hexagrams/1

# View AI usage
curl http://localhost:8088/api/limits/ai
```

### Testing with Cookie (History + Sync)

```bash
# Get a cookie first
COOKIE=$(curl -v -X POST http://localhost:8088/api/divine/coin 2>&1 \
  | grep -i 'set-cookie' | cut -d: -f2- | cut -d';' -f1 | tr -d ' \r\n')

# List history
curl -H "Cookie: $COOKIE" http://localhost:8088/api/history

# Export history
curl -H "Cookie: $COOKIE" http://localhost:8088/api/history/export
```

### Testing Rate Limiting

```bash
# Fast requests trigger 429
for i in $(seq 1 150); do
  curl -s -o /dev/null -w "%{http_code} " http://localhost:8088/api/health
  if [[ $(expr $i % 20) -eq 0 ]]; then echo; fi
done

# Check response headers
curl -v http://localhost:8088/api/divine/coin 2>&1 | grep -i x-ratelimit
```

---

## Common Tasks 常见任务

### Add a New Environment Variable

1. Add the field to `app/config.py` (Pydantic `Settings` class)
2. Add the variable to `.env.example` with a comment
3. Add it to the Configuration Reference table in `README.md`

### Add a New API Endpoint

1. Create the route function in `app/routes/api.py` (or a new router)
2. Add a Pydantic response model in `app/models/schemas.py`
3. Register the router in `app/main.py`
4. Add the endpoint to `docs/API.md`

### Add a New Divination Method

1. Create a new `app/engine/<method>.py` module returning a `Hexagram` object
2. Import and register the route in `app/routes/api.py`
3. Add the HTML form template in `app/templates/`
4. Document in `README.md` features list and `docs/API.md`

### Database Migration

The app uses SQLite with manual migration for schema changes. See `app/main.py:_migrate_db()` for the pattern — use `PRAGMA table_info` to check column existence, then `ALTER TABLE` to add columns.

---

## Dependencies 依赖说明

| Package | Purpose | Production |
|---------|---------|------------|
| `fastapi` + `uvicorn` | Web framework + ASGI server | Required |
| `sqlalchemy` + `aiosqlite` | Async ORM + SQLite driver | Required |
| `jinja2` | Template engine | Required |
| `pydantic-settings` | Environment variable loading | Required |
| `redis` + `hiredis` | Optional cache backend | Optional |
| `anthropic` | AI LLM SDK | Optional (needed for AI features) |

---

## Architecture Principles 架构原则

1. **Engine purity**: The `app/engine/` package must remain side-effect-free. No database, no network, no file I/O. Every function should be deterministic given its inputs.

2. **Middleware isolation**: Each middleware does exactly one thing. The `client_id` middleware only manages identity; the circuit breaker only manages rate limits.

3. **Configuration over code**: All tunable parameters (rate limits, TTLs, URLs) go in `config.py` / `.env`, not hardcoded in route handlers.

4. **Graceful degradation**: Redis is optional. If unavailable, the app falls back to database queries. AI is optional. If no API key is configured, the app uses rule-based interpretation.

5. **Privacy by default**: The API divination endpoints do not store user questions. All server-side queries filter by `client_id`.
