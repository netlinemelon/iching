"""
Pydantic Schemas — API 请求与响应模型

定义所有数据交换格式，包括占卜请求/响应、卦象详情、历史记录等。
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CoinTossRequest(BaseModel):
    """金钱卦占卜请求。"""
    method: str = Field(default="coin", description="占卜方法")
    seed: Optional[int] = Field(default=None, description="随机数种子（用于测试可重现）")


class LineDetail(BaseModel):
    """卦中一爻的详细信息。"""
    position: int
    name: str
    text: str
    xiang: str
    changing: bool
    is_yang: bool
    value: int


class InterpretationResult(BaseModel):
    """朱子变爻解读规则的结果。"""
    primary_source: str
    primary_description: str
    primary_lines: list[int]
    secondary_sources: list[str]
    secondary_lines: list[int]
    changing_count: int
    changing_positions: list[int]


class HexagramSummary(BaseModel):
    """卦象摘要 — 用于网格/列表显示。"""
    number: int
    binary: str
    name_cn: str
    name_pinyin: str
    unicode: str
    upper_trigram_name: str
    lower_trigram_name: str
    judgment_brief: str


class HexagramDetail(BaseModel):
    """卦象详情 — 用于研读/浏览视图。"""
    number: int
    binary: str
    name: dict
    unicode: str
    upper_trigram: dict
    lower_trigram: dict
    judgment: dict
    tuan: dict
    xiang: dict
    lines: list[dict]
    extra_lines: Optional[list[dict]] = None


class TossDetail(BaseModel):
    """单次铜钱抛掷的详细信息。"""
    position: int
    coins: list[int]
    sum: int
    line_name: str
    changing: bool
    is_yang: bool


class DivinationResponse(BaseModel):
    """完整的占卜结果响应。"""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    method: str

    # 本卦
    original_binary: str
    original_values: list[int]
    original_number: int
    original_name_cn: str
    original_name_pinyin: str
    original_unicode: str
    original_judgment: str

    # 变爻
    changing_positions: list[int]
    changing_count: int

    # 变卦
    changed_binary: Optional[str] = None
    changed_number: Optional[int] = None
    changed_name_cn: Optional[str] = None
    changed_name_pinyin: Optional[str] = None
    changed_unicode: Optional[str] = None
    changed_judgment: Optional[str] = None

    # 解读
    interpretation: dict

    # 相关卦象
    mutual_hexagram: Optional[dict] = None
    opposite_hexagram: Optional[dict] = None
    reverse_hexagram: Optional[dict] = None

    # 体用分析
    body_use: Optional[dict] = None

    # 爻详情
    lines: list[dict]

    # 铜钱抛掷详情
    toss_details: Optional[list[dict]] = None

    # 分享与元数据
    share_token: Optional[str] = None
    is_favorite: bool = False


class HistoryRecord(BaseModel):
    """历史记录摘要。"""
    id: int
    created_at: str
    method: str
    original_binary: str
    original_name_cn: str
    original_unicode: str
    changing_positions: list[int]
    changed_binary: Optional[str] = None
    changed_name_cn: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: bool = False


class HistoryDetail(BaseModel):
    """历史记录详情。"""
    id: int
    created_at: str
    method: str
    original_binary: str
    original_values: list[int]
    original_name_cn: str
    original_name_pinyin: str
    original_unicode: str
    original_judgment: str
    changing_positions: list[int]
    changing_count: int
    changed_binary: Optional[str] = None
    changed_number: Optional[int] = None
    changed_name_cn: Optional[str] = None
    changed_name_pinyin: Optional[str] = None
    changed_unicode: Optional[str] = None
    changed_judgment: Optional[str] = None
    interpretation: dict
    mutual_hexagram: Optional[dict] = None
    opposite_hexagram: Optional[dict] = None
    reverse_hexagram: Optional[dict] = None
    body_use: Optional[dict] = None
    lines: list[dict]
    toss_details: Optional[list[dict]] = None
    notes: Optional[str] = None
    is_favorite: bool = False
    share_token: Optional[str] = None
