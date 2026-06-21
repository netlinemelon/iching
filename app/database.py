"""
数据库配置模块 — Database Configuration

提供 SQLAlchemy 引擎、会话工厂和声明式基类。
独立于 app.main 以避免循环导入。
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.debug import log


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""
    pass


engine = create_async_engine(settings.database_url, echo=settings.debug)
log(30, f"database: engine created, url='{settings.database_url}'")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
log(31, "database: async_session factory created")
