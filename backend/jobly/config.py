from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


def _optional_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _ratio(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    value = float(raw)
    if not 0 < value < 1:
        raise ValueError(f"{name} must be greater than 0 and less than 1")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    frontend_origin: str
    gemini_api_key: str | None
    ai_model: str
    ai_classification_version: str
    ai_prompt_version: str
    ai_max_attempts: int
    ai_enrichment_limit: int
    source_target_count: int
    crawl_source_limit: int | None
    app_env: str
    log_level: str
    mass_drop_min_previous_jobs: int
    mass_drop_ratio: float

    def require_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return self.database_url

    def require_gemini_api_key(self) -> str:
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        return self.gemini_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Local development may use .env; production can inject the same values.
    load_dotenv()
    return Settings(
        database_url=os.getenv("DATABASE_URL", "").strip() or None,
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip() or None,
        ai_model=os.getenv("AI_MODEL", "gemini-3.5-flash-lite").strip(),
        ai_classification_version=os.getenv("AI_CLASSIFICATION_VERSION", "v2").strip(),
        ai_prompt_version=os.getenv("AI_PROMPT_VERSION", "v2").strip(),
        ai_max_attempts=_positive_int("AI_MAX_ATTEMPTS", 5),
        ai_enrichment_limit=_positive_int("AI_ENRICHMENT_LIMIT", 5000),
        source_target_count=_positive_int("SOURCE_TARGET_COUNT", 1000),
        crawl_source_limit=_optional_int("CRAWL_SOURCE_LIMIT"),
        app_env=os.getenv("APP_ENV", "development").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        mass_drop_min_previous_jobs=_positive_int("CRAWL_MASS_DROP_MIN_PREVIOUS_JOBS", 20),
        mass_drop_ratio=_ratio("CRAWL_MASS_DROP_RATIO", 0.25),
    )
