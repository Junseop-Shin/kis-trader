from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..models.strategy import Strategy, AlgorithmType
from ..models.user import User
from ..schemas.strategy import StrategyCreate, StrategyUpdate, StrategyResponse

router = APIRouter(prefix="/strategies", tags=["strategies"])

VALID_ALGORITHM_TYPES = {e.value for e in AlgorithmType}


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    req: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.algorithm_type not in VALID_ALGORITHM_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid algorithm_type. Must be one of: {', '.join(VALID_ALGORITHM_TYPES)}",
        )

    strategy = Strategy(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        algorithm_type=AlgorithmType(req.algorithm_type),
        params=req.params,
        trade_params=req.trade_params,
        custom_code=req.custom_code,
    )
    db.add(strategy)
    await db.flush()
    return strategy


@router.get("/", response_model=list[StrategyResponse])
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Strategy).where(
            Strategy.user_id == current_user.id,
            Strategy.is_active == True,  # noqa: E712
        ).order_by(Strategy.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    req: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if req.name is not None:
        strategy.name = req.name
    if req.description is not None:
        strategy.description = req.description
    if req.params is not None:
        strategy.params = req.params
    if req.trade_params is not None:
        strategy.trade_params = req.trade_params
    if req.custom_code is not None:
        strategy.custom_code = req.custom_code

    await db.flush()
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Strategy).where(
            Strategy.id == strategy_id,
            Strategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy.is_active = False
    await db.flush()
