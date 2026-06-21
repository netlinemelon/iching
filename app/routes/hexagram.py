"""
六十四卦浏览路由 — Hexagram Browse Routes

包含:
- 八卦网格视图（8x8）
- 单卦详情页
- 关键词搜索
"""

from fastapi import APIRouter, Request, Query, Path
from fastapi.responses import HTMLResponse
from fastapi import HTTPException

from app.debug import log

from app.main import templates
from app.models.hexagram_data import (
    get_all_hexagrams,
    get_hexagram_by_binary,
    get_hexagram_by_number,
    get_trigram_by_binary,
    search_hexagrams,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def hexagram_grid(request: Request):
    """六十四卦网格视图 — 8x8 布局。

    按卦序排列，每卦显示名称、符号、上下卦名。
    """
    all_hexagrams = get_all_hexagrams()

    # 构建摘要数据，每行8卦
    grid_rows = []
    for i in range(0, 64, 8):
        row = all_hexagrams[i:i + 8]
        summaries = []
        for h in row:
            upper = get_trigram_by_binary(h["upper_trigram"])
            lower = get_trigram_by_binary(h["lower_trigram"])
            summaries.append({
                "number": h["number"],
                "binary": h["binary"],
                "name_cn": h["name"]["cn"],
                "name_pinyin": h["name"]["pinyin"],
                "unicode": h["unicode"],
                "upper_trigram_name": upper["name_cn"] if upper else h["upper_name"],
                "lower_trigram_name": lower["name_cn"] if lower else h["lower_name"],
                "judgment_brief": h["judgment"]["cn"].split("。")[0] + "。" if h["judgment"]["cn"] else "",
            })
        grid_rows.append(summaries)

    context = {
        "request": request,
        "grid_rows": grid_rows,
        "total": 64,
    }
    return templates.TemplateResponse(request, "hexagram/grid.html", context)


@router.get("/search", response_class=HTMLResponse)
async def hexagram_search(
    request: Request,
    q: str = Query("", min_length=0, description="搜索关键词"),
):
    """搜索卦象。

    按卦名（中文/拼音/英文）、卦辞、爻辞搜索。

    注意：此路由必须定义在 /{number} 之前，否则静态路径会被动态路由捕获。
    """
    if not q or not q.strip():
        return templates.TemplateResponse(request, "hexagram/grid.html", {
            "request": request,
            "grid_rows": [],
            "total": 0,
            "search_query": "",
            "search_results": None,
            "message": "请输入搜索关键词",
        })

    query = q.strip()
    results = search_hexagrams(query)

    # 构建搜索结果摘要
    summaries = []
    for h in results:
        upper = get_trigram_by_binary(h["upper_trigram"])
        lower = get_trigram_by_binary(h["lower_trigram"])
        summaries.append({
            "number": h["number"],
            "binary": h["binary"],
            "name_cn": h["name"]["cn"],
            "name_pinyin": h["name"]["pinyin"],
            "unicode": h["unicode"],
            "upper_trigram_name": upper["name_cn"] if upper else h["upper_name"],
            "lower_trigram_name": lower["name_cn"] if lower else h["lower_name"],
            "judgment_brief": h["judgment"]["cn"].split("。")[0] + "。" if h["judgment"]["cn"] else "",
        })

    context = {
        "request": request,
        "search_results": summaries,
        "search_query": query,
        "total": len(results),
        "search_message": f"找到 {len(results)} 个结果",
        "grid_rows": [],
    }
    return templates.TemplateResponse(request, "hexagram/search.html", context)


@router.get("/{number}", response_class=HTMLResponse)
async def hexagram_detail(
    request: Request,
    number: int = Path(..., description="卦序 1-64"),
):
    """单卦详情页。

    显示卦名、卦辞、彖传、象传、爻辞、相关卦象等。
    """
    if number < 1 or number > 64:
        log(360, f"hexagram_detail: invalid number={number}", level="WARN")
        raise HTTPException(status_code=404, detail=f"未找到第 {number} 卦")

    hexagram = get_hexagram_by_number(number)
    if hexagram is None:
        log(361, f"hexagram_detail: get_hexagram_by_number returned None for {number}", level="ERROR")
        raise HTTPException(status_code=404, detail=f"未找到第 {number} 卦")

    # 查找上下卦详情
    upper_trigram = get_trigram_by_binary(hexagram["upper_trigram"])
    lower_trigram = get_trigram_by_binary(hexagram["lower_trigram"])

    # 构建相关卦象
    binary = hexagram["binary"]

    # 错卦（全变）
    opposite_binary = "".join("0" if c == "1" else "1" for c in binary)
    opposite = get_hexagram_by_binary(opposite_binary)

    # 综卦（颠倒）
    reversed_binary = binary[::-1]
    rev = get_hexagram_by_binary(reversed_binary)

    # 互卦（取2-5爻）
    # 下互：2,3,4爻；上互：3,4,5爻
    lines = hexagram.get("lines", [])
    if len(lines) >= 5:
        mutual_lower = "".join("1" if "九" in l["name"] else "0"
                               for l in lines[1:4])  # 2,3,4
        mutual_upper = "".join("1" if "九" in l["name"] else "0"
                               for l in lines[2:5])  # 3,4,5
        mutual_binary = mutual_upper + mutual_lower
        mutual = get_hexagram_by_binary(mutual_binary)
    else:
        mutual = None

    context = {
        "request": request,
        "hexagram": hexagram,
        "upper_trigram": upper_trigram,
        "lower_trigram": lower_trigram,
        "opposite_hexagram": opposite,
        "reverse_hexagram": rev,
        "mutual_hexagram": mutual,
    }
    return templates.TemplateResponse(request, "hexagram/detail.html", context)
