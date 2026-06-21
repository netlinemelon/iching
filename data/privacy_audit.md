# 隐私审计报告：八卦 I Ching 数据泄露向量分析

审计日期：2026-06-21
审计范围：所有 HTTP 端点、数据库存储、缓存层、同步机制
审计目标：找出所有可能泄露用户 `question`（所问之事）和 `ai_interpretation`（AI 解卦结果）的路径

---

## 背景

此应用存在双重存储架构：
- **浏览器 localStorage**（前端 `storage.js`）：预期的主要存储方式，用户可控制
- **服务端 SQLite**（`data/iching.db`）：通过 `DivinationRecord` 表持久化所有数据

HTML 表单占卜（`divine.py`）会存储用户提交的 `question` 字段。
API 占卜（`api.py`）不存储 `question` 字段。
AI 解卦（`POST /api/interpret/{token}`）会将结果写入 `ai_interpretation` 列。

---

## 第一章：全部泄露向量

### LEAK-1: `GET /api/history/export` — 导出全部记录（含 question）【CRITICAL】

- **文件**: `D:\Project\python\8gua\app\routes\api.py` 第 349-386 行
- **路径**: `GET /api/history/export`
- **暴露数据**: 所有字段包括 `question`、`share_token`、`original_values`
- **认证**: 无。完全公开。
- **描述**: 该端点返回数据库中全部 `DivinationRecord` 记录，且显式包含了 `rec.question`（第 368 行）。没有 `response_model` 过滤，原始 dict 被直接返回。任何知道此路径的人都能下载全部用户的占卜问题。
- **响应体样例**:
  ```json
  {"total": 100, "items": [{"id": 1, "question": "我今年能换工作吗？", "share_token": "uuid-...", ...}]}
  ```

### LEAK-2: `GET /history/{record_id}` — 详细历史页面（含 question 和 ai_interpretation）【CRITICAL】

- **文件**: `D:\Project\python\8gua\app\routes\history.py` 第 135-174 行
- **路径**: `GET /history/{record_id}`
- **暴露数据**: `question`（第 165 行）、`ai_interpretation`（第 166 行）
- **认证**: 无。通过自增整数 ID 即可访问。
- **描述**: 此 HTML 页面不仅渲染了 `record.question` 和 `record.ai_interpretation`，模板 `history/detail.html` 第 339 行还有一个内联脚本：
  ```html
  <script>
  var saveData = {{ record | tojson | safe }};
  IChingStorage.saveResult(saveData);
  ```
  这会将整个 `record` 对象（包含全部 DB 字段）序列化到 HTML 源码中。由于 `id` 是自增整数（`DivinationRecord.id = Column(Integer, primary_key=True, autoincrement=True)`），任何人都可以枚举 `id=1,2,3...` 来读取所有用户的问题和 AI 解读。

### LEAK-3: `POST /api/interpret/{token}` — AI 解卦端点【HIGH】

- **文件**: `D:\Project\python\8gua\app\routes\api.py` 第 455-531 行
- **路径**: `POST /api/interpret/{token}`
- **暴露数据**: 读取 `record.question`（第 492 行），写入 `record.ai_interpretation`（第 525 行）
- **认证**: 仅 IP 速率限制（`can_use_ai`），无用户认证。
- **描述**: 任何人只要有一个有效的 `share_token`，就可以：
  1. 触发 AI 解卦（消耗日限额）
  2. 获取 AI 解读文本
  3. 该解读会被持久化到数据库
  4. 30 分钟内重复请求直接返回缓存的解读结果

### LEAK-4: `GET /history/share/{token}` — 分享页面暴露 question【HIGH】

- **文件**: `D:\Project\python\8gua\app\routes\history.py` 第 218-254 行
- **路径**: `GET /history/share/{token}`
- **暴露数据**: `question`（第 246 行）
- **认证**: 无。只需有效的 UUID share_token。
- **描述**: 分享页面完整渲染了用户的 question。Token 虽然是 UUID（不易猜测），但一旦通过 LEAK-1（导出）或其他渠道泄露，即可关联到具体用户的问题。另外，此页面未暴露 `ai_interpretation`（`record_data.update` 中未包含此字段）。

### LEAK-5: `POST /api/sync/create` — 同步上传存储全部数据【HIGH】

- **文件**: `D:\Project\python\8gua\app\routes\api.py` 第 579-634 行
- **路径**: `POST /api/sync/create`
- **暴露数据**: 客户端上传的全部记录，包含 `question` 和 `ai_interpretation`
- **认证**: 仅 IP 速率限制（每 IP 每小时 10 次）。
- **描述**: 前端 `sync.js` 从 localStorage 读取全部记录（含 question 和 ai_interpretation），通过 POST 请求发送到服务器。服务器将其 JSON 序列化后存入 `SyncCode` 表（`records` 字段）。数据保留 24 小时或最多访问 3 次后删除。

### LEAK-6: `GET /api/sync/{code}` — 同步下载返回全部数据【HIGH】

- **文件**: `D:\Project\python\8gua\app\routes\api.py` 第 637-686 行
- **路径**: `GET /api/sync/{code}`
- **暴露数据**: 完整的记录数据，包括 `question` 和 `ai_interpretation`
- **认证**: 仅 8 位码 + IP 速率限制。
- **描述**: 同步码格式为 `[a-z]{4}[0-9]{4}`，任何人都可以输入此码获取对应数据。虽然有速率限制（每 IP 每小时 10 次）和 3 次访问上限，但数据本身在传输中无额外保护。

### LEAK-7: `SQLite 数据库文件无加密存储 — 全部静态数据泄露【CRITICAL】

- **文件**: `D:\Project\python\8gua\data\iching.db`
- **路径**: 本地文件系统
- **暴露数据**: `DivinationRecord` 表全部字段，包括 `question`（第 27 行）和 `ai_interpretation`（第 28 行）
- **认证**: 文件系统权限
- **描述**: `app/models/divination_record.py` 第 27-28 行定义了两个明文文本列：
  ```python
  question = Column(Text, nullable=True, default="")
  ai_interpretation = Column(Text, nullable=True)
  ```
  数据库文件位于 `data/iching.db`（配置见 `app/config.py` 第 8 行：`database_url: str = "sqlite+aiosqlite:///./data/iching.db"`）。Nginx 配置未暴露 `/data/` 路径，但如果服务器被入侵，数据库文件可被完整下载。

### LEAK-8: `Redis 缓存存在用户问题数据【HIGH】**

- **文件**: `D:\Project\python\8gua\app\routes\divine.py` 第 177 行
- **路径**: Redis 内存数据库
- **暴露数据**: 完整的占卜结果字典，包含 `question`
- **认证**: Redis 默认无认证（连接 `redis://localhost:6379/0`）
- **描述**: HTML 占卜结果被缓存到 Redis，键为 `share_token`，值为包含 `question` 的完整结果字典（第 177 行：`result["question"] = question or ""`）。`cache.py` 第 14 行配置了 `redis_url`，TTL 为 3600 秒（`config.py` 第 14 行）。如果 Redis 端口暴露或未设置密码，数据可被读取。

### LEAK-9: `POST /api/history/{record_id}/favorite` — 无权限收藏操作【MEDIUM】

- **文件**: `D:\Project\python\8gua\app\routes\api.py` 第 389-414 行
- **路径**: `POST /api/history/{record_id}/favorite`
- **暴露数据**: 不直接泄露隐私数据，但允许任意用户修改任意记录
- **认证**: 无
- **描述**: 任何人都可以通过自增 ID 切换任何占卜记录的收藏状态。此端点在 HTML 端也有对应实现（`POST /history/{record_id}/favorite` in `history.py` 第 177-195 行）。

### LEAK-10: `POST /history/{record_id}/delete` — 无权限删除【MEDIUM】

- **文件**: `D:\Project\python\8gua\app\routes\history.py` 第 198-215 行
- **路径**: `POST /history/{record_id}/delete`
- **暴露数据**: 不泄露，但允许任意用户删除任意记录
- **认证**: 无
- **描述**: 任何人都可以通过自增 ID 删除任何占卜记录。这是一个数据可用性问题，也属于安全漏洞。

---

## 第二章：解决方案

### 方案 A: 彻底删除服务端存储

**核心操作**:
1. 删除 `DivinationRecord` 和 `SyncCode` 表及其 ORM 模型
2. 删除 `app/routes/history.py` 中所有数据库操作
3. 删除 `app/routes/api.py` 中 `_perform_and_cache` 的数据库写入逻辑（第 63-75 行）
4. 删除 `app/routes/api.py` 中 `/api/history`, `/api/history/export`, `/api/history/share/{token}`, `/api/sync/create`, `/api/sync/{code}` 等端点
5. 删除 `app/routes/divine.py` 中的 `_save_to_db` 函数
6. 修改 `POST /api/interpret/{token}` 使其仅依赖缓存数据
7. 历史页面改为仅读取 localStorage（前端渲染或前端 API）

**优点**:
- 服务器零用户数据，攻击者即使攻入服务器也无法获取任何用户隐私
- 无需数据库备份、数据保护等合规工作
- 架构简单，隐私保护最彻底
- 通过 ICP 备案审查最有利（符合"最小化数据收集"原则）

**缺点**:
- 无跨设备历史记录同步功能
- 分享链接无法直接恢复完整卦象（需 URL 编码数据，URL 可能很长）
- 需要前端全面改造，工程量大
- 用户更换浏览器或清除数据后历史丢失

### 方案 B: 保留存储但加认证

**核心操作**:
1. 增加用户系统：JWT token 认证或 session 认证
2. 所有 `/history/` 和 `/api/history/*` 端点要求登录
3. 记录与用户关联：`DivinationRecord` 增加 `user_id` 外键
4. 所有查询增加 `WHERE user_id = current_user.id` 过滤
5. `question` 和 `ai_interpretation` 字段在数据库层加密存储（AES-256-GCM）
6. 分享令牌生成时，可选择暴露哪些字段

**优点**:
- 功能完整保留：跨设备同步、历史记录、分享
- 符合行业标准实践
- 数据加密后即使 DB 泄露也无法直接读取

**缺点**:
- 开发工作量最大：用户注册/登录、密码重置、session 管理等
- 增加用户管理复杂性（隐私政策、用户数据导出、删除请求等）
- 对于占卜类应用，要求用户注册可能影响用户体验
- Redis 缓存中的数据仍需保护

### 方案 C: 混合模式（推荐）

**核心操作**:

**立即执行（第 1 层）**:
1. 从 `GET /api/history/export` 的响应中移除 `question` 字段（`api.py` 第 368 行）
2. 从 `GET /history/{record_id}` 的上下文中移除 `question` 和 `ai_interpretation`，仅在页面中展示卦象数据，不展示用户问题与 AI 解读
3. 从 `GET /history/share/{token}` 的上下文中移除 `question` 字段
4. 在 `GET /api/history` 和 `GET /api/history/export` 增加 `response_model` 过滤，或直接删除 `/export` 端点
5. 从 `POST /api/interpret/{token}` 移除从 DB 读取 `question` 的逻辑，仅使用 hexagram 数据构建 prompt
6. 在 `result/divination_result.html` 和 `history/detail.html` 的内联脚本中，过滤 `tojson` 序列化内容，移除敏感字段

**短期执行（第 2 层）**:
7. 设置 `STORE_QUESTIONS=false` 环境变量（默认 `false`）
   - 当 `STORE_QUESTIONS=false` 时，`question` 字段不写入 DB
   - `question` 仅在内存中存在，用于 AI 解读后丢弃
8. 设置自动清理：DB 中记录超过 7 天后删除
9. 删除 `GET /api/history/export` 端点
10. 删除 `GET /api/history` API 端点（仅保留 HTML 版本）

**可推迟（第 3 层）**:
11. 移除 `DivinationRecord` 表中的 `question` 和 `ai_interpretation` 列
12. 移除 `SyncCode` 表相关功能
13. 迁移历史数据到客户端 localStorage

**优点**:
- 立即见效的修复：几分钟内可上线，阻断主要泄露路径
- 工作量小：最小的代码改动，最大的安全收益
- 保留核心功能：占卜、分享、简单历史记录
- 渐进式架构：可分阶段实施，最终过渡到方案 A

**缺点**:
- DB 中仍保留 `original_binary`、`original_values` 等 hexagram 基础数据
- 如果 DB 完全泄露，攻击者仍能看到"某个时间有人占出了某卦"，但看不到问题和解读内容
- 同步码仍存在（但数据量减少）

---

## 第三章：推荐立即执行操作

### 优先级 P0 — ICP 备案前必须修复（数据泄露风险）

#### 修复 1: 阻止 `/api/history/export` 泄露 question
**文件**: `D:\Project\python\8gua\app\routes\api.py` 第 368 行
**操作**: 删除 `"question": rec.question or "",` 这一行
**代码变更**:
```python
# 删除第 368 行
item = {
    "id": rec.id,
    "created_at": ...,
    "method": rec.method,
    # 删除下行：
    # "question": rec.question or "",
    ...
}
```

#### 修复 2: 阻止 `/history/{record_id}` 暴露 question 和 ai_interpretation
**文件**: `D:\Project\python\8gua\app\routes\history.py` 第 158-167 行
**操作**: 从 `record_data.update()` 中移除 `question` 和 `ai_interpretation`
**代码变更**:
```python
# 修改第 158-167 行，移除 question 和 ai_interpretation
record_data.update({
    "id": record.id,
    "created_at": record.created_at.isoformat() if record.created_at else "",
    "method": record.method,
    "notes": record.notes,
    "is_favorite": record.is_favorite,
    "share_token": record.share_token,
    # 删除下行：
    # "question": record.question or "",
    # "ai_interpretation": record.ai_interpretation,
})
```

#### 修复 3: 阻止 `/history/share/{token}` 暴露 question
**文件**: `D:\Project\python\8gua\app\routes\history.py` 第 242-247 行
**操作**: 从 `record_data.update()` 中移除 `question`
**代码变更**:
```python
record_data.update({
    "id": record.id,
    "created_at": record.created_at.isoformat() if record.created_at else "",
    "method": record.method,
    # 删除下行：
    # "question": record.question or "",
})
```

#### 修复 4: 阻止内联脚本序列化敏感字段
**文件**: `D:\Project\python\8gua\app\templates\result\divination_result.html` 第 489 行
**文件**: `D:\Project\python\8gua\app\templates\history\detail.html` 第 339 行
**操作**: 过滤 `tojson` 输出，移除 `question` 和 `ai_interpretation`
**代码变更**（两处模板相同）:
```html
<script>
if (window.IChingStorage) {
    (function() {
        try {
            var saveData = {{ result | tojson | safe }};
            // 清理敏感字段，仅保存到本地
            delete saveData.question;
            delete saveData.ai_interpretation;
            IChingStorage.saveResult(saveData);
        } catch (e) {
            console.warn('[IChingStorage] 保存到本地失败:', e);
        }
    })();
}
</script>
```
(但更好的做法是从 Python 后端就已经移除，见修复 2 和 3)

#### 修复 5: 阻止 AI 解读端点从 DB 读取 question
**文件**: `D:\Project\python\8gua\app\routes\api.py` 第 492 行
**操作**: 设置 `question` 为空字符串，避免从 DB 读取用户问题传递给 AI
**代码变更**:
```python
# 将第 492 行：
# result["question"] = record.question or ""
# 改为：
result["question"] = ""  # 隐私保护：不将存储的问题传递给 AI
```

### 优先级 P1 — ICP 备案后/公测前修复

#### 修复 6: 移除 `GET /api/history/export` 端点
**文件**: `D:\Project\python\8gua\app\routes\api.py` 第 349-386 行
**操作**: 删除整个 `api_export_history` 函数
**原因**: 导出功能应完全由客户端 localStorage 完成（`storage.js` 中已有 `exportJSON` 方法）

#### 修复 7: 移除 `GET /api/history` API 端点
**文件**: `D:\Project\python\8gua\app\routes\api.py` 第 286-346 行
**操作**: 删除整个 `api_list_history` 函数
**原因**: HTML 版本 `/history/` 已提供历史记录功能，API 版本增加了攻击面

#### 修复 8: 添加 `.env` 配置控制是否存储 question
**文件**: `D:\Project\python\8gua\app\config.py`
**操作**: 添加配置项
```python
class Settings(BaseSettings):
    # ...
    store_questions: bool = False  # 默认不存储用户问题
```
**文件**: `D:\Project\python\8gua\app\routes\divine.py` 第 36-59 行
**操作**: 条件写入 question
```python
record = DivinationRecord(
    method=method,
    original_binary=hexagram.binary,
    original_values=hexagram.line_values,
    changed_binary=changed.binary if changed else None,
    changing_positions=hexagram.changing_positions,
    share_token=share_token,
    question=question if settings.store_questions else "",
)
```

#### 修复 9: 添加自动清理过期记录
**文件**: `D:\Project\python\8gua\app\config.py`
**操作**:
```python
record_ttl_days: int = 7  # 记录保留天数
```
**文件**: `D:\Project\python\8gua\app\routes\api.py` 添加启动时清理任务，或每次写入前清理
```python
# 在 lifespan 或定期任务中执行
cutoff = datetime.utcnow() - timedelta(days=settings.record_ttl_days)
query = select(DivinationRecord).where(DivinationRecord.created_at < cutoff)
# ... 删除过期记录
```

#### 修复 10: 阻止 `POST /history/{record_id}/delete` 无需认证删除
**文件**: `D:\Project\python\8gua\app\routes\history.py` 第 198-215 行
**操作**: 在实现认证之前，可暂时添加 Referer 检查或 CSRF token；更彻底的方案是要求用户确认并通过 POST body 传递确认字段

### 优先级 P2 — 发布后可推迟

#### 修复 11: 移除数据库中的 `question` 和 `ai_interpretation` 列
**文件**: `D:\Project\python\8gua\app\models\divination_record.py` 第 27-28 行
**操作**: 删除这两个列定义
```python
# question = Column(Text, nullable=True, default="")       # 删除
# ai_interpretation = Column(Text, nullable=True)          # 删除
```
并创建数据库迁移脚本，移除这两个列的数据。

#### 修复 12: 数据库文件保护
**操作**: 
- 确保 `data/` 目录不在静态文件服务路径下
- 在 nginx 中添加显式拒绝规则：
```nginx
location /data/ {
    deny all;
    access_log off;
    log_not_found off;
}
```

#### 修复 13: Redis 安全加固
**操作**:
- 为 Redis 设置密码 (`requirepass`)
- 确保 Redis 监听 127.0.0.1 而非 0.0.0.0
- 在 `config.py` 的 `redis_url` 中包含密码：`redis://:password@localhost:6379/0`

---

## 修复影响评估汇总

| 修复编号 | 严重度 | 影响范围 | 工作量 | 紧急度 |
|---------|--------|---------|-------|-------|
| 修复 1 | CRITICAL | API 导出 | 1 行删除 | P0 |
| 修复 2 | CRITICAL | HTML 历史详情 | 2 行删除 | P0 |
| 修复 3 | HIGH | HTML 分享页面 | 1 行删除 | P0 |
| 修复 4 | HIGH | 模板内联脚本 | 每模板 2 行 | P0 |
| 修复 5 | HIGH | AI 解读端点 | 1 行修改 | P0 |
| 修复 6 | CRITICAL | 删除端点 | ~40 行删除 | P1 |
| 修复 7 | MEDIUM | 删除端点 | ~60 行删除 | P1 |
| 修复 8 | MEDIUM | 配置层 | 3 处修改 | P1 |
| 修复 9 | MEDIUM | 启动任务 | ~20 行 | P1 |
| 修复 10 | MEDIUM | 删除端点 | ~10 行 | P1 |
| 修复 11 | MEDIUM | ORM 模型 | 迁移脚本 | P2 |
| 修复 12 | LOW | nginx 配置 | 5 行 | P2 |
| 修复 13 | LOW | 运维配置 | 运维操作 | P2 |

---

## 总结

当前应用存在 **2 个 CRITICAL 级泄露**（无需认证即可批量读取所有用户的问题和 AI 解读）、**4 个 HIGH 级泄露**（分享/同步机制暴露隐私数据）、**2 个 MEDIUM 级泄露**（未授权数据修改/删除）。

最紧迫的修复是：
1. 立即从 `GET /api/history/export` 响应中移除 `question` 字段
2. 立即从 `GET /history/{record_id}` 的响应数据中移除 `question` 和 `ai_interpretation`
3. 立即从 `GET /history/share/{token}` 的响应数据中移除 `question`

以上 3 处修复总计约 4 行代码删除，可在 5 分钟内上线，阻断当前所有数据泄露路径。

建议最终采用 **方案 C（混合模式）**，在 1-2 周内分阶段实施，最终彻底移除服务端的 `question` 和 `ai_interpretation` 存储。
