from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..database import get_db
from ..deps import get_current_user
from ..services.analytics import track
from ..models.account import Account
from ..models.strategy import Strategy
from ..models.trading import StrategyActivation, ActivationStatus
from ..models.user import User
from ..schemas.trading import (
    ActivateStrategyRequest,
    ActivationResponse,
    DeactivateStrategyRequest,
    NotificationSettingsUpdate,
)

router = APIRouter(prefix="/trading", tags=["trading"])


@router.post("/activate", response_model=ActivationResponse, status_code=status.HTTP_201_CREATED)
async def activate_strategy(
    req: ActivateStrategyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Activate a strategy on an account for live/sim trading."""
    # Verify strategy ownership
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == req.strategy_id,
            Strategy.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Verify account ownership
    result = await db.execute(
        select(Account).where(
            Account.id == req.account_id,
            Account.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    # Check for existing active activation
    result = await db.execute(
        select(StrategyActivation).where(
            StrategyActivation.strategy_id == req.strategy_id,
            StrategyActivation.account_id == req.account_id,
            StrategyActivation.status == ActivationStatus.ACTIVE,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Strategy already active on this account")

    activation = StrategyActivation(
        strategy_id=req.strategy_id,
        account_id=req.account_id,
        tickers=req.tickers,
        config=req.config,
        status=ActivationStatus.ACTIVE,
    )
    db.add(activation)
    await db.flush()

    track(
        settings.INGESTOR_URL, "simulation_activate",
        user_id=current_user.id,
        strategy_id=req.strategy_id,
        account_id=req.account_id,
        tickers=req.tickers,
    )
    return activation


@router.post("/deactivate")
async def deactivate_strategy(
    req: DeactivateStrategyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stop an active strategy."""
    result = await db.execute(
        select(StrategyActivation)
        .where(StrategyActivation.id == req.activation_id)
        .join(Account, Account.id == StrategyActivation.account_id)
        .where(Account.user_id == current_user.id)
    )
    activation = result.scalar_one_or_none()
    if not activation:
        raise HTTPException(status_code=404, detail="Activation not found")

    activation.status = ActivationStatus.STOPPED
    await db.flush()
    return {"message": "Strategy deactivated", "activation_id": activation.id}


@router.get("/active", response_model=list[ActivationResponse])
async def list_active_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active strategy activations for the current user."""
    result = await db.execute(
        select(StrategyActivation)
        .join(Account, Account.id == StrategyActivation.account_id)
        .where(
            Account.user_id == current_user.id,
            StrategyActivation.status == ActivationStatus.ACTIVE,
        )
    )
    return result.scalars().all()


@router.get("/settings/notifications")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
):
    """Get current user's notification preferences."""
    defaults = {
        "trade_signal": True,
        "order_filled": True,
        "daily_report": True,
        "anomaly_alert": True,
        "weekly_report": False,
        "crash_threshold": -0.05,
        "portfolio_crash_threshold": -0.10,
        "auto_sell_on_crash": False,
    }
    settings = current_user.notification_settings or {}
    return {**defaults, **settings}


@router.put("/settings/notifications")
async def update_notification_settings(
    req: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update notification preferences."""
    current_user.notification_settings = req.model_dump()
    await db.flush()
    return current_user.notification_settings
