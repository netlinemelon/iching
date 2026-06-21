from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "八卦 - I Ching Divination"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./data/iching.db"
    data_dir: Path = Path(__file__).parent.parent / "data"
    static_dir: Path = Path(__file__).parent / "static"
    template_dir: Path = Path(__file__).parent / "templates"

    redis_url: str = "redis://localhost:6379/0"
    redis_ttl: int = 3600  # 1 hour TTL for divination results

    # AI 解卦配置（可选，不配置则使用规则回退）
    # 支持 Anthropic API 和兼容服务（如 DeepSeek）
    anthropic_api_key: str = "REDACTED_API_KEY_PLACEHOLDER"
    anthropic_base_url: str = "https://api.deepseek.com/anthropic"
    anthropic_model: str = "deepseek-v4-pro"

    model_config = {"env_file": ".env"}


settings = Settings()
