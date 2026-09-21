"""
M11 — AI Financial Assistant
Groq LLM (Llama 3.1 70B) + RAG (ChromaDB) + 5 financial tools.

Tools:
1. get_prediction(ticker)     → ML ensemble prediction
2. optimize_portfolio(tickers) → Markowitz optimization
3. run_backtest(ticker)        → Strategy comparison
4. get_news(ticker)            → News sentiment
5. explain_prediction(ticker)  → SHAP explanation
"""
import httpx
import json
import logging
from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime

from app.services.rag.rag_service import rag_service

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"
BACKEND_URL  = "http://localhost:8000/api/v1"

SYSTEM_PROMPT = """You are QuantAI Financial Assistant. You help users with stock analysis, portfolio management, and trading strategies.

You have these tools:
- get_prediction(ticker): ML prediction for a stock (UP/DOWN probability)
- optimize_portfolio(tickers): Markowitz portfolio optimization
- run_backtest(ticker): Compare trading strategies
- get_news(ticker): News sentiment
- explain_prediction(ticker): SHAP explanation of model decision

IMPORTANT: When a user asks about a stock or portfolio, call ONE tool at a time with a simple ticker string like "AAPL". Do not chain multiple tool calls in one response. Keep responses concise and data-driven. Always note predictions are not financial advice.

Current date: """ + datetime.now().strftime("%Y-%m-%d")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_prediction",
            "description": "Get ML ensemble prediction for a stock ticker. Returns direction (UP/DOWN), probability, confidence, and signal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker e.g. AAPL, MSFT, NVDA"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_portfolio",
            "description": "Run Markowitz portfolio optimization. Returns optimal weights, Sharpe ratio, expected return, and risk metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tickers to optimize e.g. ['AAPL', 'MSFT', 'NVDA', 'SPY']"
                    },
                    "objective": {
                        "type": "string",
                        "enum": ["sharpe", "min_vol", "max_return"],
                        "description": "Optimization objective"
                    }
                },
                "required": ["tickers"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "Compare trading strategies on a ticker. Returns ranking by Sharpe ratio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker"},
                    "days": {"type": "integer", "description": "Number of days to backtest (default 252)"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get latest news and sentiment analysis for a ticker or the market.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker or 'market' for general news"}
                },
                "required": ["ticker"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain_prediction",
            "description": "Get SHAP feature importance explaining why the model predicts UP or DOWN for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker"}
                },
                "required": ["ticker"]
            }
        }
    },
]


class AssistantService:

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    #  TOOL EXECUTION
    # ------------------------------------------------------------------ #

    async def _call_tool(self, name: str, args: Dict) -> str:
        """Execute a financial tool and return the result as a string."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                if name == "get_prediction":
                    ticker = args["ticker"].upper()
                    r = await client.get(f"{BACKEND_URL}/predict/predict/{ticker}")
                    if r.status_code == 200:
                        d = r.json()
                        result = (
                            f"Prediction for {ticker}: Direction={d.get('ensemble_direction','?').upper()}, "
                            f"Probability={d.get('ensemble_probability',0):.1%}, "
                            f"Signal={d.get('signal','?')}, "
                            f"Agreement={d.get('agreement_score',0):.1%}. "
                            f"Models: LightGBM={d.get('individual_predictions',{}).get('lightgbm',{}).get('probability',0):.1%}, "
                            f"LSTM={d.get('individual_predictions',{}).get('lstm',{}).get('probability',0):.1%}, "
                            f"Transformer={d.get('individual_predictions',{}).get('transformer',{}).get('probability',0):.1%}"
                        )
                        # Index in RAG
                        rag_service.add_prediction(
                            ticker,
                            d.get("ensemble_direction", ""),
                            d.get("ensemble_probability", 0),
                            d.get("signal", ""),
                        )
                        return result
                    return f"Could not get prediction for {ticker}: {r.status_code}"

                elif name == "optimize_portfolio":
                    tickers = [t.upper() for t in args.get("tickers", [])]
                    objective = args.get("objective", "sharpe")
                    r = await client.post(
                        f"{BACKEND_URL}/portfolio/optimize/markowitz",
                        json={"tickers": tickers, "objective": objective, "max_weight": 0.4, "days": 252},
                    )
                    if r.status_code == 200:
                        d = r.json()
                        weights = d.get("weights", {})
                        w_str = ", ".join(f"{k}={v:.1%}" for k, v in weights.items())
                        return (
                            f"Optimal portfolio ({objective}): {w_str}. "
                            f"Expected return: {d.get('expected_annual_return',0):.1f}%, "
                            f"Volatility: {d.get('annual_volatility',0):.1f}%, "
                            f"Sharpe: {d.get('sharpe_ratio',0):.2f}. "
                            f"Max drawdown: {d.get('risk_metrics',{}).get('max_drawdown',0)*100:.1f}%"
                        )
                    return f"Portfolio optimization failed: {r.status_code}"

                elif name == "run_backtest":
                    ticker = args["ticker"].upper()
                    days = args.get("days", 252)
                    r = await client.post(
                        f"{BACKEND_URL}/backtest/compare",
                        json={"ticker": ticker, "days": days},
                    )
                    if r.status_code == 200:
                        d = r.json()
                        best = d.get("best_strategy", "?")
                        ranking = d.get("ranking", [])
                        rank_str = " | ".join(
                            f"#{r['rank']} {r['strategy']}: Sharpe={r['sharpe']:.2f}"
                            for r in ranking[:3]
                        )
                        comp = d.get("comparison", {})
                        best_ret = comp.get(best, {}).get("total_return_pct", 0)
                        return (
                            f"Backtest on {ticker} ({days} days): Best strategy = {best} "
                            f"(return={best_ret:+.1f}%). Rankings: {rank_str}"
                        )
                    return f"Backtest failed: {r.status_code}"

                elif name == "get_news":
                    ticker = args.get("ticker", "market").upper()
                    r = await client.get(f"{BACKEND_URL}/news/feed?limit=5")
                    if r.status_code == 200:
                        articles = r.json().get("articles", [])
                        if ticker != "MARKET":
                            articles = [a for a in articles if ticker in a.get("title","").upper()][:3]
                        else:
                            articles = articles[:5]
                        if not articles:
                            return f"No recent news found for {ticker}"
                        news_str = " | ".join(
                            f"[{a.get('sentiment_label','?').upper()}] {a.get('title','')[:80]}"
                            for a in articles
                        )
                        return f"Recent news for {ticker}: {news_str}"
                    return "News feed unavailable"

                elif name == "explain_prediction":
                    ticker = args["ticker"].upper()
                    r = await client.get(f"{BACKEND_URL}/explain/explain/{ticker}")
                    if r.status_code == 200:
                        d = r.json()
                        shap = d.get("shap_values", {})
                        top_pos = sorted(
                            [(k, v) for k, v in shap.items() if v > 0],
                            key=lambda x: x[1], reverse=True
                        )[:3]
                        top_neg = sorted(
                            [(k, v) for k, v in shap.items() if v < 0],
                            key=lambda x: x[1]
                        )[:3]
                        pos_str = ", ".join(f"{k}(+{v:.4f})" for k, v in top_pos)
                        neg_str = ", ".join(f"{k}({v:.4f})" for k, v in top_neg)
                        explanation = d.get("explanation", "")
                        return (
                            f"SHAP explanation for {ticker}: "
                            f"Supporting UP: {pos_str}. "
                            f"Dragging DOWN: {neg_str}. "
                            f"Summary: {explanation[:200] if explanation else 'See individual SHAP values.'}"
                        )
                    return f"Could not get explanation for {ticker}"

            except Exception as e:
                logger.error(f"[Tool] {name} failed: {e}")
                return f"Tool {name} encountered an error: {str(e)}"

        return "Tool execution failed"

    # ------------------------------------------------------------------ #
    #  MAIN CHAT
    # ------------------------------------------------------------------ #

    async def chat(
        self,
        messages: List[Dict],
        user_message: str,
    ) -> Dict:
        """
        Main chat method with tool use.
        Returns assistant response + tools used.
        """
        # Get RAG context
        rag_context = rag_service.get_context_for_query(user_message)

        # Build messages
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT + f"\n\n{rag_context}"}]
        full_messages.extend(messages[-10:])  # Keep last 10 messages
        full_messages.append({"role": "user", "content": user_message})

        tools_used = []

        async with httpx.AsyncClient(timeout=60) as client:
            # First call with tools
            payload = {
                "model": GROQ_MODEL,
                "messages": full_messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "max_tokens": 800,
                "temperature": 0.3,
            }

            r = await client.post(GROQ_API_URL, headers=self.headers, json=payload)

            if r.status_code != 200:
                logger.error(f"Groq API error: {r.status_code} {r.text}")
                return {
                    "response": f"API error {r.status_code}: {r.text[:200]}",
                    "tools_used": [],
                }

            data = r.json()
            choice = data["choices"][0]
            message = choice["message"]

            # Handle tool calls
            if choice.get("finish_reason") == "tool_calls" and message.get("tool_calls"):
                tool_results = []

                for tool_call in message["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    fn_args = json.loads(tool_call["function"]["arguments"])

                    logger.info(f"[Assistant] Calling tool: {fn_name}({fn_args})")
                    result = await self._call_tool(fn_name, fn_args)

                    tools_used.append({"tool": fn_name, "args": fn_args, "result": result})

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    })

                # Second call with tool results
                full_messages.append(message)
                full_messages.extend(tool_results)

                payload2 = {
                    "model": GROQ_MODEL,
                    "messages": full_messages,
                    "max_tokens": 1000,
                    "temperature": 0.3,
                }

                r2 = await client.post(GROQ_API_URL, headers=self.headers, json=payload2)
                if r2.status_code == 200:
                    final = r2.json()["choices"][0]["message"]["content"]
                else:
                    final = message.get("content", "I encountered an error processing the tool results.")

                return {"response": final, "tools_used": tools_used}

            # Direct response (no tools needed)
            return {
                "response": message.get("content", "I couldn't generate a response."),
                "tools_used": [],
            }

    # ------------------------------------------------------------------ #
    #  QUICK ANALYSIS
    # ------------------------------------------------------------------ #

    async def quick_analysis(self, ticker: str) -> Dict:
        """
        Quick one-shot analysis of a ticker.
        Combines prediction + news + explanation.
        """
        question = f"Give me a complete analysis of {ticker}: prediction, key drivers, recent news, and your recommendation."
        result = await self.chat([], question)
        return {
            "ticker": ticker,
            "analysis": result["response"],
            "tools_used": result["tools_used"],
        }

    async def portfolio_advice(self, tickers: List[str]) -> Dict:
        """
        Portfolio advice for a list of tickers.
        """
        question = f"Optimize a portfolio with these assets: {', '.join(tickers)}. Show me the best allocation and explain why."
        result = await self.chat([], question)
        return {
            "tickers": tickers,
            "advice": result["response"],
            "tools_used": result["tools_used"],
        }