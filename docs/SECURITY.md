# Security Design 安全设计

> Security architecture, threat model, and defense mechanisms for the I Ching Divination server.

---

## Threat Model 威胁模型

### Assumptions

- **Network**: Application is deployed behind nginx reverse proxy on a single VM (2C2G Alibaba ECS)
- **Attack surface**: All `/api/*` endpoints are public (no authentication). HTML routes serve Jinja2 templates.
- **Attacker capabilities**: Can call any public endpoint, spoof HTTP headers, enumerate URLs, send arbitrary request bodies
- **Attacker limitations**: Cannot access the server filesystem directly, cannot intercept TLS, cannot modify DNS

### In-Scope Threats

| Threat | Description | Severity |
|--------|-------------|----------|
| Data leak via API | Accessing other users' divination records | HIGH |
| Rate limit bypass | Spoofing IP headers to exhaust AI quota | MEDIUM |
| XSS via AI output | Stored XSS via prompt-injected AI response | HIGH |
| Sync code brute-force | Enumerating 8-char codes to steal data | MEDIUM |
| Memory exhaustion | Flooding sync store with fake records | LOW |
| Multi-worker bypass | Per-process rate limits in multi-worker deployments | MEDIUM |

### Out-of-Scope

- Physical server access
- Compromise of nginx/AWS/cloud provider
- Compromise of DeepSeek/Anthropic API infrastructure
- Browser-level attacks (keyloggers, malware)

---

## Defenses 防御措施

### D1: Anonymous Client ID (Identity Isolation)

**Mechanism**: 256-bit random token via `secrets.token_urlsafe(32)`, stored in HttpOnly cookie.

**Code**: `app/main.py:103-120`

```python
@app.middleware("http")
async def client_id_middleware(request: Request, call_next):
    cid = request.cookies.get(COOKIE_NAME)
    if not cid:
        cid = secrets.token_urlsafe(32)
    request.state.client_id = cid
    # ...
    response.set_cookie(
        key=COOKIE_NAME, value=cid,
        max_age=COOKIE_MAX_AGE,   # 1 year
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )
```

**Properties**:
- 256-bit entropy: brute-force infeasible (2^256 combinations)
- HttpOnly: JavaScript cannot read the token
- SameSite=Lax: mitigates CSRF on POST routes
- Auto-expires after 1 year, rotated on re-visit

---

### D2: Data Isolation per Client

**Mechanism**: All database queries for history/list endpoints filter by `client_id`.

**Code**: `app/routes/api.py:322`

```python
records = records.where(DivinationRecord.client_id == request.state.client_id)
```

**Exemptions** (public by design):
- `GET /api/history/share/{token}` — UUID lookup, no client_id filter (`api.py:453-457`)
- `GET /api/sync/{code}` — code lookup, no client_id filter (`api.py:678-683`)

---

### D3: IP Rate Limiting + Circuit Breaker

**Mechanism**: Sliding window rate limiter with burst detection and automatic IP ban.

**Code**: `app/limits.py:89-125`

```python
_IP_RATE_PER_MIN = 120          # 120 req/min per IP
_BURST_PER_SEC = 10             # burst threshold
_BAN_SECONDS = 300              # 300s automatic ban

def check_rate_limit(client_ip: str) -> tuple[bool, dict]:
    # ...
    # Burst detection
    burst = sum(1 for t in _IP_WINDOW[client_ip] if t > now - 1)
    if burst > _BURST_PER_SEC:
        _IP_BANNED[client_ip] = now + _BAN_SECONDS
        return False, {"error": "...", "retry_after": 300}
    # Sliding window
    used = len(_IP_WINDOW[client_ip])
    if used > _IP_RATE_PER_MIN:
        return False, {"error": "...", "retry_after": 60}
```

**Middleware**: `app/main.py:127-143`

```python
@app.middleware("http")
async def circuit_breaker_middleware(request: Request, call_next):
    # Skip static files
    if request.url.path.startswith("/static"):
        return await call_next(request)
    ip = get_client_ip(request)
    allowed, info = check_rate_limit(ip)
    if not allowed:
        return JSONResponse(status_code=429, ...)
```

---

### D4: IP Extraction — Anti-Spoofing

**Mechanism**: Only trusts `X-Real-IP` header. Explicitly ignores `X-Forwarded-For` to prevent IP spoofing.

**Code**: `app/limits.py:72-82`

```python
def get_client_ip(request) -> str:
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"
```

**Why not X-Forwarded-For**: The `X-Forwarded-For` header can contain multiple comma-separated IPs and can be trivially spoofed by clients. `X-Real-IP` is set by nginx from `$remote_addr` and trusted by the application.

**nginx configuration** (`deploy/iching-nginx.conf`):

```nginx
proxy_set_header X-Real-IP $remote_addr;
```

---

### D5: AI Daily Limit

**Mechanism**: Global daily cap on AI interpretations. Prevents quota exhaustion from a single attacker or runaway script.

**Code**: `app/limits.py:17-55`, `app/config.py:24`

```python
# config.py
daily_ai_limit: int = 10_000

# limits.py
def can_use_ai(client_ip: str) -> bool:
    _check_reset()
    return _daily["total"] < DAILY_AI_LIMIT
```

**Properties**:
- Per-worker counter (in single-worker deployments, exact; in multi-worker, effective limit = `DAILY_AI_LIMIT * num_workers`)
- Resets at midnight UTC
- Per-IP tracking available via `get_usage()` but enforcement is global

---

### D6: Cookie Security Flags

**Code**: `app/main.py:114-119`

| Flag | Value | Purpose |
|------|-------|---------|
| `httponly` | `True` | Prevents JavaScript access (XSS mitigation) |
| `samesite` | `"lax"` | Prevents CSRF on top-level navigations |
| `secure` | `True` (production) | Ensures cookie sent over HTTPS only |

---

### D7: Sync Code Protection

**Code**: `app/routes/api.py:605-713`

| Defense | Implementation | File:Line |
|---------|---------------|-----------|
| 8-char code space | `[a-z]{4}[0-9]{4}` = 456,976,000 combinations | `api.py:632-634` |
| Auto-delete after 3 accesses | `entry.access_count >= entry.max_accesses` | `api.py:700-703` |
| TTL expiration | `datetime.utcnow() > expires_at` | `api.py:689-694` |
| Rate limit | 10 req/h/IP via `_check_sync_rate_limit()` | `api.py:574-583` |
| Code format validation | `re.match(r'^[a-z]{4}\d{4}$', code)` | `api.py:674` |

---

### D8: nginx Security Headers

**Configured in**: `deploy/iching-nginx.conf`

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |

**Static file protection**:

```nginx
# .env and .git are not in the static directory, but explicit deny
location ~ /\.(env|git) {
    deny all;
    access_log off;
    log_not_found off;
}
```

---

### D9: Jinja2 Template Escaping

**Mechanism**: Jinja2's `tojson` filter escapes `<`, `>`, `&`, `/` as Unicode escapes when rendering in `<script>` contexts.

```html
<script>
var saveData = {{ result | tojson | safe }};
</script>
```

The `tojson` filter produces JSON-safe output. The `safe` flag is necessary because `tojson` already performs escaping — adding `safe` after `tojson` does not undo the escaping. This is a recognized safe pattern in Jinja2.

**Source**: `app/templates/result/divination_result.html`, `app/templates/history/detail.html`

---

### D10: Static File Direct Serving

**Mechanism**: Static files are served directly by nginx, bypassing the Python application entirely. This reduces the attack surface on the Python process.

```
nginx: /static/* → filesystem (no proxy to uvicorn)
nginx: /*        → proxy_pass to uvicorn:8088
```

**Code**: `deploy/iching-nginx.conf`, `app/main.py:146`

---

## Known Limitations 已知局限

### L1: In-Memory Rate Limiter (Per-Worker)

The rate limiter (`app/limits.py`) uses per-process Python dicts. In multi-worker deployments:

- Each worker has independent counters
- Effective rate limit = 120 req/min × num_workers
- AI daily limit = 10,000 × num_workers
- IP ban is per-worker (attacker can rotate workers)

**Fix**: Use Redis-based centralized counters (Redis is already a project dependency).

**Source**: `app/limits.py:14-15`, audit finding #12

### L2: No CSRF Token

There is no CSRF token validation on POST routes. The `SameSite=Lax` cookie flag mitigates top-level CSRF but does not protect against all CSRF vectors (e.g., subdomain attacks).

**Mitigation**: `SameSite=Lax` on the `iching_cid` cookie prevents it from being sent on cross-site POST requests from external origins.

### L3: AI Output Trust Level

The AI interpretation text is rendered with `| replace('\n', '<br>') | safe` in `history/detail.html`. While the AI is trusted not to emit malicious HTML, prompt injection is a known attack vector for LLMs.

**Current guards**:
- CSS is pre-wrapped in `<div class="ai-interpretation">` — not raw CSS injection
- No `| safe` used on raw user input — only on AI output which is server-generated
- The `ai_interpretation` field is not included in API responses by default

**Recommendation**: Replace `| safe` with `| e | replace('\n', '<br>')` and sanitize through a DOM text node instead of `innerHTML`.

**Source**: `app/templates/history/detail.html:189`, audit finding #2

### L4: SQLite Database Unencrypted at Rest

The `data/iching.db` file is stored in plaintext. If the server is compromised, the database can be read directly. This includes hexagram binary data and timestamps.

**Mitigation**:
- Nginx does not expose the `/data/` path
- File permissions restrict access to the `www-data` user only
- The `question` and `ai_interpretation` columns are not included in API response schemas

### L5: Sync Store Uses SQLite (Was In-Memory)

The sync store originally used a per-process dict (`_sync_store`), which caused data loss in multi-worker deployments (audit finding #3). This was migrated to SQLite via the `SyncCode` model.

**Current behavior**:
- Sync codes are stored in the `sync_codes` table in SQLite
- Shared across all workers
- TTL enforced at query time
- Auto-deleted after max_accesses (default: 3)

**Source**: `app/models/divination_record.py:54-63`, `app/routes/api.py:605-713`

---

## Vulnerability Disclosure 漏洞报告

If you discover a security issue, please open a GitHub Issue at:
https://github.com/netlinemelon/iching/issues

Please do not open a public PR for critical security vulnerabilities. Report privately via the issue tracker with a security label.
