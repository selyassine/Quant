# QuantAI — Plateforme de trading quantitatif et de gestion de portefeuille

**Plateforme full-stack de simulation : prévisions par ensemble de modèles ML, optimisation de portefeuille, backtesting de stratégies sans code, paper trading connecté à Alpaca et assistant IA à outils.**

[![Tests](https://github.com/selyassine/Quant/actions/workflows/tests.yml/badge.svg)](https://github.com/selyassine/Quant/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-02569B)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Licence MIT](https://img.shields.io/badge/licence-MIT-green)

> Projet personnel. Environnement de **paper trading uniquement** (aucun capital réel), sur données **journalières** : ce n'est pas un système de trading haute fréquence ni un conseil en investissement.

## En bref

- **Prévision de direction** (hausse / baisse) par un **ensemble LightGBM + LSTM + Transformer**, pondéré par l'AUC de validation de chaque modèle, avec **explications SHAP**.
- **Gestion de portefeuille** : optimisation de **Markowitz** et modèle de **Black-Litterman** ; mesures de risque complètes (VaR et CVaR à 95 %, Sharpe, Sortino, Calmar, drawdown maximal, bêta et alpha).
- **Stratégies sans code** : règles combinant RSI, MACD, moyennes mobiles simples et exponentielles, ATR, stochastique, VWAP… ; stratégies prêtes à l'emploi (RSI Mean Reversion, MACD Crossover, Golden Cross…) et **backtest** avec courbe d'équité.
- **Agent de trading** : propose des ordres à partir de l'ensemble de modèles, avec filtres de risque ; **chaque ordre est validé ou refusé par l'utilisateur**.
- **Assistant IA** (Groq, Llama 3.3 70B) avec **RAG** (ChromaDB, optionnel) et 5 outils : prédiction, optimisation de portefeuille, backtest, sentiment des actualités, explication SHAP.
- **Production** : API FastAPI (14 modules, 60+ endpoints), PostgreSQL, Celery + Redis pour les tâches lourdes, suivi MLOps des modèles, rapports PDF (ReportLab), le tout lancé par Docker Compose.

## Architecture

```
┌──────────────────────────────┐        ┌────────────────────────────────────┐
│        quantai-frontend       │  HTTP  │            quantai-backend           │
│  Next.js 14 · TypeScript      │◄──────►│  FastAPI · SQLAlchemy · Pydantic v2 │
│  Tailwind · Recharts · SSE    │  SSE   │  Celery worker + beat · Redis        │
└──────────────────────────────┘        │  PostgreSQL                           │
                                         └──────────────────┬─────────────────┘
                                                            │
             ┌──────────────────────────────┬───────────────┴─────────────┬──────────────────────┐
             ▼                              ▼                             ▼                      ▼
   Modèles ML (LightGBM,          Portefeuille et risque        Alpaca Paper Trading       Groq (LLM) + RAG
   LSTM, Transformer, SHAP)       (Markowitz, Black-Litterman)  (ordres, flux de prix)     Yahoo Finance (données)
```

## Modules

| Module | Ce qu'il fait | Endpoint |
| --- | --- | --- |
| Données de marché | Historique OHLCV (Yahoo Finance), indicateurs techniques | `/api/v1/market` |
| Prédiction | Ensemble LightGBM + LSTM + Transformer par actif | `/api/v1/predict` |
| Explicabilité | Valeurs SHAP des décisions du modèle | `/api/v1/explain` |
| Portefeuille | Markowitz, Black-Litterman, mesures de risque | `/api/v1/portfolio` |
| Stratégies | Constructeur de règles sans code, stratégies prêtes à l'emploi | `/api/v1/strategy` |
| Backtesting | Simulation historique, courbe d'équité, Sharpe, drawdown, taux de réussite | `/api/v1/backtest` |
| Actualités | Collecte et analyse de sentiment | `/api/v1/news` |
| Paper trading | Compte virtuel de 100 000 $, ordres, positions, P&L | `/api/v1/paper` |
| Temps quasi réel | Flux de prix Alpaca diffusé en SSE | `/api/v1/realtime` |
| Agent | Propositions d'ordres, validation humaine | `/api/v1/agent` |
| Assistant IA | Chat Groq + RAG + 5 outils financiers | `/api/v1/assistant` |
| Analytique | Statistiques de la plateforme | `/api/v1/analytics` |
| MLOps | Registre des modèles entraînés, suivi des prédictions | `/api/v1/mlops` |
| Rapports | Export PDF (portefeuille, backtest, plateforme) | `/api/v1/report` |

La documentation interactive complète (OpenAPI) est disponible sur `http://localhost:8000/docs` une fois l'API lancée.

## Installation

Prérequis : Docker et Docker Compose, Node.js 18 ou plus, une clé Alpaca Paper Trading (gratuite) et une clé Groq (gratuite).

```bash
git clone https://github.com/selyassine/Quant.git
cd Quant/quantai-backend
cp .env.example .env          # renseigner ALPACA_API_KEY, ALPACA_SECRET_KEY et GROQ_API_KEY
docker compose up --build     # API, PostgreSQL, Redis, worker et planificateur Celery
```

Charger les données historiques fournies (9 actifs : AAPL, MSFT, GOOGL, NVDA, TSLA, SPY, QQQ, BTC, ETH) :

```bash
docker cp scripts/market_data_csv quantai_api:/app/scripts/market_data_csv
docker exec quantai_api python scripts/import_csv.py
```

Puis le frontend :

```bash
cd ../quantai-frontend
npm install
npm run dev                   # http://localhost:3000
```

## Structure du dépôt

```
quantai-backend/
├── app/
│   ├── api/endpoints/      # un fichier par module (routes FastAPI)
│   ├── core/config.py      # configuration (pydantic-settings, lue depuis .env)
│   ├── db/                 # modèles SQLAlchemy et connexion
│   ├── schemas/            # schémas Pydantic
│   ├── services/           # logique métier : ml/, portfolio/, risk/, strategy/, backtest/,
│   │                       # paper_trading/, alpaca/, assistant/, rag/, news/, mlops/, reports/ …
│   └── tasks/              # tâches Celery
├── scripts/                # téléchargement et import des données historiques
├── docker-compose.yml
└── requirements.txt

quantai-frontend/src/
├── app/                    # routes Next.js (accueil, inscription)
├── components/             # une page par module (Dashboard, Predict, Portfolio, Strategy, Backtest, Agent…)
├── contexts/               # authentification
└── lib/api.ts              # client de l'API
```

## Choix techniques et difficultés résolues

- **Pondération de l'ensemble** : chaque modèle pèse selon son AUC de validation ; quand un seul modèle est entraîné pour un actif, l'agent assouplit ses filtres de confiance au lieu d'exiger un accord entre modèles.
- **Yahoo Finance bloque les IP des conteneurs Docker** : les données sont téléchargées sur la machine hôte, puis importées dans PostgreSQL par script.
- **PyTorch en version CPU** : image Docker environ 4 fois plus légère (environ 200 Mo au lieu de 780 Mo).
- **Configuration sans secret dans le code** : toutes les clés sont lues depuis `.env`, jamais versionné.

## Limites

- Données journalières (fin de séance) : le flux « temps réel » rafraîchit les prix toutes les deux secondes environ, mais les modèles raisonnent sur des barres quotidiennes.
- Paper trading uniquement.
- Tests unitaires sur les mesures de risque et le moteur de stratégies (`quantai-backend/tests`, lancés par GitHub Actions) ; les services connectés à Alpaca, à la base et aux modèles ne sont pas encore couverts.

## Licence

Distribué sous licence MIT : voir [`LICENSE`](LICENSE).

---

Réalisé par **Yassine Selmi** — [github.com/selyassine](https://github.com/selyassine)
