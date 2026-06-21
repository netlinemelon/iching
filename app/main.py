from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import engine, async_session, Base
from app.debug import log

templates = Jinja2Templates(directory=str(settings.template_dir))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log(1, "lifespan: startup starting")

    # 启动时：创建数据库表（用于占卜记录持久化和分享功能）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log(2, "lifespan: database tables created")

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
