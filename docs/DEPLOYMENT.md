# Deployment Guide

## Setup Local (Docker Compose)

### Prérequis
- Docker + Docker Compose v2
- Au moins un provider cloud configuré (AWS/Azure/GCP)

### Variables d'environnement

Copier `.env.example` vers `.env` et configurer :

```bash
cp .env.example .env
```

### Lancer la stack

```bash
# Build et lancement
docker compose up --build

# En arrière-plan
docker compose up --build -d

# Voir les logs
docker compose logs -f backend
```

### Accès
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- LiteLLM Proxy: http://localhost:4000
- Qdrant Dashboard: http://localhost:6333/dashboard

---

## Setup Cloud (Kubernetes)

### Architecture Cloud

```
                    ┌──────────────┐
                    │  Ingress /   │
                    │  Load        │
                    │  Balancer    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Frontend │ │ Backend  │ │ LiteLLM  │
        │ (nginx)  │ │ (FastAPI)│ │ Proxy    │
        │ 2 pods   │ │ 3 pods   │ │ 2 pods   │
        └──────────┘ └──────────┘ └──────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Qdrant   │ │PostgreSQL│ │  Redis   │
        │ (managed │ │ (managed │ │ (managed │
        │  or pod) │ │  or RDS) │ │  or pod) │
        └──────────┘ └──────────┘ └──────────┘
```

### Déploiement avec Terraform

```bash
cd infra/terraform

# Initialiser
terraform init

# Planifier
terraform plan -var-file=env/production.tfvars

# Appliquer
terraform apply -var-file=env/production.tfvars
```

### Déploiement Kubernetes

```bash
cd infra/k8s

# Créer le namespace
kubectl apply -f namespace.yaml

# Déployer les secrets
kubectl apply -f secrets.yaml

# Déployer la stack
kubectl apply -f .
```
