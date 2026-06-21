"""
金钱卦起卦模块 — 3-Coin Divination Method

传统三枚铜钱起卦法 (金钱卦):
- 每枚铜钱: 正面(字/head)=3, 背面(花/tail)=2
- 每次抛掷三枚: 和值 6-9
- 共抛6次, 从下往上建卦
"""

import random
from typing import Optional

from app.engine.core import Hexagram, LineType
from app.debug import log


def toss_three_coins(rng: Optional[random.Random] = None) -> int:
    """抛三枚铜钱，返回和值 (6-9).

    每枚铜钱: 正面=3, 反面=2.
    三反=6 (老阴), 二反一正=7 (少阳), 一反二正=8 (少阴), 三正=9 (老阳).

    Args:
        rng: 可选随机数生成器，用于可重现测试

    Returns:
        6-9 之间的和值
    """
    rng = rng or random.Random()
    values = [rng.choice([2, 3]) for _ in range(3)]
    total = sum(values)
    log(110, f"toss_three_coins: coins={values}, sum={total}")
    return total


def cast_hexagram(rng: Optional[random.Random] = None) -> Hexagram:
    """进行一次完整的六爻金钱卦占卜.

    从初爻 (bottom, position 1) 到上爻 (top, position 6) 逐爻生成.

    Args:
        rng: 可选随机数生成器

    Returns:
        六爻卦 Hexagram 对象
    """
    rng = rng or random.Random()
    log(111, "cast_hexagram: start")
    values = [toss_three_coins(rng) for _ in range(6)]
    hexagram = Hexagram.from_values(values)
    log(112, f"cast_hexagram: OK values={values}, binary={hexagram.binary}")
    return hexagram


def simulate_toss_history() -> list[dict]:
    """模拟一次详细的铜钱抛掷记录.

    返回6组(从下到上)详细结果，每组包含:
    - coins: [2或3, ...] — 每枚铜钱的值
    - sum: 和值 (6-9)
    - line_name: 爻名 (如 '初九', '六二')
    - changing: 是否为变爻
    - is_yang: 是否为阳

    Returns:
        6个字典的列表 (从下到上)
    """
    log(113, "simulate_toss_history: start")
    rng = random.Random()
    results = []
    for pos in range(1, 7):
        coins = [rng.choice([2, 3]) for _ in range(3)]
        value = sum(coins)
        line_type = LineType.from_coin_value(value)

        # 传统爻名
        base = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}
        yao = "九" if line_type.is_yang else "六"

        results.append({
            "position": pos,
            "coins": coins,
            "sum": value,
            "line_name": f"{base[pos]}{yao}",
            "changing": line_type.is_changing,
            "is_yang": line_type.is_yang,
        })

    log(114, f"simulate_toss_history: OK {len(results)} lines")
    return results
