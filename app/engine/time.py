"""
时间起卦模块 — Time-based Divination Method

以当前年月日时起卦，无需任何工具，随时随地可占。

算法:
- (年 + 月 + 日) mod 8 → 上卦
- (月 + 日 + 时) mod 8 → 下卦
- (年 + 月 + 日 + 时) mod 6 → 动爻位置 (1-6)

其中"时"为地支时辰序数 (子=1, 丑=2, ..., 亥=12)。

先天八卦数: 1=乾, 2=兑, 3=离, 4=震, 5=巽, 6=坎, 7=艮, 8=坤
"""

from datetime import datetime
from typing import Optional

from app.engine.core import Hexagram
from app.debug import log

# 先天八卦数：序数→名称映射
TRIGRAM_ORDINAL = {
    1: "乾", 2: "兑", 3: "离", 4: "震",
    5: "巽", 6: "坎", 7: "艮", 8: "坤",
}

# 八卦名称→3位二进制映射
TRIGRAM_NAME_TO_BINARY = {
    "乾": "111", "兑": "110", "离": "101", "震": "100",
    "巽": "011", "坎": "010", "艮": "001", "坤": "000",
}

# 地支时辰→序数
# 子=1, 丑=2, 寅=3, 卯=4, 辰=5, 巳=6
# 午=7, 未=8, 申=9, 酉=10, 戌=11, 亥=12
HOUR_TO_BRANCH = {
    0: 1, 1: 1,   # 子时 23:00-00:59
    2: 2, 3: 2,   # 丑时 01:00-02:59
    4: 3, 5: 3,   # 寅时 03:00-04:59
    6: 4, 7: 4,   # 卯时 05:00-06:59
    8: 5, 9: 5,   # 辰时 07:00-08:59
    10: 6, 11: 6,  # 巳时 09:00-10:59
    12: 7, 13: 7,  # 午时 11:00-12:59
    14: 8, 15: 8,  # 未时 13:00-14:59
    16: 9, 17: 9,  # 申时 15:00-16:59
    18: 10, 19: 10,  # 酉时 17:00-18:59
    20: 11, 21: 11,  # 戌时 19:00-20:59
    22: 12, 23: 12,  # 亥时 21:00-22:59
}


def _ordinal_to_value(ordinal: int) -> int:
    """将先天八卦序数转换为爻值 (7=阳/8=阴)。

    Args:
        ordinal: 八卦序数 (1-8)

    Returns:
        7 (阳) 或 8 (阴)
    """
    return 7 if ordinal % 2 == 1 else 8


def _build_values_from_binary(binary: str, changing_line: int) -> list[int]:
    """从6位二进制和动爻位置构建爻值列表。

    Args:
        binary: 6位二进制字符串 (上卦+下卦)
        changing_line: 动爻位置 (1-6)

    Returns:
        6个爻值的列表 (6/7/8/9)
    """
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
            # 动爻：阳变老阳(9)，阴变老阴(6)
            values.append(9 if base_val == 7 else 6)
        else:
            values.append(base_val)

    return values


def cast_time_hexagram(dt: Optional[datetime] = None) -> Hexagram:
    """以当前日期时间起卦。

    算法:
    - (年 + 月 + 日) mod 8 → 上卦 (余0则取8)
    - (月 + 日 + 时辰) mod 8 → 下卦 (余0则取8)
    - (年 + 月 + 日 + 时辰) mod 6 → 动爻 (余0则取6)

    Args:
        dt: 日期时间对象，默认使用当前时间

    Returns:
        六爻卦 Hexagram 对象
    """
    dt = dt or datetime.now()
    log(130, f"cast_time_hexagram: start dt={dt}")

    year = dt.year
    month = dt.month
    day = dt.day
    hour_branch = HOUR_TO_BRANCH.get(dt.hour, 1)

    # 上卦
    upper_ord = (year + month + day) % 8
    if upper_ord == 0:
        upper_ord = 8

    # 下卦
    lower_ord = (month + day + hour_branch) % 8
    if lower_ord == 0:
        lower_ord = 8

    # 动爻
    changing_line = (year + month + day + hour_branch) % 6
    if changing_line == 0:
        changing_line = 6

    upper_name = TRIGRAM_ORDINAL[upper_ord]
    lower_name = TRIGRAM_ORDINAL[lower_ord]
    binary = TRIGRAM_NAME_TO_BINARY[upper_name] + TRIGRAM_NAME_TO_BINARY[lower_name]

    values = _build_values_from_binary(binary, changing_line)
    hexagram = Hexagram.from_values(values)
    log(131, f"cast_time_hexagram: OK binary={hexagram.binary}, changing_line={changing_line}")
    return hexagram


def get_time_details(dt: Optional[datetime] = None) -> dict:
    """获取时间起卦的详细时间信息。

    Args:
        dt: 日期时间对象，默认使用当前时间

    Returns:
        包含详细时间信息的字典
    """
    dt = dt or datetime.now()
    log(132, f"get_time_details: start dt={dt}")

    branch_names = {
        1: "子", 2: "丑", 3: "寅", 4: "卯", 5: "辰", 6: "巳",
        7: "午", 8: "未", 9: "申", 10: "酉", 11: "戌", 12: "亥",
    }
    hour_branch = HOUR_TO_BRANCH.get(dt.hour, 1)

    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "hour": dt.hour,
        "hour_branch": hour_branch,
        "hour_branch_name": branch_names.get(hour_branch, ""),
        "weekday": dt.strftime("%A"),
        "datetime_str": dt.strftime("%Y年%m月%d日 %H:%M"),
        "lunar_note": "（实际应用建议使用农历日期）",
    }
