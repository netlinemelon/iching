"""
朱熹变爻解读规则 — Zhu Xi's Interpretation Rules

根据本卦变爻数量，确定应查阅哪些卦辞、爻辞作为主要和次要解读依据。

朱熹《易学启蒙》规则:
- 0变爻: 以本卦卦辞为主
- 1变爻: 以本卦变爻爻辞为主
- 2变爻: 以本卦两变爻爻辞为主，上爻为重
- 3变爻: 以本卦卦辞为主，兼看变卦卦辞
- 4变爻: 以变卦中不变爻爻辞为主
- 5变爻: 以变卦中不变爻爻辞为主
- 6变爻: 以变卦卦辞为主 (乾坤有用九用六)
"""

from dataclasses import dataclass, field
from typing import Optional

from app.engine.core import Hexagram


@dataclass
class InterpretationGuide:
    """解读指南 — 告诉用户应查阅哪些文本.

    Attributes:
        changing_positions: 变爻位置列表
        changing_count: 变爻数量
        primary_source: 主要资料来源标识
        primary_description: 主要解读规则描述 (中文)
        secondary_sources: 次要资料来源标识列表
        primary_lines: 应阅读的主要爻位 (1-indexed)
        secondary_lines: 应阅读的次要爻位
    """
    changing_positions: list[int]
    changing_count: int
    primary_source: str
    primary_description: str
    secondary_sources: list[str]
    primary_lines: list[int] = field(default_factory=list)
    secondary_lines: list[int] = field(default_factory=list)


def interpret(
    original: Hexagram,
    changed: Optional[Hexagram] = None,
) -> InterpretationGuide:
    """应用朱熹规则确定应查询哪些卦辞/爻辞.

    Args:
        original: 本卦 (original hexagram)
        changed: 变卦 (已计算好的变卦, optional)

    Returns:
        InterpretationGuide 解读指南
    """
    count = original.changing_count
    positions = original.changing_positions

    if count == 0:
        # 无变爻 — 以本卦卦辞为主
        return InterpretationGuide(
            changing_positions=positions,
            changing_count=0,
            primary_source="original_judgment",
            primary_description="无变爻，以本卦卦辞为主",
            secondary_sources=["original_xiang", "original_tuan"],
            primary_lines=[],
            secondary_lines=[],
        )

    elif count == 1:
        # 一爻变 — 以本卦变爻爻辞为主
        return InterpretationGuide(
            changing_positions=positions,
            changing_count=1,
            primary_source="changing_line",
            primary_description=f"一爻变，以本卦变爻（{_position_name(positions[0])}）爻辞为主",
            secondary_sources=["changed_judgment", "original_judgment"],
            primary_lines=positions,
            secondary_lines=[],
        )

    elif count == 2:
        # 二爻变 — 以两变爻爻辞为主，上爻为重
        upper_pos = max(positions)
        lower_pos = min(positions)
        return InterpretationGuide(
            changing_positions=positions,
            changing_count=2,
            primary_source="changing_lines",
            primary_description=f"二爻变，以本卦两变爻爻辞为主，上爻（{_position_name(upper_pos)}）为重",
            secondary_sources=["original_judgment"],
            primary_lines=[upper_pos],
            secondary_lines=[lower_pos],
        )

    elif count == 3:
        # 三爻变 — 以本卦卦辞为主，兼看变卦卦辞
        return InterpretationGuide(
            changing_positions=positions,
            changing_count=3,
            primary_source="original_judgment",
            primary_description="三爻变，以本卦卦辞为主，兼看变卦卦辞",
            secondary_sources=["changed_judgment", "changing_lines"],
            primary_lines=[],
            secondary_lines=positions,
        )

    elif count == 4:
        # 四爻变 — 以变卦中不变爻爻辞为主
        unchanged = [p for p in range(1, 7) if p not in positions]
        lower = min(unchanged)
        upper = max(unchanged)
        return InterpretationGuide(
            changing_positions=positions,
            changing_count=4,
            primary_source="unchanged_lines",
            primary_description=(
                f"四爻变，以变卦中不变爻爻辞为主，"
                f"下爻（{_position_name(lower)}）为重"
            ),
            secondary_sources=["changed_judgment"],
            primary_lines=[lower],
            secondary_lines=[upper],
        )

    elif count == 5:
        # 五爻变 — 以变卦中唯一不变爻爻辞为主
        unchanged = [p for p in range(1, 7) if p not in positions][0]
        return InterpretationGuide(
            changing_positions=positions,
            changing_count=5,
            primary_source="unchanged_line",
            primary_description=f"五爻变，以变卦中不变爻（{_position_name(unchanged)}）爻辞为主",
            secondary_sources=["changed_judgment"],
            primary_lines=[unchanged],
            secondary_lines=[],
        )

    elif count == 6:
        # 六爻全变
        original_binary = original.binary
        if original_binary == "111111":
            # 乾卦 — 用九见群龙无首吉
            return InterpretationGuide(
                changing_positions=positions,
                changing_count=6,
                primary_source="extra_line",
                primary_description="六爻全变，乾卦以用九为主",
                secondary_sources=["changed_judgment"],
                primary_lines=[7],  # 7 表示用九 (特殊爻)
                secondary_lines=[],
            )
        elif original_binary == "000000":
            # 坤卦 — 用六利永贞
            return InterpretationGuide(
                changing_positions=positions,
                changing_count=6,
                primary_source="extra_line",
                primary_description="六爻全变，坤卦以用六为主",
                secondary_sources=["changed_judgment"],
                primary_lines=[7],  # 7 表示用六 (特殊爻)
                secondary_lines=[],
            )
        else:
            # 其他卦 — 以变卦卦辞为主
            return InterpretationGuide(
                changing_positions=positions,
                changing_count=6,
                primary_source="changed_judgment",
                primary_description="六爻全变，以变卦卦辞为主",
                secondary_sources=["changed_xiang", "changed_tuan"],
                primary_lines=[],
                secondary_lines=[],
            )

    raise ValueError(f"意外的变爻数量: {count}")


def _position_name(pos: int) -> str:
    """将数字爻位转换为传统称谓.

    Args:
        pos: 爻位 (1-6), 7 表示用爻 (用九/用六)

    Returns:
        传统称谓: 初, 二, 三, 四, 五, 上, 用爻
    """
    if pos == 7:
        return "用爻"
    base = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}
    return base.get(pos, str(pos))
