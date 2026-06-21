from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import engine, async_session, Base
from app.debug import log

templates = Jinja2Templates(directory=str(settings.template_dir))


from sqlalchemy import text


def _migrate_db(conn):
    """数据库迁移：为新增加的列执行 ALTER TABLE。"""
    log(11, "_migrate_db: start checking columns")
    result = conn.execute(text("PRAGMA table_info(divination_records)"))
    cols = {row[1] for row in result.fetchall()}
    if "question" not in cols:
        log(12, "_migrate_db: adding question column via ALTER TABLE")
        conn.execute(
            text("ALTER TABLE divination_records ADD COLUMN question TEXT DEFAULT ''")
        )
    if "ai_interpretation" not in cols:
        log(14, "_migrate_db: adding ai_interpretation column via ALTER TABLE")
        conn.execute(
            text("ALTER TABLE divination_records ADD COLUMN ai_interpretation TEXT")
        )
    log(13, "_migrate_db: completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log(1, "lifespan: startup starting")

    # 启动时：创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log(2, "lifespan: database tables created")

    # 迁移：为已存在的数据库添加 question 列
    async with engine.begin() as conn:
        await conn.run_sync(_migrate_db)
    log(3, "lifespan: migration check completed")

    # 启动时：尝试初始化 Redis 连接（优雅降级，Redis 不可用不影响应用）
    from app.cache import get_redis
    try:
        r = await get_redis()
        if r:
            await r.ping()
        log(4, "lifespan: redis initialized OK")
    except Exception:
        log(5, "lifespan: redis unavailable, graceful degradation", level="WARN")
        pass  # Redis 不可用时静默忽略

    log(6, "lifespan: startup complete, yielding")
    yield

    # 关闭时：关闭 Redis 连接
    log(7, "lifespan: shutdown starting")
    from app.cache import close_redis
    await close_redis()
    log(8, "lifespan: redis connection closed")
    await engine.dispose()
    log(9, "lifespan: engine disposed")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
log(10, f"app: FastAPI app created, title='{settings.app_name}'")

app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

from app.routes import home, divine, hexagram, study, history, api

app.include_router(home.router, prefix="", tags=["home"])
app.include_router(divine.router, prefix="/divine", tags=["divine"])
app.include_router(hexagram.router, prefix="/hexagram", tags=["hexagram"])
app.include_router(study.router, prefix="/study", tags=["study"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(api.router, prefix="/api", tags=["api"])
