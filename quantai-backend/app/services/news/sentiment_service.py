"""
M8 — Sentiment Analysis
Uses FinBERT (financial BERT) for accurate financial news sentiment.
Falls back to rule-based if transformers not available.
"""
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  FinBERT (Hugging Face)                                              #
# ------------------------------------------------------------------ #

_pipeline = None

def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from transformers import pipeline
        _pipeline = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
            device=-1,  # CPU
            top_k=None,
        )
        logger.info("[Sentiment] FinBERT loaded successfully")
    except Exception as e:
        logger.warning(f"[Sentiment] FinBERT not available: {e} — using rule-based fallback")
        _pipeline = "fallback"
    return _pipeline


# ------------------------------------------------------------------ #
#  Rule-based fallback                                                 #
# ------------------------------------------------------------------ #

POSITIVE_WORDS = [
    "surge", "soar", "rally", "gain", "rise", "jump", "beat", "exceed",
    "record", "growth", "profit", "revenue", "bullish", "upgrade", "buy",
    "strong", "positive", "outperform", "breakthrough", "partnership",
    "acquisition", "innovation", "expansion", "dividend", "buyback",
]

NEGATIVE_WORDS = [
    "fall", "drop", "decline", "loss", "miss", "below", "cut", "layoff",
    "lawsuit", "fine", "penalty", "bearish", "downgrade", "sell", "weak",
    "concern", "risk", "debt", "bankrupt", "fraud", "investigation",
    "recall", "hack", "breach", "crash", "plunge", "tumble",
]

def _rule_based_sentiment(text: str) -> Dict:
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    total = pos_count + neg_count

    if total == 0:
        return {"label": "neutral", "positive": 0.33, "negative": 0.33, "neutral": 0.34}

    pos_score = pos_count / total
    neg_score = neg_count / total
    neu_score = max(0, 1 - pos_score - neg_score)

    if pos_score > 0.6:
        label = "positive"
    elif neg_score > 0.6:
        label = "negative"
    else:
        label = "neutral"

    return {
        "label": label,
        "positive": round(pos_score, 3),
        "negative": round(neg_score, 3),
        "neutral": round(neu_score, 3),
    }


# ------------------------------------------------------------------ #
#  Sentiment Service                                                   #
# ------------------------------------------------------------------ #

class SentimentService:

    def analyze_text(self, text: str) -> Dict:
        """Analyze sentiment of a single text."""
        if not text or len(text.strip()) < 5:
            return {"label": "neutral", "positive": 0.33, "negative": 0.33, "neutral": 0.34}

        # Truncate to 512 chars (BERT limit)
        text = text[:512]

        pipe = _get_pipeline()

        if pipe == "fallback" or pipe is None:
            return _rule_based_sentiment(text)

        try:
            results = pipe(text)[0]
            scores = {r["label"].lower(): r["score"] for r in results}
            label = max(scores, key=scores.get)
            return {
                "label": label,
                "positive": round(scores.get("positive", 0), 3),
                "negative": round(scores.get("negative", 0), 3),
                "neutral": round(scores.get("neutral", 0), 3),
            }
        except Exception as e:
            logger.warning(f"FinBERT inference failed: {e}")
            return _rule_based_sentiment(text)

    def analyze_articles(self, articles: List[Dict]) -> List[Dict]:
        """Analyze sentiment for a list of articles."""
        enriched = []
        for article in articles:
            text = article.get("title", "") + " " + article.get("summary", "")
            sentiment = self.analyze_text(text)
            article["sentiment"] = sentiment["label"]
            article["sentiment_scores"] = sentiment
            article["impact_score"] = self._estimate_impact(article, sentiment)
            enriched.append(article)
        return enriched

    def _estimate_impact(self, article: Dict, sentiment: Dict) -> float:
        """
        Estimate price impact score: -1 to +1
        Based on sentiment strength + title keywords
        """
        title = article.get("title", "").lower()

        # Sentiment base
        if sentiment["label"] == "positive":
            base = sentiment["positive"]
        elif sentiment["label"] == "negative":
            base = -sentiment["negative"]
        else:
            base = 0.0

        # Amplifiers — strong words increase impact
        amplifiers = ["earnings", "revenue", "guidance", "acquisition", "merger",
                      "bankruptcy", "recall", "investigation", "beat", "miss", "record"]
        amp_factor = 1.0
        for word in amplifiers:
            if word in title:
                amp_factor = 1.4
                break

        return round(base * amp_factor, 3)

    def aggregate_sentiment(self, articles: List[Dict]) -> Dict:
        """Compute aggregate sentiment metrics for a set of articles."""
        if not articles:
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "positive_pct": 0,
                "negative_pct": 0,
                "neutral_pct": 0,
                "avg_impact": 0.0,
                "article_count": 0,
            }

        sentiments = [a.get("sentiment", "neutral") for a in articles]
        impacts = [a.get("impact_score", 0.0) for a in articles]

        pos_count = sentiments.count("positive")
        neg_count = sentiments.count("negative")
        neu_count = sentiments.count("neutral")
        total = len(sentiments)

        avg_impact = sum(impacts) / total if total > 0 else 0

        if pos_count > neg_count * 1.5:
            overall = "positive"
        elif neg_count > pos_count * 1.5:
            overall = "negative"
        else:
            overall = "neutral"

        # Sentiment score: -100 to +100
        sentiment_score = round((pos_count - neg_count) / total * 100, 1)

        return {
            "overall_sentiment": overall,
            "sentiment_score": sentiment_score,
            "positive_pct": round(pos_count / total * 100, 1),
            "negative_pct": round(neg_count / total * 100, 1),
            "neutral_pct": round(neu_count / total * 100, 1),
            "avg_impact": round(avg_impact, 3),
            "article_count": total,
        }


sentiment_service = SentimentService()
