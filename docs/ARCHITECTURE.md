# Architecture 系统架构

> Developer-focused overview of the I Ching Divination server architecture.

---

## Request Flow 请求流

Every HTTP request traverses this pipeline:

```
                          ┌─────────────────────────────────────┐
                          │          nginx (reverse proxy)       │
                          │  • TLS termination                   │
                          │  • Static file direct serving        │
                          │  • gzip compression                  │
                          │  • Rate limit: upstream 120/min/IP   │
                          └────────────┬────────────────────────┘
                                       │ proxy_pass http://127.0.0.1:8088
                                       │ X-Real-IP: client IP
                                       ▼
                    ┌──────────────────────────────────────┐
                    │         FastAPI Application            │
                    │                                        │
                    │  ┌──────────────────────────────────┐  │
                    │  │  client_id_middleware             │  │
                    │  │  app/main.py:103-120              │  │
                    │  │                                   │  │
                    │  │  1. Read iching_cid cookie        │  │
                    │  │  2. Not found → generate 256-bit  │  │
                    │  │     (secrets.token_urlsafe(32))   │  │
                    │  │  3. Set request.state.client_id   │  │
                    │  │  4. First visit → Set-Cookie      │  │
                    │  │     HttpOnly + Secure + SameSite  │  │
                    │  └──────────┬───────────────────────┘  │
                    │             ▼                          │
                    │  ┌──────────────────────────────────┐  │
                    │  │  circuit_breaker_middleware       │  │
                    │  │  app/main.py:127-143              │  │
                    │  │                                   │  │
                    │  │  1. Skip /static/ paths            │  │
                    │  │  2. Get client IP from X-Real-IP  │  │
                    │  │  3. check_rate_limit(ip)          │  │
                    │  │     ├─ Banned? → 429 + Retry-After│  │
                    │  │     ├─ Burst? (10/s) → 429 + ban  │  │
                    │  │     ├─ Over 120/min? → 429        │  │
                    │  │     └─ OK → add header             │  │
                    │  └──────────┬───────────────────────┘  │
                    │             ▼                          │
                    │  ┌──────────────────────────────────┐  │
                    │  │  Route Handler                    │  │
                    │  │  ┌───────┐ ┌────────┐ ┌───────┐  │  │
                    │  │  │ home │ │ divine │ │ api   │  │  │
                    │  │  │routes│ │ routes │ │routes │  │  │
                    │  │  └───────┘ └────────┘ └───────┘  │  │
                    │  │  ┌────────┐ ┌─────────┐          │  │
                    │  │  │history │ │ hexagram│          │  │
                    │  │  │ routes │ │ study   │          │  │
                    │  │  └────────┘ └─────────┘          │  │
                    │  └──────────────────────────────────┘  │
                    └────────────┬─────────────────────────┘
                                 │ JSON / HTML response
                                 ▼
                    ┌──────────────────────────────────────┐
                    │         Client (Browser / curl)       │
                    │  • Stores hexagram data in localStorage│
                    │  • AJAX calls via Alpine.js            │
                    └──────────────────────────────────────┘
```

---

## Data Model 数据模型

### DivinationRecord

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK, auto) | Sequential record ID |
| `client_id` | STRING(64) | 256-bit anonymous identity, indexed |
| `created_at` | DATETIME | UTC timestamp, indexed |
| `method` | STRING(50) | `coin`, `yarrow`, `time`, `number`, `plum-blossom` |
| `original_binary` | STRING(6) | 6-bit binary of the original hexagram |
| `original_values` | JSON | `[6,7,8,9,...]` line values bottom→top |
| `changed_binary` | STRING(6) | 6-bit binary of the changed hexagram (nullable) |
| `changing_positions` | JSON | Array of changing line positions `[1,3,5]` |
| `notes` | TEXT | User notes (nullable) |
| `question` | TEXT | User's question — **not stored via API endpoints** |
| `ai_interpretation` | TEXT | AI interpretation text (nullable) |
| `is_favorite` | BOOLEAN | Bookmark flag |
| `share_token` | STRING(36) | UUID for public sharing, unique indexed |

**Source**: `app/models/divination_record.py:15-51`

### SyncCode

| Column | Type | Description |
|--------|------|-------------|
| `code` | STRING(8) (PK) | `[a-z]{4}[0-9]{4}` sync code |
| `client_id` | STRING(64) | Owner's client_id, indexed |
| `records` | TEXT | JSON-serialized records array |
| `created_at` | DATETIME | UTC timestamp |
| `access_count` | INTEGER | Number of times downloaded |
| `max_accesses` | INTEGER | Max downloads before auto-delete (default: 3) |

**Source**: `app/models/divination_record.py:54-63`

### client_id Isolation

All history queries filter by `client_id` from the cookie:

```python
# app/routes/api.py:322
records = records.where(DivinationRecord.client_id == request.state.client_id)
```

Share endpoints (`/api/history/share/{token}`, `/api/sync/{code}`) use token/code lookup without client_id filter — they are **public by design**.

### 64 Hexagrams JSON

Read-only reference data loaded from `data/hexagrams.json`:

- **Structure**: Array of 64 hexagram objects, indexed by King Wen order (1-64)
- **Fields per hexagram**: number, binary, name (cn/pinyin/en), unicode, upper/lower trigram, judgment, tuan (彖传), xiang (大象传), lines (6 lines with text/xiang), extra_lines (乾坤用九用六)
- **Loaded once** at import time via `app/models/hexagram_data.py`
- **No database dependency** — pure JSON parsing

---

## Engine Pipeline 占卜引擎管线

All five casting methods feed into the same analysis pipeline:

```
                    ┌─────────────┐
                    │ Coin Toss   │──┐
                    ├─────────────┤  │   ┌──────────────────┐
                    │ Yarrow      │──┤   │                  │
                    ├─────────────┤  ├──▶│  Hexagram        │
                    │ Time-base   │──┤   │  (core.py)       │
                    ├─────────────┤  │   │                  │
                    │ Number      │──┤   │  6 x Line        │
                    ├─────────────┤  │   │  (6/7/8/9 vals)  │
                    │ Plum Blossom│──┘   └────────┬─────────┘
                    └─────────────┘               │
                                                  ▼
                              ┌───────────────────────────────┐
                              │   changed_hexagram()          │
                              │   app/engine/transform.py     │
                              │   Flip old yin/yang lines     │
                              └───────────────┬───────────────┘
                                              │
                                              ▼
                    ┌───────────────────────────────────────────┐
                    │        build_divination_result()          │
                    │        app/engine/result_builder.py       │
                    │                                           │
                    │   ┌───────────────┐                       │
                    │   │ mutual (互卦) │ ← inner 234 + 345     │
                    │   ├───────────────┤                       │
                    │   │ opposite (错卦)│ ← flip all bits      │
                    │   ├───────────────┤                       │
                    │   │ reverse (综卦) │ ← reverse order      │
                    │   ├───────────────┤                       │
                    │   │ body-use      │ ← 体用生克 analysis   │
                    │   │ (体用)        │                       │
                    │   ├───────────────┤                       │
                    │   │ interpretation │ ← Zhu Xi rules       │
                    │   │ (朱子解卦)     │    0-6 changing lines │
                    │   └───────────────┘                       │
                    └───────────────────┬───────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────────┐
                    │      _build_api_result() / AI interpret    │
                    │                                           │
                    │   Flatten to JSON response schema         │
                    │   OR pass to AI interpret_with_ai()       │
                    └───────────────────────────────────────────┘
```

### Engine Modules

| Module | File | Purity | Description |
|--------|------|--------|-------------|
| `core.py` | `app/engine/core.py` | Pure | `LineType`, `TrigramBagua`, `Line`, `Hexagram` types |
| `coin.py` | `app/engine/coin.py` | Pure | Three-coin method, 6 tosses → 6 values |
| `yarrow.py` | `app/engine/yarrow.py` | Pure | 50-stalk method simulation |
| `time.py` | `app/engine/time.py` | Pure | Date+time → upper/lower/changing trigram |
| `number.py` | `app/engine/number.py` | Pure | Three user-provided numbers |
| `plum_blossom.py` | `app/engine/plum_blossom.py` | Pure | Two trigrams + optional changing line |
| `transform.py` | `app/engine/transform.py` | Pure | Changed/mutual/opposite/reverse hexagrams |
| `interpretation.py` | `app/engine/interpretation.py` | Pure | Zhu Xi rules for 0-6 changing lines |
| `result_builder.py` | `app/engine/result_builder.py` | Pure | Assembles full result dict |

All engine modules are **pure functions** — no I/O, no database access, no side effects. They take input values and return structured data.

---

## Privacy Design 隐私设计

```
┌──────────────────────────────────────────────────────────────┐
│                     Privacy Architecture                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Client ID System:                                           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  256-bit random via secrets.token_urlsafe(32)        │    │
│  │  Stored in HttpOnly cookie (iching_cid)             │    │
│  │  Auto-assigned on first visit, no registration      │    │
│  │  Client never sees the raw value (HttpOnly)         │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Data Isolation:                                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  All DB queries: WHERE client_id = current_id        │    │
│  │  Two exceptions (public by design):                  │    │
│  │    • /api/history/share/{token}  — UUID lookup       │    │
│  │    • /api/sync/{code}            — code lookup       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Storage Layers:                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Browser      │  │ Server       │  │ Redis (optional)  │   │
│  │ localStorage │  │ SQLite       │  │                   │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────────┤   │
│  │ Full records │  │ Hexagram     │  │ Cached results   │   │
│  │ with question│  │ binary +     │  │ TTL: 3600s       │   │
│  │ & AI text    │  │ timestamps   │  │                   │   │
│  │              │  │ Question     │  │                   │   │
│  │              │  │ NOT stored   │  │                   │   │
│  │              │  │ by API       │  │                   │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                              │
│  Share Tokens:                                               │
│  • UUID v4 → /api/history/share/{token}                     │
│  • Public hexagram data only (no question, no AI text)      │
│  • Sync codes: 8-char [a-z]{4}[0-9]{4}, max 3 accesses     │
│                                                              │
│  Rate Limiting:                                              │
│  • 120 req/min/IP sliding window                            │
│  • Burst detection: 10 req/s → 300s ban                     │
│  • AI: 10,000/day global (in-memory, per-worker)            │
│  • Sync: 10 req/h/IP                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions 关键设计决策

1. **In-memory rate limiter** (`app/limits.py`): Per-process counters work for single-worker deployments. Multi-worker setups should use Redis-based centralized counters (Redis is already a project dependency).

2. **SQLite with aiosqlite**: Single-file database, suitable for low-traffic deployments. No separate database server needed. The `data/iching.db` file includes all persisted records.

3. **Optional Redis**: Caches divination results and AI interpretations. Graceful degradation — if Redis is unavailable, the app falls back to database queries for cache misses. Configured via `REDIS_URL` in `.env`.

4. **Anonymous by design**: No user accounts, no passwords, no OAuth. The `client_id` cookie is the sole identity mechanism. This simplifies privacy compliance but limits cross-device features without the sync code system.

5. **Engine purity**: The `app/engine/` package has zero dependencies on FastAPI, database, or Redis. It can be tested and used independently as a Python library for I Ching divination.
