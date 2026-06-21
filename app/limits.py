"""
IP 速率限制模块 — IP-based rate limiting

使用内存字典存储每日计数，每天零点 (UTC) 自动重置。

注意：
  在多 worker 部署下，每个 worker 有独立的计数器，
  实际日限额 = DAILY_AI_LIMIT * num_workers。
  对于精确限流，请使用 Redis 集中式计数（项目依赖已包含 redis）。
  本实现适用于单 worker 或 sticky-session 反向代理场景。
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
    """返回今日 UTC 日期字符串 YYYY-MM-DD。"""
    return time.strftime("%Y-%m-%d", time.gmtime())


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

    安全策略：只信任 X-Real-IP 头（由反向代理设置），
    不信任 X-Forwarded-For（可被客户端伪造，且值可能包含代理链）。
    如果应用部署在反向代理后，请确保代理正确设置了 X-Real-IP。
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


# ============================================================
# 熔断器 — 滑动窗口 + 突刺检测 + IP 封禁
# ============================================================

_IP_WINDOW: dict[str, list[float]] = defaultdict(list)   # {ip: [timestamps]}
_IP_BANNED: dict[str, float] = {}                         # {ip: 解封时间}

_IP_RATE_PER_MIN = 120          # 每IP每分钟最大请求
_BURST_PER_SEC = 10             # 每秒突刺阈值
_BAN_SECONDS = 300              # 封禁时长(秒)


def check_rate_limit(client_ip: str) -> tuple[bool, dict]:
    """熔断检查。返回 (放行?, {info})。"""
    now = time.time()

    # 封禁中
    if client_ip in _IP_BANNED:
        if now < _IP_BANNED[client_ip]:
            remain = int(_IP_BANNED[client_ip] - now)
            return False, {"error": "IP已被临时封禁", "retry_after": remain}
        del _IP_BANNED[client_ip]

    # 清理 60 秒前的旧记录
    cutoff = now - 60
    _IP_WINDOW[client_ip] = [t for t in _IP_WINDOW[client_ip] if t > cutoff]
    _IP_WINDOW[client_ip].append(now)

    # 突刺检测
    burst = sum(1 for t in _IP_WINDOW[client_ip] if t > now - 1)
    if burst > _BURST_PER_SEC:
        _IP_BANNED[client_ip] = now + _BAN_SECONDS
        log(810, f"limits: IP BANNED {client_ip[:15]}... burst={burst}/s, {_BAN_SECONDS}s ban")
        return False, {"error": "检测到异常访问频率，IP已被封禁5分钟", "retry_after": _BAN_SECONDS}

    # 滑动窗口
    used = len(_IP_WINDOW[client_ip])
    if used > _IP_RATE_PER_MIN:
        return False, {"error": "请求过于频繁，请稍后重试", "retry_after": 60}

    return True, {"remaining": _IP_RATE_PER_MIN - used}
