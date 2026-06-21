"""
编号调试系统 — Numbered Debug Logging

所有调试输出统一通过此模块，格式: [D{N:03d}] {message}

编号分配:
  D001-D049  启动/关闭 (main.py, database.py)
  D050-D099  缓存 (cache.py)
  D100-D199  引擎 (engine/*.py)
  D200-D249  结果构建 (result_builder.py)
  D250-D299  数据加载 (hexagram_data.py)
  D300-D349  路由 divine.py
  D350-D399  路由 api.py
  D400-D449  路由 hexagram.py
  D450-D499  路由 history.py
  D500-D519  路由 home.py
  D520-D549  路由 study.py
  D550-D579  ORM (divination_record.py)
  D580-D599  模板渲染错误
  D900-D999  通用/未分类
"""
import sys
import time
from app.config import settings


def log(debug_id: int, message: str, *, level: str = "INFO", error: Exception | None = None):
    """输出编号调试信息。

    生产环境(debug=False)只输出 ERROR 级别。
    开发环境(debug=True)输出全部。
    """
    if not settings.debug and level not in ("ERROR", "WARN"):
        return

    ts = time.strftime("%H:%M:%S")
    prefix = f"[D{debug_id:03d}]"
    text = f"{ts} {prefix} [{level}] {message}"

    if error:
        text += f" | err={type(error).__name__}: {error}"

    print(text, file=sys.stderr, flush=True)
