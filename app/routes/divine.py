"""
占卜路由 — Divination Routes

包含多种起卦方法及完整的变卦解读流程。
使用 POST-Redirect-GET 模式避免重复提交。
"""

import random
from typing import Optional

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import HTTPException
from sqlalchemy import select

from app.main import templates
from app.database import async_session
from app.engine.core import Hexagram
from app.engine.result_builder import build_divination_result
from app.cache import cache_get, cache_set
from app.config import settings
from app.engine.coin import cast_hexagram as cast_coin_hexagram
from app.engine.yarrow import cast_yarrow_hexagram, get_yarrow_details
from app.engine.time import cast_time_hexagram, get_time_details
from app.engine.number import cast_number_hexagram, generate_random_numbers
from app.engine.plum_blossom import cast_plum_blossom_hexagram
from app.engine.transform import (
    changed_hexagram,
)
from app.debug import log
from app.models.divination_record import DivinationRecord

router = APIRouter()


async def _save_to_db(hexagram: Hexagram, changed: Hexagram | None,
                      share_token: str, method: str = "coin",
                      question: str = "") -> int:
    """将占卜结果保存到数据库。"""
    log(300, f"_save_to_db: method={method} bin={hexagram.binary}")
    try:
        async with async_session() as session:
            record = DivinationRecord(
                method=method,
                original_binary=hexagram.binary,
                original_values=hexagram.line_values,
                changed_binary=changed.binary if changed else None,
                changing_positions=hexagram.changing_positions,
                share_token=share_token,
                question=question or "",
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            log(301, f"_save_to_db: OK id={record.id}")
            return record.id
    except Exception as e:
        log(302, "_save_to_db: FAILED", level="ERROR", error=e)
        raise


@router.get("/", response_class=HTMLResponse)
async def divine_select(request: Request):
    """占卜方法选择页面。"""
    methods = [
        {
            "id": "coin",
            "name": "金钱卦",
            "icon": "🪙",
            "desc": "使用三枚铜钱，抛掷六次成卦。最传统、最常用的起卦方法。",
            "status": "ready",
            "url": "/divine/coin",
        },
        {
            "id": "yarrow",
            "name": "蓍草法",
            "icon": "🌿",
            "desc": "大衍之数五十，其用四十有九。最古老的起卦方法，仪式感最强。",
            "status": "ready",
            "url": "/divine/yarrow",
        },
        {
            "id": "time",
            "name": "时间卦",
            "icon": "⏰",
            "desc": "以当前年月日时起卦，无需任何工具，随时随地可占。",
            "status": "ready",
            "url": "/divine/time",
        },
        {
            "id": "number",
            "name": "数字卦",
            "icon": "🔢",
            "desc": "任意输入三个数字起卦，简单快捷。",
            "status": "ready",
            "url": "/divine/number",
        },
        {
            "id": "plum-blossom",
            "name": "梅花易数",
            "icon": "🌸",
            "desc": "邵雍所创，以物象、声音、方位等起卦，万物皆可占。",
            "status": "ready",
            "url": "/divine/plum-blossom",
        },
    ]
    return templates.TemplateResponse(request, "divine/index.html", {
        "request": request,
        "methods": methods,
    })


@router.get("/coin", response_class=HTMLResponse)
async def coin_divination(request: Request):
    """金钱卦占卜页面 — 铜钱抛掷界面。"""
    return templates.TemplateResponse(request, "divine/coin.html", {
        "request": request,
    })


@router.post("/coin/toss")
async def coin_toss(
    request: Request,
    seed: Optional[int] = Form(default=None),
    values: Optional[str] = Form(default=None),
    question: Optional[str] = Form(default=""),
):
    """执行金钱卦占卜。

    若客户端提交了真实 values（逗号分隔的 6 个 6-9 数值），
    直接使用这些值构建卦象，确保动画显示与服务器结果一致。
    否则使用 seed 或系统随机数生成。
    """
    if values and values.strip():
        log(303, f"coin_toss: using client values={values}")
        try:
            parsed = [int(v.strip()) for v in values.split(",")]
            if len(parsed) != 6 or any(v not in (6, 7, 8, 9) for v in parsed):
                log(304, f"coin_toss: invalid values={parsed}", level="WARN")
                raise ValueError("Invalid values")
            hexagram = Hexagram.from_values(parsed)
        except Exception:
            log(305, "coin_toss: client values parse FAILED", level="ERROR")
            raise HTTPException(status_code=400, detail="无效的起卦数据，请重新开始。")
    else:
        log(306, "coin_toss: using server RNG")
        rng = random.Random(seed) if seed is not None else None
        try:
            hexagram = cast_coin_hexagram(rng)
        except Exception as e:
            log(307, "coin_toss: RNG FAILED", level="ERROR", error=e)
            raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")

    # 预计算变卦（仅一次），同时用于结果构建和数据库保存
    changed = None
    if hexagram.changing_count > 0:
        changed = changed_hexagram(hexagram)

    # 构建完整结果
    log(308, f"coin_toss: building result bin={hexagram.binary}")
    try:
        result = build_divination_result(hexagram, changed=changed)
    except ValueError as e:
        log(309, f"coin_toss: build result FAILED bin={hexagram.binary}", level="ERROR", error=e)
        raise HTTPException(status_code=500, detail=str(e))

    # 生成分享令牌
    share_token = DivinationRecord.generate_share_token()
    log(310, f"coin_toss: share_token={share_token[:8]}...")

    # 保存到数据库
    record_id = await _save_to_db(hexagram, changed, share_token,
                                  method="coin", question=question or "")

    result["id"] = record_id
    result["share_token"] = share_token
    result["question"] = question or ""

    # 存入缓存（Redis，优雅降级）
    await cache_set(share_token, result, settings.redis_ttl)
    log(311, f"coin_toss: redirect to result token={share_token[:8]}...")

    return RedirectResponse(
        url=f"/divine/result?token={share_token}",
        status_code=303,
    )


@router.get("/result", response_class=HTMLResponse)
async def divination_result(
    request: Request,
    token: str = Query(..., description="占卜结果令牌"),
):
    """占卜结果页面。

    从缓存（Redis）中读取完整的占卜解读数据并渲染。
    如果缓存未命中，从数据库回查并重建结果。
    """
    log(320, f"divination_result: lookup token={token[:8]}...")
    result = await cache_get(token)

    # 缓存未命中：从数据库回查
    if result is None:
        log(321, f"divination_result: cache miss, checking DB token={token[:8]}...")
        async with async_session() as session:
            db_result = await session.execute(
                select(DivinationRecord).where(DivinationRecord.share_token == token)
            )
            record = db_result.scalar_one_or_none()

        if record is None:
            log(322, f"divination_result: token not found in DB token={token[:8]}...", level="WARN")
            return templates.TemplateResponse(request, "result/not_found.html", {
                "request": request,
                "message": "占卜结果未找到。可能已经过期，请重新占卜。",
            })

        # 从数据库记录重建完整结果
        log(323, f"divination_result: rebuilding from DB id={record.id}")
        hexagram = Hexagram.from_values(record.original_values)
        result = build_divination_result(hexagram, method=record.method)
        result["id"] = record.id
        result["share_token"] = record.share_token
        result["question"] = record.question or ""

        # 写回缓存
        await cache_set(token, result, settings.redis_ttl)
        log(324, "divination_result: rebuilt and cached OK")

    context = {
        "request": request,
        "result": result,
    }
    return templates.TemplateResponse(request, "result/divination_result.html", context)


@router.get("/yarrow", response_class=HTMLResponse)
async def yarrow_divination(request: Request):
    """蓍草法占卜页面。"""
    details = get_yarrow_details()
    return templates.TemplateResponse(request, "divine/yarrow.html", {
        "request": request,
        "preview_details": details,
    })


@router.post("/yarrow/cast")
async def yarrow_cast(request: Request, seed: Optional[int] = Form(default=None),
                      question: Optional[str] = Form(default="")):
    """执行蓍草法占卜。"""
    rng = random.Random(seed) if seed is not None else None
    try:
        hexagram = cast_yarrow_hexagram(rng)
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")

    changed = None
    if hexagram.changing_count > 0:
        changed = changed_hexagram(hexagram)

    try:
        result = build_divination_result(hexagram, method="yarrow", changed=changed)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    share_token = DivinationRecord.generate_share_token()
    record_id = await _save_to_db(hexagram, changed, share_token, method="yarrow", question=question or "")

    result["id"] = record_id
    result["share_token"] = share_token
    result["question"] = question or ""
    await cache_set(share_token, result, settings.redis_ttl)

    return RedirectResponse(
        url=f"/divine/result?token={share_token}",
        status_code=303,
    )


@router.get("/time", response_class=HTMLResponse)
async def time_divination(request: Request):
    """时间卦占卜页面。"""
    time_info = get_time_details()
    return templates.TemplateResponse(request, "divine/time.html", {
        "request": request,
        "time_info": time_info,
    })


@router.post("/time/cast")
async def time_cast(request: Request,
                    question: Optional[str] = Form(default="")):
    """执行时间卦占卜。"""
    try:
        hexagram = cast_time_hexagram()
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")

    changed = None
    if hexagram.changing_count > 0:
        changed = changed_hexagram(hexagram)

    try:
        result = build_divination_result(hexagram, method="time", changed=changed)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    share_token = DivinationRecord.generate_share_token()
    record_id = await _save_to_db(hexagram, changed, share_token, method="time", question=question or "")

    result["id"] = record_id
    result["share_token"] = share_token
    result["question"] = question or ""
    await cache_set(share_token, result, settings.redis_ttl)

    return RedirectResponse(
        url=f"/divine/result?token={share_token}",
        status_code=303,
    )


@router.get("/number", response_class=HTMLResponse)
async def number_divination(request: Request):
    """数字卦占卜页面。"""
    random_numbers = generate_random_numbers()
    return templates.TemplateResponse(request, "divine/number.html", {
        "request": request,
        "random_numbers": random_numbers,
    })


@router.post("/number/cast")
async def number_cast(
    request: Request,
    n1: int = Form(..., ge=1, description="第一个数字（上卦）"),
    n2: int = Form(..., ge=1, description="第二个数字（下卦）"),
    n3: int = Form(..., ge=1, description="第三个数字（动爻）"),
    question: Optional[str] = Form(default=""),
):
    """执行数字卦占卜。"""
    try:
        hexagram = cast_number_hexagram(n1, n2, n3)
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")

    changed = None
    if hexagram.changing_count > 0:
        changed = changed_hexagram(hexagram)

    try:
        result = build_divination_result(hexagram, method="number", changed=changed)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    share_token = DivinationRecord.generate_share_token()
    record_id = await _save_to_db(hexagram, changed, share_token, method="number", question=question or "")

    result["id"] = record_id
    result["share_token"] = share_token
    result["question"] = question or ""
    await cache_set(share_token, result, settings.redis_ttl)

    return RedirectResponse(
        url=f"/divine/result?token={share_token}",
        status_code=303,
    )


@router.get("/plum-blossom", response_class=HTMLResponse)
async def plum_blossom_divination(request: Request):
    """梅花易数占卜页面。"""
    from app.engine.plum_blossom import get_phenomena_categories
    phenomena = get_phenomena_categories()
    trigram_names = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
    return templates.TemplateResponse(request, "divine/plum_blossom.html", {
        "request": request,
        "trigram_names": trigram_names,
        "phenomena": phenomena,
    })


@router.post("/plum-blossom/cast")
async def plum_blossom_cast(
    request: Request,
    upper_trigram: str = Form(..., description="上卦"),
    lower_trigram: str = Form(..., description="下卦"),
    changing_line: Optional[int] = Form(default=None, description="动爻位置（可选）"),
    question: Optional[str] = Form(default=""),
):
    """执行梅花易数占卜。"""
    try:
        hexagram = cast_plum_blossom_hexagram(upper_trigram, lower_trigram, changing_line)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="占卜失败，请稍后重试。")

    changed = None
    if hexagram.changing_count > 0:
        changed = changed_hexagram(hexagram)

    try:
        result = build_divination_result(hexagram, method="plum-blossom", changed=changed)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    share_token = DivinationRecord.generate_share_token()
    record_id = await _save_to_db(hexagram, changed, share_token, method="plum-blossom", question=question or "")

    result["id"] = record_id
    result["share_token"] = share_token
    result["question"] = question or ""
    await cache_set(share_token, result, settings.redis_ttl)

    return RedirectResponse(
        url=f"/divine/result?token={share_token}",
        status_code=303,
    )
