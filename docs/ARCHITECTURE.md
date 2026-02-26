# Architecture - Enterprise Chat + RAG avec LiteLLM (v2.0)

## 1. Vue d'ensemble

```mermaid
graph TB
    subgraph Users["🧑‍💻 Utilisateurs"]
        Browser["Navigateur / API / SDK"]
    end

    subgraph Frontend["🖥️ Frontend React"]
        ChatUI["Chat UI"]
        Upload["Upload Documents"]
        History["Historique Conversations"]
    end

    subgraph Backend["⚙️ Backend FastAPI"]
        direction TB
        subgraph Middleware["Middleware"]
            Auth["Auth JWT + API Key"]
            OTel["OpenTelemetry"]
            LF["Langfuse Traces"]
        end

        subgraph Routes["Routes API"]
            ChatAPI["/chat stream"]
            DocsAPI["/documents upload"]
            AssistAPI["/assistants CRUD"]
            AuthAPI["/auth token"]
        end

        CeleryW["Celery Worker<br/><i>async doc processing</i>"]

        subgraph RAG["🔍 RAG Engine"]
            Parser["Parser + OCR"]
            Chunker["Chunker"]
            Embeddings["Embeddings<br/><i>LiteLLM</i>"]
            Reranker["Reranker<br/><i>cross-encoder</i>"]
            CtxBuilder["Context Builder"]
        end

        subgraph OCR["OCR Providers"]
            Tesseract["Tesseract"]
            Textract["AWS Textract"]
            AzureDI["Azure Doc Intelligence"]
            GCPDAI["GCP Document AI"]
        end
    end

    subgraph LiteLLM["🔀 LiteLLM Proxy"]
        LB["Load Balancing + Fallback"]
        Bedrock["AWS Bedrock<br/>Claude + Embed"]
        Foundry["Azure Foundry<br/>GPT-4o + Embed"]
        Vertex["Google Vertex<br/>Gemini + Embed"]
    end

    subgraph Storage["☁️ Object Storage"]
        S3["S3"]
        GCS["GCS"]
        AzureBlob["Azure Blob"]
    end

    subgraph Data["💾 Data Layer"]
        Qdrant[("Qdrant<br/>Vector DB")]
        Postgres[("PostgreSQL<br/>Metadata + History")]
        Redis[("Redis<br/>Cache + Broker")]
    end

    subgraph Observability["📊 Observabilité"]
        OTelCol["OpenTelemetry → Jaeger / Grafana / Datadog"]
        LangfuseObs["Langfuse → Traces LLM, coûts, qualité"]
    end

    Browser -->|"HTTPS + JWT"| Frontend
    Frontend -->|"REST + SSE"| Backend
    DocsAPI --> CeleryW
    CeleryW --> RAG
    ChatAPI --> RAG
    Parser --> OCR
    RAG --> LiteLLM
    LB --> Bedrock
    LB --> Foundry
    LB --> Vertex
    DocsAPI --> Storage
    RAG --> Qdrant
    Backend --> Postgres
    Backend --> Redis
    Backend --> Observability
```

---

## 2. Flux d'ingestion de documents

```mermaid
flowchart TD
    Doc["📄 Document<br/><i>PDF / DOCX / MD / TXT / PNG / JPG / TIFF</i>"]

    Doc --> ObjStore["☁️ Object Storage<br/><i>S3 / GCS / Azure Blob</i><br/>raw file backup"]
    Doc --> ParseStep

    subgraph Pipeline["Pipeline d'ingestion"]
        ParseStep["1️⃣ Parser"]
        OCRStep["🔍 OCR<br/><i>si image/scan</i>"]
        ChunkStep["2️⃣ Chunker<br/><i>500-1000 tokens, overlap 100</i>"]
        EmbedStep["3️⃣ Embedding<br/><i>via LiteLLM</i>"]
        StoreStep["4️⃣ Stockage Qdrant<br/><i>vecteurs + metadata</i>"]
    end

    ParseStep -->|"image/scan ?"| OCRStep
    OCRStep -->|"texte extrait"| ParseStep
    ParseStep -->|"texte brut"| ChunkStep
    ChunkStep -->|"chunks"| EmbedStep
    EmbedStep -->|"vecteurs"| StoreStep

    subgraph OCRProviders["OCR Providers"]
        direction LR
        Tess["Tesseract<br/><i>local, défaut</i>"]
        AWS["AWS Textract"]
        Azure["Azure Doc Intelligence"]
        GCP["GCP Document AI"]
    end

    OCRStep --> OCRProviders

    Note["💡 Si USE_CELERY=true,<br/>les étapes 1-4 sont<br/>exécutées en arrière-plan"]

    style Doc fill:#4a90d9,color:#fff
    style ObjStore fill:#f5a623,color:#fff
    style StoreStep fill:#7ed321,color:#fff
    style Note fill:#fff3cd,color:#856404,stroke:#ffc107
```

---

## 3. Flux Chat avec RAG

```mermaid
flowchart TD
    Question["💬 Question utilisateur"]

    Question --> EmbedQ["1️⃣ Embedding de la query<br/><i>via LiteLLM</i>"]
    EmbedQ --> Search["2️⃣ Qdrant Similarity Search<br/><i>récupère 2×k candidats</i>"]
    Search --> Rerank["3️⃣ Reranker<br/><i>cross-encoder, optionnel</i><br/>→ Top-K final"]
    Rerank --> Context["4️⃣ Context Builder<br/><i>assemble le prompt enrichi</i>"]
    Context --> LLM["5️⃣ LiteLLM Completion<br/><i>Bedrock / Foundry / Vertex</i>"]
    LLM --> Response["✅ Réponse streamée<br/><i>avec sources citées</i>"]

    style Question fill:#4a90d9,color:#fff
    style Response fill:#7ed321,color:#fff
    style Rerank fill:#f5a623,color:#fff
```

---

## 4. Stack technique

```mermaid
graph LR
    subgraph Presentation["Présentation"]
        React["React + TypeScript + Tailwind"]
    end

    subgraph Application["Application"]
        FastAPI["FastAPI<br/><i>Python</i>"]
        Celery["Celery + Redis<br/><i>Background Jobs</i>"]
    end

    subgraph AI["Intelligence"]
        LiteLLM["LiteLLM<br/><i>Proxy multi-provider</i>"]
        CrossEncoder["Cross-encoder<br/><i>Reranking</i>"]
    end

    subgraph Données["Stockage"]
        Qdrant["Qdrant<br/><i>Vecteurs</i>"]
        PG["PostgreSQL<br/><i>Metadata</i>"]
        RedisC["Redis<br/><i>Cache</i>"]
        ObjSt["S3 / GCS / Blob<br/><i>Fichiers</i>"]
    end

    subgraph Ops["Ops & Observabilité"]
        Docker["Docker Compose<br/><i>Local</i>"]
        K8s["Terraform + K8s<br/><i>Cloud</i>"]
        OTel["OpenTelemetry"]
        Langfuse["Langfuse"]
    end

    React --> FastAPI
    FastAPI --> Celery
    FastAPI --> LiteLLM
    FastAPI --> CrossEncoder
    FastAPI --> Qdrant
    FastAPI --> PG
    FastAPI --> RedisC
    FastAPI --> ObjSt
    FastAPI --> OTel
    FastAPI --> Langfuse
```

---

## 5. Modèles supportés via LiteLLM

```mermaid
graph TD
    LiteLLM["🔀 LiteLLM Proxy<br/><i>Load Balancing + Fallback</i>"]

    subgraph AWS["AWS Bedrock"]
        BComp["bedrock/anthropic.claude-3-5-sonnet"]
        BEmbed["bedrock/amazon.titan-embed-text-v2"]
    end

    subgraph Azure["Azure AI Foundry"]
        AComp["azure/gpt-4o"]
        AEmbed["azure/text-embedding-3-small"]
    end

    subgraph Google["Google Vertex"]
        GComp["vertex_ai/gemini-2.0-flash"]
        GEmbed["vertex_ai/text-embedding-005"]
    end

    LiteLLM -->|"Completion"| BComp
    LiteLLM -->|"Embedding"| BEmbed
    LiteLLM -->|"Completion"| AComp
    LiteLLM -->|"Embedding"| AEmbed
    LiteLLM -->|"Completion"| GComp
    LiteLLM -->|"Embedding"| GEmbed

    style LiteLLM fill:#6c5ce7,color:#fff
    style AWS fill:#ff9900,color:#fff
    style Azure fill:#0078d4,color:#fff
    style Google fill:#4285f4,color:#fff
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
| Observabilité infra | OpenTelemetry | Tracing distribué (latence, erreurs) |
| Observabilité LLM | Langfuse | Traces LLM, coûts, qualité, debug |
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

### Mode Cloud (multi-provider)

| Provider | Completion | Embedding |
|----------|-----------|-----------|
| AWS Bedrock | `bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0` | `bedrock/amazon.titan-embed-text-v2:0` |
| Azure AI Foundry | `azure/gpt-4o` | `azure/text-embedding-3-small` |
| Google Vertex | `vertex_ai/gemini-2.0-flash` | `vertex_ai/text-embedding-005` |

### Mode Local (LM Studio) — Zero Cloud

Pour une version 100% locale sans aucune dépendance cloud, le projet supporte
LM Studio comme backend LLM via son API compatible OpenAI.

#### Démarrage rapide

```bash
cp .env.local.example .env
docker compose -f docker-compose.yml -f docker-compose.local.yml up
```

#### Prérequis

1. **LM Studio** installé et démarré sur la machine hôte
2. Serveur activé sur le **port 1234** (Developer → Local Server → Start)
3. Modèles chargés (voir tableau ci-dessous)

#### Modèles recommandés à charger dans LM Studio

| Usage | Modèle recommandé | VRAM | Notes |
|-------|-------------------|------|-------|
| **Completion** | `Qwen2.5-7B-Instruct` | ~5 GB | Excellent rapport qualité/taille, multilingue FR/EN |
| **Completion** | `Mistral-7B-Instruct-v0.3` | ~5 GB | Bon en français, rapide |
| **Completion** | `Meta-Llama-3.1-8B-Instruct` | ~5 GB | Très polyvalent |
| **Completion (puissant)** | `Qwen2.5-14B-Instruct` | ~10 GB | Meilleure qualité, nécessite plus de VRAM |
| **Completion (léger)** | `Qwen2.5-3B-Instruct` | ~2 GB | Pour machines avec peu de VRAM |
| **Embedding** | `nomic-ai/nomic-embed-text-v1.5-GGUF` | ~0.3 GB | 768 dims, excellent pour RAG |
| **Embedding** | `CompendiumLabs/bge-large-en-v1.5-gguf` | ~0.4 GB | 1024 dims, très précis |
| **Embedding** | `second-state/all-MiniLM-L6-v2-GGUF` | ~0.1 GB | 384 dims, ultra léger |

> **Minimum recommandé** : 1 modèle completion + 1 modèle embedding.
> Avec 8 GB de VRAM : Qwen2.5-7B + nomic-embed-text.
> Avec 16 GB+ de VRAM : Qwen2.5-14B + nomic-embed-text.

#### Configuration LM Studio

Dans LM Studio :
1. **Developer** → **Local Server** → **Start Server** (port 1234)
2. Charger le modèle de completion → il sera disponible via l'API
3. Charger le modèle d'embedding → il sera disponible sur `/v1/embeddings`

> **Important** : LM Studio doit avoir les deux modèles chargés simultanément
> (completion + embedding). Activez "Allow multiple models" dans les paramètres.

#### Architecture locale

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Frontend   │────→│   Backend    │────→│   LiteLLM Proxy      │
│   React      │     │   FastAPI    │     │   (config.local.yaml)│
└──────────────┘     └──────┬───────┘     └──────────┬───────────┘
                            │                        │
                     ┌──────▼───────┐         ┌──────▼───────────┐
                     │  Qdrant      │         │  LM Studio       │
                     │  (Docker)    │         │  (host machine)  │
                     └──────────────┘         │  - Qwen 2.5 7B   │
                            │                 │  - nomic-embed    │
                     ┌──────▼───────┐         └──────────────────┘
                     │  PostgreSQL  │
                     │  Redis       │
                     │  (Docker)    │
                     └──────────────┘
```

Tout tourne en local : pas d'API key cloud, pas de données envoyées à l'extérieur.

## Langfuse - Observabilité LLM

Langfuse trace chaque requête de bout en bout pour offrir une visibilité complète
sur les appels LLM, les coûts, la latence et la qualité des réponses.

### Configuration

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com    # ou self-hosted: http://langfuse:3000
```

---

## 7. Observabilité Langfuse — Traces

### Chat Request

```mermaid
flowchart TD
    subgraph Trace["📊 Trace: chat-stream"]
        subgraph RAGSpan["Span: rag-retrieval"]
            EmbedGen["Generation: embedding<br/><i>query embedding via LiteLLM</i>"]
            RerankSpan["Span: rerank<br/><i>cross-encoder reranking</i>"]
        end

        LLMGen["Generation: llm-stream-completion<br/><i>model, input, output, tokens, latence</i>"]
    end

    EmbedGen --> RerankSpan
    RerankSpan --> LLMGen

    style Trace fill:#f0f0f0,stroke:#333
    style RAGSpan fill:#e8f4fd,stroke:#4a90d9
    style EmbedGen fill:#fff,stroke:#f5a623
    style LLMGen fill:#fff,stroke:#7ed321
```

### Document Ingestion

```mermaid
flowchart TD
    subgraph Trace2["📊 Trace: document-ingestion"]
        UploadSpan["Span: upload-storage<br/><i>S3 / GCS / Azure Blob / local</i>"]
        ParseSpan["Span: parse-document<br/><i>extraction texte + OCR</i>"]
        ChunkSpan["Span: chunk-text<br/><i>découpage en chunks</i>"]
        subgraph EmbedSpan["Span: embed-chunks"]
            EmbedBatch["Generation: embedding × N batches"]
        end
        StoreSpan["Span: store-vectors<br/><i>stockage Qdrant</i>"]
    end

    UploadSpan --> ParseSpan --> ChunkSpan --> EmbedSpan --> StoreSpan

    style Trace2 fill:#f0f0f0,stroke:#333
    style EmbedSpan fill:#e8f4fd,stroke:#4a90d9
```

### Données capturées par Langfuse

```mermaid
mindmap
  root((Langfuse))
    Traces
      Chaque requête chat
      Chaque ingestion document
    Generations
      Appels LLM completion
      Appels embedding
      Model / Input / Output / Tokens
    Spans
      Retrieval
      Reranking
      Parsing
      Chunking
      Storage
    Metadata
      Assistant
      Collection
      Modèle / Provider
      Taille fichier
    Sessions
      Groupement par conversation_id
    Coûts
      Calcul auto via tokens
```
