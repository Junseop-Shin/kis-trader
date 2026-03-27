from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models.account import Account, AccountType, Position, Order
from ..models.user import User
from ..schemas.account import (
    AccountCreate,
    AccountResponse,
    OrderResponse,
    PositionResponse,
)
from ..workers.kis_token_refresher import encrypt_value

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    req: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account = Account(
        user_id=current_user.id,
        name=req.name,
        type=AccountType(req.type),
        initial_balance=req.initial_balance,
        cash_balance=req.initial_balance,
    )

    if req.type == "REAL" and req.kis_app_key and req.kis_app_secret:
        account.kis_account_no = req.kis_account_no
        account.kis_app_key = encrypt_value(req.kis_app_key)
        account.kis_app_secret = encrypt_value(req.kis_app_secret)

    db.add(account)
    await db.flush()
    return account


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account).where(
            Account.user_id == current_user.id,
            Account.is_active == True,  # noqa: E712
        )
    )
    return result.scalars().all()


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/{account_id}/positions", response_model=list[PositionResponse])
async def get_positions(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    result = await db.execute(
        select(Position).where(Position.account_id == account_id, Position.qty > 0)
    )
    return result.scalars().all()


@router.get("/{account_id}/orders", response_model=list[OrderResponse])
async def get_orders(
    account_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    result = await db.execute(
        select(Order)
        .where(Order.account_id == account_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    await db.flush()
