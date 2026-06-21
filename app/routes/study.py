"""
学习研读路由 — Study/Learning Routes

包含:
- 易经学习中心
- 八卦详解
- 起卦方法介绍
- 解读指南
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.debug import log

from app.main import templates
from app.models.hexagram_data import load_trigrams, get_all_hexagrams, get_trigram_by_binary

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def study_index(request: Request):
    """学习中心首页。

    提供易经学习的入口，包括：
    - 八卦基础
    - 六十四卦概览
    - 起卦方法
    - 解读指南
    """
    trigrams = load_trigrams()
    hexagrams = get_all_hexagrams()

    sections = [
        {
            "id": "trigrams",
            "title": "八卦基础",
            "desc": "八卦（乾兑离震巽坎艮坤）是易经的基础符号系统，每一卦代表一种自然现象和属性。",
            "icon": "☯",
            "link": "/study/trigrams",
            "count": 8,
        },
        {
            "id": "hexagrams",
            "title": "六十四卦",
            "desc": "由两个八卦上下相叠而成六十四卦，每卦包含六爻，象征世间万物的变化规律。",
            "icon": "📖",
            "link": "/hexagram/",
            "count": 64,
        },
        {
            "id": "methods",
            "title": "起卦方法",
            "desc": "传统易经占卜有多种起卦方式，包括金钱卦、蓍草法、梅花易数等。",
            "icon": "🔮",
            "link": "/study/methods",
            "count": 5,
        },
        {
            "id": "interpretation",
            "title": "解读指南",
            "desc": "了解如何解读卦象，包括变爻规则、体用生克、卦辞爻辞的运用。",
            "icon": "📜",
            "link": "/study/interpretation",
            "count": 4,
        },
    ]

    # 第一个和最后一个卦作为示例
    first_hex = hexagrams[0]
    last_hex = hexagrams[-1]

    context = {
        "request": request,
        "sections": sections,
        "trigrams": trigrams,
        "first_hexagram": first_hex,
        "last_hexagram": last_hex,
        "total_hexagrams": len(hexagrams),
    }
    return templates.TemplateResponse(request, "study/index.html", context)


@router.get("/trigrams", response_class=HTMLResponse)
async def study_trigrams(request: Request):
    """八卦详解页面。

    逐一介绍八个基本卦象的含义、象征、五行属性等。
    """
    trigrams = load_trigrams()

    # 为每个卦象补充详细说明
    details = {
        "乾": {
            "meaning": "健",
            "description": "乾为天，象征天、父、君王、刚健、创造。六爻纯阳，至刚至健。",
            "traits": "刚健中正，自强不息",
            "direction": "西北",
            "season": "秋冬之交",
            "body": "首",
            "animal": "马",
        },
        "兑": {
            "meaning": "说（悦）",
            "description": "兑为泽，象征泽、少女、喜悦、口舌。一阴在上，二阳在下。",
            "traits": "喜悦和悦，言语沟通",
            "direction": "西",
            "season": "秋",
            "body": "口",
            "animal": "羊",
        },
        "离": {
            "meaning": "丽（附丽）",
            "description": "离为火，象征火、日、电、中女、文明。一阴在二阳之间。",
            "traits": "光明美丽，依附传承",
            "direction": "南",
            "season": "夏",
            "body": "目",
            "animal": "雉",
        },
        "震": {
            "meaning": "动",
            "description": "震为雷，象征雷、长子、震动、行动。一阳在二阴之下。",
            "traits": "震动奋起，果断行动",
            "direction": "东",
            "season": "春",
            "body": "足",
            "animal": "龙",
        },
        "巽": {
            "meaning": "入",
            "description": "巽为风，象征风、长女、顺入、渗透。一阴在二阳之下。",
            "traits": "顺从谦逊，渐入佳境",
            "direction": "东南",
            "season": "春夏之交",
            "body": "股",
            "animal": "鸡",
        },
        "坎": {
            "meaning": "陷",
            "description": "坎为水，象征水、中男、险陷、困难。一阳在二阴之中。",
            "traits": "险陷艰难，习坎而进",
            "direction": "北",
            "season": "冬",
            "body": "耳",
            "animal": "豕",
        },
        "艮": {
            "meaning": "止",
            "description": "艮为山，象征山、少男、静止、停止。一阳在二阴之上。",
            "traits": "静止安定，适可而止",
            "direction": "东北",
            "season": "冬春之交",
            "body": "手",
            "animal": "狗",
        },
        "坤": {
            "meaning": "顺",
            "description": "坤为地，象征地、母、臣民、柔顺、包容。六爻纯阴，至柔至顺。",
            "traits": "柔顺包容，厚德载物",
            "direction": "西南",
            "season": "夏秋之交",
            "body": "腹",
            "animal": "牛",
        },
    }

    trigram_details = []
    for t in trigrams:
        extra = details.get(t["name_cn"], {})
        trigram_details.append({
            **t,
            "meaning": extra.get("meaning", ""),
            "full_description": extra.get("description", ""),
            "traits": extra.get("traits", ""),
            "direction_detail": extra.get("direction", t.get("direction", "")),
            "season": extra.get("season", ""),
            "body": extra.get("body", ""),
            "animal": extra.get("animal", ""),
        })

    context = {
        "request": request,
        "trigrams": trigram_details,
    }
    return templates.TemplateResponse(request, "study/trigrams.html", context)


@router.get("/methods", response_class=HTMLResponse)
async def study_methods(request: Request):
    """起卦方法介绍页面。

    详细介绍各种易经占卜方法的历史和步骤。
    """
    methods = [
        {
            "name": "金钱卦（三枚铜钱法）",
            "icon": "🪙",
            "history": "金钱卦是民间最流行的起卦方法。以三枚铜钱代替复杂的蓍草演算，"
                       "简化了起卦流程，使易经占卜得以普及。",
            "steps": [
                "准备三枚相同的铜钱（或硬币），静心凝神，默念所问之事。",
                "将三枚铜钱同时抛掷，记录正反面：正面（字）为3，背面（花）为2。",
                "计算三枚铜钱的和值：6为老阴（变爻），7为少阳，8为少阴，9为老阳（变爻）。",
                "重复抛掷6次，从下往上记录每一爻的结果。",
                "六爻全部记录后，即成本卦。若有变爻，再求变卦。",
            ],
            "rule": "三枚铜钱的和值映射：三反=6（老阴），二反一正=7（少阳），"
                    "一反二正=8（少阴），三正=9（老阳）。",
            "status": "ready",
        },
        {
            "name": "蓍草法（大衍筮法）",
            "icon": "🌿",
            "history": ("蓍草法是最古老的易经起卦方法，记载于《易传·系辞上》："
                       "「大衍之数五十，其用四十有九。」"
                       "使用50根蓍草（或竹签）进行演算。"),
            "steps": [
                "取50根蓍草，取出一根不用（象征太极）。",
                "将剩余49根随机分为两堆（象征两仪）。",
                "从右堆取一根挂于左手小指（象征三才）。",
                "左堆每4根一组分数（象征四时），取尽剩余。",
                "右堆同样每4根一组分数，取尽剩余。",
                "将两次剩余与挂于小指的一根合并，完成一变。",
                "重复三变，得到一爻（6-9）。",
                "重复六次，得到六爻，完成起卦。",
            ],
            "rule": "三变后剩余蓍草数除以4，得6-9：6为老阴，7为少阳，8为少阴，9为老阳。",
            "status": "ready",
        },
        {
            "name": "时间卦",
            "icon": "⏰",
            "history": "时间卦以当前时间信息起卦，无需任何工具，随时随地可占。"
                       "是梅花易数中最便捷的起卦方式。",
            "steps": [
                "取当前年月日时四个数字。",
                "上卦 = 年 + 月 + 日，除以8取余数对应八卦（1乾2兑3离4震5巽6坎7艮8坤）。",
                "下卦 = 日 + 时，除以8取余数对应八卦。",
                "动爻 = 年 + 月 + 日 + 时，除以6取余数（余0则为6）。",
                "若余数为0，则对应坤卦或第6爻。",
            ],
            "rule": "八卦对应：1乾、2兑、3离、4震、5巽、6坎、7艮、8/0坤。动爻对应：1-6爻。",
            "status": "ready",
        },
        {
            "name": "梅花易数",
            "icon": "🌸",
            "history": "梅花易数为宋代邵雍（康节先生）所创。相传邵雍观梅见二雀争枝坠地，"
                       "以此起卦占得明日有少女折花伤股之象，后果然应验，遂名「梅花易数」。",
            "steps": [
                "以物象、声音、方位、颜色等为起卦依据。",
                "第一个数 ÷ 8 余数为上卦。",
                "第二个数 ÷ 8 余数为下卦。",
                "第三个数 ÷ 6 余数为动爻。",
                "结合卦象、五行、体用生克进行综合解读。",
            ],
            "rule": "万物皆可起卦：字数、声音数、方位数、颜色数等均可转化为数字。",
            "status": "ready",
        },
        {
            "name": "数字卦",
            "icon": "🔢",
            "history": "数字卦是梅花易数的变体，由问卦者任意提供三个数字起卦。"
                       "简单直观，适合初学者。",
            "steps": [
                "问卦者任意想三个数字（如 3, 8, 15）。",
                "第一个数 ÷ 8 取余 → 上卦。",
                "第二个数 ÷ 8 取余 → 下卦。",
                "第三个数 ÷ 6 取余 → 动爻。",
                "根据结果查找对应的卦象和爻辞。",
            ],
            "rule": "数字过大的话，逐次除以8或6取余数即可。",
            "status": "ready",
        },
    ]

    context = {
        "request": request,
        "methods": methods,
    }
    return templates.TemplateResponse(request, "study/methods.html", context)


@router.get("/interpretation", response_class=HTMLResponse)
async def study_interpretation(request: Request):
    """解读指南页面。

    介绍朱熹变爻解读规则及如何综合判断卦象。
    """
    rules = [
        {
            "changing": 0,
            "title": "无变爻",
            "rule": "以本卦卦辞为主",
            "description": "没有变爻，说明当前局势相对稳定。"
                           "应重点阅读本卦的卦辞，了解整体趋势和启示。",
            "detail": "同时参考彖传和象传，深入理解卦象的含义。",
        },
        {
            "changing": 1,
            "title": "一爻变",
            "rule": "以本卦变爻爻辞为主",
            "description": "只有一个变爻，这是最常见的情况。"
                           "该爻的爻辞是解读的核心，直接回应所问之事。",
            "detail": "变爻所在位置也代表事情的关键所在（初爻为始，上爻为终）。",
        },
        {
            "changing": 2,
            "title": "二爻变",
            "rule": "以本卦两变爻爻辞为主，上爻为重",
            "description": "两个变爻，以上面的变爻为主，下面的变爻为辅。"
                           "两爻共同揭示事情的发展趋势。",
            "detail": "同时参考本卦卦辞作为背景理解。",
        },
        {
            "changing": 3,
            "title": "三爻变",
            "rule": "以本卦卦辞为主，兼看变卦卦辞",
            "description": "三个变爻，本卦和变卦的力量相当。"
                           "本卦代表当前状态，变卦代表发展趋势。",
            "detail": "同时阅读三个变爻的爻辞以了解具体变化。",
        },
        {
            "changing": 4,
            "title": "四爻变",
            "rule": "以变卦中不变爻爻辞为主",
            "description": "四个变爻，变卦的力量已占主导。"
                           "变卦中两个不变爻揭示问题的关键。",
            "detail": "以下面的不变爻为主，上面的不变爻为辅。",
        },
        {
            "changing": 5,
            "title": "五爻变",
            "rule": "以变卦中唯一不变爻爻辞为主",
            "description": "五个变爻，变卦几乎完全取代本卦。"
                           "变卦中唯一的不变爻是解读的核心。",
            "detail": "那个不变爻代表事情中不可改变的核心因素。",
        },
        {
            "changing": 6,
            "title": "六爻全变",
            "rule": "以变卦卦辞为主（乾坤有用九/用六）",
            "description": "所有爻都是变爻，代表根本性的转变。"
                           "乾卦参考「用九」，坤卦参考「用六」，其他卦以变卦卦辞为主。",
            "detail": "这是极其罕见的情况，说明事情正在发生根本性的变化。",
        },
    ]

    # 体用生克关系
    body_use_relations = [
        {"relation": "比和", "meaning": "体用相同五行", "level": "大吉", "description": "表里如一，内外和谐，事情顺利。"},
        {"relation": "用生体", "meaning": "用卦生体卦", "level": "吉", "description": "外部环境有利于求测者，得外力相助。"},
        {"relation": "体克用", "meaning": "体卦克用卦", "level": "次吉", "description": "求测者可以掌控局面，但需付出努力。"},
        {"relation": "体生用", "meaning": "体卦生用卦", "level": "小凶", "description": "求测者付出较多，精力外泄，需要谨慎。"},
        {"relation": "克体", "meaning": "用卦克体卦", "level": "凶", "description": "外部压力大，环境不利，宜守不宜攻。"},
    ]

    context = {
        "request": request,
        "rules": rules,
        "body_use_relations": body_use_relations,
    }
    return templates.TemplateResponse(request, "study/interpretation.html", context)
