"""
BiblioAgent AI - Configuration Management
==========================================
Centralized configuration using pydantic-settings for type safety and validation.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    scopus_api_key: str = Field(default="", env="SCOPUS_API_KEY")
    unpaywall_email: str = Field(default="", env="UNPAYWALL_EMAIL")
    semantic_scholar_api_key: Optional[str] = Field(default=None, env="SEMANTIC_SCHOLAR_API_KEY")
    core_api_key: Optional[str] = Field(default=None, env="CORE_API_KEY")

    # ChromaDB
    chroma_persist_dir: str = Field(default="./data/chroma_db", env="CHROMA_PERSIST_DIR")

    # Rate Limits (requests per minute)
    scopus_rate_limit: int = Field(default=9, env="SCOPUS_RATE_LIMIT")
    unpaywall_rate_limit: int = Field(default=100, env="UNPAYWALL_RATE_LIMIT")
    core_rate_limit: int = Field(default=10, env="CORE_RATE_LIMIT")
    semantic_scholar_rate_limit: int = Field(default=100, env="SEMANTIC_SCHOLAR_RATE_LIMIT")

    # Processing
    batch_size: int = Field(default=20, env="BATCH_SIZE")
    max_retries: int = Field(default=3, env="MAX_RETRIES")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # API Endpoints
    scopus_base_url: str = "https://api.elsevier.com/content/search/scopus"
    unpaywall_base_url: str = "https://api.unpaywall.org/v2"
    core_base_url: str = "https://api.core.ac.uk/v3"
    arxiv_base_url: str = "http://export.arxiv.org/api/query"
    semantic_scholar_base_url: str = "https://api.semanticscholar.org/graph/v1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for quick access
settings = get_settings()
