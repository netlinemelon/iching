# 八卦 · I Ching Divination

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/status-active-success" alt="Status">
</p>

一套融合传统易经占卜与现代 AI 智能解卦的 Web 应用。支持 5 种起卦方法，内置 64 卦完整原文数据，可接入 DeepSeek / Anthropic 大模型进行个性化解读。

> A modern web-based I Ching divination tool. 5 casting methods, full classic text reference, AI-powered interpretation via DeepSeek LLM.

## 📸 预览

<p align="center">
  <img src="docs/screenshots/home.png" alt="首页" width="32%">
  <img src="docs/screenshots/hexagram_grid.png" alt="六十四卦" width="32%">
  <img src="docs/screenshots/ai_result.png" alt="AI解卦" width="32%">
  <br><sub>首页 · 六十四卦网格 · AI 智能解卦</sub>
</p>

## ✨ 功能

- **5 种起卦方法**：金钱卦、蓍草法（大衍筮法）、时间卦、数字卦、梅花易数
- **AI 智能解卦**：接入 DeepSeek / Anthropic 兼容 API，综合卦辞爻辞、变卦互卦、体用生克进行全面分析
- **完整卦象分析**：本卦 → 变卦 → 互卦 → 错卦 → 综卦 + 体用生克五行分析
- **朱熹解卦规则**：0-6 变爻全覆盖，含乾坤用九用六特殊处理
- **64 卦参考库**：卦辞、爻辞、彖传、大象传、小象传全文收录
- **隐私优先**：占卜历史存储在浏览器本地 (localStorage)，服务器仅处理占卜引擎和 AI 解卦，不保留个人记录
- **REST API**：完整 JSON 接口，可对接第三方
- **深色主题**：中国传统配色 + 暗色模式切换
- **调试系统**：编号调试日志 `[Dxxx]`，精确定位问题

## 🚀 快速开始

```bash
git clone https://github.com/netlinemelon/iching.git
cd iching
pip install -r requirements.txt
cp .env.example .env          # 编辑 .env 填入 API Key（可选）
python run.py                  # 默认 http://localhost:8088
```

Windows 用户可直接双击 `start.bat`。

## ⚙️ 配置

`.env` 文件（不填 API Key 则使用规则回退解卦）：

```ini
ANTHROPIC_API_KEY=sk-your-key       # DeepSeek API Key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-pro
HOST=127.0.0.1
PORT=8088
DEBUG=true
```

## 📡 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/divine/coin` | POST | 金钱卦 |
| `/api/divine/yarrow` | POST | 蓍草法 |
| `/api/divine/time` | POST | 时间卦 |
| `/api/divine/number` | POST | 数字卦 |
| `/api/divine/plum-blossom` | POST | 梅花易数 |
| `/api/hexagrams` | GET | 六十四卦列表 |
| `/api/hexagrams/{1-64}` | GET | 单卦详情 |
| `/api/hexagrams/search?q=` | GET | 搜索卦象 |
| `/api/history` | GET | 历史记录 |
| `/api/history/export` | GET | 导出 JSON |
| `/api/interpret/{token}` | POST | AI 解卦 |

## 🏗️ 技术栈

| 层 | 技术 |
|----|------|
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 前端 | Jinja2 + Alpine.js + CSS Animations |
| 缓存 | Redis（可选，自动降级） |
| AI | Anthropic SDK → DeepSeek API |

## 🔒 Security & Privacy 安全与隐私

- **Anonymous client_id system**: 256-bit random ID assigned via HttpOnly cookie (`iching_cid`), auto-generated on first visit, no registration required
- **Data isolation**: All server-side queries are filtered by `client_id` — each user can only see their own records
- **No question storage**: The API divination endpoints (`POST /api/divine/*`) do **not** accept or store the user's `question` field. HTML form submissions store it only when configured
- **Share tokens**: `GET /api/history/share/{token}` uses a UUID-based share token to expose a single record publicly (hexagram data only, no `question`)
- **IP rate limiting**: 120 req/min/IP sliding window + burst detection (10 req/s) + 300s automatic ban (`app/limits.py:89-125`)
- **AI daily limit**: Global 10,000 interpretations/day default, enforced per-worker (`app/limits.py:17-55`)
- **Circuit breaker**: Middleware checks every non-static request against the rate limiter (`app/main.py:127-143`)
- **No AI interpretation in API**: The API divination response (`DivinationResponse` schema) does **not** contain `ai_interpretation` — that data is only returned from `POST /api/interpret/{token}`
- **Cookie security**: `HttpOnly` + `SameSite=Lax` + `Secure` in production (`app/main.py:114-119`)

## 🏗️ Architecture 系统架构

### Middleware Stack 中间件栈

All HTTP requests (except `/static/`) pass through two middleware layers in order:

```
Request → client_id_middleware → circuit_breaker_middleware → Route Handler → Response
              │                          │
              ├─ Assigns/reads           ├─ Checks IP rate limit
              │  iching_cid cookie       ├─ Returns 429 if exceeded
              │  (256-bit random)        └─ Adds X-RateLimit-Remaining header
              └─ Sets request.state.client_id
```

### Data Flow 数据流

```
Browser Form          FastAPI              Hexagram Engine            JSON Response
   │                     │                      │                        │
   ├─ POST /divine/coin ─┤                      │                        │
   │  (or yarrow/time/   ├─ cast_*_hexagram() ──┤                        │
   │   number/plum)      │                      ├─ Hexagram.from_values() │
   │                     │                      ├─ changed_hexagram()    │
   │                     │                      ├─ build_divination_     │
   │                     │                      │   result()              │
   │                     │                      └─ interpretation rules  │
   │                     ├── save to DB ────────┤                        │
   │                     ├── cache to Redis     │                        │
   │                     └── return JSON ───────┘────────────────────────┤
   │                                                                     │
   ├── Browser saves to localStorage ←───────────────────────────────────┘
   │   (IChingStorage.saveResult)
```

### Cookie Flow 身份标识流

```
First Visit:
  Browser ──GET /──→ Server
                     ├─ No iching_cid cookie
                     ├─ Generate: secrets.token_urlsafe(32)  → 256-bit
                     ├─ Set cookie: HttpOnly, Secure, SameSite=Lax
                     └─ Attach to request.state.client_id
  Browser ←──Set-Cookie── Server

Subsequent Requests:
  Browser ──GET/POST /──→ Server
  Cookie: iching_cid=<token>
                           ├─ Read cookie
                           ├─ Attach to request.state.client_id
                           └─ All DB queries filter by client_id
```

## ⚙️ Configuration 全部配置选项

| 变量 | 说明 | 默认值 | 文件 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | AI API 密钥 (DeepSeek / Anthropic) | `""` | `config.py:19` |
| `ANTHROPIC_BASE_URL` | API 端点 URL | `https://api.deepseek.com/anthropic` | `config.py:20` |
| `ANTHROPIC_MODEL` | 模型名称 | `deepseek-v4-pro` | `config.py:21` |
| `REDIS_URL` | Redis 连接字符串 (可选，自动降级) | `redis://localhost:6379/0` | `config.py:13` |
| `REDIS_TTL` | Redis 缓存过期时间 (秒) | `3600` | `config.py:14` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite+aiosqlite:///./data/iching.db` | `config.py:8` |
| `DEBUG` | 调试模式 (SQL echo + auto-reload) | `true` | `config.py:7` |
| `HOST` | 监听地址 | `127.0.0.1` | `config.py:29` |
| `PORT` | 监听端口 | `8088` | `config.py:30` |
| `DAILY_AI_LIMIT` | 每日全球 AI 解卦上限 | `10000` | `config.py:24` |
| `SYNC_CODE_TTL` | 同步码有效期 (秒) | `86400` (24h) | `config.py:26` |

所有配置项通过 `.env` 文件或环境变量注入，详见 `.env.example`。

## 📁 项目结构

```
iching/
├── app/
│   ├── engine/          # 起卦算法 + 卦象变换 + 解卦规则 (pure, no side effects)
│   ├── routes/          # 页面路由 + REST API (FastAPI APIRouter)
│   ├── models/          # ORM 模型 + Pydantic schemas
│   ├── templates/       # Jinja2 模板
│   ├── static/          # CSS + JS + 图片
│   ├── main.py          # FastAPI app 创建 + 中间件 + 启动生命周期
│   ├── limits.py        # IP 速率限制 + 熔断器 (in-memory)
│   ├── config.py        # Pydantic Settings (环境变量)
│   ├── database.py      # SQLAlchemy 异步引擎
│   ├── cache.py         # Redis 缓存 (可选，自动降级)
│   └── debug.py         # 编号调试日志系统 [Dxxx]
├── data/
│   ├── hexagrams.json   # 64卦完整数据
│   └── trigrams.json    # 八卦基础数据
├── deploy/              # 部署配置 (nginx, systemd)
├── docs/                # 文档
│   ├── ARCHITECTURE.md  # 系统架构
│   ├── API.md           # API 参考
│   ├── SECURITY.md      # 安全设计
│   └── DEVELOPMENT.md   # 开发指南
├── run.py               # 一键启动入口
├── start.bat            # Windows 启动脚本
├── start.sh             # Linux/Mac 启动脚本
└── .env.example         # 配置模板
```

## 🤝 贡献

欢迎 PR。功能规划中：

- [ ] 生辰八字排盘
- [ ] 称骨算命
- [ ] 小六壬
- [ ] 五行缺失分析
- [ ] 每日运势
- [ ] 六爻纳甲排盘

## 📄 协议

MIT License — 详见 [LICENSE](LICENSE)
