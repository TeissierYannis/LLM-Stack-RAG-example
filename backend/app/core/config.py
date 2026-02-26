from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # LiteLLM
    litellm_proxy_url: str = "http://litellm:4000"
    litellm_master_key: str = "sk-litellm-master-key"

    # Models
    completion_model: str = "default-completion"
    embedding_model: str = "default-embedding"

    # Database
    database_url: str = "postgresql+asyncpg://raguser:ragpassword@postgres:5432/enterprise_rag"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # RAG settings
    chunk_size: int = 512
    chunk_overlap: int = 100
    top_k_results: int = 5

    # OCR provider: "local" (Tesseract), "aws_textract", "azure_di", "google_docai", or "auto"
    ocr_provider: str = "local"

    # AWS (shared with LiteLLM, also used for Textract)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = ""

    # Azure Document Intelligence
    azure_di_endpoint: str = ""
    azure_di_key: str = ""

    # Google Document AI
    google_docai_processor: str = ""  # projects/{project}/locations/{location}/processors/{id}

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
