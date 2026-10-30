# 📈 QuantAI — Plateforme IA de Trading Quantitatif & Gestion de Portefeuille

> Plateforme full-stack combinant trading algorithmique, intelligence artificielle et analyse de portefeuille en temps quasi-réel, pensée pour le paper trading, le backtesting et l'assistance décisionnelle par IA.


---

## 📋 Table des matières

- [Aperçu](#-aperçu)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Stack technique](#-stack-technique)
- [Modules de la plateforme](#-modules-de-la-plateforme)
- [Structure du projet](#-structure-du-projet)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [API](#-api)
- [Points techniques notables](#-points-techniques-notables)
- [Limites connues](#-limites-connues--avertissements)
- [Roadmap](#-roadmap)
- [Licence](#-licence)

---

## 🎯 Aperçu

**QuantAI** est une plateforme complète de simulation de trading quantitatif permettant de :
- Construire des stratégies de trading **sans code**, à partir d'indicateurs techniques.
- **Backtester** ces stratégies sur données historiques avec courbes d'équité et métriques de performance.
- Suivre un portefeuille de **paper trading** (compte virtuel de 100 000 $).
- Recevoir des **prix en temps quasi-réel** via un flux SSE connecté à Alpaca.
- Dialoguer avec un **assistant IA financier** (propulsé par l'API Claude) capable d'interroger le portefeuille, lancer des prédictions, expliquer des backtests, résumer l'actualité ou interpréter des scores SHAP.
- Déléguer certaines décisions à un **agent de trading autonome** basé sur un ensemble de modèles ML, avec workflow de validation humaine (accepter/refuser).
- Générer des **rapports PDF professionnels** (portefeuille, backtest, plateforme complète).

Le projet a été développé **module par module**, avec un cycle complet build → debug → déploiement à chaque étape, jusqu'à son achèvement.

---

## ✨ Fonctionnalités

| Domaine | Fonctionnalités |
|---|---|
| **Trading** | Paper trading (100k$ virtuels), suivi ordres/positions/P&L, connexion Alpaca Paper Trading |
| **Stratégies** | Générateur no-code, 30+ indicateurs techniques, 5 stratégies préconfigurées |
| **Backtesting** | Simulation historique, courbes d'équité, métriques (Sharpe, drawdown, win rate, profit factor) |
| **Données live** | Flux de prix quasi-temps réel via SSE (~2 sec), streaming type WebSocket |
| **IA** | Assistant conversationnel (API Claude) avec 5 outils financiers intégrés |
| **Agent autonome** | Génération d'ordres par ensemble ML, validation humaine avant exécution |
| **Reporting** | Export PDF (ReportLab) : rapport portefeuille, rapport backtest, rapport plateforme complet |
| **Interface** | 15 pages Next.js, navigation complète, visualisations Recharts |

---

## 🏗️ Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│      quantai-frontend        │  HTTP  │        quantai-backend         │
│  Next.js 14 · TS · Tailwind  │◄──────►│  FastAPI · SQLAlchemy · Celery │
│  Recharts · 15 pages · SSE   │  SSE   │  PostgreSQL · Redis            │
└───────────────┬──────────────┘        └───────────────┬────────────────┘
                │                                        │
                │                                        ▼
                │                          ┌──────────────────────────┐
                │                          │   Services externes        │
                │                          │  - Alpaca Paper Trading    │
                │                          │  - API Claude (Anthropic)  │
                │                          │  - Yahoo Finance (données) │
                │                          └──────────────────────────┘
```

- **Deux dépôts séparés** : `quantai-backend` et `quantai-frontend`.
- **Environnement de développement** : Windows + Docker (conteneurs isolés pour l'API, la base de données, Redis et les workers Celery).
- **Tâches asynchrones** : Celery + Redis pour les traitements lourds (backtests, entraînement de modèles, génération de rapports).

---

## 🛠️ Stack technique

### Backend
- **FastAPI** — framework API principal
- **PostgreSQL** — base de données relationnelle (comptes, ordres, positions, stratégies)
- **Redis** — cache et broker de messages
- **Celery** — traitement asynchrone (backtests, tâches longues)
- **SQLAlchemy** — ORM
- **pydantic-settings v2** — gestion de la configuration
- **ReportLab** — génération de PDF
- **Alpaca API** — trading papier et streaming de prix
- **API Claude (Anthropic)** — assistant IA financier

### Frontend
- **Next.js 14**
- **TypeScript**
- **Tailwind CSS**
- **Recharts** — visualisation de données (courbes d'équité, portefeuille, indicateurs)
- **SSE (Server-Sent Events)** — flux de prix en direct

---

## 🧩 Modules de la plateforme

| Module | Description |
|---|---|
| **M4 — Strategy Builder** | Moteur de règles no-code, 30+ indicateurs techniques, 5 stratégies préconfigurées, backtesting avec courbes d'équité |
| **M9 — Paper Trading** | Compte virtuel de 100 000 $, modèles SQLAlchemy, suivi des ordres/positions/P&L |
| **M11 — Assistant IA Financier** | Chatbot propulsé par l'API Claude avec 5 outils : prédiction, portefeuille, backtest, actualités, interprétation SHAP |
| **M14 — Générateur de rapports** | Export PDF réel via ReportLab (rapport Portefeuille, rapport Backtest, rapport Plateforme complet) |
| **Intégration Alpaca** | Streaming de prix en direct via SSE, compte Alpaca Paper Trading connecté (endpoint `https://paper-api.alpaca.markets/v2`), mises à jour toutes les ~2 secondes |
| **Agent de trading autonome** | Génération d'ordres pilotée par un ensemble de modèles ML, avec workflow d'acceptation/refus par l'utilisateur |

### Pages frontend (15 pages)
Incluant notamment `RealtimePage` (prix en direct), `AssistantPage` (chat IA) et `AgentPage` (agent autonome), toutes intégrées à la navigation principale (Sidebar).

---

## 📁 Structure du projet

```
quantai-backend/
├── app/
│   ├── api/                # Routes FastAPI (trading, strategies, backtest, assistant, agent, reports)
│   ├── models/              # Modèles SQLAlchemy (comptes, ordres, positions, stratégies)
│   ├── services/            # Logique métier (Alpaca, Claude, ML, reporting)
│   ├── ml/                  # Modèles ML pour l'agent autonome et les prédictions
│   ├── core/                 # Config (pydantic-settings), sécurité, dépendances
│   └── worker/                # Tâches Celery
├── alembic/                  # Migrations base de données
├── tests/
├── docker-compose.yml
└── requirements.txt

quantai-frontend/
├── app/                       # 15 pages (Dashboard, Strategies, Backtest, Realtime, Assistant, Agent, Reports, ...)
├── components/                # Composants réutilisables (StatCard, charts, etc.)
├── lib/                       # Clients API, utilitaires SSE
├── styles/                    # Tailwind config
└── package.json
```

---

## 🚀 Installation

### Prérequis
- Docker & Docker Compose
- Node.js 18+ (si exécution du frontend hors conteneur)
- Compte Alpaca Paper Trading (clé API)
- Clé API Anthropic (Claude)

### 1. Cloner les dépôts
```bash
git clone <url-quantai-backend>
git clone <url-quantai-frontend>
```

### 2. Backend
```bash
cd quantai-backend
cp .env.example .env   # renseigner les variables (voir Configuration)
docker compose up --build
```
Le backend expose l'API sur `http://localhost:8000` (docs interactives sur `/docs`).

### 3. Frontend
```bash
cd quantai-frontend
npm install
npm run dev
```
Le frontend est disponible sur `http://localhost:3000`.

---

## ⚙️ Configuration

Variables d'environnement principales (`.env` du backend) :

```env
# Base de données
POSTGRES_USER=quantai
POSTGRES_PASSWORD=********
POSTGRES_DB=quantai_db
DATABASE_URL=postgresql://quantai:********@db:5432/quantai_db

# Redis / Celery
REDIS_URL=redis://redis:6379/0

# Alpaca Paper Trading
ALPACA_API_KEY=********
ALPACA_SECRET_KEY=********
ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2

# Anthropic (Assistant IA)
ANTHROPIC_API_KEY=********
```


---

## 💻 Utilisation

1. **Créer/consulter le compte de paper trading** (100 000 $ virtuels par défaut).
2. **Construire une stratégie** dans le Strategy Builder à partir des indicateurs disponibles, ou partir d'une des 5 stratégies préconfigurées.
3. **Backtester** la stratégie sur des données historiques et analyser la courbe d'équité, le Sharpe ratio, le max drawdown, le win rate et le profit factor.
4. **Suivre les prix en direct** sur la page Realtime (flux SSE Alpaca).
5. **Interroger l'assistant IA** pour des analyses de portefeuille, des prédictions, des résumés d'actualité ou des explications SHAP.
6. **Activer l'agent autonome** pour recevoir des propositions d'ordres générées par le modèle ML, à valider ou refuser manuellement.
7. **Exporter un rapport PDF** (portefeuille, backtest ou plateforme complète) depuis le module de reporting.

---

## 🔌 API

La documentation interactive complète (Swagger/OpenAPI) est générée automatiquement par FastAPI et disponible sur :

```
http://localhost:8000/docs
```

Grandes familles d'endpoints :
- `POST /trading/orders` — passage d'ordres (paper trading)
- `GET /portfolio` — état du portefeuille (positions, P&L)
- `POST /strategies` / `POST /backtest` — création et backtest de stratégies
- `GET /realtime/stream` — flux SSE des prix
- `POST /assistant/chat` — assistant IA financier
- `POST /agent/propose` / `POST /agent/decision` — agent autonome (proposition/validation)
- `GET /reports/{type}` — génération de rapports PDF

---

## 🔍 Points techniques notables

- **Honnêteté sur la granularité des données** : la plateforme fonctionne sur des données **fin de journée (end-of-day)**, pas du tick-level temps réel — une distinction importante à garder en tête lors de l'évaluation des fonctionnalités "temps réel".
- **Métriques d'évaluation** des stratégies : Sharpe ratio, max drawdown, win rate, profit factor.
- **Correctifs notables résolus pendant le développement** :
  - Contournement du blocage des IP Docker par Yahoo Finance : téléchargement du CSV en local puis import dans le conteneur.
  - Clé dupliquée sur `paper_accounts` : gérée par un pattern try/except avec rollback.
  - Erreurs de rendu React liées aux objets passés en enfants : conversion des éléments de `tools_used` en chaînes et encapsulation des valeurs de `StatCard` avec `String()`.
  - Bug d'affichage de `avg_confidence` (ex. 5716% au lieu de 57.16%) : correction par un seuil de vérification (`> 1`) avant multiplication par 100.

---

## ⚠️ Limites connues / avertissements

- Données **end-of-day**, pas tick-level : les décisions basées sur ce système ne reflètent pas une exécution en temps réel de marché réel.
- Environnement de **paper trading uniquement** (compte Alpaca simulé) — aucune exécution sur capital réel.
- Nécessite des clés API valides (Alpaca + Anthropic) pour l'ensemble des fonctionnalités.

---

## 🗺️ Roadmap (pistes d'évolution possibles)

- Passage à des données de marché tick-level / temps réel réel.
- Support multi-comptes et multi-devises.
- Élargissement du catalogue d'indicateurs et de stratégies préconfigurées.
- Déploiement cloud (au-delà de l'environnement Docker local).
- Tests automatisés end-to-end plus poussés.

---

## 📄 Licence

Ce projet est distribué sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

<p align="center">Développé par <strong>Yassine</strong> — plateforme QuantAI</p>
