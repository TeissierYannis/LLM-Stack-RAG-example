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

    # Qdrant (self-hosted)
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    # Qdrant Cloud (set QDRANT_URL to use managed Qdrant instead of self-hosted)
    qdrant_url: str = ""          # e.g. https://xxx.cloud.qdrant.io:6333
    qdrant_api_key: str = ""      # Qdrant Cloud API key

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # RAG settings
    chunk_size: int = 512
    chunk_overlap: int = 100
    top_k_results: int = 5

    # Reranking (set model name to enable, e.g. "cohere-rerank" or "rerank-english-v3.0")
    rerank_model: str = ""

    # OCR provider: "local" (Tesseract), "aws_textract", "azure_di", "google_docai", or "auto"
    ocr_provider: str = "local"

    # AWS (shared: LiteLLM + Textract + S3)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = ""

    # Azure Document Intelligence
    azure_di_endpoint: str = ""
    azure_di_key: str = ""

    # Google Document AI
    google_docai_processor: str = ""  # projects/{project}/locations/{location}/processors/{id}

    # Object storage for raw documents: "local", "s3", "gcs", "azure_blob"
    storage_provider: str = "local"
    storage_bucket: str = ""                      # S3 bucket / GCS bucket / Azure container
    storage_local_path: str = "/tmp/rag-storage"  # Local dev fallback path
    storage_encrypt: bool = True                  # Enable server-side encryption (S3 KMS)
    azure_storage_connection_string: str = ""     # Azure Blob connection string

    # Background processing (Celery)
    celery_broker_url: str = ""    # defaults to redis_url if empty
    celery_result_backend: str = ""
    use_celery: bool = False       # Set True to enable background document processing

    # Authentication
    auth_enabled: bool = False                     # Set True to require auth
    jwt_expiration_minutes: int = 1440             # 24h default
    api_keys: str = ""                             # Comma-separated valid API keys

    # OpenTelemetry
    otel_exporter_endpoint: str = ""               # e.g. http://jaeger:4317
    otel_service_name: str = "enterprise-chat-rag"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
