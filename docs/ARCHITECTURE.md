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

---

## 6. OCR multi-provider (fallback)

```mermaid
flowchart LR
    Input["📄 Document image/scan"]

    Input --> Auto{"Mode auto ?"}

    Auto -->|"Oui"| Try1["Essai AWS Textract"]
    Try1 -->|"❌ échec"| Try2["Essai Azure DI"]
    Try2 -->|"❌ échec"| Try3["Essai GCP DAI"]
    Try3 -->|"❌ échec"| Fallback["Tesseract local"]

    Try1 -->|"✅"| Result["Texte extrait"]
    Try2 -->|"✅"| Result
    Try3 -->|"✅"| Result
    Fallback --> Result

    Auto -->|"Non<br/><i>provider spécifique</i>"| Direct["Provider configuré"]
    Direct --> Result

    style Input fill:#4a90d9,color:#fff
    style Result fill:#7ed321,color:#fff
    style Fallback fill:#f5a623,color:#fff
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
