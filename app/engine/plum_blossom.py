"""
梅花易数起卦模块 — Plum Blossom Divination Method

邵雍（邵康节）所创，以物象、声音、方位、时间等起卦。
万物皆可归类于八卦，从观察到的现象推演卦象。

核心方法:
1. 根据观察到的现象确定上卦和下卦
2. 根据时间或互动规则确定动爻
3. 应用体用生克分析进行解读

万物类象分类:
乾: 天、君、父、头、马、金、玉、圆物...
兑: 泽、少女、口、羊、金、毁折...
离: 火、中女、目、雉、日、电...
震: 雷、长男、足、龙、动...
巽: 风、长女、股、鸡、木、入...
坎: 水、中男、耳、豕、险...
艮: 山、少男、手、犬、止...
坤: 地、母、腹、牛、顺...
"""

from datetime import datetime
from typing import Optional

from app.engine.core import Hexagram
from app.engine.time import HOUR_TO_BRANCH

# 八卦名称→3位二进制
TRIGRAM_BINARY = {
    "乾": "111", "兑": "110", "离": "101", "震": "100",
    "巽": "011", "坎": "010", "艮": "001", "坤": "000",
}

# 万物类象 — Categories for associating phenomena with trigrams
PHENOMENA_MAP = {
    "乾": ["天", "君", "父", "头", "马", "金", "玉", "圆物", "冰", "寒", "西北", "大赤", "良马", "老马", "瘠马", "驳马", "木果"],
    "兑": ["泽", "少女", "口", "羊", "金", "毁折", "巫", "妾", "西", "口舌", "缺", "附决"],
    "离": ["火", "中女", "目", "雉", "日", "电", "文书", "南", "明", "甲胄", "戈兵", "大腹", "鳖", "蟹", "蚌", "龟"],
    "震": ["雷", "长男", "足", "龙", "动", "东", "青", "大涂", "决躁", "玄黄", "萑苇", "鼓"],
    "巽": ["风", "长女", "股", "鸡", "木", "入", "东南", "长", "高", "白", "臭", "绳直"],
    "坎": ["水", "中男", "耳", "豕", "险", "北", "隐伏", "弓轮", "月", "沟渎", "矫輮", "加忧"],
    "艮": ["山", "少男", "手", "犬", "止", "东北", "径路", "石", "门阙", "果蓏", "鼠"],
    "坤": ["地", "母", "腹", "牛", "顺", "西南", "众", "布", "釜", "吝啬", "均", "子母牛", "大舆"],
}


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
            values.append(9 if base_val == 7 else 6)
        else:
            values.append(base_val)

    return values


def cast_plum_blossom_hexagram(
    upper_trigram_name: str,
    lower_trigram_name: str,
    changing_line: Optional[int] = None,
) -> Hexagram:
    """梅花易数起卦，以指定的上下卦和动爻生成卦象。

    Args:
        upper_trigram_name: 上卦名称 (乾/兑/离/震/巽/坎/艮/坤)
        lower_trigram_name: 下卦名称 (乾/兑/离/震/巽/坎/艮/坤)
        changing_line: 动爻位置 (1-6)。若为None，根据当前时辰计算。

    Returns:
        六爻卦 Hexagram 对象

    Raises:
        ValueError: 无效的八卦名称
    """
    if upper_trigram_name not in TRIGRAM_BINARY:
        raise ValueError(f"无效的上卦名称: {upper_trigram_name}")
    if lower_trigram_name not in TRIGRAM_BINARY:
        raise ValueError(f"无效的下卦名称: {lower_trigram_name}")

    upper_bin = TRIGRAM_BINARY[upper_trigram_name]
    lower_bin = TRIGRAM_BINARY[lower_trigram_name]
    binary = upper_bin + lower_bin

    if changing_line is None:
        # 使用当前时辰确定动爻
        hour_branch = HOUR_TO_BRANCH.get(datetime.now().hour, 1)
        changing_line = hour_branch % 6
        if changing_line == 0:
            changing_line = 6

    values = _build_values_from_binary(binary, changing_line)
    return Hexagram.from_values(values)


def classify_phenomenon(keyword: str) -> Optional[str]:
    """将现象描述归类为八卦名称。

    遍历万物类象表，查找匹配的卦名。

    Args:
        keyword: 用于匹配的描述性词语

    Returns:
        八卦名称 (如 "乾", "坤")，未找到则返回 None
    """
    for trigram_name, keywords in PHENOMENA_MAP.items():
        for kw in keywords:
            if kw == keyword or (len(keyword) >= 2 and kw in keyword):
                return trigram_name
    # 尝试部分匹配
    for trigram_name, keywords in PHENOMENA_MAP.items():
        for kw in keywords:
            if keyword in kw or kw in keyword:
                return trigram_name
    return None


def get_phenomena_categories() -> dict:
    """获取所有万物类象分类表。

    Returns:
        八卦名称→关键词列表 的映射字典
    """
    return dict(PHENOMENA_MAP)
