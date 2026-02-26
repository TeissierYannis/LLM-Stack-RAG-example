# Setup Guide

Guide d'installation complet pour Enterprise Chat + RAG.
Trois modes disponibles : **Local** (LM Studio), **Cloud Dev** (multi-provider), **Production Azure**.

---

## Table des matières

- [Prérequis communs](#prérequis-communs)
- [Mode 1 — Local (LM Studio, zero cloud)](#mode-1--local-lm-studio-zero-cloud)
- [Mode 2 — Cloud Dev (multi-provider)](#mode-2--cloud-dev-multi-provider)
- [Mode 3 — Production Azure](#mode-3--production-azure)
- [Features optionnelles](#features-optionnelles)
- [Endpoints API](#endpoints-api)
- [Troubleshooting](#troubleshooting)

---

## Prérequis communs

| Outil | Version min. | Installation |
|-------|-------------|-------------|
| Docker | 24+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | v2+ | Inclus avec Docker Desktop |
| Git | 2.30+ | `apt install git` / `brew install git` |

```bash
git clone <repo-url>
cd LLM-Stack-RAG-example
```

---

## Mode 1 — Local (LM Studio, zero cloud)

Aucune API key, aucune donnée envoyée à l'extérieur. Tout tourne sur votre machine.

### 1.1 Installer LM Studio

Télécharger et installer depuis [lmstudio.ai](https://lmstudio.ai).

### 1.2 Charger les modèles

Ouvrir LM Studio → **Discover** → Télécharger :

| Usage | Modèle | VRAM |
|-------|--------|------|
| **Completion** | `Qwen2.5-7B-Instruct` | ~5 GB |
| **Embedding** | `nomic-ai/nomic-embed-text-v1.5-GGUF` | ~0.3 GB |

Alternatives selon votre GPU :

| VRAM disponible | Completion | Embedding |
|-----------------|-----------|-----------|
| 4 GB | Qwen2.5-3B-Instruct | all-MiniLM-L6-v2-GGUF |
| 8 GB | Qwen2.5-7B-Instruct | nomic-embed-text-v1.5-GGUF |
| 12 GB | Mistral-7B-Instruct-v0.3 | bge-large-en-v1.5-gguf |
| 16 GB+ | Qwen2.5-14B-Instruct | nomic-embed-text-v1.5-GGUF |

### 1.3 Démarrer le serveur LM Studio

1. Aller dans **Developer** → **Local Server**
2. Activer **"Allow multiple models"**
3. Charger les 2 modèles (completion + embedding)
4. Cliquer **Start Server** (port 1234)

Vérifier que ça fonctionne :
```bash
curl http://localhost:1234/v1/models
```

### 1.4 Configurer l'environnement

```bash
cp .env.local.example .env
```

Aucune modification nécessaire, le fichier est prêt.

### 1.5 Lancer le stack

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

Premier lancement : ~3-5 min pour build les images.

### 1.6 Vérifier

| Service | URL | Status attendu |
|---------|-----|----------------|
| Frontend | http://localhost:3000 | Interface chat |
| Backend | http://localhost:8000/health | `{"status": "ok"}` |
| LiteLLM | http://localhost:4000/health | Health check OK |
| Qdrant | http://localhost:6333/dashboard | Dashboard Qdrant |

```bash
# Test rapide
curl http://localhost:8000/health
```

---

## Mode 2 — Cloud Dev (multi-provider)

Utilise les LLMs cloud (Bedrock, Azure Foundry, Vertex AI) avec l'infrastructure en local (Docker).

### 2.1 Configurer les providers LLM

```bash
cp .env.example .env
```

Éditer `.env` et remplir les credentials des providers que vous voulez utiliser :

#### AWS Bedrock (Claude)

```env
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION_NAME=us-east-1
```

Prérequis AWS :
1. Un utilisateur IAM avec accès Bedrock
2. Activer les modèles dans la console Bedrock (Claude 3.5 Sonnet + Titan Embed)

#### Azure AI Foundry (GPT-4o)

```env
AZURE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_API_BASE=https://your-resource.openai.azure.com/
AZURE_API_VERSION=2024-10-21
```

Prérequis Azure :
1. Créer une ressource Azure OpenAI
2. Déployer les modèles : `gpt-4o` + `text-embedding-3-small`

#### Google Vertex AI (Gemini)

```env
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-service-account.json
VERTEX_PROJECT=your-gcp-project
VERTEX_LOCATION=us-central1
```

Prérequis GCP :
1. Activer l'API Vertex AI
2. Créer un Service Account avec le rôle `Vertex AI User`
3. Monter le fichier JSON dans le container (ajouter un volume dans docker-compose)

### 2.2 Configurer les modèles

```env
# Modèle par défaut pour le chat
COMPLETION_MODEL=default-completion

# Modèle par défaut pour les embeddings
EMBEDDING_MODEL=default-embedding
```

Les modèles `default-*` utilisent le load-balancing LiteLLM avec fallback automatique
entre tous les providers configurés.

Pour forcer un seul provider :
```env
COMPLETION_MODEL=claude-sonnet       # Force AWS Bedrock
COMPLETION_MODEL=gpt-4o              # Force Azure
COMPLETION_MODEL=gemini-flash        # Force Google
```

### 2.3 Lancer

```bash
docker compose up --build
```

### 2.4 Vérifier les modèles disponibles

```bash
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-litellm-master-key"
```

---

## Mode 3 — Production Azure

Voir le guide dédié : **[docs/DEPLOY_AZURE.md](docs/DEPLOY_AZURE.md)**

---

## Features optionnelles

Toutes les features sont **opt-in** via variables d'environnement.

### OCR (extraction de texte depuis images/scans)

```env
# Local (Tesseract, inclus dans l'image Docker)
OCR_PROVIDER=local

# Cloud providers
OCR_PROVIDER=aws_textract           # + AWS creds
OCR_PROVIDER=azure_di               # + AZURE_DI_ENDPOINT + AZURE_DI_KEY
OCR_PROVIDER=google_docai           # + GOOGLE_DOCAI_PROCESSOR

# Auto : essaie cloud → fallback local
OCR_PROVIDER=auto
```

### Object Storage (persistance des fichiers bruts)

```env
# Local (défaut, /tmp/rag-storage dans le container)
STORAGE_PROVIDER=local

# AWS S3
STORAGE_PROVIDER=s3
STORAGE_BUCKET=my-rag-bucket

# Google Cloud Storage
STORAGE_PROVIDER=gcs
STORAGE_BUCKET=my-rag-bucket

# Azure Blob
STORAGE_PROVIDER=azure_blob
STORAGE_BUCKET=rag-documents
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
```

### Qdrant Cloud (vector DB managé)

```env
# Laisser vide = utilise le Qdrant self-hosted Docker
QDRANT_URL=
QDRANT_API_KEY=

# Qdrant Cloud
QDRANT_URL=https://xxx-xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-cloud-api-key
```

Si `QDRANT_URL` est défini, le Qdrant Docker est ignoré et tout pointe vers le cloud.

### Reranking (améliore la précision RAG)

```env
# Désactivé par défaut
RERANK_MODEL=

# Activer (Cohere Rerank via Bedrock)
RERANK_MODEL=cohere-rerank
```

Le reranker over-retrieve 2x le nombre de chunks puis re-score avec un cross-encoder
pour garder uniquement les plus pertinents.

### Background processing (Celery)

```env
USE_CELERY=true
```

```bash
# Lancer avec le worker Celery
docker compose --profile celery up
```

Les documents sont uploadés immédiatement (stockés en object storage) puis
traités en arrière-plan par le worker. Utile pour les gros fichiers.

### Authentication (JWT + API keys)

```env
AUTH_ENABLED=true
SECRET_KEY=votre-secret-jwt-de-32-chars-minimum
API_KEYS=key-1-xxx,key-2-yyy         # Clés pour accès programmatique
```

Endpoints auth :
- `POST /api/auth/token` → obtenir un JWT
- `GET /api/auth/me` → infos utilisateur courant
- `GET /api/auth/status` → état de l'auth

### Langfuse (observabilité LLM)

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

Créer un compte sur [cloud.langfuse.com](https://cloud.langfuse.com) et créer un projet
pour obtenir les clés. Toutes les traces (chat, RAG, embeddings, ingestion) apparaissent
automatiquement dans le dashboard.

### OpenTelemetry (tracing infra)

```env
OTEL_EXPORTER_ENDPOINT=http://jaeger:4317   # ou Grafana Tempo, Datadog, etc.
```

---

## Endpoints API

### Chat

| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/chat/stream` | Chat avec streaming SSE |
| POST | `/api/chat` | Chat non-streaming |

### Assistants

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/assistants` | Lister les assistants |
| POST | `/api/assistants` | Créer un assistant |
| GET | `/api/assistants/{id}` | Détail d'un assistant |
| PUT | `/api/assistants/{id}` | Modifier un assistant |
| DELETE | `/api/assistants/{id}` | Supprimer (+ sa collection Qdrant) |

### Documents

| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/assistants/{id}/documents` | Upload un document |
| GET | `/api/assistants/{id}/documents` | Lister les documents |
| DELETE | `/api/assistants/{id}/documents/{doc_id}` | Supprimer un document |

Formats supportés : PDF, DOCX, MD, TXT, PNG, JPG, JPEG, WebP, BMP, TIFF

### Conversations

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/conversations` | Lister les conversations |
| GET | `/api/conversations/{id}` | Détail + messages |
| DELETE | `/api/conversations/{id}` | Supprimer |

### Système

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/health` | Health check |
| GET | `/api/models` | Modèles LLM disponibles |
| GET | `/api/models/ocr` | Info provider OCR |

---

## Troubleshooting

### Le backend ne démarre pas

```bash
# Vérifier les logs
docker compose logs backend

# Cause fréquente : PostgreSQL pas encore prêt
# Solution : relancer, le healthcheck gère le retry
docker compose restart backend
```

### LiteLLM ne se connecte pas aux providers

```bash
# Vérifier les logs LiteLLM
docker compose logs litellm

# Tester directement
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer sk-litellm-master-key"
```

Causes fréquentes :
- Credentials AWS/Azure/GCP manquantes ou invalides dans `.env`
- Modèles pas activés dans la console du provider (Bedrock nécessite activation manuelle)
- Mauvais `AZURE_API_BASE` (doit finir par `.openai.azure.com/`)

### Mode local : LM Studio non accessible

```bash
# Vérifier que LM Studio répond
curl http://localhost:1234/v1/models

# Si ça marche depuis l'hôte mais pas depuis Docker, vérifier le DNS
docker compose -f docker-compose.yml -f docker-compose.local.yml exec litellm \
  curl http://host.docker.internal:1234/v1/models
```

Causes fréquentes :
- LM Studio server pas démarré
- Firewall bloque le port 1234
- Sur Linux sans Docker Desktop : `host.docker.internal` peut ne pas fonctionner.
  Solution : utiliser l'IP de l'hôte directement dans `docker-compose.local.yml`

### Upload de documents échoue

```bash
docker compose logs backend | grep -i "error\|exception"
```

Causes fréquentes :
- Fichier trop gros (augmenter le timeout nginx/ingress en prod)
- OCR cloud non configuré pour les images/scans
- Qdrant non accessible (vérifier `docker compose logs qdrant`)

### Réinitialiser toutes les données

```bash
docker compose down -v    # Supprime tous les volumes (DB, Qdrant, Redis)
docker compose up --build
```
