# 八卦 — I Ching Divination

一套基于 Web 的易经占卜系统，支持 5 种起卦方法，可选 AI 智能解卦。

## 功能

- **5 种起卦方法**：金钱卦、蓍草法（大衍筮法）、时间卦、数字卦、梅花易数
- **AI 智能解卦**：接入 DeepSeek / Anthropic 兼容 API，自动综合卦辞爻辞、变卦互卦、体用生克进行分析
- **完整卦象分析**：本卦、变卦、互卦、错卦、综卦 + 体用生克五行分析 + 朱熹变爻解卦规则
- **64 卦参考数据**：收录卦辞、爻辞、彖传、象传、小象传全文
- **历史记录**：本地 SQLite 存储，支持收藏、分享、回看
- **REST API**：完整 JSON API，支持第三方集成
- **主题切换**：中国传统配色的浅色/暗色主题

## 快速开始

### 环境要求
- Python 3.10+

### 安装

```bash
git clone <repo-url>
cd 8gua
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 DeepSeek API Key（可选，不填则使用规则回退解卦）
```

### 启动

```bash
# Windows — 双击 start.bat
start.bat

# macOS / Linux
./start.sh

# 或手动启动
python run.py
```

默认端口 21882，打开浏览器访问 `http://localhost:21882`

## 配置参考

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `ANTHROPIC_API_KEY` | (空) | DeepSeek / Anthropic API Key |
| `ANTHROPIC_BASE_URL` | `https://api.deepseek.com/anthropic` | API 地址 |
| `ANTHROPIC_MODEL` | `deepseek-v4-pro` | 模型名称 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 缓存（可选） |
| `REDIS_TTL` | `3600` | 缓存过期时间（秒） |
| `HOST` | `127.0.0.1` | 监听地址 |
| `PORT` | `21882` | 监听端口 |
| `DEBUG` | `true` | 调试模式 |

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/divine/coin` | POST | 金钱卦占卜 |
| `/api/divine/yarrow` | POST | 蓍草法占卜 |
| `/api/divine/time` | POST | 时间卦占卜 |
| `/api/divine/number` | POST | 数字卦占卜 |
| `/api/divine/plum-blossom` | POST | 梅花易数占卜 |
| `/api/hexagrams` | GET | 64 卦列表 |
| `/api/hexagrams/{number}` | GET | 单卦详情 |
| `/api/hexagrams/search?q=` | GET | 搜索卦象 |
| `/api/history` | GET | 历史记录 |
| `/api/history/export` | GET | 导出历史 JSON |
| `/api/interpret/{token}` | POST | AI 解卦 |

## 技术栈

- **后端**：FastAPI + SQLAlchemy + SQLite + Redis（可选）
- **前端**：Jinja2 + Alpine.js + CSS 动画
- **AI**：Anthropic SDK → DeepSeek API

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
