from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from decouple import config


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    openai_api_key: Optional[str] = config("OPENAI_API_KEY", default=None)
    anthropic_api_key: Optional[str] = config("ANTHROPIC_API_KEY", default=None)
    openrouter_api_key: Optional[str] = config("OPENROUTER_API_KEY", default=None)

    default_llm_provider: str = config("DEFAULT_LLM_PROVIDER", default="openai")
    default_model: str = config("DEFAULT_MODEL", default="gpt-3.5-turbo")
    llm_temperature: float = config("LLM_TEMPERATURE", default=0.1, cast=float)
    max_tokens: int = config("MAX_TOKENS", default=2000, cast=int)

    # Text Processing
    min_text_length: int = config("MIN_TEXT_LENGTH", default=300, cast=int)
    min_word_count: int = config("MIN_WORD_COUNT", default=100, cast=int)
    text_preview_words: int = config("TEXT_PREVIEW_WORDS", default=50, cast=int)
    chunk_size: int = config("CHUNK_SIZE", default=1000, cast=int)
    chunk_overlap: int = config("CHUNK_OVERLAP", default=200, cast=int)

    # Vector Database
    chroma_persist_directory: str = config(
        "CHROMA_PERSIST_DIRECTORY",
        default="./data/chroma_db"
    )
    collection_name: str = config("COLLECTION_NAME", default="scraped_content")
    embedding_model: str = config("EMBEDDING_MODEL", default="default")

    # Scraping Configuration
    request_timeout: int = config("REQUEST_TIMEOUT", default=30, cast=int)
    max_retries: int = config("MAX_RETRIES", default=3, cast=int)
    user_agent: str = config(
        "USER_AGENT",
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    # Conversation Memory
    conversation_memory_size: int = config("CONVERSATION_MEMORY_SIZE", default=5, cast=int)
    conversation_persistence: bool = config("CONVERSATION_PERSISTENCE", default=False, cast=bool)
    conversation_context_ratio: float = config("CONVERSATION_CONTEXT_RATIO", default=0.3, cast=float)

    # Logging
    log_level: str = config("LOG_LEVEL", default="INFO")
    log_file: str = config("LOG_FILE", default="./logs/scraper.log")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def ensure_directories():
    """Ensure required directories exist."""
    Path(settings.chroma_persist_directory).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)