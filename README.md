# Enterprise Chat + RAG with LiteLLM

Chat d'entreprise avec Retrieval-Augmented Generation (RAG) utilisant LiteLLM comme proxy vers AWS Bedrock, Azure AI Foundry et Google Vertex AI.

## Architecture

```
Users → React Frontend → FastAPI Backend → LiteLLM Proxy → Bedrock / Foundry / Vertex
                                ↕                              ↕
                          Qdrant (vectors)              Embedding Models
                          PostgreSQL (data)
                          Redis (cache)
```

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour les schémas détaillés.

## Quick Start (Local)

### 1. Prérequis

- Docker + Docker Compose v2
- Credentials pour au moins un provider (AWS/Azure/GCP)

### 2. Configuration

```bash
cp .env.example .env
# Éditer .env avec vos credentials
```

### 3. Lancement

```bash
docker compose up --build
```

### 4. Accès

| Service | URL |
|---------|-----|
| Chat UI | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| LiteLLM | http://localhost:4000 |
| Qdrant | http://localhost:6333/dashboard |

## Fonctionnalités

- **Chat multi-modèles** : Basculez entre Claude (Bedrock), GPT-4o (Azure), Gemini (Vertex)
- **RAG sur vos documents** : Upload PDF, DOCX, Markdown, TXT
- **Streaming** : Réponses en temps réel via Server-Sent Events
- **Historique** : Conversations persistées en PostgreSQL
- **Sources** : Chaque réponse cite les documents sources utilisés
- **Multi-provider** : Failover automatique entre providers via LiteLLM

## Stack

| Composant | Technologie |
|-----------|------------|
| Frontend | React + TypeScript + Tailwind |
| Backend | FastAPI (Python 3.12) |
| LLM Proxy | LiteLLM |
| Vectors | Qdrant |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Containers | Docker Compose |
| Cloud | Terraform + Kubernetes |

## Déploiement Cloud

Voir [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Structure du projet

```
.
├── backend/           # API FastAPI + RAG engine
│   ├── app/
│   │   ├── api/       # Endpoints REST
│   │   ├── core/      # Config, database, dependencies
│   │   ├── models/    # SQLAlchemy models
│   │   ├── rag/       # Pipeline RAG (parsing, chunking, retrieval)
│   │   └── services/  # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/          # React chat UI
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── Dockerfile
│   └── package.json
├── litellm/           # LiteLLM proxy config
│   └── config.yaml
├── docker/            # Docker configs additionnels
├── infra/             # Infrastructure as Code
│   ├── terraform/
│   └── k8s/
├── docs/              # Documentation + schémas
├── scripts/           # Scripts utilitaires
├── docker-compose.yml
└── .env.example
```
