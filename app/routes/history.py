"""
历史记录路由 — History Routes

包含:
- 占卜历史列表（分页）
- 单条记录详情
- 收藏/取消收藏
- 删除记录
- 分享记录
"""

from fastapi import APIRouter, Request, Query, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import HTTPException

from app.debug import log
from sqlalchemy import select, func

from app.main import templates
from app.database import async_session
from app.engine.core import Hexagram
from app.engine.result_builder import build_divination_result
from app.models.hexagram_data import get_hexagram_by_binary
from app.models.divination_record import DivinationRecord

router = APIRouter()

_RECORDS_PER_PAGE = 20


async def _get_paginated_records(page: int = 1, per_page: int = _RECORDS_PER_PAGE,
                                 favorite_only: bool = False,
                                 client_id: str = ""):
    """从数据库查询分页的历史记录。"""
    async with async_session() as session:
        query = select(DivinationRecord).order_by(DivinationRecord.created_at.desc())

        if favorite_only:
            query = query.where(DivinationRecord.is_favorite == True)

        query = query.where(DivinationRecord.client_id == client_id)

        # 总记录数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * per_page
        items_query = query.offset(offset).limit(per_page)
        result = await session.execute(items_query)
        records = result.scalars().all()

    total_pages = max(1, (total + per_page - 1) // per_page)
    return records, total, total_pages, page


def _build_record_summary(rec: DivinationRecord) -> dict:
    """构建单条历史记录的摘要数据。"""
    original = get_hexagram_by_binary(rec.original_binary)
    changed = None
    if rec.changed_binary:
        changed = get_hexagram_by_binary(rec.changed_binary)

    return {
        "id": rec.id,
        "created_at": rec.created_at.isoformat() if rec.created_at else "",
        "method": rec.method,
        "original_binary": rec.original_binary,
        "original_name_cn": original["name"]["cn"] if original else "未知",
        "original_name_pinyin": original["name"]["pinyin"] if original else "",
        "original_unicode": original["unicode"] if original else "",
        "changing_positions": rec.changing_positions,
        "changing_count": len(rec.changing_positions) if rec.changing_positions else 0,
        "changed_binary": rec.changed_binary,
        "changed_name_cn": changed["name"]["cn"] if changed else None,
        "changed_unicode": changed["unicode"] if changed else None,
        "notes": rec.notes,
        "is_favorite": rec.is_favorite,
        "share_token": rec.share_token,
    }


@router.get("/", response_class=HTMLResponse)
async def history_list(
    request: Request,
    page: int = Query(default=1, ge=1, description="页码"),
    favorite_only: bool = Query(default=False, description="仅显示收藏"),
):
    """占卜历史记录列表页面。

    支持分页和收藏筛选。
    """
    records, total, total_pages, current_page = await _get_paginated_records(
        page=page,
        favorite_only=favorite_only,
        client_id=request.state.client_id,
    )

    summaries = [_build_record_summary(r) for r in records]

    # 生成页码列表
    page_range = _build_page_range(current_page, total_pages)

    context = {
        "request": request,
        "records": summaries,
        "total": total,
        "page": current_page,
        "total_pages": total_pages,
        "page_range": page_range,
        "favorite_only": favorite_only,
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "prev_page": current_page - 1 if current_page > 1 else 1,
        "next_page": current_page + 1 if current_page < total_pages else total_pages,
    }
    return templates.TemplateResponse(request, "history/index.html", context)


def _build_page_range(current: int, total: int) -> list[int]:
    """生成显示的页码列表（最多显示10个页码）。"""
    if total <= 10:
        return list(range(1, total + 1))

    half_window = 4
    start = max(1, current - half_window)
    end = min(total, current + half_window)

    if start == 1:
        end = min(total, 10)
    if end == total:
        start = max(1, total - 9)

    return list(range(start, end + 1))


@router.get("/{record_id}", response_class=HTMLResponse)
async def history_detail(
    request: Request,
    record_id: int = Path(..., description="记录ID"),
):
    """单条历史记录详情页。

    显示完整的占卜结果，与即时占卜结果页面相同。
    """
    # 从数据库查询
    async with async_session() as session:
        result = await session.execute(
            select(DivinationRecord).where(
                DivinationRecord.id == record_id,
                DivinationRecord.client_id == request.state.client_id,
            )
        )
        record = result.scalar_one_or_none()

    if record is None:
        log(380, f"history_detail: record not found id={record_id}", level="WARN")
        raise HTTPException(status_code=404, detail=f"记录 #{record_id} 未找到")

    # 使用共享构建器重建占卜结果
    hexagram = Hexagram.from_values(record.original_values)
    record_data = build_divination_result(hexagram, method=record.method)
    record_data.update({
        "id": record.id,
        "created_at": record.created_at.isoformat() if record.created_at else "",
        "method": record.method,
        "notes": record.notes,
        "is_favorite": record.is_favorite,
        "share_token": record.share_token,
    })

    context = {
        "request": request,
        "record": record_data,
        "shared": False,
    }
    return templates.TemplateResponse(request, "history/detail.html", context)


@router.post("/{record_id}/favorite")
async def history_toggle_favorite(
    request: Request,
    record_id: int = Path(..., description="记录ID"),
):
    """切换收藏状态。"""
    async with async_session() as session:
        result = await session.execute(
            select(DivinationRecord).where(
                DivinationRecord.id == record_id,
                DivinationRecord.client_id == request.state.client_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail=f"记录 #{record_id} 未找到")

        record.is_favorite = not record.is_favorite
        await session.commit()

    referer = request.headers.get("Referer", "/history/")
    return RedirectResponse(url=referer, status_code=303)


@router.post("/{record_id}/delete")
async def history_delete(
    request: Request,
    record_id: int = Path(..., description="记录ID"),
):
    """删除占卜记录。"""
    async with async_session() as session:
        result = await session.execute(
            select(DivinationRecord).where(
                DivinationRecord.id == record_id,
                DivinationRecord.client_id == request.state.client_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail=f"记录 #{record_id} 未找到")

        await session.delete(record)
        await session.commit()

    return RedirectResponse(url="/history/", status_code=303)


@router.get("/share/{token}", response_class=HTMLResponse)
async def history_share(
    request: Request,
    token: str = Path(..., description="分享令牌"),
):
    """查看分享的占卜结果。

    通过唯一令牌访问，无需登录。
    """
    async with async_session() as session:
        result = await session.execute(
            select(DivinationRecord).where(DivinationRecord.share_token == token)
        )
        record = result.scalar_one_or_none()

    if record is None:
        return templates.TemplateResponse(request, "result/not_found.html", {
            "request": request,
            "message": "分享链接无效或已失效。",
        })

    # 使用共享构建器重建占卜结果
    hexagram = Hexagram.from_values(record.original_values)
    record_data = build_divination_result(hexagram, method=record.method)
    record_data.update({
        "id": record.id,
        "created_at": record.created_at.isoformat() if record.created_at else "",
        "method": record.method,
        "question": record.question or "",
    })

    context = {
        "request": request,
        "record": record_data,
        "shared": True,
    }
    return templates.TemplateResponse(request, "history/detail.html", context)
