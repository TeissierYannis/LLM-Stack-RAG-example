#!/usr/bin/env python3
"""Seed script: upload sample documents for testing the RAG pipeline."""

import sys
from pathlib import Path

import httpx

API_URL = "http://localhost:8000/api"

SAMPLE_DOCS = [
    {
        "filename": "company_policy.md",
        "content": """# Politique de l'entreprise

## Télétravail
Les employés peuvent travailler à distance jusqu'à 3 jours par semaine.
Le télétravail doit être approuvé par le manager direct.
Les jours de télétravail doivent être déclarés dans l'outil RH avant le vendredi précédent.

## Congés
- Congés payés : 25 jours par an
- RTT : 12 jours par an
- Congés exceptionnels : mariage (5 jours), naissance (3 jours), déménagement (1 jour)

Les demandes de congés doivent être soumises au moins 2 semaines à l'avance.

## Frais professionnels
Les notes de frais doivent être soumises dans les 30 jours suivant la dépense.
Le plafond pour les repas d'affaires est de 30 EUR par personne.
Les déplacements en train sont à privilégier pour les trajets inférieurs à 4 heures.

## Sécurité informatique
- Utiliser un VPN pour tout accès distant
- Activer l'authentification à deux facteurs sur tous les comptes professionnels
- Ne jamais partager ses identifiants
- Signaler tout incident de sécurité à security@company.com
""",
    },
    {
        "filename": "product_roadmap.md",
        "content": """# Roadmap Produit 2025

## Q1 - Fondations
- Migration vers microservices
- Mise en place du design system v2
- Intégration SSO avec les clients enterprise

## Q2 - Intelligence
- Lancement du module IA de recommandation
- Tableau de bord analytics avancé
- API publique v2 avec GraphQL

## Q3 - Scale
- Multi-région (EU + US)
- Optimisation des performances (objectif: < 200ms p95)
- Programme de beta testeurs

## Q4 - Enterprise
- Audit de sécurité SOC2
- Support multi-tenant amélioré
- Marketplace d'intégrations
""",
    },
    {
        "filename": "onboarding_guide.txt",
        "content": """Guide d'onboarding - Nouveaux employés

Bienvenue dans l'équipe ! Voici les étapes pour votre première semaine.

Jour 1 :
- Récupérer votre badge et votre matériel IT
- Configurer votre poste de travail (guide sur l'intranet)
- Rencontrer votre buddy d'onboarding
- Tour des bureaux

Jour 2 :
- Formation sécurité informatique (obligatoire)
- Configuration de vos accès (email, Slack, GitHub, Jira)
- Lecture de la documentation d'architecture

Jour 3 :
- Premier stand-up avec l'équipe
- Revue du backlog et des conventions de code
- Premier commit (tradition : corriger un bug simple)

Jour 4-5 :
- Sessions de pair programming avec différents membres de l'équipe
- Premiers tickets assignés
- Feedback avec le manager

Contact utiles :
- IT Support : it-support@company.com
- RH : rh@company.com
- Buddy program : buddy@company.com
""",
    },
]


def seed():
    print("Seeding sample documents...")
    for doc in SAMPLE_DOCS:
        print(f"  Uploading {doc['filename']}...")
        files = {"file": (doc["filename"], doc["content"].encode(), "text/plain")}
        response = httpx.post(f"{API_URL}/documents", files=files, timeout=60.0)
        if response.status_code == 200:
            data = response.json()
            print(f"    OK - {data['chunk_count']} chunks, status: {data['status']}")
        else:
            print(f"    FAILED - {response.status_code}: {response.text}")

    print("\nDone! Documents available at http://localhost:8000/api/documents")


if __name__ == "__main__":
    seed()
