"""
六爻卦变换模块 — Hexagram Transformations

给定本卦 (original hexagram)，生成相关卦象:
- 变卦 (changed hexagram): 变爻翻转后所得之卦
- 互卦 (mutual/nuclear hexagram): 取中间四爻交互
- 错卦 (opposite hexagram): 每爻阴阳全变
- 综卦 (reverse hexagram): 上下颠倒
- 体用生克 (body/use analysis): 梅花易数体用关系
"""

from app.engine.core import Hexagram, Line, LineType, TrigramBagua


def changed_hexagram(original: Hexagram) -> Hexagram:
    """求变卦/之卦 (the hexagram after changing lines are flipped).

    变爻翻转规则:
    - 老阴 (6) → 少阳 (7): 阴变阳
    - 老阳 (9) → 少阴 (8): 阳变阴
    - 不变爻保持原状

    Args:
        original: 本卦

    Returns:
        变卦 (之卦)
    """
    new_values = []
    for line in original.lines:
        if line.line_type.is_changing:
            # 变爻翻转: 阳变阴(8), 阴变阳(7)
            new_values.append(8 if line.line_type.is_yang else 7)
        else:
            new_values.append(line.line_type.value)
    return Hexagram.from_values(new_values)


def mutual_hexagram(original: Hexagram) -> Hexagram:
    """求互卦/交互卦 (the mutual/nuclear hexagram).

    互卦取法:
    - 下互卦 = 本卦的第2、3、4爻 (positions 2,3,4)
    - 上互卦 = 本卦的第3、4、5爻 (positions 3,4,5)
    - 所有爻视为稳定爻

    Args:
        original: 本卦

    Returns:
        互卦
    """
    lines = original.lines  # index 0=pos1, ... index 5=pos6
    # 下互: positions 2,3,4 → indices 1,2,3
    # 上互: positions 3,4,5 → indices 2,3,4
    mutual_lower = [lines[1], lines[2], lines[3]]  # 下互
    mutual_upper = [lines[2], lines[3], lines[4]]  # 上互
    new_lines_data = mutual_lower + mutual_upper
    new_values = [(7 if l.line_type.is_yang else 8) for l in new_lines_data]
    return Hexagram.from_values(new_values)


def opposite_hexagram(original: Hexagram) -> Hexagram:
    """求错卦/旁通卦 (the opposite hexagram, 错卦).

    每爻阴阳全变: 阳变阴, 阴变阳. 所有爻均为稳定爻.
    错卦即六爻全变的旁通卦.

    Args:
        original: 本卦

    Returns:
        错卦
    """
    binary = original.binary
    flipped = "".join("0" if c == "1" else "1" for c in binary)
    return Hexagram.from_binary(flipped)


def reverse_hexagram(original: Hexagram) -> Hexagram:
    """求综卦/倒卦 (the reversed/upside-down hexagram, 综卦).

    将整个卦上下颠倒 (180度旋转): 初爻变上爻, 上爻变初爻.

    Args:
        original: 本卦

    Returns:
        综卦
    """
    binary = original.binary
    reversed_binary = binary[::-1]
    return Hexagram.from_binary(reversed_binary)


def body_and_use(original: Hexagram) -> dict:
    """梅花易数体用分析 (Plum Blossom body/use analysis).

    体卦 (body) = 下卦 (inner trigram) = 问卦者本人/主体
    用卦 (use) = 上卦 (outer trigram) = 环境/客体/所问之事

    五行生克关系:
    - 相生: 木→火→土→金→水→木 (generating cycle)
    - 相克: 木→土→水→火→金→木 (overcoming cycle)

    Result keys:
    - body_trigram / use_trigram: 卦名
    - body_nature / use_nature: 卦象
    - body_element / use_element: 五行
    - relation: 体用关系 (比和/我生/生我/我克/克我)
    - auspicious: 是否吉利

    Args:
        original: 本卦

    Returns:
        体用分析字典
    """
    lower = original.lower_trigram   # 体卦
    upper = original.upper_trigram   # 用卦

    # 五行相生关系: A→B 表示 A 生 B
    generating = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}

    # 五行相克关系: A→B 表示 A 克 B
    overcoming = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

    def relation(body_elem: str, use_elem: str) -> str:
        """判断体用生克关系."""
        if body_elem == use_elem:
            return "比和"  # 体用相同，和谐
        if generating.get(body_elem) == use_elem:
            return "我生"  # 体生用 — 泄气，付出
        if generating.get(use_elem) == body_elem:
            return "生我"  # 用生体 — 得益，吉利
        if overcoming.get(body_elem) == use_elem:
            return "我克"  # 体克用 — 克制对方
        if overcoming.get(use_elem) == body_elem:
            return "克我"  # 用克体 — 被克制，不利
        return "未知"

    rel = relation(lower.element, upper.element)

    return {
        "body_trigram": lower.name_cn,
        "body_nature": lower.nature,
        "body_element": lower.element,
        "use_trigram": upper.name_cn,
        "use_nature": upper.nature,
        "use_element": upper.element,
        "relation": rel,
        "auspicious": rel in ("比和", "生我", "我克"),
    }
