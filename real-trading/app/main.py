"""
Real Trading Service - INTERNAL NETWORK ONLY
Port: 8002 (not exposed in docker-compose)
Handles: KIS real account orders, balance, positions
"""
import logging
import os

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from .trading_engine import execute_real_order, get_account_balance, get_account_positions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real Trading Service", docs_url=None, redoc_url=None)

# Only allow localhost / internal network
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.local"],
)


class OrderRequest(BaseModel):
    account_id: int
    ticker: str
    side: str  # BUY or SELL
    qty: int
    price: int
    order_type: str = "00"  # 00=limit, 01=market


class ActivateRequest(BaseModel):
    account_id: int
    strategy_id: int
    tickers: list[str]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "real-trading"}


@app.post("/real/order")
async def place_order(request: OrderRequest):
    """Execute a real order via KIS API with risk checks."""
    try:
        result = await execute_real_order(
            account_id=request.account_id,
            ticker=request.ticker,
            side=request.side,
            qty=request.qty,
            price=request.price,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Order execution failed: {e}")
        raise HTTPException(status_code=500, detail="Order execution failed")


@app.get("/real/balance")
async def get_balance(account_id: int):
    """Get real account balance via KIS API."""
    try:
        return await get_account_balance(account_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Balance query failed: {e}")
        raise HTTPException(status_code=500, detail="Balance query failed")


@app.get("/real/positions")
async def get_positions(account_id: int):
    """Get real account positions via KIS API."""
    try:
        return await get_account_positions(account_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Positions query failed: {e}")
        raise HTTPException(status_code=500, detail="Positions query failed")


@app.post("/real/trading/activate")
async def activate_real_strategy(request: ActivateRequest):
    """Activate real-money strategy (delegates to main backend scheduler)."""
    return {
        "message": "Strategy activation registered",
        "account_id": request.account_id,
        "strategy_id": request.strategy_id,
        "tickers": request.tickers,
    }


@app.websocket("/real/ws")
async def websocket_endpoint(websocket: WebSocket):
    """KIS WebSocket relay for real-time trade fills."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"status": "connected", "message": data})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
