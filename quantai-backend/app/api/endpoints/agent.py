"""
Agent Autonome — API Endpoints
Run cycle, get pending orders, accept/refuse
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.agent.trading_agent import trading_agent

router = APIRouter(tags=["Autonomous Agent"])


@router.post("/run")
async def run_agent_cycle():
    """
    **Trigger one agent cycle manually.**
    The agent analyzes all tickers and creates PENDING orders.
    """
    try:
        result = await trading_agent.run_cycle()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/pending")
async def get_pending_orders():
    """
    **Get all PENDING orders** waiting for user approval.
    The user can accept or refuse each one.
    """
    try:
        orders = await trading_agent.get_pending_orders()
        return {"orders": orders, "count": len(orders)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_all_orders(limit: int = 50):
    """Get all agent orders (all statuses)."""
    try:
        orders = await trading_agent.get_all_orders(limit)
        return {"orders": orders, "count": len(orders)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/accept")
async def accept_order(order_id: int):
    """
    **Accept an agent order** → executes immediately via Paper Trading.
    """
    try:
        result = await trading_agent.accept_order(order_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/refuse")
async def refuse_order(order_id: int):
    """
    **Refuse an agent order** → cancels without executing.
    """
    try:
        result = await trading_agent.refuse_order(order_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def agent_performance():
    """
    **Agent performance statistics.**
    Total orders, acceptance rate, buy/sell split, avg confidence.
    """
    try:
        return await trading_agent.get_performance()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health():
    return {
        "status": "ok",
        "module": "Autonomous Agent",
        "risk_management": {
            "max_position_pct": "10%",
            "stop_loss": "5%",
            "max_trades_per_day": 3,
            "min_confidence": "55%",
        },
    }
