"""
REST API 路由 — JSON API Routes

提供完整的 RESTful API，用于前端 AJAX 调用和第三方集成。
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Path, Request
from sqlalchemy import select, func

from app.database import async_session
from app.engine.core import Hexagram
from app.engine.result_builder import build_divination_result
from app.engine.coin import cast_hexagram as cast_coin_hexagram
from app.engine.yarrow import cast_yarrow_hexagram
from app.engine.time import cast_time_hexagram
from app.engine.number import cast_number_hexagram
from app.engine.plum_blossom import cast_plum_blossom_hexagram
from app.cache import cache_set
from app.config import settings
from app.models.hexagram_data import (
    get_all_hexagrams,
    get_hexagram_by_binary,
    get_hexagram_by_number,
    get_trigram_by_binary,
    load_trigrams,
    search_hexagrams,
)
from app.debug import log
from app.models.divination_record import DivinationRecord
from app.models.schemas import DivinationResponse

router = APIRouter()


# ─── 健康检查 ──────────────────────────────────────────

@router.get("/health")
async def api_health():
    """API 健康检查。"""
    return {"status": "ok", "app": "八卦 - I Ching Divination"}


# ─── 占卜 ──────────────────────────────────────────────

async def _perform_and_cache(hexagram: Hexagram, method: str = "coin") -> dict:
    """执行占卜：构建结果、保存数据库、写入缓存。"""
    log(330, f"_perform_and_cache: method={method} bin={hexagram.binary}")
    changed = None
    if hexagram.changing_count > 0:
        from app.engine.transform import changed_hexagram
        changed = changed_hexagram(hexagram)

    result = _build_api_result(hexagram, method=method)

    # 保存到数据库
    share_token = DivinationRecord.generate_share_token()
    async with async_session() as session:
        record = DivinationRecord(
            method=method,
            original_binary=hexagram.binary,
            original_values=hexagram.line_values,
            changed_binary=changed.binary if changed else None,
            changing_positions=hexagram.changing_positions,
            share_token=share_token,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

    result["id"] = record.id
    result["share_token"] = share_token
    result["created_at"] = record.created_at.isoformat() if record.created_at else ""

    # 写入缓存
    await cache_set(share_token, result, settings.redis_ttl)

    return result


@router.post("/divine/coin", response_model=DivinationResponse)
async def api_coin_divination(
    seed: Optional[int] = Query(default=None),
    values: Optional[str] = Query(default=None),
):
    """执行金钱卦占卜，返回 JSON 格式的完整结果。

    Args:
        seed: 可选随机数种子（用于测试可重现）
        values: 可选的客户端真实抛掷值（逗号分隔的6个6-9数值）

    Returns:
        完整占卜结果
    """
    if values and values.strip():
        try:
            parsed = [int(v.strip()) for v in values.split(",")]
            if len(parsed) != 6 or any(v not in (6, 7, 8, 9) for v in parsed):
                raise ValueError("Invalid values")
            hexagram = Hexagram.from_values(parsed)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的起卦数据，请检查 values 参数。")
    else:
        rng = random.Random(seed) if seed is not None else None
        try:
            hexagram = cast_coin_hexagram(rng)
        except Exception:
            raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")

    return await _perform_and_cache(hexagram, method="coin")


@router.post("/divine/yarrow", response_model=DivinationResponse)
async def api_yarrow_divination(
    seed: Optional[int] = Query(default=None),
):
    """执行蓍草法占卜。"""
    rng = random.Random(seed) if seed is not None else None
    try:
        hexagram = cast_yarrow_hexagram(rng)
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")
    return await _perform_and_cache(hexagram, method="yarrow")


@router.post("/divine/time", response_model=DivinationResponse)
async def api_time_divination():
    """执行时间卦占卜。"""
    try:
        hexagram = cast_time_hexagram()
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")
    return await _perform_and_cache(hexagram, method="time")


@router.post("/divine/number", response_model=DivinationResponse)
async def api_number_divination(
    n1: int = Query(..., ge=1, description="第一个数字（上卦）"),
    n2: int = Query(..., ge=1, description="第二个数字（下卦）"),
    n3: int = Query(..., ge=1, description="第三个数字（动爻）"),
):
    """执行数字卦占卜。"""
    try:
        hexagram = cast_number_hexagram(n1, n2, n3)
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")
    return await _perform_and_cache(hexagram, method="number")


@router.post("/divine/plum-blossom", response_model=DivinationResponse)
async def api_plum_blossom_divination(
    upper_trigram: str = Query(..., description="上卦"),
    lower_trigram: str = Query(..., description="下卦"),
    changing_line: Optional[int] = Query(default=None, description="动爻位置（可选）"),
):
    """执行梅花易数占卜。"""
    try:
        hexagram = cast_plum_blossom_hexagram(upper_trigram, lower_trigram, changing_line)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")
    return await _perform_and_cache(hexagram, method="plum-blossom")


def _build_api_result(hexagram: Hexagram, method: str = "coin") -> dict:
    """将 Hexagram 对象转换为扁平的 API 响应字典。"""
    full = build_divination_result(hexagram, method=method)
    original = full["original_hexagram"]
    changed = full["changed_hexagram"]

    return {
        "method": method,
        "original_binary": full["original_binary"],
        "original_values": full["original_values"],
        "original_number": original["number"],
        "original_name_cn": original["name"]["cn"],
        "original_name_pinyin": original["name"]["pinyin"],
        "original_unicode": original["unicode"],
        "original_judgment": original["judgment"]["cn"],
        "changing_positions": full["changing_positions"],
        "changing_count": full["changing_count"],
        "changed_binary": full["changed_binary"],
        "changed_number": changed["number"] if changed else None,
        "changed_name_cn": changed["name"]["cn"] if changed else None,
        "changed_name_pinyin": changed["name"]["pinyin"] if changed else None,
        "changed_unicode": changed["unicode"] if changed else None,
        "changed_judgment": changed["judgment"]["cn"] if changed else None,
        "interpretation": full["interpretation"],
        "mutual_hexagram": full["mutual_hexagram"],
        "opposite_hexagram": full["opposite_hexagram"],
        "reverse_hexagram": full["reverse_hexagram"],
        "body_use": full["body_use"],
        "lines": full["lines"],
    }


# ─── 卦象 ──────────────────────────────────────────────

@router.get("/hexagrams")
async def api_list_hexagrams():
    """获取所有卦象的摘要列表。"""
    hexagrams = get_all_hexagrams()
    summaries = []
    for h in hexagrams:
        upper = get_trigram_by_binary(h["upper_trigram"])
        lower = get_trigram_by_binary(h["lower_trigram"])
        judgment = h["judgment"]["cn"]
        brief = judgment.split("。")[0] + "。" if judgment else ""
        summaries.append({
            "number": h["number"],
            "binary": h["binary"],
            "name_cn": h["name"]["cn"],
            "name_pinyin": h["name"]["pinyin"],
            "name_en": h["name"]["en"],
            "unicode": h["unicode"],
            "upper_trigram_name": upper["name_cn"] if upper else h["upper_name"],
            "lower_trigram_name": lower["name_cn"] if lower else h["lower_name"],
            "judgment_brief": brief,
        })
    return {"total": len(summaries), "hexagrams": summaries}


@router.get("/hexagrams/search")
async def api_search_hexagrams(
    q: str = Query(..., min_length=1, description="搜索关键词"),
):
    """搜索卦象。

    Args:
        q: 搜索关键词（卦名、卦辞、爻辞）

    Returns:
        匹配的卦象列表
    """
    results = search_hexagrams(q.strip())
    return {
        "total": len(results),
        "query": q,
        "hexagrams": results,
    }


@router.get("/hexagrams/{number}")
async def api_get_hexagram(
    number: int = Path(..., ge=1, le=64, description="卦序 1-64"),
):
    """获取单个卦象的完整详情。

    Args:
        number: 卦序

    Returns:
        包含上下卦、爻辞、彖传、象传等的完整卦象数据
    """
    hexagram = get_hexagram_by_number(number)
    if hexagram is None:
        raise HTTPException(status_code=404, detail=f"未找到第 {number} 卦")

    upper = get_trigram_by_binary(hexagram["upper_trigram"])
    lower = get_trigram_by_binary(hexagram["lower_trigram"])

    return {
        **hexagram,
        "upper_trigram_detail": upper,
        "lower_trigram_detail": lower,
    }


# ─── 八卦 ──────────────────────────────────────────────

@router.get("/trigrams")
async def api_list_trigrams():
    """获取全部八卦信息。"""
    return {"total": 8, "trigrams": load_trigrams()}


# ─── 历史记录 ──────────────────────────────────────────

@router.get("/history")
async def api_list_history(
    page: int = Query(default=1, ge=1, description="页码"),
    per_page: int = Query(default=20, ge=1, le=100, description="每页条数"),
    favorite_only: bool = Query(default=False, description="仅显示收藏"),
):
    """获取占卜历史记录列表。

    Args:
        page: 页码（从1开始）
        per_page: 每页记录数
        favorite_only: 是否只显示收藏的记录

    Returns:
        分页的历史记录列表
    """
    async with async_session() as session:
        query = select(DivinationRecord).order_by(DivinationRecord.created_at.desc())

        if favorite_only:
            query = query.where(DivinationRecord.is_favorite == True)

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        result = await session.execute(query)
        records = result.scalars().all()

    items = []
    for rec in records:
        original_data = get_hexagram_by_binary(rec.original_binary)
        changed_data = None
        if rec.changed_binary:
            changed_data = get_hexagram_by_binary(rec.changed_binary)

        items.append({
            "id": rec.id,
            "created_at": rec.created_at.isoformat() if rec.created_at else "",
            "method": rec.method,
            "original_binary": rec.original_binary,
            "original_name_cn": original_data["name"]["cn"] if original_data else "未知",
            "original_unicode": original_data["unicode"] if original_data else "",
            "changing_positions": rec.changing_positions,
            "changed_binary": rec.changed_binary,
            "changed_name_cn": changed_data["name"]["cn"] if changed_data else None,
            "notes": rec.notes,
            "is_favorite": rec.is_favorite,
        })

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "items": items,
    }


@router.get("/history/export")
async def api_export_history():
    """导出全部占卜历史记录为 JSON。"""
    async with async_session() as session:
        query = select(DivinationRecord).order_by(DivinationRecord.created_at.desc())
        result = await session.execute(query)
        records = result.scalars().all()

    items = []
    for rec in records:
        original_data = get_hexagram_by_binary(rec.original_binary)
        changed_data = None
        if rec.changed_binary:
            changed_data = get_hexagram_by_binary(rec.changed_binary)

        item = {
            "id": rec.id,
            "created_at": rec.created_at.isoformat() if rec.created_at else "",
            "method": rec.method,
            "question": rec.question or "",
            "original_binary": rec.original_binary,
            "original_values": rec.original_values,
            "original_name_cn": original_data["name"]["cn"] if original_data else "未知",
            "original_unicode": original_data["unicode"] if original_data else "",
            "changing_positions": rec.changing_positions,
            "changed_binary": rec.changed_binary,
            "changed_name_cn": changed_data["name"]["cn"] if changed_data else None,
            "is_favorite": rec.is_favorite,
            "notes": rec.notes,
            "share_token": rec.share_token,
        }
        items.append(item)

    return {
        "total": len(items),
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
        "items": items,
    }


@router.post("/history/{record_id}/favorite")
async def api_toggle_favorite(
    record_id: int = Path(..., description="记录ID"),
):
    """切换收藏状态。

    Args:
        record_id: 记录ID

    Returns:
        更新后的收藏状态
    """
    async with async_session() as session:
        result = await session.execute(
            select(DivinationRecord).where(DivinationRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail=f"记录 #{record_id} 未找到")

        record.is_favorite = not record.is_favorite
        await session.commit()
        return {
            "id": record.id,
            "is_favorite": record.is_favorite,
        }


@router.get("/history/share/{token}", response_model=DivinationResponse)
async def api_history_share(
    token: str = Path(..., description="分享令牌"),
):
    """通过分享令牌获取完整占卜结果。

    从数据库查找记录，重建完整的占卜解读数据并以 JSON 格式返回。

    Args:
        token: 分享令牌（UUID）

    Returns:
        包含完整占卜结果的字典
    """
    async with async_session() as session:
        result = await session.execute(
            select(DivinationRecord).where(DivinationRecord.share_token == token)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="分享链接无效或已失效。")

    # 重建完整的占卜结果（使用记录的实际方法）
    hexagram = Hexagram.from_values(record.original_values)
    divination_result = _build_api_result(hexagram, method=record.method)

    # 补充记录元数据
    divination_result["id"] = record.id
    divination_result["share_token"] = record.share_token
    divination_result["created_at"] = record.created_at.isoformat() if record.created_at else ""
    divination_result["is_favorite"] = record.is_favorite

    return divination_result


# ─── AI 解卦 ──────────────────────────────────────────────

@router.post("/interpret/{token}")
async def api_ai_interpret(
    request: Request,
    token: str = Path(..., description="占卜结果令牌"),
):
    """AI 智能解卦 —— 使用大语言模型对占卜结果进行综合解读。

    同一个 token 的解读结果会被缓存（30分钟）。
    """
    import hashlib
    from app.cache import cache_get, cache_set
    from app.limits import can_use_ai, record_ai_use, get_client_ip

    client_ip = get_client_ip(request)

    # 检查速率限制
    if not can_use_ai(client_ip):
        log(802, f"limits: AI limit reached for ip={client_ip[:15]}...")
        raise HTTPException(
            status_code=429,
            detail={"error": "今日 AI 解卦已达日限额", "code": "DAILY_LIMIT_REACHED"},
        )

    # 先从缓存获取占卜结果
    result = await cache_get(token)
    if result is None:
        # 从数据库回查
        async with async_session() as session:
            db_result = await session.execute(
                select(DivinationRecord).where(DivinationRecord.share_token == token)
            )
            record = db_result.scalar_one_or_none()

        if record is None:
            raise HTTPException(status_code=404, detail="占卜结果未找到")
        hexagram = Hexagram.from_values(record.original_values)
        result = _build_api_result(hexagram, method=record.method)
        result["question"] = record.question or ""

    # 检查 AI 解读缓存
    cache_key = f"ai:{token}"
    cached = await cache_get(cache_key)
    if cached:
        log(906, f"api_ai_interpret: cache hit token={token[:8]}...")
        return cached

    # 调用 AI 解读
    from app.ai_interpreter import interpret_with_ai
    try:
        text = await interpret_with_ai(result)
    except Exception as e:
        log(907, "api_ai_interpret: FAILED", level="ERROR", error=e)
        raise HTTPException(status_code=500, detail="AI 解卦服务暂不可用，请稍后重试。")

    # 记录 AI 使用次数
    record_ai_use(client_ip)

    response = {"token": token, "interpretation": text}

    # 缓存解读结果（30分钟）
    await cache_set(cache_key, response, 1800)

    # 持久化到数据库
    try:
        async with async_session() as session:
            db_result = await session.execute(
                select(DivinationRecord).where(DivinationRecord.share_token == token)
            )
            record = db_result.scalar_one_or_none()
            if record:
                record.ai_interpretation = text
                await session.commit()
                log(908, f"api_ai_interpret: saved to DB id={record.id}")
    except Exception as e:
        log(909, "api_ai_interpret: DB save FAILED", level="WARN", error=e)

    return response


@router.get("/limits/ai")
async def api_ai_limits(request: Request):
    """查询今日 AI 使用情况。"""
    from app.limits import get_usage, get_client_ip
    client_ip = get_client_ip(request)
    return get_usage(client_ip)


# ─── 同步码 ──────────────────────────────────────────────

_sync_store: dict[str, dict] = {}
"""内存同步码存储。
   key = 6 位数字码, value = {"records": [...], "expires_at": datetime}
   读取时检查过期，过期条目自动删除。24 小时后过期。
"""


def _clean_expired_sync_codes():
    """清理过期的同步码。"""
    now = datetime.utcnow()
    expired = [k for k, v in _sync_store.items() if v["expires_at"] < now]
    for k in expired:
        del _sync_store[k]
    if expired:
        log(355, f"sync: cleaned {len(expired)} expired codes")


@router.post("/sync/create")
async def sync_create(request: Request):
    """上传占卜记录，返回 6 位数字同步码。

    请求体: 包含 records 数组的 JSON 对象（与导出格式兼容）
    响应: {code: "123456", expires_at: "2026-01-01T00:00:00"}
    """
    _clean_expired_sync_codes()

    body = await request.json()
    records = body.get("records", [])
    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="请求体必须包含 records 数组")

    # 生成 6 位不重复数字码
    import random as rnd
    for _ in range(100):
        code = f"{rnd.randint(100000, 999999)}"
        if code not in _sync_store:
            break
    else:
        raise HTTPException(status_code=500, detail="无法生成唯一同步码，请重试")

    expires_at = datetime.utcnow() + timedelta(hours=24)
    _sync_store[code] = {
        "records": records,
        "expires_at": expires_at,
    }

    log(353, f"sync: created code={code} records={len(records)}")
    return {
        "code": code,
        "expires_at": expires_at.isoformat(),
    }


@router.get("/sync/{code}")
async def sync_download(code: str):
    """通过 6 位同步码下载占卜记录。"""
    _clean_expired_sync_codes()

    entry = _sync_store.get(code)
    if entry is None:
        log(354, f"sync: code={code} NOT FOUND", level="WARN")
        raise HTTPException(status_code=404, detail="同步码无效或已过期")

    log(353, f"sync: downloaded code={code} records={len(entry['records'])}")
    return {
        "code": code,
        "records": entry["records"],
        "expires_at": entry["expires_at"].isoformat(),
    }
