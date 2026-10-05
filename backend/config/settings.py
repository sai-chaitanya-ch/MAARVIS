from pathlib import Path
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), "../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # ── AI Providers Configuration & Encryption ──────────────────────────────
    provider_encryption_key: str = ""
    default_ai_provider: str = "google"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    deepseek_api_key: str = ""

    # ── Optional Web search (Tavily) ─────────────────────────────────────────
    tavily_api_key: str = ""
    tavily_base_url: str = "https://api.tavily.com"

    # ── App identity ──────────────────────────────────────────────────────────
    app_name: str = "MAARVIS"
    environment: str = "development"

    # ── RAG configuration ─────────────────────────────────────────────────────
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 150
    rag_top_k: int = 10
    rag_final_k: int = 5

    # ── Application limits ───────────────────────────────────────────────────
    max_verification_iterations: int = 3
    code_execution_timeout: int = 10
    max_upload_size_mb: int = 20
    code_memory_limit: str = "256m"
    code_cpu_limit: float = 0.5

    # ── Database & CORS ──────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/verify.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Auth & rate-limiting ─────────────────────────────────────────────────
    verify_api_key: str = ""
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"

    # ── Optional JEV AI semantic decision engine ─────────────────────────────
    jev_api_key: str = ""
    jev_base_url: str = "https://api.typesafe.ai/v1/systemone"
    jev_model: str = "jev-latest"

    # ── Supabase (Database, Auth, Storage, pgvector) ─────────────────────────
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_storage_bucket: str = "documents"
    port: int = 8000

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.environment.lower() == "development":
            dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
            for d in dev_origins:
                if d not in origins:
                    origins.append(d)
        return origins

    @property
    def sqlite_path(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "", 1)
        return "./data/verify.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
