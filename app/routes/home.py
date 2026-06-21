"""
首页路由 — Home Page Routes

包含:
- 首页：八卦介绍、快速入口、每日一卦
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.debug import log
from app.main import templates
from app.models.hexagram_data import get_hexagram_by_number

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """首页 — 八卦占卜应用入口。

    包含:
    - Hero 区域：易经八卦简介
    - 快速占卜入口
    - 每日一卦/推荐卦象
    - 易经简介说明
    """
    featured = get_hexagram_by_number(1)

    context = {
        "request": request,
        "featured": featured,
        "quick_methods": [
            {"name": "金钱卦", "path": "/divine/coin", "desc": "传统三枚铜钱起卦法，最经典的方式"},
            {"name": "蓍草法", "path": "/divine/yarrow", "desc": "大衍之数五十，其用四十有九，最古老的筮法"},
            {"name": "时间卦", "path": "/divine/time", "desc": "以当前年月日时起卦，随时随地可占"},
            {"name": "数字卦", "path": "/divine/number", "desc": "任意输入三个数字起卦，简单快捷"},
            {"name": "梅花易数", "path": "/divine/plum-blossom", "desc": "以物象起卦，万物皆可占，邵雍所创"},
        ],
    }
    return templates.TemplateResponse(request, "home/index.html", context)
