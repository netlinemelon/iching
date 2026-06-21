"""
数字起卦模块 — Number-based Divination Method

任意输入三个数字起卦，简单快捷。

算法:
- 第一个数字 mod 8 → 上卦 (余0则取8)
- 第二个数字 mod 8 → 下卦 (余0则取8)
- 第三个数字 mod 6 → 动爻位置 (余0则取6)

先天八卦数: 1=乾, 2=兑, 3=离, 4=震, 5=巽, 6=坎, 7=艮, 8=坤
"""

import random
from typing import Optional

from app.engine.core import Hexagram

# 先天八卦数：序数→名称映射
TRIGRAM_ORDINAL = {
    1: "乾", 2: "兑", 3: "离", 4: "震",
    5: "巽", 6: "坎", 7: "艮", 8: "坤",
}

# 八卦名称→3位二进制
TRIGRAM_BINARY = {
    "乾": "111", "兑": "110", "离": "101", "震": "100",
    "巽": "011", "坎": "010", "艮": "001", "坤": "000",
}


def ordinal_to_trigram(ordinal: int) -> str:
    """将先天八卦序数 (1-8) 转换为3位二进制字符串。

    Args:
        ordinal: 先天八卦序数 (1-8)，1=乾, 8=坤

    Returns:
        3位二进制字符串

    Raises:
        ValueError: 序数不在 1-8 范围内
    """
    if ordinal < 1 or ordinal > 8:
        raise ValueError(f"八卦序数必须为 1-8, 实际得到 {ordinal}")
    return TRIGRAM_BINARY[TRIGRAM_ORDINAL[ordinal]]


def cast_number_hexagram(n1: int, n2: int, n3: int) -> Hexagram:
    """以3个数字起卦。

    Args:
        n1: 第一个数字，决定上卦 (mod 8)
        n2: 第二个数字，决定下卦 (mod 8)
        n3: 第三个数字，决定动爻位置 (mod 6)

    Returns:
        六爻卦 Hexagram 对象
    """
    upper_ord = n1 % 8
    if upper_ord == 0:
        upper_ord = 8

    lower_ord = n2 % 8
    if lower_ord == 0:
        lower_ord = 8

    changing_line = n3 % 6
    if changing_line == 0:
        changing_line = 6

    upper_bin = ordinal_to_trigram(upper_ord)
    lower_bin = ordinal_to_trigram(lower_ord)
    binary = upper_bin + lower_bin

    values = []
    for pos in range(1, 7):
        # 映射爻位到二进制索引
        # Hexagram.binary 格式: [pos4][pos5][pos6][pos1][pos2][pos3]
        # pos 1→binary[3], 2→binary[4], 3→binary[5]
        # pos 4→binary[0], 5→binary[1], 6→binary[2]
        bin_idx = pos + 2 if pos <= 3 else pos - 4

        digit = binary[bin_idx]
        base_val = 7 if digit == "1" else 8
        if pos == changing_line:
            values.append(9 if base_val == 7 else 6)
        else:
            values.append(base_val)

    return Hexagram.from_values(values)


def generate_random_numbers() -> tuple[int, int, int]:
    """生成3个随机数字用于数字起卦。

    Returns:
        (n1, n2, n3) 三个随机整数 (1-999)
    """
    rng = random.SystemRandom()
    return (
        rng.randint(1, 999),
        rng.randint(1, 999),
        rng.randint(1, 999),
    )
