"""
易经八卦核心类型系统 — Core Type System & Enums

定义六爻占卜的全部基础数据类型：爻的类型、八卦枚举、爻与卦的数据类。
"""

from enum import Enum, IntEnum
from dataclasses import dataclass, field
from typing import Optional

from app.debug import log


class LineType(IntEnum):
    """六爻的四种可能状态 (the four possible line values from divination)."""
    OLD_YIN = 6      # 老阴 — 变爻，阴变阳 (broken → solid)
    YOUNG_YANG = 7   # 少阳 — 不变阳 (stable yang, solid)
    YOUNG_YIN = 8    # 少阴 — 不变阴 (stable yin, broken)
    OLD_YANG = 9     # 老阳 — 变爻，阳变阴 (solid → broken)

    @property
    def is_changing(self) -> bool:
        """是否为变爻（老阴或老阳）?"""
        return self in (LineType.OLD_YIN, LineType.OLD_YANG)

    @property
    def is_yang(self) -> bool:
        """当前状态是否为阳?"""
        return self in (LineType.YOUNG_YANG, LineType.OLD_YANG)

    @property
    def as_binary(self) -> str:
        """当前状态的二进制表示 (1=阳, 0=阴)."""
        return "1" if self.is_yang else "0"

    @property
    def changed_binary(self) -> str:
        """变爻后的二进制表示. 不变爻则返回当前状态."""
        if self.is_changing:
            return "0" if self.is_yang else "1"
        return self.as_binary

    @staticmethod
    def from_coin_value(value: int) -> "LineType":
        """将三枚铜钱的和值映射为爻类型.

        每枚铜钱: 正面=3, 反面=2
        和值范围: 6(三反)→老阴, 7(二反一正)→少阳, 8(一反二正)→少阴, 9(三正)→老阳
        """
        mapping = {
            6: LineType.OLD_YIN,
            7: LineType.YOUNG_YANG,
            8: LineType.YOUNG_YIN,
            9: LineType.OLD_YANG,
        }
        if value not in mapping:
            raise ValueError(f"无效的铜钱和值: {value}, 必须为 6-9")
        return mapping[value]


class TrigramBagua(Enum):
    """八卦 (the eight trigrams).

    每个八卦成员包含:
    - binary: 3位二进制字符串 (上爻←初爻)
    - name_cn: 中文名称
    - nature: 卦象 (自然象征)
    - element: 五行属性
    - unicode: 八卦符号
    """
    QIAN = ("111", "乾", "天", "金", "☰")
    DUI = ("110", "兑", "泽", "金", "☱")
    LI = ("101", "离", "火", "火", "☲")
    ZHEN = ("100", "震", "雷", "木", "☳")
    XUN = ("011", "巽", "风", "木", "☴")
    KAN = ("010", "坎", "水", "水", "☵")
    GEN = ("001", "艮", "山", "土", "☶")
    KUN = ("000", "坤", "地", "土", "☷")

    def __init__(self, binary: str, name_cn: str, nature: str, element: str, unicode: str):
        self._binary = binary
        self._name_cn = name_cn
        self._nature = nature
        self._element = element
        self._unicode = unicode

    @property
    def binary(self) -> str:
        """3位二进制字符串."""
        return self._binary

    @property
    def name_cn(self) -> str:
        """中文名称 (如: 乾, 坤)."""
        return self._name_cn

    @property
    def nature(self) -> str:
        """卦象—自然象征 (如: 天, 地, 火)."""
        return self._nature

    @property
    def element(self) -> str:
        """五行属性 (金/木/水/火/土)."""
        return self._element

    @property
    def unicode(self) -> str:
        """八卦Unicode符号 (如: ☰, ☷)."""
        return self._unicode

    @classmethod
    def from_binary(cls, binary: str) -> "TrigramBagua":
        """通过3位二进制字符串查找八卦."""
        for t in cls:
            if t.binary == binary:
                return t
        raise ValueError(f"未知的八卦二进制: {binary}")

    @classmethod
    def from_name(cls, name: str) -> "TrigramBagua":
        """通过中文名称查找八卦."""
        for t in cls:
            if t.name_cn == name:
                return t
        raise ValueError(f"未知的八卦名称: {name}")


@dataclass
class Line:
    """六爻中的一爻 (a single line in a hexagram).

    Attributes:
        position: 爻位 1-6，从下往上 (bottom to top)
        line_type: 爻的类型 (6老阴/7少阳/8少阴/9老阳)
        text: 爻辞原文
        xiang: 象传原文
    """
    position: int  # 1-6, bottom to top
    line_type: LineType
    text: str = ""
    xiang: str = ""

    @property
    def name(self) -> str:
        """传统爻名: 初九、九二、九三、六四、九五、上六 等.

        命名规则:
        - 初爻 (position 1): "初" + 九/六
        - 中爻 (positions 2-5): 九/六 + 二/三/四/五
        - 上爻 (position 6): "上" + 九/六
        """
        yao = "九" if self.line_type.is_yang else "六"
        if self.position == 1:
            return f"初{yao}"
        elif self.position == 6:
            return f"上{yao}"
        else:
            middle = {2: "二", 3: "三", 4: "四", 5: "五"}
            return f"{yao}{middle[self.position]}"

    @property
    def is_changing(self) -> bool:
        """是否为变爻?"""
        return self.line_type.is_changing

    @property
    def as_binary(self) -> str:
        """当前状态的二进制位."""
        return self.line_type.as_binary

    @property
    def changed_binary(self) -> str:
        """变爻后的二进制位."""
        return self.line_type.changed_binary


@dataclass
class Hexagram:
    """六爻卦 (a six-line hexagram).

    包含6爻，index 0 为初爻（最下），index 5 为上爻（最上）。

    Attributes:
        lines: 6个爻的列表，从下到上 (bottom to top)
    """
    lines: list[Line]  # index 0 = bottom (position 1), index 5 = top (position 6)

    def __post_init__(self):
        """初始化后验证: 必须恰好6爻, 并修正爻位."""
        if len(self.lines) != 6:
            log(100, f"Hexagram.__post_init__: invalid line count {len(self.lines)}", level="ERROR")
            raise ValueError(f"六爻卦必须有恰好6个爻, 实际得到 {len(self.lines)}")
        for i, line in enumerate(self.lines):
            if line.position != i + 1:
                line.position = i + 1
        log(101, "Hexagram.__post_init__: validation OK")

    @property
    def binary(self) -> str:
        """6位二进制字符串: 上卦 + 下卦 (upper trigram + lower trigram).

        注意: 第1-3位是下卦 (内卦), 第4-6位是上卦 (外卦).
        这是标准的 binary 排列: 最左是上卦最上爻, 最右是下卦最下爻.
        """
        upper = "".join(l.as_binary for l in self.lines[3:])   # positions 4,5,6 → 上卦
        lower = "".join(l.as_binary for l in self.lines[:3])    # positions 1,2,3 → 下卦
        return upper + lower

    @property
    def changed_binary(self) -> str:
        """变爻翻转后的二进制字符串."""
        upper = "".join(l.changed_binary for l in self.lines[3:])
        lower = "".join(l.changed_binary for l in self.lines[:3])
        return upper + lower

    @property
    def upper_trigram(self) -> TrigramBagua:
        """上卦 (外卦) — 二进制前3位."""
        return TrigramBagua.from_binary(self.binary[:3])

    @property
    def lower_trigram(self) -> TrigramBagua:
        """下卦 (内卦) — 二进制后3位."""
        return TrigramBagua.from_binary(self.binary[3:])

    @property
    def changing_positions(self) -> list[int]:
        """变爻所在位置列表 (1-6)."""
        return [i + 1 for i, line in enumerate(self.lines) if line.is_changing]

    @property
    def changing_count(self) -> int:
        """变爻数量."""
        return len(self.changing_positions)

    @property
    def line_values(self) -> list[int]:
        """原始数值列表 (6/7/8/9), 从下到上."""
        return [line.line_type.value for line in self.lines]

    @classmethod
    def from_values(cls, values: list[int]) -> "Hexagram":
        """从6个数值 (6/7/8/9, 从下到上) 创建六爻卦."""
        log(102, f"Hexagram.from_values: start values={values}")
        if len(values) != 6:
            log(103, f"Hexagram.from_values: invalid count {len(values)}", level="ERROR")
            raise ValueError(f"需要恰好6个值, 实际得到 {len(values)}")
        lines = [Line(position=i + 1, line_type=LineType(v)) for i, v in enumerate(values)]
        hexagram = cls(lines=lines)
        log(104, f"Hexagram.from_values: OK binary={hexagram.binary}")
        return hexagram

    @classmethod
    def from_binary(cls, binary: str) -> "Hexagram":
        """从6位二进制字符串创建六爻卦. 所有爻均为稳定爻 (无变爻)."""
        log(105, f"Hexagram.from_binary: start binary='{binary}'")
        if len(binary) != 6 or any(c not in "01" for c in binary):
            log(106, f"Hexagram.from_binary: invalid binary '{binary}'", level="ERROR")
            raise ValueError(f"二进制字符串必须为6位0/1, 实际得到: {binary}")
        # 从上卦+下卦的顺序: binary[:3]是上卦, binary[3:]是下卦
        # 但 lines 从下到上: lines[0]=position1, ..., lines[5]=position6
        # 所以我们要把 binary 倒序: binary[5]→line[0](初爻), binary[0]→line[5](上爻)
        values = [(7 if c == "1" else 8) for c in reversed(binary)]
        hexagram = cls.from_values(values)
        log(107, f"Hexagram.from_binary: OK")
        return hexagram
