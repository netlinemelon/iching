"""
IP 速率限制模块 — IP-based rate limiting

使用内存字典存储每日计数，每天零点自动重置。
"""
import time
from collections import defaultdict
from app.config import settings
from app.debug import log

# 每日 AI 解卦总限额
DAILY_AI_LIMIT = settings.daily_ai_limit

# 数据结构: {date_str: {"total": int, "ips": {"ip": count}}}
_daily: dict = {"date": "", "total": 0, "ips": defaultdict(int)}


def _get_today() -> str:
    """返回今日日期字符串 YYYY-MM-DD"""
    return time.strftime("%Y-%m-%d")


def _check_reset():
    """检查是否需要进入新的一天，重置计数器。"""
    today = _get_today()
    if _daily["date"] != today:
        log(800, f"limits: new day, resetting counters. Yesterday total={_daily.get('total', 0)}")
        _daily["date"] = today
        _daily["total"] = 0
        _daily["ips"].clear()


def can_use_ai(client_ip: str) -> bool:
    """检查该 IP 是否可以使用 AI 解卦。

    Returns:
        True 如果今日总次数未超限
    """
    _check_reset()
    return _daily["total"] < DAILY_AI_LIMIT


def record_ai_use(client_ip: str) -> int:
    """记录一次 AI 使用，返回今日已用次数。"""
    _check_reset()
    _daily["total"] += 1
    _daily["ips"][client_ip] += 1
    log(801, f"limits: AI used by ip={client_ip[:15]}... today_total={_daily['total']}")
    return _daily["ips"][client_ip]


def get_usage(client_ip: str) -> dict:
    """获取今日使用情况。

    Returns:
        {"total_used": int, "total_limit": int, "your_count": int}
    """
    _check_reset()
    return {
        "total_used": _daily["total"],
        "total_limit": DAILY_AI_LIMIT,
        "your_count": _daily["ips"].get(client_ip, 0),
    }


def get_client_ip(request) -> str:
    """从请求中提取客户端 IP。
    优先检查 X-Forwarded-For (经过代理时)，fallback 到直接 IP。
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
