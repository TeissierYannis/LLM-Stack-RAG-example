# Architecture - Enterprise Chat + RAG with LiteLLM

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UTILISATEURS                                 │
│                    (Navigateur / API)                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React)                               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐                 │
│  │   Chat    │  │  Upload      │  │  Historique   │                 │
│  │   UI      │  │  Documents   │  │  Conversations│                 │
│  └──────────┘  └──────────────┘  └───────────────┘                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ REST / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                                 │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │  /chat       │  │  /documents  │  │  /conversations      │      │
│  │  endpoint    │  │  upload +    │  │  CRUD                │      │
│  │  (streaming) │  │  processing  │  │                      │      │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘      │
│         │                 │                                         │
│  ┌──────▼─────────────────▼────────────────────────────────────┐   │
│  │              RAG ENGINE                                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌─────────────────────┐     │   │
│  │  │ Document   │ │ Chunking   │ │ Context             │     │   │
│  │  │ Parser     │ │ Strategy   │ │ Builder             │     │   │
│  │  │(PDF,DOCX,  │ │(recursive, │ │(query+relevant      │     │   │
│  │  │ MD,TXT)    │ │ semantic)  │ │ chunks → prompt)    │     │   │
│  │  └────────────┘ └────────────┘ └─────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         │  Embedding / Completion requests                          │
└─────────┼───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LiteLLM PROXY                                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Routage intelligent  │  Load balancing  │  Fallback        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                      │                    │               │
│         ▼                      ▼                    ▼               │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐      │
│  │  AWS         │    │  Azure AI    │    │  Google          │      │
│  │  Bedrock     │    │  Foundry     │    │  Vertex AI       │      │
│  │             │    │              │    │                  │      │
│  │ Claude      │    │ GPT-4o       │    │ Gemini           │      │
│  │ Titan Embed │    │ Ada Embed    │    │ Gecko Embed      │      │
│  └─────────────┘    └──────────────┘    └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                      │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │  Qdrant      │  │  PostgreSQL  │  │  Redis               │      │
│  │  (Vectors)   │  │  (Metadata + │  │  (Cache +            │      │
│  │              │  │  Historique) │  │   Sessions)          │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

## Flux de données

### 1. Ingestion de documents
```
Document (PDF/DOCX/MD/TXT)
    │
    ▼
┌──────────────┐
│  Parser       │──→ Texte brut
└──────┬───────┘
       ▼
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
└──────────────┘
```

### 2. Chat avec RAG
```
Question utilisateur
    │
    ▼
┌──────────────┐       ┌──────────────┐
│  Embedding   │──────→│  Qdrant      │
│  de la query │       │  Similarity  │
└──────────────┘       │  Search      │
                       └──────┬───────┘
                              │ Top-K chunks
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
| Frontend | React + TypeScript | Interface chat |
| Backend | FastAPI (Python) | API REST + WebSocket |
| LLM Proxy | LiteLLM | Routage multi-provider |
| Vector DB | Qdrant | Stockage embeddings |
| Database | PostgreSQL | Métadonnées + historique |
| Cache | Redis | Sessions + cache |
| Containers | Docker Compose | Orchestration locale |
| Cloud | Terraform + K8s | Déploiement cloud |

## Modèles supportés via LiteLLM

| Provider | Completion | Embedding |
|----------|-----------|-----------|
| AWS Bedrock | `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` | `bedrock/amazon.titan-embed-text-v2:0` |
| Azure AI Foundry | `azure/gpt-4o` | `azure/text-embedding-3-small` |
| Google Vertex | `vertex_ai/gemini-2.0-flash` | `vertex_ai/text-embedding-005` |
