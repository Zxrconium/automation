from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    search_provider: str = Field("mock", env="SEARCH_PROVIDER")
    bing_api_key: Optional[str] = Field(None, env="BING_API_KEY")
    serpapi_key: Optional[str] = Field(None, env="SERPAPI_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    google_cse_id: Optional[str] = Field(None, env="GOOGLE_CSE_ID")
    request_delay: float = Field(1.5, env="REQUEST_DELAY")
    search_delay: float = Field(2.0, env="SEARCH_DELAY")
    cache_ttl_hours: int = Field(24, env="CACHE_TTL_HOURS")
    enable_smtp_probe: bool = Field(False, env="ENABLE_SMTP_PROBE")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    user_agent: str = "Mozilla/5.0 (compatible; UNGCResearchBot/1.0; +research)"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
