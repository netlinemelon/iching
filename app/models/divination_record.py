"""
占卜记录 ORM 模型 — Divination Record SQLAlchemy Model

使用 SQLAlchemy 将占卜结果持久化到 SQLite 数据库。
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON

from app.database import Base


class DivinationRecord(Base):
    """占卜历史记录表。"""
    __tablename__ = "divination_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    method = Column(String(50), nullable=False, default="coin")
    original_binary = Column(String(6), nullable=False)
    original_values = Column(JSON, nullable=False)  # [6,7,8,9,...] 从下到上
    changed_binary = Column(String(6), nullable=True)
    changing_positions = Column(JSON, nullable=False)  # [1,3,5] 等
    notes = Column(Text, nullable=True)
    question = Column(Text, nullable=True, default="")
    ai_interpretation = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)
    share_token = Column(String(36), nullable=True, unique=True, index=True)

    @classmethod
    def generate_share_token(cls) -> str:
        """生成用于分享的唯一令牌。"""
        return str(uuid.uuid4())

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "method": self.method,
            "original_binary": self.original_binary,
            "original_values": self.original_values,
            "changed_binary": self.changed_binary,
            "changing_positions": self.changing_positions,
            "notes": self.notes,
            "is_favorite": self.is_favorite,
            "share_token": self.share_token,
        }


class SyncCode(Base):
    """同步码表 — 用于跨设备数据同步，支持多 worker。"""
    __tablename__ = "sync_codes"

    code = Column(String(8), primary_key=True)
    records = Column(Text, nullable=False)  # JSON 序列化的记录数据
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    max_accesses = Column(Integer, default=3)
