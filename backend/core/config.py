"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    elevenlabs_api_key: str = ""
    elevenlabs_api_base: str = "https://api.elevenlabs.io"

    qdrant_url: str = ""  # empty → embedded path store
    qdrant_path: str = "qdrant_storage/local"
    qdrant_collection: str = "msmarco_xi_mini"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"
    ollama_timeout_s: float = 25.0
    llm_max_tokens: int = 96

    default_answer_mode: str = "fast"  # fast | generative
    hybrid_candidates: int = 20
    rerank_top_k: int = 5
    relevance_threshold: float = 0.5
    grounding_overlap: float = 0.22

    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
