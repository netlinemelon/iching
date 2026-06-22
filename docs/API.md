# API Reference API 接口文档

> Complete REST API reference for the I Ching Divination server.
>
> **Base URL**: `http://localhost:8088/api` (development) or `https://iching-ai.cn/api` (production)

---

## Index

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/divine/coin` | Coin toss divination |
| POST | `/api/divine/yarrow` | Yarrow stalk divination |
| POST | `/api/divine/time` | Time-based divination |
| POST | `/api/divine/number` | Number-based divination |
| POST | `/api/divine/plum-blossom` | Plum blossom divination |
| GET | `/api/hexagrams` | List all 64 hexagrams |
| GET | `/api/hexagrams/{number}` | Hexagram detail (1-64) |
| GET | `/api/hexagrams/search?q=` | Search hexagrams |
| GET | `/api/trigrams` | List all 8 trigrams |
| GET | `/api/history` | List divination history |
| GET | `/api/history/export` | Export history as JSON |
| POST | `/api/history/{id}/favorite` | Toggle favorite status |
| GET | `/api/history/share/{token}` | Access shared record |
| POST | `/api/interpret/{token}` | AI interpretation |
| GET | `/api/limits/ai` | AI usage status |
| POST | `/api/sync/create` | Create sync code |
| GET | `/api/sync/{code}` | Download by sync code |
| GET | `/api/health` | Health check |

---

## Divination 占卜

### POST /api/divine/coin

**Three-coin method**: Simulates 6 tosses of 3 coins. Each coin: heads=3, tails=2. Sum per toss: 6 (old yin), 7 (young yang), 8 (young yin), 9 (old yang).

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `seed` | int | No | Random seed for reproducible results |
| `values` | string | No | Comma-separated 6 values (6-9), bypasses random generation |

**Example**:

```bash
curl -X POST "http://localhost:8088/api/divine/coin" \
  -H "Cookie: iching_cid=<your-cookie>"
```

```bash
# With custom values (client-side toss)
curl -X POST "http://localhost:8088/api/divine/coin?values=7,8,6,9,7,8" \
  -H "Cookie: iching_cid=<your-cookie>"
```

**Response** (truncated for readability):

```json
{
  "id": 42,
  "created_at": "2026-06-22T10:30:00",
  "method": "coin",
  "original_binary": "101001",
  "original_values": [7, 8, 6, 9, 7, 8],
  "original_number": 13,
  "original_name_cn": "同人",
  "original_name_pinyin": "Tong Ren",
  "original_unicode": "䷌",
  "original_judgment": "同人于野，亨。利涉大川，利君子贞。",
  "changing_positions": [3, 4],
  "changing_count": 2,
  "changed_binary": "100001",
  "changed_number": 5,
  "changed_name_cn": "需",
  "changed_name_pinyin": "Xu",
  "changed_unicode": "䷄",
  "changed_judgment": "需，有孚，光亨，贞吉。利涉大川。",
  "interpretation": {
    "primary_source": "本卦爻辞",
    "primary_description": "以本卦九三、九四爻辞为主 ...",
    "primary_lines": [3, 4],
    "secondary_sources": ["变卦卦辞"],
    "secondary_lines": [],
    "changing_count": 2,
    "changing_positions": [3, 4]
  },
  "mutual_hexagram": { "number": 38, "name_cn": "睽", "unicode": "䷥", ... },
  "opposite_hexagram": { "number": 6, "name_cn": "讼", "unicode": "䷅", ... },
  "reverse_hexagram": { "number": 33, "name_cn": "遯", "unicode": "䷠", ... },
  "body_use": {
    "body_trigram": { "name_cn": "离", "element": "火" },
    "use_trigram": { "name_cn": "乾", "element": "金" },
    "relationship": "用克体",
    "meaning": "凶 — 外部因素克制自身"
  },
  "lines": [
    { "position": 1, "name": "初九", "text": "...", "xiang": "...", "changing": false, "is_yang": true, "value": 7 },
    { "position": 2, "name": "六二", "text": "...", "xiang": "...", "changing": false, "is_yang": false, "value": 8 },
    { "position": 3, "name": "九三", "text": "...", "xiang": "...", "changing": true, "is_yang": true, "value": 6 },
    { "position": 4, "name": "九四", "text": "...", "xiang": "...", "changing": true, "is_yang": true, "value": 9 },
    { "position": 5, "name": "九五", "text": "...", "xiang": "...", "changing": false, "is_yang": true, "value": 7 },
    { "position": 6, "name": "上九", "text": "...", "xiang": "...", "changing": false, "is_yang": true, "value": 8 }
  ]
}
```

**Response schema**: `DivinationResponse` (`app/models/schemas.py:77-123`)

---

### POST /api/divine/yarrow

**Yarrow stalk method (大衍筮法)**: Traditional 50-stalk divination simulation. Uses random partitioning to derive each line value.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `seed` | int | No | Random seed for reproducible results |

**Example**:

```bash
curl -X POST "http://localhost:8088/api/divine/yarrow" \
  -H "Cookie: iching_cid=<your-cookie>"
```

**Response**: Same schema as `/api/divine/coin` with `"method": "yarrow"`.

---

### POST /api/divine/time

**Time-based divination (时间卦)**: Derives the hexagram from the current date and time. No input parameters needed.

**Example**:

```bash
curl -X POST "http://localhost:8088/api/divine/time" \
  -H "Cookie: iching_cid=<your-cookie>"
```

**Response**: Same schema with `"method": "time"`.

---

### POST /api/divine/number

**Number-based divination (数字卦)**: User provides three positive integers. The first determines the upper trigram, the second the lower trigram, the third the changing line.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `n1` | int | Yes | First number → upper trigram (≥1) |
| `n2` | int | Yes | Second number → lower trigram (≥1) |
| `n3` | int | Yes | Third number → changing line (≥1) |

**Example**:

```bash
curl -X POST "http://localhost:8088/api/divine/number?n1=3&n2=7&n3=5" \
  -H "Cookie: iching_cid=<your-cookie>"
```

**Response**: Same schema with `"method": "number"`.

---

### POST /api/divine/plum-blossom

**Plum blossom divination (梅花易数)**: User specifies the upper and lower trigram names, optionally with a changing line position.

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `upper_trigram` | string | Yes | Upper trigram name: 乾/兑/离/震/巽/坎/艮/坤 |
| `lower_trigram` | string | Yes | Lower trigram name |
| `changing_line` | int | No | Changing line position 1-6 (optional) |

**Example**:

```bash
curl -X POST "http://localhost:8088/api/divine/plum-blossom" \
  -d "upper_trigram=乾&lower_trigram=坤&changing_line=3" \
  -H "Cookie: iching_cid=<your-cookie>"
```

**Response**: Same schema with `"method": "plum-blossom"`.

---

## Hexagrams 卦象

### GET /api/hexagrams

**List all 64 hexagrams** with summary information.

**Example**:

```bash
curl http://localhost:8088/api/hexagrams
```

**Response**:

```json
{
  "total": 64,
  "hexagrams": [
    {
      "number": 1,
      "binary": "111111",
      "name_cn": "乾",
      "name_pinyin": "Qian",
      "name_en": "The Creative",
      "unicode": "䷀",
      "upper_trigram_name": "乾",
      "lower_trigram_name": "乾",
      "judgment_brief": "乾，元亨利贞。"
    },
    ...
  ]
}
```

**Source**: `app/routes/api.py:219-240`

---

### GET /api/hexagrams/{number}

**Get full hexagram detail** including all line texts, tuan zhuan, and xiang zhuan.

**Parameters**:

| Param | Type | Constraints |
|-------|------|-------------|
| `number` | path int | 1-64 (King Wen order) |

**Example**:

```bash
curl http://localhost:8088/api/hexagrams/1
```

**Response**:

```json
{
  "number": 1,
  "binary": "111111",
  "name": { "cn": "乾", "pinyin": "Qian", "en": "The Creative" },
  "unicode": "䷀",
  "upper_trigram": "111",
  "lower_trigram": "111",
  "judgment": { "cn": "乾，元亨利贞。", ... },
  "tuan": { "cn": "大哉乾元，万物资始，乃统天。", ... },
  "xiang": { "cn": "天行健，君子以自强不息。", ... },
  "lines": [
    { "position": 1, "name": "初九", "text": { "cn": "潜龙勿用。" }, "xiang": { "cn": "潜龙勿用，阳在下也。" } },
    { "position": 2, "name": "九二", "text": { "cn": "见龙在田，利见大人。" }, "xiang": { "cn": "见龙在田，德施普也。" } },
    ...
    { "position": 6, "name": "上九", "text": { "cn": "亢龙有悔。" }, "xiang": { "cn": "亢龙有悔，盈不可久也。" } }
  ],
  "extra_lines": [
    { "position": null, "name": "用九", "text": { "cn": "见群龙无首，吉。" }, "xiang": { "cn": "用九，天德不可为首也。" } }
  ],
  "upper_trigram_detail": { "binary": "111", "name_cn": "乾", "nature": "天", "element": "金", "unicode": "☰" },
  "lower_trigram_detail": { "binary": "111", "name_cn": "乾", "nature": "天", "element": "金", "unicode": "☰" }
}
```

**Source**: `app/routes/api.py:263-286`

---

### GET /api/hexagrams/search

**Search hexagrams** by name, judgment text, or line text (Chinese characters supported).

**Parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `q` | query string | Yes | Search keyword (min 1 char) |

**Example**:

```bash
curl "http://localhost:8088/api/hexagrams/search?q=龙"
```

**Response**:

```json
{
  "total": 2,
  "query": "龙",
  "hexagrams": [
    { "number": 1, "binary": "111111", "name_cn": "乾", ... },
    { "number": 5, "binary": "010001", "name_cn": "需", ... }
  ]
}
```

**Source**: `app/routes/api.py:243-260`

---

### GET /api/trigrams

**List all 8 trigrams** (八卦) with their attributes.

**Example**:

```bash
curl http://localhost:8088/api/trigrams
```

**Response**:

```json
{
  "total": 8,
  "trigrams": [
    { "binary": "111", "name_cn": "乾", "nature": "天", "element": "金", "unicode": "☰" },
    { "binary": "110", "name_cn": "兑", "nature": "泽", "element": "金", "unicode": "☱" },
    ...
    { "binary": "000", "name_cn": "坤", "nature": "地", "element": "土", "unicode": "☷" }
  ]
}
```

---

## History 历史记录

### GET /api/history

**List divination history** for the current client (filtered by `client_id` cookie).

**Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (≥1) |
| `per_page` | int | 20 | Items per page (1-100) |
| `favorite_only` | bool | false | Show only bookmarked records |

**Example**:

```bash
curl -H "Cookie: iching_cid=<your-cookie>" \
  "http://localhost:8088/api/history?page=1&per_page=5"
```

**Response**:

```json
{
  "total": 42,
  "page": 1,
  "per_page": 5,
  "total_pages": 9,
  "items": [
    {
      "id": 42,
      "created_at": "2026-06-22T10:30:00",
      "method": "coin",
      "original_binary": "101001",
      "original_name_cn": "同人",
      "original_unicode": "䷌",
      "changing_positions": [3, 4],
      "changed_binary": "100001",
      "changed_name_cn": "需",
      "notes": null,
      "is_favorite": false
    },
    ...
  ]
}
```

Note: The `question` field is **not included** in the API history response.

**Source**: `app/routes/api.py:299-362`

---

### GET /api/history/export

**Export all history** as JSON for the current client.

**Example**:

```bash
curl -H "Cookie: iching_cid=<your-cookie>" \
  "http://localhost:8088/api/history/export"
```

**Response**:

```json
{
  "total": 42,
  "exported_at": "2026-06-22T10:30:00",
  "items": [
    {
      "id": 42,
      "created_at": "2026-06-22T10:30:00",
      "method": "coin",
      "original_binary": "101001",
      "original_values": [7, 8, 6, 9, 7, 8],
      "original_name_cn": "同人",
      "original_unicode": "䷌",
      "changing_positions": [3, 4],
      "changed_binary": "100001",
      "changed_name_cn": "需",
      "is_favorite": false,
      "notes": null,
      "share_token": "a1b2c3d4-..."
    },
    ...
  ]
}
```

**Source**: `app/routes/api.py:365-404`

---

### POST /api/history/{record_id}/favorite

**Toggle favorite** status for a record.

**Parameters**:

| Param | Type | Constraints |
|-------|------|-------------|
| `record_id` | path int | Must belong to current client_id |

**Example**:

```bash
curl -X POST \
  -H "Cookie: iching_cid=<your-cookie>" \
  "http://localhost:8088/api/history/42/favorite"
```

**Response**:

```json
{
  "id": 42,
  "is_favorite": true
}
```

**Source**: `app/routes/api.py:407-436`

---

### GET /api/history/share/{token}

**Access a shared divination record** by UUID token. No `client_id` required — public by design.

**Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `token` | path string | UUID share_token |

**Example**:

```bash
curl "http://localhost:8088/api/history/share/a1b2c3d4-1234-5678-9abc-def012345678"
```

**Response**: Same full `DivinationResponse` schema without `question` or `ai_interpretation`.

**Source**: `app/routes/api.py:439-472`

---

## AI Interpretation AI 解卦

### POST /api/interpret/{token}

**Request AI interpretation** for a stored divination result. Uses the configured LLM (DeepSeek / Anthropic) to generate a comprehensive reading.

**Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `token` | path string | Share token of the divination record |

**Rate limited**: Global 10,000/day (in-memory, per-worker). Check current usage via `GET /api/limits/ai`.

**Example**:

```bash
curl -X POST \
  "http://localhost:8088/api/interpret/a1b2c3d4-1234-5678-9abc-def012345678"
```

**Response**:

```json
{
  "token": "a1b2c3d4-1234-5678-9abc-def012345678",
  "interpretation": "## 卦象解读\n\n### 本卦：䷌ 同人\n**同人于野，亨。利涉大川，利君子贞。**\n\n此卦象征团结与共鸣...\n\n### 变爻分析\n九三爻动：伏戎于莽，升其高陵，三岁不兴...\n\n### 体用生克\n离火（体）生乾金（用）...\n\n### 综合建议\n当前局势需要您...\n\n---\n*AI 解卦由 DeepSeek 大模型生成，仅供参考。*"
}
```

The interpretation is cached for **30 minutes** (TTL: 1800s). Subsequent requests within the window return the cached result instantly.

**Source**: `app/routes/api.py:477-557`

---

### GET /api/limits/ai

**Check current AI usage** for today.

**Example**:

```bash
curl "http://localhost:8088/api/limits/ai"
```

**Response**:

```json
{
  "total_used": 152,
  "total_limit": 10000,
  "your_count": 3
}
```

| Field | Description |
|-------|-------------|
| `total_used` | Global AI interpretations used today (per-worker) |
| `total_limit` | Daily global limit (configurable via `DAILY_AI_LIMIT`) |
| `your_count` | Count for the requesting IP address |

**Source**: `app/routes/api.py:560-565`, `app/limits.py:58-69`

---

## Sync 跨设备同步

### POST /api/sync/create

**Create a sync code** for cross-device data transfer. Uploads records from the current device and returns an 8-character code (`[a-z]{4}[0-9]{4}`).

**Rate limit**: 10 requests per hour per IP.

**Example**:

```bash
curl -X POST \
  -H "Cookie: iching_cid=<your-cookie>" \
  -H "Content-Type: application/json" \
  -d '{"records": [{"id": 1, "method": "coin", ...}]}' \
  "http://localhost:8088/api/sync/create"
```

**Response**:

```json
{
  "code": "kfyr3847",
  "expires_at": "2026-06-23T10:30:00Z"
}
```

| Field | Description |
|-------|-------------|
| `code` | 8-char alphanumeric sync code (4 letters + 4 digits) |
| `expires_at` | ISO 8601 timestamp of expiry (default: 24h TTL) |

**Limits**:
- Max 1000 records per upload (`api.py:624-626`)
- Max 3 downloads before auto-delete (`api.py:700-703`)
- TTL: 24 hours (configurable via `SYNC_CODE_TTL`)

**Source**: `app/routes/api.py:605-661`

---

### GET /api/sync/{code}

**Download records** using a sync code. The code is consumed after 3 accesses.

**Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `code` | path string | 8-char sync code (`[a-z]{4}[0-9]{4}`) |

**Rate limit**: 10 requests per hour per IP (shared with create endpoint).

**Example**:

```bash
curl "http://localhost:8088/api/sync/kfyr3847"
```

**Response**:

```json
{
  "code": "kfyr3847",
  "records": [
    { "id": 1, "method": "coin", ... }
  ],
  "expires_at": "2026-06-23T10:30:00Z"
}
```

**Source**: `app/routes/api.py:664-713`

---

## Health 健康检查

### GET /api/health

**Simple health check** endpoint. Returns a 200 OK with basic app info. Not rate-limited (serves as a liveness probe).

**Example**:

```bash
curl http://localhost:8088/api/health
```

**Response**:

```json
{
  "status": "ok",
  "app": "八卦 - I Ching Divination"
}
```

**Source**: `app/routes/api.py:44-47`

---

## Error Responses 错误响应格式

All endpoints return consistent error responses:

### 400 Bad Request

```json
{
  "detail": "无效的起卦数据，请检查 values 参数。"
}
```

### 404 Not Found

```json
{
  "detail": "未找到第 99 卦"
}
```

### 429 Rate Limited

```json
{
  "error": "请求过于频繁，请稍后重试",
  "code": "RATE_LIMITED"
}
```

Headers: `Retry-After: 300`, `X-RateLimit-Remaining: 0`

### 500 Server Error

```json
{
  "detail": "占卜失败，请稍后重试。"
}
```

---

## Notes 注意事项

1. **client_id cookie**: The `iching_cid` cookie is required for all history-related endpoints. It is auto-generated on first visit. Without it, history endpoints return empty results.

2. **No question in API**: The API divination endpoints do not store the user's `question` field. Only HTML form submissions (`POST /divine/*`) store `question` in the database.

3. **AI interpretation caches**: Each `POST /api/interpret/{token}` caches the result for 30 minutes. Re-interpreting the same record within that window returns the cached text.

4. **Sync codes are single-use**: After 3 downloads or 24 hours, sync codes are deleted. Data must be downloaded before expiry.

5. **Rate limits are per-worker**: The in-memory rate limiter is local to each uvicorn worker. In multi-worker deployments, effective limits scale with worker count.
