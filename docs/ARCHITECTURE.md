# Architecture - Enterprise Chat + RAG with LiteLLM (v2.0)

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UTILISATEURS                                 │
│                (Navigateur / API / SDK)                              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS + JWT / API Key
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐                 │
│  │   Chat    │  │  Upload      │  │  Historique   │                 │
│  │   UI      │  │  Documents   │  │  Conversations│                 │
│  └──────────┘  └──────────────┘  └───────────────┘                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ REST + SSE
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Auth (JWT + API Key)  │  OpenTelemetry Tracing              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  ┌────────────┐   │
│  │ /chat    │  │ /documents│  │ /assistants  │  │ /auth      │   │
│  │ stream   │  │ upload    │  │ CRUD         │  │ token      │   │
│  └────┬─────┘  └─────┬─────┘  └──────────────┘  └────────────┘   │
│       │              │                                              │
│       │         ┌────▼──────┐                                      │
│       │         │ Celery    │  (async document processing)         │
│       │         │ Worker    │                                      │
│       │         └────┬──────┘                                      │
│       │              │                                              │
│  ┌────▼──────────────▼──────────────────────────────────────────┐  │
│  │                    RAG ENGINE                                 │  │
│  │  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ │  │
│  │  │ Parser │ │Chunker │ │Embeddings│ │Reranker│ │ Context │ │  │
│  │  │+ OCR   │ │        │ │(LiteLLM) │ │(cross- │ │ Builder │ │  │
│  │  │        │ │        │ │          │ │encoder)│ │         │ │  │
│  │  └───┬────┘ └────────┘ └──────────┘ └────────┘ └─────────┘ │  │
│  │      ▼                                                       │  │
│  │  ┌──────────────────────────────────────────────────────┐   │  │
│  │  │ OCR: Tesseract │ AWS Textract │ Azure DI │ GCP DAI   │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────┬─────────────────────────────────────┬────────────────────┘
          │                                     │
          ▼                                     ▼
┌──────────────────────┐          ┌──────────────────────────────────┐
│   LiteLLM PROXY      │          │  OBJECT STORAGE                  │
│  ┌────────────────┐  │          │  ┌──────┐ ┌─────┐ ┌───────────┐ │
│  │ Load balancing │  │          │  │  S3  │ │ GCS │ │Azure Blob │ │
│  │ + Fallback     │  │          │  └──────┘ └─────┘ └───────────┘ │
│  └────────────────┘  │          └──────────────────────────────────┘
│   │       │       │  │
│   ▼       ▼       ▼  │
│ Bedrock Foundry Vertex│
│ Claude  GPT-4o  Gemini│
│ +Embed  +Embed  +Embed│
│ +Rerank              │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     DATA LAYER (managed or self-hosted)             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │ Qdrant       │  │ PostgreSQL   │  │ Redis                │      │
│  │ (self-hosted │  │ (RDS /       │  │ (ElastiCache /       │      │
│  │  or Cloud)   │  │  Cloud SQL)  │  │  Memorystore)        │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY                                    │
│  OpenTelemetry → Jaeger / Grafana Tempo / Datadog / New Relic       │
└─────────────────────────────────────────────────────────────────────┘
```

## Flux de données

### 1. Ingestion de documents
```
Document (PDF/DOCX/MD/TXT/PNG/JPG/TIFF...)
    │
    ├──→ Object Storage (S3 / GCS / Azure Blob)   ← raw file backup
    │
    ▼
┌──────────────┐     ┌──────────────────────────────────┐
│  Parser       │────→│  OCR (si image/scan)              │
│              │     │  local: Tesseract                 │
│              │     │  cloud: Textract / Azure DI / DAI │
└──────┬───────┘     └──────────────────────────────────┘
       │
       ▼ Texte brut
┌──────────────┐
│  Chunker      │──→ Chunks (500-1000 tokens, overlap 100)
└──────┬───────┘
       ▼
┌──────────────┐       ┌──────────────┐
│  LiteLLM     │──────→│  Embedding   │
│  (embed)     │       │  Model       │
└──────┬───────┘       └──────────────┘
       ▼
┌──────────────┐
│  Qdrant      │──→ Vecteurs stockés avec metadata
│  (or Cloud)  │
└──────────────┘

Note: si USE_CELERY=true, les étapes 2-5 sont exécutées
en arrière-plan par un worker Celery.
```

### 2. Chat avec RAG
```
Question utilisateur
    │
    ▼
┌──────────────┐       ┌──────────────┐
│  Embedding   │──────→│  Qdrant      │
│  de la query │       │  Similarity  │
└──────────────┘       │  Search (2×k)│
                       └──────┬───────┘
                              │ Candidats
                              ▼
                       ┌──────────────┐
                       │  Reranker    │  (cross-encoder, optional)
                       │  Top-K final │
                       └──────┬───────┘
                              │ Chunks reranked
                              ▼
                       ┌──────────────┐
                       │  Context     │
                       │  Builder     │
                       └──────┬───────┘
                              │ Prompt enrichi
                              ▼
                       ┌──────────────┐
                       │  LiteLLM     │──→ Bedrock / Foundry / Vertex
                       │  (completion)│
                       └──────┬───────┘
                              │ Réponse streamée
                              ▼
                       Réponse à l'utilisateur
                       (avec sources citées)
```

## Stack technique

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Frontend | React + TypeScript + Tailwind | Interface chat |
| Backend | FastAPI (Python) | API REST + SSE |
| LLM Proxy | LiteLLM | Routage multi-provider |
| Vector DB | Qdrant (self-hosted ou Cloud) | Stockage embeddings |
| Database | PostgreSQL (ou RDS/Cloud SQL) | Métadonnées + historique |
| Cache | Redis (ou ElastiCache) | Cache + broker Celery |
| Object Storage | S3 / GCS / Azure Blob | Fichiers bruts |
| Background | Celery + Redis | Ingestion async |
| Auth | JWT + API Keys | Authentification |
| Reranking | Cross-encoder via LiteLLM | Précision RAG |
| Observabilité | OpenTelemetry | Tracing distribué |
| Containers | Docker Compose | Orchestration locale |
| Cloud | Terraform + K8s | Déploiement cloud |

## OCR multi-provider

| Provider | Service | Configuration |
|----------|---------|---------------|
| Local | Tesseract (fra+eng) | Par défaut, aucune config |
| AWS | Textract | `OCR_PROVIDER=aws_textract` + AWS creds |
| Azure | Document Intelligence | `OCR_PROVIDER=azure_di` + endpoint + key |
| Google | Document AI | `OCR_PROVIDER=google_docai` + processor ID |
| Auto | Essaie cloud → local | `OCR_PROVIDER=auto` |

En mode `auto`, le système essaie chaque provider cloud configuré dans l'ordre
(AWS → Azure → Google), puis fallback sur Tesseract local si tous échouent.

Formats supportés : PDF (hybride texte+scan), PNG, JPG, JPEG, WebP, BMP, TIFF (multi-page).

## Modèles supportés via LiteLLM

| Provider | Completion | Embedding |
|----------|-----------|-----------|
| AWS Bedrock | `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` | `bedrock/amazon.titan-embed-text-v2:0` |
| Azure AI Foundry | `azure/gpt-4o` | `azure/text-embedding-3-small` |
| Google Vertex | `vertex_ai/gemini-2.0-flash` | `vertex_ai/text-embedding-005` |
