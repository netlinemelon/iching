"""
蓍草法起卦模块 — Yarrow Stalk Divination Method

最古老的起卦方法，源自《系辞上传》：
"大衍之数五十，其用四十有九。分而为二以象两，挂一以象三，
揲之以四以象四时，归奇于扐以象闰..."

三变成一爻，十八变成一卦。

概率分布:
- 6 (老阴): 1/16
- 7 (少阳): 5/16
- 8 (少阴): 7/16
- 9 (老阳): 3/16
"""

import random
from typing import Optional

from app.engine.core import Hexagram, LineType
from app.debug import log


def _one_change(stalks: int, rng: random.Random) -> int:
    """一变：分二、挂一、揲四、归奇。

    步骤:
    1. 将蓍草随机分为两堆 (分二以象两)
    2. 从右堆取一根挂起 (挂一以象三)
    3. 左堆每4根一数，取余数 (揲之以四以象四时)
    4. 右堆每4根一数，取余数
    5. 余数加挂一为"扐" (归奇于扐以象闰)

    Args:
        stalks: 当前蓍草总数
        rng: 随机数生成器

    Returns:
        本次变所去除的蓍草数
    """
    # 分二：随机分为左右两堆
    split = rng.randint(1, stalks - 1)
    pile_a = split      # 左堆 (天)
    pile_b = stalks - split  # 右堆 (地)

    # 挂一：从右堆取一根
    pile_b -= 1
    held = 1  # 挂一之蓍 (人)

    # 揲四：左堆每4根一数
    ra = pile_a % 4
    if ra == 0:
        ra = 4

    # 揲四：右堆每4根一数
    rb = pile_b % 4
    if rb == 0:
        rb = 4

    removed = held + ra + rb  # 归奇于扐
    log(120, f"_one_change: stalks={stalks}, split={split}, removed={removed}")
    return removed


def yarrow_one_line(rng: Optional[random.Random] = None) -> int:
    """完整的蓍草三变程序，生成一爻。

    三变流程:
    - 第一变: 49 → 去除5或9 → 剩44或40
    - 第二变: 44或40 → 去除4或8 → 剩40/36/32
    - 第三变: 40/36/32 → 去除4或8 → 剩36/32/28/24
    - 结果 = 剩余 ÷ 4 → 9/8/7/6

    Args:
        rng: 可选随机数生成器

    Returns:
        6-9 之间的爻值
    """
    rng = rng or random.Random()
    log(121, "yarrow_one_line: start")

    stalks = 49  # 大衍之数五十，其用四十有九

    # 第一变
    removed = _one_change(stalks, rng)
    stalks -= removed

    # 第二变
    removed = _one_change(stalks, rng)
    stalks -= removed

    # 第三变
    removed = _one_change(stalks, rng)
    stalks -= removed

    # 结果：剩余蓍草 ÷ 4
    value = stalks // 4
    log(122, f"yarrow_one_line: OK value={value}")
    return value  # 6, 7, 8, or 9


def cast_yarrow_hexagram(rng: Optional[random.Random] = None) -> Hexagram:
    """进行一次完整的蓍草法起卦（十八变）。

    从初爻 (bottom, position 1) 到上爻 (top, position 6)，
    每爻三变，共十八变。

    Args:
        rng: 可选随机数生成器

    Returns:
        六爻卦 Hexagram 对象
    """
    rng = rng or random.Random()
    log(123, "cast_yarrow_hexagram: start")
    values = [yarrow_one_line(rng) for _ in range(6)]
    hexagram = Hexagram.from_values(values)
    log(124, f"cast_yarrow_hexagram: OK values={values}, binary={hexagram.binary}")
    return hexagram


def get_yarrow_details() -> list[dict]:
    """模拟一次详细的蓍草演算记录。

    返回6组(从下到上)详细结果:
    - position: 爻位 (1-6)
    - value: 爻值 (6/7/8/9)
    - line_name: 爻名 (如 '初九', '六二')
    - changing: 是否为变爻
    - is_yang: 是否为阳
    - description: 文字描述

    Returns:
        6个字典的列表 (从下到上)
    """
    log(125, "get_yarrow_details: start")
    rng = random.Random()
    results = []
    base = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}

    for pos in range(1, 7):
        value = yarrow_one_line(rng)
        line_type = LineType(value)
        yao = "九" if line_type.is_yang else "六"

        results.append({
            "position": pos,
            "value": value,
            "line_name": f"{base[pos]}{yao}",
            "changing": line_type.is_changing,
            "is_yang": line_type.is_yang,
            "description": _describe_line(value),
        })

    log(126, f"get_yarrow_details: OK {len(results)} lines")
    return results


def _describe_line(value: int) -> str:
    """获取爻值的文字描述。"""
    descriptions = {
        6: "老阴（六）— 阴爻将变为阳",
        7: "少阳（七）— 阳爻不变",
        8: "少阴（八）— 阴爻不变",
        9: "老阳（九）— 阳爻将变为阴",
    }
    return descriptions.get(value, "")
