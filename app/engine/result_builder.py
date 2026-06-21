"""
占卜结果构建模块 — Divination Result Builder

从六爻卦 (Hexagram) 出发，构建完整的占卜解读结果字典。
统一被 divine.py、history.py、api.py 调用，消除代码重复。
"""

from datetime import datetime

from app.debug import log
from app.engine.core import Hexagram
from app.engine.transform import (
    changed_hexagram,
    mutual_hexagram,
    opposite_hexagram,
    reverse_hexagram,
    body_and_use,
)
from app.engine.interpretation import interpret
from app.models.hexagram_data import get_hexagram_by_binary


def build_toss_details(hexagram: Hexagram) -> list[dict]:
    """根据实际卦象反推铜钱抛掷详情。

    根据每个爻的值（6/7/8/9）反推三枚铜钱的正反面结果。

    Args:
        hexagram: 六爻卦

    Returns:
        6个抛掷详情的列表（从下到上）
    """
    coin_combo = {
        6: [2, 2, 2],   # 三反 → 老阴
        7: [2, 2, 3],   # 二反一正 → 少阳
        8: [2, 3, 3],   # 一反二正 → 少阴
        9: [3, 3, 3],   # 三正 → 老阳
    }
    base = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}
    results = []
    for line in hexagram.lines:
        pos = line.position
        val = line.line_type.value
        yao = "九" if line.line_type.is_yang else "六"
        results.append({
            "position": pos,
            "coins": coin_combo[val],
            "sum": val,
            "line_name": f"{base[pos]}{yao}",
            "changing": line.line_type.is_changing,
            "is_yang": line.line_type.is_yang,
        })
    return results


def build_line_details(hexagram: Hexagram, hexagram_data: dict) -> list[dict]:
    """构建每爻的详细信息。

    从卦象数据中匹配爻辞和象传。

    Args:
        hexagram: 六爻卦对象
        hexagram_data: 从 JSON 加载的卦象数据

    Returns:
        6个爻详情的列表
    """
    json_lines = {l["position"]: l for l in hexagram_data.get("lines", [])}
    lines = []
    for line in hexagram.lines:
        jl = json_lines.get(line.position, {})
        lines.append({
            "position": line.position,
            "name": line.name,
            "text": jl.get("text", ""),
            "xiang": jl.get("xiang", ""),
            "changing": line.is_changing,
            "is_yang": line.line_type.is_yang,
            "value": line.line_type.value,
            "original_name": jl.get("name", ""),
        })
    return lines


def gather_interpretation_texts(
    original_data: dict,
    changed_data: dict | None,
    lines: list[dict],
    guide: object,
) -> dict:
    """收集解读所需的文本内容。

    Args:
        original_data: 本卦数据
        changed_data: 变卦数据
        lines: 爻详情列表
        guide: InterpretationGuide 对象

    Returns:
        按来源分类的文本字典
    """
    texts = {
        "original_judgment": original_data.get("judgment", {}).get("cn", ""),
        "original_xiang": original_data.get("xiang", {}).get("cn", ""),
        "original_tuan": original_data.get("tuan", {}).get("cn", ""),
        "changing_lines": [],
        "unchanged_lines": [],
        "extra_line": None,
        "changed_judgment": "",
        "changed_xiang": "",
        "changed_tuan": "",
    }

    # 变爻爻辞
    for line in lines:
        if line["changing"]:
            texts["changing_lines"].append(line)
        else:
            texts["unchanged_lines"].append(line)

    # 变卦文本
    if changed_data:
        texts["changed_judgment"] = changed_data.get("judgment", {}).get("cn", "")
        texts["changed_xiang"] = changed_data.get("xiang", {}).get("cn", "")
        texts["changed_tuan"] = changed_data.get("tuan", {}).get("cn", "")

    # 用九/用六（乾坤特殊爻）
    extra_lines = original_data.get("extra_lines", [])
    if extra_lines:
        texts["extra_line"] = extra_lines[0]

    return texts


def build_divination_result(
    hexagram: Hexagram,
    method: str = "coin",
    changed: Hexagram | None = None,
) -> dict:
    """执行完整占卜并构建结果字典。

    Args:
        hexagram: 已通过起卦得到的六爻卦
        method: 占卜方法标识 (coin/yarrow/time/number/plum-blossom)
        changed: 可选的已计算变卦（避免重复计算）

    Returns:
        包含完整占卜结果的字典
    """
    # 本卦数据
    original_data = get_hexagram_by_binary(hexagram.binary)
    if original_data is None:
        log(200, f"build_divination_result: hexagram data MISSING bin={hexagram.binary}", level="ERROR")
        raise ValueError(f"未找到二进制为 {hexagram.binary} 的卦象")

    # 变卦（若未提供则自动计算）
    changed_obj = changed
    if changed_obj is None and hexagram.changing_count > 0:
        changed_obj = changed_hexagram(hexagram)

    changed_data = None
    if changed_obj:
        changed_data = get_hexagram_by_binary(changed_obj.binary)

    # 解读规则
    guide = interpret(hexagram, changed_obj) if changed_obj else interpret(hexagram)

    # 相关卦象
    mutual = mutual_hexagram(hexagram)
    opposite = opposite_hexagram(hexagram)
    rev = reverse_hexagram(hexagram)
    body_use_result = body_and_use(hexagram)

    # 爻详情
    lines = build_line_details(hexagram, original_data)

    # 铜钱抛掷详情（仅金钱卦需要）
    toss_details = build_toss_details(hexagram) if method == "coin" else None

    # 构建结构化的解读信息，包含文本内容
    interpretation_data = {
        "primary_source": guide.primary_source,
        "primary_description": guide.primary_description,
        "primary_lines": guide.primary_lines,
        "secondary_sources": guide.secondary_sources,
        "secondary_lines": guide.secondary_lines,
        "changing_count": guide.changing_count,
        "changing_positions": guide.changing_positions,
        "_texts": gather_interpretation_texts(
            original_data, changed_data, lines, guide
        ),
    }

    result = {
        "method": method,
        "created_at": datetime.utcnow().isoformat(),
        "original_binary": hexagram.binary,
        "original_values": hexagram.line_values,
        "original_hexagram": original_data,
        "changing_positions": hexagram.changing_positions,
        "changing_count": hexagram.changing_count,
        "changed_hexagram": changed_data,
        "changed_binary": changed_obj.binary if changed_obj else None,
        "interpretation": interpretation_data,
        "mutual_hexagram": get_hexagram_by_binary(mutual.binary),
        "opposite_hexagram": get_hexagram_by_binary(opposite.binary),
        "reverse_hexagram": get_hexagram_by_binary(rev.binary),
        "body_use": body_use_result,
        "lines": lines,
        "toss_details": toss_details,
    }
    return result
