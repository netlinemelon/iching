# Server Branch Audit Report

**Branch**: server
**Date**: 2026-06-21
**Scope**: All new/modified files from the feature sprint (limits, sync, localStorage, donate, mobile CSS)

---

## P0 -- CRITICAL

### 1. Sync Endpoints Have Zero Authentication -- Data Leak by Design

**File**: `D:\Project\python\8gua\app\routes\api.py` (lines 558-609)
**File**: `D:\Project\python\8gua\app\static\js\sync.js` (lines 30-137)

The two sync endpoints (`POST /api/sync/create` and `GET /api/sync/{code}`) have **no authentication of any kind** -- no API key, no session, no CSRF token, not even a basic rate limit.

- **Anyone** can `POST /api/sync/create` with arbitrary JSON containing a `records` array. This fills the server's in-memory store with unwanted data.
- **Anyone** can brute-force the 6-digit sync codes. The code space is 100000-999999 (900,000 values). At 1000 req/s the entire space can be enumerated in ~15 minutes. Each hit returns that user's complete divination records including their question text.
- The `/api/sync/{code}` GET endpoint has **no rate limiting at all**. No limits.py check, no throttling.

**Impact**: All user data synced via this feature is trivially discoverable by anyone who probes the URL space. The sync feature as implemented is a data disclosure vulnerability, not a feature.

**Fix**: At minimum: (a) rate-limit the GET endpoint to 5 req/min/IP, (b) increase sync code entropy (e.g. 8-char alphanumeric), (c) add a one-time consumption model where the code is deleted after first download, (d) preferably add user authentication or a verification mechanism.

---

### 2. Stored XSS via AI Interpretation Output

**File**: `D:\Project\python\8gua\app\templates\history\detail.html` (line 189)

```jinja
{{ record.ai_interpretation | replace('\n', '<br>') | safe }}
```

The `safe` filter marks the AI interpretation as trusted HTML. The AI model (DeepSeek-v4-pro via Anthropic API) can be prompt-injected to output arbitrary HTML, including `<script>` tags and event handlers. This output is stored in the SQLite database and served to every visitor of that detail or share page.

**Attack scenario**: A user crafts a divination question that tricks the AI into emitting `<script>alert(document.cookie)</script>`. The AI's response is persisted to the database. Anyone who views that record's detail page (or share link) executes the payload.

**Fix**: Never use `safe` on AI-generated text. Either:
- Use `{{ record.ai_interpretation | e | replace('\n', '<br>') }}` (escape then replace)
- Or use a proper HTML sanitizer like `bleach`
- Or render the text into a DOM text node via JavaScript, not innerHTML

---

### 3. `_sync_store` Breaks Under Multiple Workers -- Silent Data Loss

**File**: `D:\Project\python\8gua\app\routes\api.py` (line 541)

```python
_sync_store: dict[str, dict] = {}
```

This is a process-local in-memory dict. In production deployments using multiple uvicorn workers (e.g., `gunicorn -k uvicorn.workers.UvicornWorker -w 4`), each worker has its own independent `_sync_store`:

- Worker A creates a sync code `374592` and stores data in its memory.
- Worker B receives the download request for `374592` -- its `_sync_store` dict has no entry for that code, returns 404.
- **50-75% of sync downloads will fail** depending on worker count and routing.

**Fix**: Move sync storage to a shared backing store -- either Redis (already configured in the project) or the SQLite database. Delete entirely from per-process memory.

---

### 4. `detail.html` Save-to-localStorage Is Dead Code

**File**: `D:\Project\python\8gua\app\templates\history\detail.html` (lines 334-346)

```javascript
if (window.IChingStorage && typeof shared !== 'undefined' && !shared) {
    (function() {
        try {
            var saveData = {{ record | tojson | safe }};
            IChingStorage.saveResult(saveData);
        } catch (e) {
            console.warn('[IChingStorage] 保存到本地失败:', e);
        }
    })();
}
```

The variable `shared` is a Jinja2 template variable (passed via the context dict in `history.py`), but it is **never declared as a JavaScript variable** in the rendered page. The condition `typeof shared !== 'undefined'` evaluates to `false`, so the entire save-to-localStorage block is dead code. Users viewing their own history detail page never get the data saved to localStorage.

The divination_result.html page (line 486) does NOT have this check -- it only tests `if (window.IChingStorage)` -- so it works correctly. But the history detail page's save is completely broken.

**Fix**: Add a `<script>var shared = {{ 'true' if shared else 'false' }};</script>` at the top of the script block, or change the condition to simply `if (window.IChingStorage)` like the result page does (since the `shared` guard is not meaningful on a page the user is already authenticated to view by virtue of having the URL).

---

## P1 -- BUGS

### 5. Undeclared JavaScript Variable `shared`

Same root cause as #4 but listed separately because it also affects the template's Jinja2 logic indirectly and represents a misunderstanding of Jinja2/JS boundaries. The template assumes Jinja2 context variables are automatically available as JavaScript globals, which they are not.

---

### 6. Donation QR Images Are 1x1 Transparent Placeholders, `onerror` Never Fires

**File**: `D:\Project\python\8gua\app\static\img\wechat-qr.png` (70 bytes, 1x1 transparent PNG)
**File**: `D:\Project\python\8gua\app\static\img\alipay-qr.png` (70 bytes, 1x1 transparent PNG)
**File**: `D:\Project\python\8gua\app\templates\components\donate.html` (lines 10, 14)

```html
<img src="/static/img/wechat-qr.png" alt="微信赞赏" loading="lazy" onerror="this.style.display='none'">
```

Both QR images are verified 1x1 transparent placeholder PNGs (confirmed via hex dump: IHDR width=1, height=1). The `onerror` handler is designed to hide broken images, but since the PNG files **load successfully** (they are valid PNGs), `onerror` never fires. Users see empty rectangles where QR codes should be.

**Fix**: Either (a) replace with actual QR code images, or (b) check image dimensions via `onload` and hide undersized images, or (c) add a `::after` CSS placeholder message when the image has zero intrinsic size.

---

### 7. `_saveAll()` Has No Error Handling -- Called From Contexts Without try/catch

**File**: `D:\Project\python\8gua\app\static\js\storage.js` (lines 50-52)

```javascript
function _saveAll(records) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}
```

This function throws uncaught exceptions when:
- `localStorage` is **undefined** (private browsing in some browsers, localStorage disabled via settings)
- `JSON.stringify(records)` throws due to circular references (unlikely but unhandled)

`_saveAll` is called from:
- `saveResult()` -- **has** try/catch around it (line 127) -- SAFE
- `toggleFavorite()` (line 206) -- **NO** try/catch -- UNSAFE
- `deleteResult()` (line 225) -- **NO** try/catch -- UNSAFE
- `importJSON()` (line 304) -- **NO** try/catch -- UNSAFE

If localStorage is unavailable, toggling a favorite or deleting a record throws a silent exception that may prevent the UI from reflecting the change.

**Fix**: Add try/catch to `_saveAll` itself, or wrap every call site.

---

### 8. `syncUpload()` Uses Leaked Global `event`

**File**: `D:\Project\python\8gua\app\templates\history\index.html` (lines 101-102)

```javascript
function syncUpload() {
  var btn = event && event.target;
```

The `event` parameter is not declared. It relies on the legacy IE behavior where `window.event` is available. In strict mode or in modern frameworks this is undefined. While inline `onclick` handlers do make `event` available as a global, this is fragile behavior.

**Fix**: Accept `event` as a function parameter: `function syncUpload(event) { ... }`.

---

### 9. IP Spoofing via `X-Forwarded-For` Injection

**File**: `D:\Project\python\8gua\app\limits.py` (lines 66-73)

```python
def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
```

The function trusts the first value in `X-Forwarded-For` unconditionally. If the app is behind a reverse proxy that doesn't sanitize this header, an attacker can inject:

```
curl -H "X-Forwarded-For: 1.2.3.4" ...
```

This means the AI rate limiter can be bypassed by rotating spoofed IP addresses. Each request appears to come from a different IP, resetting the per-IP count.

**Fix**: Document the expected proxy configuration. If behind a trusted proxy, use only the proxy-provided value (typically the last IP in the chain) or configure FastAPI's `trusted_hosts` and proxy middleware.

---

### 10. `sync_code_ttl` Config Value Ignored

**File**: `D:\Project\python\8gua\app\config.py` (line 26)
**File**: `D:\Project\python\8gua\app\routes\api.py` (line 581)

```python
# config.py
sync_code_ttl: int = 86400  # 24 hours

# api.py
expires_at = datetime.utcnow() + timedelta(hours=24)  # hardcoded
```

The `settings.sync_code_ttl` config value exists but is never imported or referenced. Sync code expiry is hardcoded to 24 hours.

**Fix**: Use `settings.sync_code_ttl` instead of hardcoded `timedelta(hours=24)`.

---

## P2 -- SHORTCUTS AND RELIABILITY ISSUES

### 11. No Rate Limiting on Sync Endpoints

**File**: `D:\Project\python\8gua\app\routes\api.py` (lines 558-609)

Neither `POST /api/sync/create` nor `GET /api/sync/{code}` has any rate limiting. An attacker can:
- Flood the sync store with millions of useless entries (unbounded memory growth)
- Brute-force the 6-digit code space with no throttling

The limits.py module exists but is only applied to the AI interpretation endpoint.

**Fix**: Apply per-IP rate limiting (reuse limits.py or add separate limits) to both sync endpoints.

---

### 12. Multi-Worker Inconsistency: Per-Process Rate Limits

**File**: `D:\Project\python\8gua\app\limits.py` (lines 14-15)

```python
_daily: dict = {"date": "", "total": 0, "ips": defaultdict(int)}
```

Same architecture issue as the sync store: in a multi-worker deployment, each worker has its own `_daily` dict. The effective daily AI limit becomes `DAILY_AI_LIMIT * num_workers`, not `DAILY_AI_LIMIT`. 4 workers = 40,000 AI calls/day.

**Fix**: Use Redis for centralized rate limit counters (Redis is already in the project's dependencies).

---

### 13. Unbounded Memory Growth in `_sync_store`

**File**: `D:\Project\python\8gua\app\routes\api.py` (line 541)

The sync store has no maximum size limit. Even with the 24-hour expiry cleanup, an attacker creating 1 million sync codes in an hour could consume gigabytes of server memory. Each entry stores the full records array, which could itself be large.

**Fix**: Add an upper bound (e.g., max 10,000 entries) and/or a maximum records-per-code limit. Preferably move to Redis with automatic TTL.

---

### 14. Timezone-Dependent Daily Reset, Undocumented

**File**: `D:\Project\python\8gua\app\limits.py` (line 20)

```python
def _get_today() -> str:
    return time.strftime("%Y-%m-%d")
```

This uses the **server's local timezone**, which may not match the user's timezone. If the server runs in UTC, the AI limit resets at 00:00 UTC, which is 08:00 Beijing time or 16:00 US Pacific. Not documented anywhere.

**Fix**: Either (a) use UTC explicitly (`time.strftime("%Y-%m-%d", time.gmtime())`) and document it, or (b) use timezone-aware datetimes.

---

### 15. No iOS Safe Area for Donate Button

**File**: `D:\Project\python\8gua\app\static\css\donate.css` (lines 4-7)
**File**: `D:\Project\python\8gua\app\static\css\main.css` (lines 981-984)

```css
.donate-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
}
```

On iOS Safari, the bottom toolbar (approx 50px) can overlap with the donate button positioned at `bottom: 24px`. In main.css at 480px, it's even lower at `bottom: 16px`.

**Fix**: Add `bottom: calc(24px + env(safe-area-inset-bottom))` and `bottom: calc(16px + env(safe-area-inset-bottom))` for the mobile breakpoint.

---

### 16. `importJSON()` Uses `reader.onload` Pattern -- Lacks Abort Handling

**File**: `D:\Project\python\8gua\app\static\js\storage.js` (lines 264-316)

The `FileReader` has no `onabort` handler. If the user cancels the file selection or the browser aborts the read, the Promise never resolves or rejects -- it hangs indefinitely. Not a critical issue (the user canceled, so no one is waiting), but technically an unhandled promise.

---

### 17. `detail.html` Line 189 -- AI Text Rendered Without Sanitization

Already listed as P0 #2. Listed here again because even without malicious intent, AI models sometimes output raw HTML entities, angle brackets, or markdown that gets mangled by the `safe` filter into broken or invisible HTML. The `replace('\n', '<br>')` approach is insufficient for safe rendering of LLM output.

---

## FIX LIST

Ordered by priority (P0 first, within each tier by estimated fix effort).

| # | Priority | File:Line | Issue | Fix |
|---|----------|-----------|-------|-----|
| 1 | P0 | `api.py:594-609` | Sync GET endpoint: zero auth, brute-forceable codes, no rate limit | Rate-limit to 5/min/IP; increase code to 8-char; consume-on-read; or add real auth |
| 2 | P0 | `detail.html:189` | `ai_interpretation \| safe` -- stored XSS via AI prompt injection | Remove `safe`; use `\| e \| replace(...)` or DOM text node |
| 3 | P0 | `api.py:541` | `_sync_store` in per-process memory breaks with multiple workers | Move to Redis (already in deps) or SQLite |
| 4 | P0 | `detail.html:336-346` | Save-to-localStorage is dead code (shared JS var undeclared) | Declare `var shared = {{ 'true' if shared else 'false' }}` or remove the check |
| 5 | P1 | `donate.html:10,14` | QR images are 1x1 transparent placeholders; `onerror` never fires | Replace with real QR images or add dimension check |
| 6 | P1 | `storage.js:50-52` | `_saveAll()` can throw; 3 call sites lack try/catch | Wrap `_saveAll` body in try/catch or wrap all calls |
| 7 | P1 | `history/index.html:101` | `syncUpload()` uses undeclared `event` global | Add `event` as function parameter |
| 8 | P1 | `limits.py:66-73` | X-Forwarded-For spoofing bypasses rate limiter | Document proxy setup; validate or use `request.client.host` |
| 9 | P1 | `api.py:581` vs `config.py:26` | `settings.sync_code_ttl` defined but never used; hardcoded 24h | Use `settings.sync_code_ttl` instead of literal |
| 10 | P2 | `api.py:558-609` | No rate limiting on sync endpoints (separate from auth gap) | Add per-IP throttling to both sync endpoints |
| 11 | P2 | `limits.py:15` | Per-process rate limits in multi-worker = limit * N | Use Redis-based centralized counters |
| 12 | P2 | `api.py:541` | No max size on `_sync_store` (memory exhaustion vector) | Cap entries; limit records per code; use Redis TTL |
| 13 | P2 | `limits.py:20` | `time.strftime` uses server local timezone, undocumented | Use `time.gmtime()` or timezone-aware datetime; document behavior |
| 14 | P2 | `donate.css:4` / `main.css:981` | iOS bottom toolbar overlaps donate button | Add `env(safe-area-inset-bottom)` to bottom positioning |

---

## Cross-References

- **Only one sync store**: Confirmed. `_sync_store` only exists in `app/routes/api.py`. `limits.py` has no sync mechanism. No conflict.
- **No sync dependency on IChingStorage**: Confirmed. `sync.js` reads/writes localStorage directly, not through `IChingStorage`. No race condition on load order.
- **Load order is correct**: `base.html` loads `storage.js` before `sync.js`, both as blocking `<script>` tags. IIFE patterns in both files ensure their namespace assignments complete before any page code runs.
- **`tojson` XSS safety**: Jinja2 3.1.6's `tojson` filter escapes `<`, `>`, `&`, `/` as Unicode escapes. The `{{ result \| tojson \| safe }}` pattern in `<script>` contexts is safe.
- **`_check_reset` single-thread safety**: In single-worker asyncio, no `await` in the critical section means no race condition. In multi-worker, each worker has its own counter (see #11).
- **Server restart**: Both `_daily` and `_sync_store` are lost. Acceptable for rate limits (counter resets). Problematic for sync codes (data loss).
- **Mobile CSS at 375px**: 3-column hexagram grid works at 375px (content area ~343px). The 360px breakpoint drops to 2 columns. Responsive design is adequate.
