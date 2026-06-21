""" 八卦 - I Ching Divination — 一键启动入口 """
import uvicorn
from app.config import settings

if __name__ == "__main__":
    # forwarded_allow_ips="*" 会信任所有代理头（不安全）
    # 设为空字符串则拒绝所有代理头，防止客户端伪造 X-Forwarded-For 绕过限流
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        forwarded_allow_ips="",
    )
