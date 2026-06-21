"""
六十四卦与八卦数据加载模块 — Hexagram & Trigram Data Loader

从 JSON 文件加载卦象数据，提供查找和搜索功能。
数据在首次加载后缓存到内存中。
"""

import json
from pathlib import Path
from functools import lru_cache

from app.debug import log
from app.config import settings


@lru_cache(maxsize=1)
def load_hexagrams() -> list[dict]:
    """加载全部64卦数据。JSON文件在首次调用后缓存。"""
    path = settings.data_dir / "hexagrams.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_trigrams() -> list[dict]:
    """加载全部8卦数据。JSON文件在首次调用后缓存。"""
    path = settings.data_dir / "trigrams.json"
    return json.loads(path.read_text(encoding="utf-8"))


def get_hexagram_by_binary(binary: str) -> dict | None:
    """通过6位二进制字符串查找卦象。

    Args:
        binary: 6位二进制字符串，格式为"上卦+下卦"（如 "111111"）

    Returns:
        卦象字典，未找到则返回 None
    """
    for h in load_hexagrams():
        if h["binary"] == binary:
            return h
    log(250, f"get_hexagram_by_binary: NOT FOUND binary={binary}", level="WARN")
    return None


def get_hexagram_by_number(number: int) -> dict | None:
    """通过序号（1-64）查找卦象。

    Args:
        number: 卦序（1-64）

    Returns:
        卦象字典，序号无效则返回 None
    """
    hexagrams = load_hexagrams()
    if 1 <= number <= 64:
        return hexagrams[number - 1]
    return None


def get_trigram_by_binary(binary: str) -> dict | None:
    """通过3位二进制字符串查找八卦。

    Args:
        binary: 3位二进制字符串

    Returns:
        八卦字典，未找到则返回 None
    """
    for t in load_trigrams():
        if t["binary"] == binary:
            return t
    return None


def search_hexagrams(query: str) -> list[dict]:
    """按关键词搜索卦象。

    在卦名、卦辞、爻辞中搜索匹配项。

    Args:
        query: 搜索关键词

    Returns:
        匹配的卦象列表
    """
    query_lower = query.lower()
    results = []
    for h in load_hexagrams():
        # 搜索卦名
        name_cn = h["name"]["cn"]
        name_en = h["name"]["en"].lower()
        name_pinyin = h["name"]["pinyin"].lower()
        if query in name_cn or query_lower in name_en or query_lower in name_pinyin:
            results.append(h)
            continue

        # 搜索卦辞
        if query in h["judgment"]["cn"]:
            results.append(h)
            continue

        # 搜索爻辞
        for line in h.get("lines", []):
            if query in line.get("text", ""):
                results.append(h)
                break

    return results


def get_all_hexagrams() -> list[dict]:
    """获取全部64卦。"""
    return load_hexagrams()
