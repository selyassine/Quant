"""
RAG Service — Retrieval Augmented Generation
ChromaDB vector store + sentence-transformers embeddings.
Stores: OHLCV summaries, news articles, strategy results.
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy imports to avoid startup errors if not installed
_chroma_client = None
_embedding_fn = None
_collection = None


def _get_chroma():
    global _chroma_client, _collection, _embedding_fn
    if _chroma_client is not None:
        return _chroma_client, _collection

    try:
        import chromadb
        from chromadb.utils import embedding_functions

        _chroma_client = chromadb.Client()

        # Use sentence-transformers if available, fallback to simple
        try:
            _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        except Exception:
            _embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        _collection = _chroma_client.get_or_create_collection(
            name="quantai_knowledge",
            embedding_function=_embedding_fn,
        )
        logger.info("[RAG] ChromaDB initialized")
        return _chroma_client, _collection
    except ImportError:
        logger.warning("[RAG] ChromaDB not installed — RAG disabled")
        return None, None


class RAGService:
    """
    Financial RAG pipeline.
    Indexes: market summaries, news, strategy results, predictions.
    Retrieves: top-K relevant chunks for LLM context.
    """

    def add_market_context(
        self,
        ticker: str,
        price: float,
        change_pct: float,
        volume: int,
        extra: Optional[Dict] = None,
    ):
        """Add a market data summary to the vector store."""
        _, collection = _get_chroma()
        if collection is None:
            return

        text = (
            f"{ticker} — Price: ${price:.2f}, Change: {change_pct:+.2f}%, "
            f"Volume: {volume:,}. "
        )
        if extra:
            text += " ".join(f"{k}: {v}" for k, v in extra.items())

        doc_id = f"market_{ticker}_{datetime.now().strftime('%Y%m%d%H')}"
        try:
            collection.upsert(
                documents=[text],
                ids=[doc_id],
                metadatas=[{"type": "market", "ticker": ticker, "ts": str(datetime.now())}],
            )
        except Exception as e:
            logger.warning(f"[RAG] upsert failed: {e}")

    def add_news(self, title: str, summary: str, ticker: str, sentiment: str):
        """Add a news article to the vector store."""
        _, collection = _get_chroma()
        if collection is None:
            return

        text = f"NEWS [{ticker}] [{sentiment.upper()}]: {title}. {summary}"
        doc_id = f"news_{ticker}_{abs(hash(title)) % 1_000_000}"
        try:
            collection.upsert(
                documents=[text],
                ids=[doc_id],
                metadatas=[{"type": "news", "ticker": ticker, "sentiment": sentiment}],
            )
        except Exception as e:
            logger.warning(f"[RAG] news upsert failed: {e}")

    def add_prediction(
        self,
        ticker: str,
        direction: str,
        probability: float,
        signal: str,
    ):
        """Add a prediction result to the vector store."""
        _, collection = _get_chroma()
        if collection is None:
            return

        text = (
            f"PREDICTION [{ticker}]: Direction={direction.upper()}, "
            f"Probability={probability:.1%}, Signal={signal}. "
            f"Ensemble of LightGBM + LSTM + Transformer models."
        )
        doc_id = f"pred_{ticker}_{datetime.now().strftime('%Y%m%d%H')}"
        try:
            collection.upsert(
                documents=[text],
                ids=[doc_id],
                metadatas=[{"type": "prediction", "ticker": ticker}],
            )
        except Exception as e:
            logger.warning(f"[RAG] prediction upsert failed: {e}")

    def add_strategy_result(
        self,
        strategy: str,
        ticker: str,
        total_return: float,
        sharpe: float,
        win_rate: float,
    ):
        """Add a backtest strategy result to the vector store."""
        _, collection = _get_chroma()
        if collection is None:
            return

        text = (
            f"STRATEGY [{strategy}] on {ticker}: "
            f"Return={total_return:+.2f}%, Sharpe={sharpe:.2f}, "
            f"Win Rate={win_rate:.1f}%."
        )
        doc_id = f"strat_{ticker}_{strategy}_{datetime.now().strftime('%Y%m%d')}"
        try:
            collection.upsert(
                documents=[text],
                ids=[doc_id],
                metadatas=[{"type": "strategy", "ticker": ticker}],
            )
        except Exception as e:
            logger.warning(f"[RAG] strategy upsert failed: {e}")

    def retrieve(self, query: str, n_results: int = 5) -> List[str]:
        """
        Retrieve top-K relevant chunks for a query.
        Returns list of text chunks.
        """
        _, collection = _get_chroma()
        if collection is None:
            return []

        try:
            count = collection.count()
            if count == 0:
                return []

            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
            )
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logger.warning(f"[RAG] retrieve failed: {e}")
            return []

    def get_context_for_query(self, query: str) -> str:
        """
        Build a context string from retrieved chunks.
        Used to inject into the LLM prompt.
        """
        chunks = self.retrieve(query, n_results=5)
        if not chunks:
            return "No specific context available from the knowledge base."

        return "Relevant financial context:\n" + "\n".join(
            f"• {chunk}" for chunk in chunks
        )

    def index_count(self) -> int:
        """Return total number of indexed documents."""
        _, collection = _get_chroma()
        if collection is None:
            return 0
        try:
            return collection.count()
        except Exception:
            return 0


rag_service = RAGService()
