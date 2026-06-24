from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    deepseek_api_key: str = ""
    llm_model: str = "deepseek-chat"

    es_url: str = "http://localhost:9200"
    qdrant_url: str = "http://localhost:6333"
    index_name: str = "japanlife_kb"

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    embedding_dim: int = 1024

    retrieval_top_k: int = 20
    rerank_top_n: int = 5
    rrf_k: int = 60

    # Caching (see rag/cache.py). All optional and safe to disable.
    enable_embedding_cache: bool = True
    embedding_cache_path: str = "./.cache/japanlife_embeddings.db"
    enable_retrieval_cache: bool = False
    cache_ttl_seconds: int = 60

    checkpoint_db: str = "./japanlife.db"
    admin_api_key: str = ""


settings = Settings()
