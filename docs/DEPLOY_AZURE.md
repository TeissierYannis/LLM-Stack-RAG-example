# Deploiement Production — Azure

Guide complet pour deployer Enterprise Chat + RAG sur Azure en production.

---

## Table des matieres

- [Architecture cible](#architecture-cible)
- [Services Azure et couts](#services-azure-et-couts)
- [Etape 1 — Prerequisites](#etape-1--prerequisites)
- [Etape 2 — Resource Group](#etape-2--resource-group)
- [Etape 3 — Container Registry (ACR)](#etape-3--container-registry-acr)
- [Etape 4 — Azure Kubernetes Service (AKS)](#etape-4--azure-kubernetes-service-aks)
- [Etape 5 — PostgreSQL](#etape-5--postgresql)
- [Etape 6 — Redis](#etape-6--redis)
- [Etape 7 — Blob Storage](#etape-7--blob-storage)
- [Etape 8 — Azure AI Foundry (LLM)](#etape-8--azure-ai-foundry-llm)
- [Etape 9 — Document Intelligence (OCR)](#etape-9--document-intelligence-ocr)
- [Etape 10 — Qdrant](#etape-10--qdrant)
- [Etape 11 — Key Vault](#etape-11--key-vault)
- [Etape 12 — Kubernetes manifests](#etape-12--kubernetes-manifests)
- [Etape 13 — Deployer](#etape-13--deployer)
- [Etape 14 — Ingress et TLS](#etape-14--ingress-et-tls)
- [Etape 15 — Monitoring](#etape-15--monitoring)
- [Configuration .env de reference](#configuration-env-de-reference)
- [Checklist securite](#checklist-securite)
- [Maintenance et operations](#maintenance-et-operations)

---

## Architecture cible

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AZURE CLOUD                                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Azure Kubernetes Service (AKS)                                 │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │ │
│  │  │ Frontend │ │ Backend  │ │ LiteLLM  │ │ Worker   │          │ │
│  │  │ ×2       │ │ ×3       │ │ ×2       │ │ ×2       │          │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│         │              │              │              │                │
│         ▼              ▼              ▼              ▼                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐    │
│  │ Blob      │  │ PostgreSQL│  │ Redis     │  │ Azure AI      │    │
│  │ Storage   │  │ Flex 16   │  │ Cache     │  │ (GPT-4o +     │    │
│  │           │  │           │  │           │  │  Embeddings)  │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────┘    │
│                                                                       │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐    │
│  │ Document  │  │ Qdrant    │  │ Key Vault │  │ App Insights  │    │
│  │ Intel.    │  │ Cloud     │  │           │  │ + Langfuse    │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────────┘    │
│                                                                       │
│  ┌───────────┐                                                       │
│  │ ACR       │                                                       │
│  │ (images)  │                                                       │
│  └───────────┘                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Services Azure et couts

| Service | SKU recommande | Cout estime/mois |
|---------|---------------|------------------|
| AKS | 3× Standard_D2s_v3 | ~300 € |
| Azure DB for PostgreSQL | Flexible GP D2s_v3 | ~120 € |
| Azure Cache for Redis | C1 Standard | ~45 € |
| Azure Blob Storage | StorageV2 Hot | ~5 € |
| Azure AI Foundry | Pay-as-you-go | Variable (tokens) |
| Azure Document Intelligence | S0 | ~1 €/1000 pages |
| Azure Container Registry | Basic | ~5 € |
| Azure Key Vault | Standard | ~1 € |
| Qdrant Cloud | Starter | ~25 € |
| Application Insights | Pay-as-you-go | ~10 € |

**Total infra : ~500-600 €/mois** (hors tokens LLM)

---

## Etape 1 — Prerequisites

```bash
# Installer Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Se connecter
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Outils necessaires
az aks install-cli              # kubectl
```

Verifier :
```bash
az account show --query name -o tsv
kubectl version --client
docker --version
```

---

## Etape 2 — Resource Group

```bash
export RG="rg-enterprise-rag"
export LOCATION="westeurope"       # ou francecentral

az group create --name $RG --location $LOCATION
```

---

## Etape 3 — Container Registry (ACR)

```bash
export ACR_NAME="acrenterprisrag"   # unique globalement, alphanum only

az acr create \
  --resource-group $RG \
  --name $ACR_NAME \
  --sku Basic

# Login Docker
az acr login --name $ACR_NAME

# Build et push les images
docker build -t $ACR_NAME.azurecr.io/rag-backend:v1 ./backend
docker build -t $ACR_NAME.azurecr.io/rag-frontend:v1 ./frontend

docker push $ACR_NAME.azurecr.io/rag-backend:v1
docker push $ACR_NAME.azurecr.io/rag-frontend:v1
```

> **Note** : Pour le Dockerfile backend en production, retirer `--reload` de la commande
> uvicorn et utiliser plusieurs workers :
> ```dockerfile
> CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
> ```

---

## Etape 4 — Azure Kubernetes Service (AKS)

```bash
export AKS_NAME="aks-enterprise-rag"

az aks create \
  --resource-group $RG \
  --name $AKS_NAME \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3 \
  --enable-managed-identity \
  --attach-acr $ACR_NAME \
  --network-plugin azure \
  --generate-ssh-keys

# Recuperer kubeconfig
az aks get-credentials --resource-group $RG --name $AKS_NAME

# Verifier
kubectl get nodes
```

---

## Etape 5 — PostgreSQL

```bash
export PG_SERVER="pg-enterprise-rag"     # unique globalement
export PG_ADMIN="ragadmin"
export PG_PASSWORD="$(openssl rand -base64 24)"

echo "PG_PASSWORD=$PG_PASSWORD"          # NOTER CE PASSWORD

az postgres flexible-server create \
  --resource-group $RG \
  --name $PG_SERVER \
  --location $LOCATION \
  --admin-user $PG_ADMIN \
  --admin-password "$PG_PASSWORD" \
  --sku-name Standard_D2s_v3 \
  --tier GeneralPurpose \
  --version 16 \
  --storage-size 64

# Creer la base
az postgres flexible-server db create \
  --resource-group $RG \
  --server-name $PG_SERVER \
  --database-name enterprise_rag
```

**Securite reseau** — Deux options :

```bash
# Option A : Private Endpoint (recommande pour la prod)
az postgres flexible-server update \
  --resource-group $RG \
  --name $PG_SERVER \
  --public-access Disabled

# Puis creer un Private Endpoint vers le VNet AKS
# (voir section Securite ci-dessous)

# Option B : Firewall (plus simple, moins securise)
az postgres flexible-server firewall-rule create \
  --resource-group $RG \
  --name $PG_SERVER \
  --rule-name AllowAKS \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

Connection string :
```
postgresql+asyncpg://ragadmin:PASSWORD@pg-enterprise-rag.postgres.database.azure.com:5432/enterprise_rag?ssl=require
```

---

## Etape 6 — Redis

```bash
export REDIS_NAME="redis-enterprise-rag"    # unique globalement

az redis create \
  --resource-group $RG \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Standard \
  --vm-size C1

# Attendre le provisionnement (~5-10 min)
az redis show --resource-group $RG --name $REDIS_NAME --query provisioningState

# Recuperer la cle
export REDIS_KEY=$(az redis list-keys \
  --resource-group $RG \
  --name $REDIS_NAME \
  --query primaryKey -o tsv)
```

Connection string (noter le `rediss://` double-s = SSL) :
```
rediss://:REDIS_KEY@redis-enterprise-rag.redis.cache.windows.net:6380/0
```

---

## Etape 7 — Blob Storage

```bash
export STORAGE_ACCOUNT="stenterprisrag"    # unique, lowercase, pas de tirets

az storage account create \
  --resource-group $RG \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2

az storage container create \
  --account-name $STORAGE_ACCOUNT \
  --name rag-documents

# Recuperer la connection string
export STORAGE_CONN=$(az storage account show-connection-string \
  --resource-group $RG \
  --name $STORAGE_ACCOUNT \
  --query connectionString -o tsv)
```

---

## Etape 8 — Azure AI Foundry (LLM)

```bash
export AI_ACCOUNT="ai-enterprise-rag"

# Creer la ressource Azure OpenAI
az cognitiveservices account create \
  --resource-group $RG \
  --name $AI_ACCOUNT \
  --location $LOCATION \
  --kind OpenAI \
  --sku S0

# Deployer GPT-4o (completion)
az cognitiveservices account deployment create \
  --resource-group $RG \
  --name $AI_ACCOUNT \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-08-06" \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 30           # 30K tokens/min

# Deployer text-embedding-3-small (embeddings)
az cognitiveservices account deployment create \
  --resource-group $RG \
  --name $AI_ACCOUNT \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small \
  --model-version "1" \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 120          # 120K tokens/min

# Recuperer endpoint + cle
export AZURE_ENDPOINT=$(az cognitiveservices account show \
  --resource-group $RG \
  --name $AI_ACCOUNT \
  --query properties.endpoint -o tsv)

export AZURE_KEY=$(az cognitiveservices account keys list \
  --resource-group $RG \
  --name $AI_ACCOUNT \
  --query key1 -o tsv)
```

---

## Etape 9 — Document Intelligence (OCR)

```bash
az cognitiveservices account create \
  --resource-group $RG \
  --name "di-enterprise-rag" \
  --location $LOCATION \
  --kind FormRecognizer \
  --sku S0

export DI_ENDPOINT=$(az cognitiveservices account show \
  --resource-group $RG \
  --name "di-enterprise-rag" \
  --query properties.endpoint -o tsv)

export DI_KEY=$(az cognitiveservices account keys list \
  --resource-group $RG \
  --name "di-enterprise-rag" \
  --query key1 -o tsv)
```

---

## Etape 10 — Qdrant

### Option A — Qdrant Cloud (recommande)

1. Creer un compte sur [cloud.qdrant.io](https://cloud.qdrant.io)
2. Creer un cluster dans la region **Azure West Europe**
3. Copier l'URL et l'API key

```
QDRANT_URL=https://xxx-xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=your-key
```

### Option B — Qdrant sur AKS (self-hosted)

Utiliser le manifest existant :
```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/qdrant.yaml
```

Dans ce cas, l'URL interne est :
```
QDRANT_HOST=qdrant.enterprise-rag.svc.cluster.local
QDRANT_PORT=6333
QDRANT_URL=         # laisser vide pour self-hosted
```

---

## Etape 11 — Key Vault

```bash
export KV_NAME="kv-enterprise-rag"     # unique globalement

az keyvault create \
  --resource-group $RG \
  --name $KV_NAME \
  --location $LOCATION

# Stocker tous les secrets
az keyvault secret set --vault-name $KV_NAME --name "pg-password" --value "$PG_PASSWORD"
az keyvault secret set --vault-name $KV_NAME --name "redis-key" --value "$REDIS_KEY"
az keyvault secret set --vault-name $KV_NAME --name "azure-ai-key" --value "$AZURE_KEY"
az keyvault secret set --vault-name $KV_NAME --name "di-key" --value "$DI_KEY"
az keyvault secret set --vault-name $KV_NAME --name "storage-conn" --value "$STORAGE_CONN"
az keyvault secret set --vault-name $KV_NAME --name "jwt-secret" --value "$(openssl rand -base64 32)"
az keyvault secret set --vault-name $KV_NAME --name "litellm-key" --value "$(openssl rand -base64 32)"
```

Optionnel : integrer Key Vault directement dans AKS avec le CSI driver :
```bash
az aks enable-addons \
  --resource-group $RG \
  --name $AKS_NAME \
  --addons azure-keyvault-secrets-provider
```

---

## Etape 12 — Kubernetes manifests

Creer le namespace et les secrets :

```yaml
# k8s/azure-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  namespace: enterprise-rag
type: Opaque
stringData:
  SECRET_KEY: "<jwt-secret-from-keyvault>"
  LITELLM_MASTER_KEY: "<litellm-key-from-keyvault>"
  AZURE_API_KEY: "<azure-ai-key>"
  AZURE_DI_KEY: "<di-key>"
  AZURE_STORAGE_CONNECTION_STRING: "<storage-conn>"
  QDRANT_API_KEY: "<qdrant-api-key>"
  LANGFUSE_SECRET_KEY: "<langfuse-secret-key>"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: enterprise-rag
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "WARNING"
  LITELLM_PROXY_URL: "http://litellm:4000"
  COMPLETION_MODEL: "default-completion"
  EMBEDDING_MODEL: "default-embedding"

  # Azure AI
  AZURE_API_BASE: "<azure-endpoint>"
  AZURE_API_VERSION: "2024-10-21"

  # PostgreSQL
  DATABASE_URL: "postgresql+asyncpg://ragadmin:<pg-password>@<pg-server>.postgres.database.azure.com:5432/enterprise_rag?ssl=require"

  # Redis
  REDIS_URL: "rediss://:<redis-key>@<redis-name>.redis.cache.windows.net:6380/0"

  # Qdrant
  QDRANT_URL: "https://xxx.cloud.qdrant.io:6333"

  # Storage
  STORAGE_PROVIDER: "azure_blob"
  STORAGE_BUCKET: "rag-documents"

  # OCR
  OCR_PROVIDER: "azure_di"
  AZURE_DI_ENDPOINT: "<di-endpoint>"

  # Features
  AUTH_ENABLED: "true"
  USE_CELERY: "true"

  # Observability
  LANGFUSE_ENABLED: "true"
  LANGFUSE_HOST: "https://cloud.langfuse.com"
  LANGFUSE_PUBLIC_KEY: "<langfuse-public-key>"
```

Mettre a jour les images dans les manifests K8s existants :

```bash
# infra/k8s/backend.yaml → image
sed -i "s|image: .*backend.*|image: $ACR_NAME.azurecr.io/rag-backend:v1|" infra/k8s/backend.yaml

# infra/k8s/frontend.yaml → image
sed -i "s|image: .*frontend.*|image: $ACR_NAME.azurecr.io/rag-frontend:v1|" infra/k8s/frontend.yaml
```

---

## Etape 13 — Deployer

```bash
# Namespace
kubectl apply -f infra/k8s/namespace.yaml

# Secrets et config
kubectl apply -f k8s/azure-secrets.yaml

# Qdrant (si self-hosted)
kubectl apply -f infra/k8s/qdrant.yaml

# Services applicatifs
kubectl apply -f infra/k8s/litellm.yaml
kubectl apply -f infra/k8s/backend.yaml
kubectl apply -f infra/k8s/frontend.yaml

# Ingress
kubectl apply -f infra/k8s/ingress.yaml

# Verifier
kubectl get pods -n enterprise-rag
kubectl get svc -n enterprise-rag
```

Verifier les logs :
```bash
kubectl logs -n enterprise-rag -l app=backend --tail=50
kubectl logs -n enterprise-rag -l app=litellm --tail=50
```

Verifier le health check :
```bash
kubectl port-forward -n enterprise-rag svc/backend 8000:8000
curl http://localhost:8000/health
```

---

## Etape 14 — Ingress et TLS

### NGINX Ingress Controller

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz
```

### Recuperer l'IP publique

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

Pointer votre DNS (ex: `chat.votredomaine.com`) vers cette IP.

### cert-manager (Let's Encrypt automatique)

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true
```

Creer le ClusterIssuer :
```yaml
# k8s/cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@votredomaine.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

```bash
kubectl apply -f k8s/cluster-issuer.yaml
```

Mettre a jour l'ingress pour NGINX + TLS :
```yaml
# infra/k8s/ingress.yaml (version Azure)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: enterprise-rag-ingress
  namespace: enterprise-rag
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
spec:
  tls:
    - hosts:
        - chat.votredomaine.com
      secretName: rag-tls
  rules:
    - host: chat.votredomaine.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /health
            pathType: Exact
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
```

---

## Etape 15 — Monitoring

### Application Insights

```bash
az monitor app-insights component create \
  --resource-group $RG \
  --app "ai-enterprise-rag" \
  --location $LOCATION

# Recuperer l'instrumentation key pour OpenTelemetry
az monitor app-insights component show \
  --resource-group $RG \
  --app "ai-enterprise-rag" \
  --query connectionString -o tsv
```

Ajouter dans le ConfigMap :
```yaml
OTEL_EXPORTER_ENDPOINT: "<application-insights-connection-string>"
```

### Langfuse

1. Creer un compte sur [cloud.langfuse.com](https://cloud.langfuse.com)
2. Creer un projet
3. Copier les cles dans le ConfigMap/Secret

Dashboard disponible sur Langfuse avec :
- Traces de chaque requete chat
- Cout par modele et par utilisateur
- Latence et taux d'erreur
- Debug des prompts et reponses

---

## Configuration .env de reference

```env
# Production Azure — reference complete
ENVIRONMENT=production
LOG_LEVEL=WARNING
SECRET_KEY=<random-64-chars>

# Azure AI Foundry
AZURE_API_KEY=<from-key-vault>
AZURE_API_BASE=https://ai-enterprise-rag.openai.azure.com/
AZURE_API_VERSION=2024-10-21
COMPLETION_MODEL=default-completion
EMBEDDING_MODEL=default-embedding

# Database
DATABASE_URL=postgresql+asyncpg://ragadmin:xxx@pg-enterprise-rag.postgres.database.azure.com:5432/enterprise_rag?ssl=require

# Qdrant Cloud
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=<from-qdrant>

# Redis
REDIS_URL=rediss://:xxx@redis-enterprise-rag.redis.cache.windows.net:6380/0

# Azure Blob
STORAGE_PROVIDER=azure_blob
STORAGE_BUCKET=rag-documents
AZURE_STORAGE_CONNECTION_STRING=<from-key-vault>

# Azure Document Intelligence (OCR)
OCR_PROVIDER=azure_di
AZURE_DI_ENDPOINT=https://di-enterprise-rag.cognitiveservices.azure.com/
AZURE_DI_KEY=<from-key-vault>

# Features
AUTH_ENABLED=true
USE_CELERY=true

# Langfuse
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## Checklist securite

### Reseau
- [ ] Private Endpoints sur PostgreSQL (pas de firewall `0.0.0.0`)
- [ ] Private Endpoints sur Redis
- [ ] Private Endpoints sur Blob Storage
- [ ] Network Policy dans AKS pour isoler les pods
- [ ] VNet peering si Qdrant self-hosted

### Authentification
- [ ] `AUTH_ENABLED=true` en production
- [ ] `SECRET_KEY` genere aleatoirement (64+ chars)
- [ ] API keys rotees regulierement
- [ ] Azure AD integration sur AKS (RBAC)

### Chiffrement
- [ ] TLS sur l'ingress (cert-manager + Let's Encrypt)
- [ ] SSL sur PostgreSQL (`?ssl=require` dans la connection string)
- [ ] SSL sur Redis (`rediss://` protocole)
- [ ] Server-side encryption sur Blob Storage (actif par defaut)

### Secrets
- [ ] Tous les secrets dans Key Vault
- [ ] Pas de secrets en clair dans les manifests K8s (utiliser CSI driver)
- [ ] `LITELLM_MASTER_KEY` complexe et unique

### Backup et resilite
- [ ] Backup PostgreSQL active (retention 7-35 jours, actif par defaut)
- [ ] Qdrant snapshot regulier (si self-hosted)
- [ ] AKS multi-zone pour haute disponibilite
- [ ] Blob Storage avec replication GRS pour les documents critiques

### Monitoring
- [ ] Application Insights connecte
- [ ] Langfuse pour les traces LLM
- [ ] Alertes sur le health check backend
- [ ] Log Analytics Workspace connecte a AKS

---

## Maintenance et operations

### Mettre a jour l'application

```bash
# Build nouvelle version
docker build -t $ACR_NAME.azurecr.io/rag-backend:v2 ./backend
docker push $ACR_NAME.azurecr.io/rag-backend:v2

# Rolling update (zero downtime)
kubectl set image -n enterprise-rag deployment/backend \
  backend=$ACR_NAME.azurecr.io/rag-backend:v2

# Verifier le rollout
kubectl rollout status -n enterprise-rag deployment/backend
```

### Rollback si probleme

```bash
kubectl rollout undo -n enterprise-rag deployment/backend
```

### Scaler

```bash
# Scaler le backend
kubectl scale -n enterprise-rag deployment/backend --replicas=5

# Autoscaling
kubectl autoscale -n enterprise-rag deployment/backend \
  --min=3 --max=10 --cpu-percent=70
```

### Migrations base de donnees

```bash
# Exec dans un pod backend
kubectl exec -n enterprise-rag -it deploy/backend -- \
  alembic upgrade head
```

### Logs en temps reel

```bash
# Tous les pods backend
kubectl logs -n enterprise-rag -l app=backend -f --tail=100

# Un pod specifique
kubectl logs -n enterprise-rag backend-xxx-yyy -f
```
